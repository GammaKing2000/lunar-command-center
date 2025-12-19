#!/usr/bin/env python3

import time
import threading
import cv2
import requests
import json
import base64
import signal
import os
import atexit
import math
from jetracer.nvidia_racecar import NvidiaRacecar

# New Modules
try:
    from gamepad_control import GamepadController
except ImportError:
    GamepadController = None
    print("WARNING: gamepad_control module not found.")

# --- Configuration ---
SERVER_IP = "192.168.1.8" 
SERVER_URL = f"http://{SERVER_IP}:8485"
API_TELEMETRY = f"{SERVER_URL}/display"
API_COMMAND = f"{SERVER_URL}/jetson_command"
API_HIRES_CAPTURE = f"{SERVER_URL}/hires_capture"

# Driving Parameters
SPD_NORMAL = 0.22      

# --- Helper Classes ---

class TelemetrySender:
    """Async sender to stream frame + telemetry to the Laptop"""
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
                    # Posting to the laptop server
                    requests.post(API_TELEMETRY, data=data_to_send, timeout=0.15)
                except Exception as e:
                    # print(f"Telemetry Send Error: {e}")
                    pass
            else:
                time.sleep(0.01)

    def stop(self):
        self.running = False


class MoonRoverBrain:
    def __init__(self):
        print(">> Initializing Moon Rover Brain (Lightweight Refactor)...")
        
        # 1. Setup Systems
        self.car = NvidiaRacecar()
        self.car.steering_gain = 0.65
        self.car.steering_offset = 0.3
        self.telemetry = TelemetrySender()
        
        # Gamepad (Direct Control on Rover)
        self.gamepad = None
        if GamepadController:
            self.gamepad = GamepadController()
            self.gamepad.start()
            print("✓ Gamepad Controller Started")
        else:
            print("! NO GAMEPAD FOUND. Rover is immobile without gamepad.")

        # 2. Setup Camera (Jetracer Config) - Output 720p, resize for streaming
        gst = ("nvarguscamerasrc sensor-id=0 ! "
               "video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12 ! "
               "nvvidconv ! video/x-raw, width=1280, height=720, format=BGRx ! "
               "videoconvert ! video/x-raw,format=BGR ! "
               "appsink drop=true max-buffers=1")
        
        self.cam = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
        if not self.cam.isOpened():
             print("WARNING: GStreamer failed, failing back to V4L2")
             self.cam = cv2.VideoCapture(0)
        
        # Stream resolution (resize from 720p for bandwidth)
        self.stream_size = (416, 416)
             
        # 3. State
        # 3. State
        self.is_running = False
        self.throttle_val = 0.0
        self.steering_raw = 0.0
        self.server_throttle = 0.0
        self.server_steering = 0.0
        
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        print("✓ System Ready. Waiting for Gamepad Input...")

    def cleanup(self):
        print("Cleaning up...")
        self.set_drive(0, 0)
        self.telemetry.stop()
        if self.gamepad: 
            self.gamepad.stop()
        if self.cam.isOpened():
            self.cam.release()
            
    def _signal_handler(self, sig, frame):
        self.is_running = False
        self.cleanup()
        os._exit(0)

    def set_drive(self, throttle, steering):
        steering = max(-1.0, min(1.0, steering))
        throttle = max(-1.0, min(1.0, throttle))
        self.throttle_val = throttle
        self.car.throttle = throttle  # No negation - negative values go forward
        self.car.steering = -steering
    
    def send_hires_capture(self, frame):
        """Send a high-res frame to the server"""
        try:
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            payload = {'hires_image': base64.b64encode(jpg).decode()}
            requests.post(API_HIRES_CAPTURE, data=payload, timeout=2.0)
            print(">> HiRes Capture Sent!")
        except Exception as e:
            print(f"HiRes Capture Error: {e}")
    
    def update_server_command(self):
        """Check for server commands (driving + capture)"""
        try:
            resp = requests.get(API_COMMAND, timeout=0.1)
            data = resp.json()
            
            # Update driving command
            self.server_throttle = float(data.get('throttle', 0.0))
            self.server_steering = float(data.get('steering', 0.0))
            
            return data.get('capture', False)
        except:
            # Failsafe: Stop rover if communication is lost
            self.server_throttle = 0.0
            self.server_steering = 0.0
            return False

    def run(self):
        print(">> Starting Main Loop...")
        self.is_running = True
        
        frame_counter = 0
        
        while self.is_running:
            # --- 1. Perceptions (Camera) ---
            ret, frame = self.cam.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_counter += 1

            # --- 2. Update Remote Command (Server) ---
            if frame_counter % 5 == 0: # Check every 5 frames (~6Hz)
                if self.update_server_command():
                    self.send_hires_capture(frame)

            # --- 3. Driving Logic ---
            # Priority: Server Mission > Gamepad
            if abs(self.server_throttle) > 0.05 or abs(self.server_steering) > 0.05:
                 # Server is commanding movement (Mission Mode)
                 self.set_drive(self.server_throttle, self.server_steering)
                 self.steering_raw = self.server_steering
                 if frame_counter % 30 == 0: # Log less frequently
                    print(f"Mission Control: Spd={self.server_throttle:.2f} Str={self.server_steering:.2f}")
            elif self.gamepad:
                g_throt, g_steer = self.gamepad.get_drive_command()
                self.set_drive(g_throt, g_steer)
                self.steering_raw = g_steer
            else:
                self.set_drive(0, 0)
                self.steering_raw = 0.0
            
            # --- 3. Telemetry Streaming (Send to Laptop) ---
            # Resize to 416x416 for streaming
            stream_frame = cv2.resize(frame, self.stream_size)
            
            # Send every frame
            if frame_counter % 1 == 0:
                _, jpg = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                
                # Payload: Image + Rover State
                payload = {
                    'img_base64': base64.b64encode(jpg).decode(),
                    'throttle': self.throttle_val,
                    'steer_real': self.steering_raw,
                    'racer': 'run'
                }
                self.telemetry.update(payload)
                
            # Loop Rate
            time.sleep(0.005)

if __name__ == "__main__":
    bot = MoonRoverBrain()
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        bot.cleanup()
