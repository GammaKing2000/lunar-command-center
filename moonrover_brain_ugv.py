#!/usr/bin/env python3
"""
UGV Beast PT Brain Controller
Waveshare UGV Beast PT with Jetson Orin Nano

Communicates with ESP32 sub-controller via GPIO UART using JSON commands.
Streams video to laptop server for AI processing.

JSON Command Reference (ESP32):
- Chassis: {"T":1,"L":<speed>,"R":<speed>}
- PTZ Move: {"T":201,"X":<-1/0/1>,"Y":<-1/0/1>,"SPD":<0-100>}
- PTZ Angle: {"T":202,"X":<angle>,"Y":<angle>,"SPD":<speed>}
- LED Control: {"T":301,"SW1":<0/1>,"SW2":<0/1>,"BR":<0-100>}
- Get Feedback: {"T":901}
"""

import time
import threading
import json
import serial
import cv2
import requests
import base64
import signal
import os
import atexit

# Import UGV Gamepad Controller
try:
    from gamepad_control_ugv import UGVGamepadController
except ImportError:
    UGVGamepadController = None
    print("WARNING: gamepad_control_ugv module not found.")

# --- Configuration ---
SERVER_IP = "192.168.1.8"  # Laptop IP
SERVER_URL = f"http://{SERVER_IP}:8485"
API_TELEMETRY = f"{SERVER_URL}/display"

# Serial port to ESP32 (GPIO UART)
SERIAL_PORT = "/dev/ttyTHS1"  # Jetson Orin GPIO UART
SERIAL_BAUD = 115200

# Camera settings
CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480


class ESP32Controller:
    """
    Handles serial communication with ESP32 sub-controller.
    Sends JSON commands and receives feedback.
    """
    
    def __init__(self, port=SERIAL_PORT, baud=SERIAL_BAUD):
        self.port = port
        self.baud = baud
        self.serial = None
        self.connected = False
        self.lock = threading.Lock()
        
        # State cache
        self.battery_voltage = 0.0
        self.encoder_left = 0
        self.encoder_right = 0
        self.imu_data = {}
        
    def connect(self):
        """Open serial connection to ESP32."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=0.1
            )
            self.connected = True
            print(f"[ESP32] Connected to {self.port}")
            return True
        except Exception as e:
            print(f"[ESP32] Failed to connect: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
    
    def send_command(self, cmd_dict):
        """Send a JSON command to ESP32."""
        if not self.connected:
            return False
        
        try:
            with self.lock:
                cmd_json = json.dumps(cmd_dict) + "\n"
                self.serial.write(cmd_json.encode())
                self.serial.flush()
            return True
        except Exception as e:
            print(f"[ESP32] Send error: {e}")
            return False
    
    def set_chassis(self, left_speed, right_speed):
        """
        Set wheel speeds.
        left_speed, right_speed: -1.0 to 1.0 (will be scaled to m/s)
        """
        # Scale to actual speed (max 0.35 m/s for UGV Beast)
        cmd = {
            "T": 1,
            "L": round(left_speed, 3),
            "R": round(right_speed, 3)
        }
        return self.send_command(cmd)
    
    def set_ptz_direction(self, pan, tilt, speed=50):
        """
        Set PTZ pan/tilt direction.
        pan: -1 (left), 0 (stop), 1 (right)
        tilt: -1 (down), 0 (stop), 1 (up)
        speed: 0-100
        """
        cmd = {
            "T": 201,
            "X": pan,
            "Y": tilt,
            "SPD": speed
        }
        return self.send_command(cmd)
    
    def set_ptz_angle(self, pan_angle, tilt_angle, speed=50):
        """
        Set PTZ to specific angles.
        pan_angle: -180 to +180
        tilt_angle: -45 to +90
        """
        cmd = {
            "T": 202,
            "X": pan_angle,
            "Y": tilt_angle,
            "SPD": speed
        }
        return self.send_command(cmd)
    
    def center_ptz(self):
        """Reset PTZ to center position."""
        return self.set_ptz_angle(0, 0, 80)
    
    def set_leds(self, main_led=False, chassis_led=False, brightness=50):
        """
        Control LEDs.
        main_led: True/False (main spotlight)
        chassis_led: True/False (chassis underglow)
        brightness: 0-100
        """
        cmd = {
            "T": 301,
            "SW1": 1 if chassis_led else 0,
            "SW2": 1 if main_led else 0,
            "BR": brightness
        }
        return self.send_command(cmd)
    
    def stop(self):
        """Emergency stop - all motors off."""
        self.set_chassis(0, 0)
        self.set_ptz_direction(0, 0, 0)
    
    def get_feedback(self):
        """Request feedback data from ESP32."""
        cmd = {"T": 901}
        self.send_command(cmd)
        
        # Read response
        try:
            if self.serial.in_waiting:
                line = self.serial.readline().decode().strip()
                if line:
                    data = json.loads(line)
                    self.battery_voltage = data.get('battery', 0)
                    return data
        except:
            pass
        return None


class TelemetrySender:
    """Async sender to stream telemetry to the Laptop server."""
    
    def __init__(self):
        self.latest_data = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def update(self, data):
        with self.lock:
            self.latest_data = data
    
    def _run_loop(self):
        while self.running:
            data_to_send = None
            with self.lock:
                if self.latest_data:
                    data_to_send = self.latest_data
                    self.latest_data = None
            
            if data_to_send:
                try:
                    requests.post(API_TELEMETRY, data=data_to_send, timeout=0.2)
                except Exception as e:
                    pass
            else:
                time.sleep(0.01)

    def stop(self):
        self.running = False


class UGVBrain:
    """
    Main controller for UGV Beast PT.
    Integrates gamepad, ESP32, camera, and telemetry.
    """
    
    def __init__(self):
        print("=" * 60)
        print("UGV BEAST PT BRAIN CONTROLLER")
        print("=" * 60)
        
        # 1. Setup ESP32 Controller
        self.esp32 = ESP32Controller()
        if not self.esp32.connect():
            print("WARNING: ESP32 not connected. Running in simulation mode.")
        
        # 2. Setup Telemetry Sender
        self.telemetry = TelemetrySender()
        
        # 3. Setup Gamepad
        self.gamepad = None
        if UGVGamepadController:
            self.gamepad = UGVGamepadController()
            self.gamepad.start()
            print("[Brain] Gamepad controller started")
        else:
            print("[Brain] WARNING: No gamepad available!")
        
        # 4. Setup Camera
        self.cam = None
        try:
            # Try GStreamer pipeline for Jetson
            gst = (
                f"nvarguscamerasrc sensor-id={CAMERA_ID} ! "
                f"video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12 ! "
                f"nvvidconv ! video/x-raw,width={FRAME_WIDTH},height={FRAME_HEIGHT},format=BGRx ! "
                "videoconvert ! video/x-raw,format=BGR ! "
                "appsink drop=true max-buffers=1"
            )
            self.cam = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
            
            if not self.cam.isOpened():
                raise Exception("GStreamer failed")
                
            print("[Brain] Camera (GStreamer) initialized")
        except:
            # Fallback to V4L2
            self.cam = cv2.VideoCapture(CAMERA_ID)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            print("[Brain] Camera (V4L2) initialized")
        
        # 5. State
        self.is_running = False
        self.current_left_speed = 0.0
        self.current_right_speed = 0.0
        self.main_led_state = False
        self.chassis_led_state = False
        
        # Register cleanup
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print("[Brain] System Ready!")
        print("=" * 60)

    def cleanup(self):
        print("\n[Brain] Cleaning up...")
        
        # Stop motors
        if self.esp32.connected:
            self.esp32.stop()
            self.esp32.set_leds(False, False)
            self.esp32.disconnect()
        
        # Stop threads
        self.telemetry.stop()
        if self.gamepad:
            self.gamepad.stop()
        
        # Release camera
        if self.cam and self.cam.isOpened():
            self.cam.release()
    
    def _signal_handler(self, sig, frame):
        self.is_running = False
        self.cleanup()
        os._exit(0)

    def run(self):
        """Main control loop."""
        print("[Brain] Starting main loop...")
        self.is_running = True
        
        frame_counter = 0
        last_feedback_time = time.time()
        
        while self.is_running:
            # --- 1. Read Gamepad & Control Chassis ---
            if self.gamepad:
                # Emergency stop check
                if self.gamepad.is_emergency_stop():
                    self.esp32.stop()
                    self.current_left_speed = 0
                    self.current_right_speed = 0
                else:
                    # Chassis control
                    left, right = self.gamepad.get_chassis_command()
                    self.current_left_speed = left
                    self.current_right_speed = right
                    self.esp32.set_chassis(left, right)
                    
                    # PTZ control
                    pan, tilt, ptz_spd = self.gamepad.get_ptz_command()
                    self.esp32.set_ptz_direction(pan, tilt, ptz_spd)
                    
                    # Center PTZ
                    if self.gamepad.should_center_ptz():
                        self.esp32.center_ptz()
                    
                    # LED control (only send on change)
                    main_led, chassis_led = self.gamepad.get_led_state()
                    if main_led != self.main_led_state or chassis_led != self.chassis_led_state:
                        self.esp32.set_leds(main_led, chassis_led)
                        self.main_led_state = main_led
                        self.chassis_led_state = chassis_led
            
            # --- 2. Capture Camera Frame ---
            ret, frame = self.cam.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            frame_counter += 1
            
            # --- 3. Get ESP32 Feedback (periodically) ---
            if time.time() - last_feedback_time > 1.0:
                feedback = self.esp32.get_feedback()
                last_feedback_time = time.time()
            
            # --- 4. Send Telemetry to Laptop (every 3rd frame) ---
            if frame_counter % 3 == 0:
                _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                
                payload = {
                    'img_base64': base64.b64encode(jpg).decode(),
                    'throttle': (self.current_left_speed + self.current_right_speed) / 2,
                    'steer_real': (self.current_right_speed - self.current_left_speed),
                    'left_speed': self.current_left_speed,
                    'right_speed': self.current_right_speed,
                    'battery': self.esp32.battery_voltage,
                    'main_led': self.main_led_state,
                    'chassis_led': self.chassis_led_state,
                    'racer': 'run'
                }
                self.telemetry.update(payload)
            
            # Loop rate control
            time.sleep(0.01)


if __name__ == "__main__":
    brain = UGVBrain()
    try:
        brain.run()
    except KeyboardInterrupt:
        pass
    finally:
        brain.cleanup()
