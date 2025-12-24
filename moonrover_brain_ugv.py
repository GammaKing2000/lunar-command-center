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
SERVER_IP = "172.20.10.8"  # Laptop IP
SERVER_URL = f"http://{SERVER_IP}:8485"
API_TELEMETRY = f"{SERVER_URL}/display"
API_COMMAND = f"{SERVER_URL}/jetson_command"  # Server mission commands

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
        self.battery_percent = 0
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
            
            # Initialize chassis type (UGV Rover + No Module)
            # T:900, main:2 (UGV Rover), module:0 (No Module)
            self.init_chassis()
            
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

    def init_chassis(self):
        """Initialize chassis configuration."""
        # CMD_MM_TYPE_SET
        cmd = {"T": 900, "main": 2, "module": 0}
        return self.send_command(cmd)
    
    def set_chassis(self, left_speed, right_speed):
        """
        Set wheel speeds.
        left_speed, right_speed: -1.0 to 1.0 (will be scaled to m/s)
        """
        # CMD_SPEED_CTRL
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
        speed: 0-100 (will be mapped to appropriate value if needed, or sent mainly)
        
        Using CMD_GIMBAL_USER_CTRL (T:141)
        X: -1 (left), 0 (stop), 1 (right)
        Y: -1 (down), 0 (stop), 1 (up)
        SPD: Speed
        """
        # Note: Protocol log says Y=-1 is down, Y=1 is up.
        cmd = {
            "T": 141,
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
        
        Using CMD_GIMBAL_CTRL_SIMPLE (T:133)
        X: Horizontal angle
        Y: Vertical angle
        SPD: Speed (0=Fastest)
        ACC: Acceleration (0=Fastest)
        """
        # Invert speed logic if protocol requires (0 is fastest), 
        # but T:133 doc says SPD=0 is max speed.
        # Assuming 'speed' arg is meant to be direct 0-100 or 0-255 scaling?
        # The doc for CMD_GIMBAL_CTRL_SIMPLE doesn't specify SPD range clearly, just "0 means fastest".
        # Let's pass 0 for max speed if 'speed' is high? or just pass 0 for now as 'simple' control.
        # Actually, let's just pass 0 for SPD/ACC to be safe for "go to angle" behavior.
        cmd = {
            "T": 133,
            "X": pan_angle,
            "Y": tilt_angle,
            "SPD": 0, 
            "ACC": 0
        }
        return self.send_command(cmd)
    
    def center_ptz(self):
        """Reset PTZ to center position."""
        return self.set_ptz_angle(0, 0, 0)
    
    def set_leds(self, main_led=False, chassis_led=False, brightness=255):
        """
        Control LEDs.
        main_led: True/False (main spotlight) -> IO5 (usually)
        chassis_led: True/False (chassis underglow) -> IO4 (usually)
        brightness: 0-255
        
        Using CMD_LED_CTRL (T:132)
        IO4: Chassis LED? (Example says IO4/IO5)
        IO5: Main LED?
        Let's assume default mapping.
        """
        val_main = brightness if main_led else 0
        val_chassis = brightness if chassis_led else 0
        
        cmd = {
            "T": 132,
            "IO4": val_chassis,
            "IO5": val_main
        }
        return self.send_command(cmd)
    
    def stop(self):
        """Emergency stop - all motors off."""
        self.set_chassis(0, 0)
        self.set_ptz_direction(0, 0, 0)
    
    def get_feedback(self):
        """Request feedback data from ESP32."""
        # CMD_BASE_FEEDBACK (T:130)
        cmd = {"T": 130}
        self.send_command(cmd)
        
        # Read response
        try:
            if self.serial.in_waiting:
                line = self.serial.readline().decode().strip()
                if line:
                    data = json.loads(line)
                    # Mapping might be different in T:130 response
                    # Usually it returns battery voltage "v" or similar.
                    # We'll need to enable print/logging to see actual structure if unknown.
                    # For now, store whatever we get.
                    if 'v' in data:
                        self.battery_voltage = data['v']
                    elif 'battery' in data: # Some firmwares use full name
                        self.battery_voltage = data['battery']
                    
                    # Calculate percentage (3S LiPo: 12.6V max, ~9.6V min)
                    # Simple linear approx for now:
                    # 12.6V -> 100%
                    # 9.6V -> 0%
                    if self.battery_voltage > 5: # Valid reading
                        pct = int((self.battery_voltage - 9.6) / (12.6 - 9.6) * 100)
                        self.battery_percent = max(0, min(100, pct))
                        
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
        
        # 4. Setup Camera (Simple V4L2 - confirmed working on UGV)
        self.cam = None
        print("[Brain] Initializing camera...")
        self.cam = cv2.VideoCapture(-1)  # Auto-detect camera device
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        if self.cam.isOpened():
            print("[Brain] Camera (V4L2) initialized successfully")
        else:
            print("[Brain] WARNING: Camera failed to open!")
        
        # 5. State
        self.is_running = False
        self.current_left_speed = 0.0
        self.current_right_speed = 0.0
        self.main_led_state = False
        self.chassis_led_state = False
        
        # Server mission control state
        self.server_throttle = 0.0
        self.server_steering = 0.0
        self.mission_active = False
        
        # Register cleanup
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print("[Brain] System Ready!")
        print("=" * 60)
    
    def update_server_command(self):
        """Poll server for mission commands (throttle/steering)."""
        try:
            resp = requests.get(API_COMMAND, timeout=0.1)
            data = resp.json()
            
            # Update driving command
            self.server_throttle = float(data.get('throttle', 0.0))
            self.server_steering = float(data.get('steering', 0.0))
            self.mission_active = data.get('mission_active', False)
            
            return data.get('capture', False)
        except:
            # Failsafe: Stop if communication is lost during mission
            self.server_throttle = 0.0
            self.server_steering = 0.0
            return False
    
    def convert_to_differential(self, throttle, steering):
        """Convert throttle/steering to left/right wheel speeds for differential drive."""
        # Mixing: left = throttle - steering, right = throttle + steering
        # Note: For UGV, throttle is negative forward (from server)
        # Steering > 0 is Right Turn.
        # Right Turn (CW) -> Left Wheel Forward (Negative), Right Wheel Backward (Positive)
        # If Throttle=0, Steer=1:
        # Left = -0.5 (Fwd), Right = 0.5 (Back). Correct.
        left = throttle - steering * 0.5
        right = throttle + steering * 0.5
        
        # Clamp to max speed
        max_spd = 0.35
        left = max(-max_spd, min(max_spd, left))
        right = max(-max_spd, min(max_spd, right))
        
        return left, right

    def cleanup(self):
        print("\n[Brain] Cleaning up...")
        
        # Stop motors first (safety)
        try:
            if self.esp32.connected:
                self.esp32.stop()
                self.esp32.set_leds(False, False)
                self.esp32.disconnect()
        except Exception as e:
            print(f"[Brain] ESP32 cleanup error: {e}")
        
        # Stop threads
        try:
            self.telemetry.stop()
        except:
            pass
            
        try:
            if self.gamepad:
                self.gamepad.stop()
        except:
            pass
        
        # Release camera (with safety wrapper)
        try:
            if self.cam is not None:
                self.cam.release()
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"[Brain] Camera cleanup error: {e}")
        
        print("[Brain] Cleanup complete.")
    
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
        last_server_poll_time = time.time()
        
        while self.is_running:
            # --- 0. Poll Server for Mission Commands (every ~150ms) ---
            if time.time() - last_server_poll_time > 0.15:
                self.update_server_command()
                last_server_poll_time = time.time()
            
            # --- 1. Driving Control (Priority: Server Mission > Gamepad) ---
            if self.mission_active and (abs(self.server_throttle) > 0.01 or abs(self.server_steering) > 0.01):
                # SERVER MISSION MODE: Convert throttle/steering to differential drive
                left, right = self.convert_to_differential(self.server_throttle, self.server_steering)
                self.current_left_speed = left
                self.current_right_speed = right
                self.esp32.set_chassis(left, right)
                
                if frame_counter % 30 == 0:
                    print(f"[Mission] T={self.server_throttle:.2f} S={self.server_steering:.2f} -> L={left:.2f} R={right:.2f}")
                    
            elif self.gamepad:
                # GAMEPAD MODE: Manual control
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
                    
                    # PTZ control (angle-based)
                    pan_angle, tilt_angle, ptz_changed = self.gamepad.get_ptz_angles()
                    if ptz_changed:
                        self.esp32.set_ptz_angle(pan_angle, tilt_angle, 0)
                    
                    # Center PTZ (A Button)
                    if self.gamepad.should_center_ptz():
                        self.gamepad.reset_ptz_angles(0, 0)
                        self.esp32.center_ptz()

                    # Custom PTZ Reset (Y Button) -> Pan -10, Tilt 0
                    if self.gamepad.should_reset_ptz_custom():
                        self.gamepad.reset_ptz_angles(-10, 0)
                        self.esp32.set_ptz_angle(-10, 0, 0)
                    
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
            
            # --- 4. Telemetry Streaming (Send to Laptop) ---
            if frame_counter % 3 == 0:
                # Resize to 416x416 (YOLO input size) for faster transmission, matching Rover logic
                frame_small = cv2.resize(frame, (416, 416))
                
                _, jpg = cv2.imencode('.jpg', frame_small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                
                payload = {
                    'img_base64': base64.b64encode(jpg).decode(),
                    'throttle': (self.current_left_speed + self.current_right_speed) / 2,
                    'steer_real': (self.current_right_speed - self.current_left_speed),
                    'left_speed': self.current_left_speed,
                    'right_speed': self.current_right_speed,
                    'battery': self.esp32.battery_voltage,
                    'battery_percent': self.esp32.battery_percent,
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
