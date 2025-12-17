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

        # 2. Setup Camera (Jetracer Config)
        gst = ("nvarguscamerasrc sensor-id=0 ! "
               "video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12 ! "
               "nvvidconv ! video/x-raw, width=416, height=416, format=BGRx ! "
               "videoconvert ! video/x-raw,format=BGR ! "
               "appsink drop=true max-buffers=1")
        
        self.cam = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
        if not self.cam.isOpened():
             print("WARNING: GStreamer failed, failing back to V4L2")
             self.cam = cv2.VideoCapture(0)
             
        # 3. State
        self.is_running = False
        self.throttle_val = 0.0
        
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

    def run(self):
        print(">> Starting Main Loop...")
        self.is_running = True
        
        frame_counter = 0
        
        while self.is_running:
            # --- 1. Driving (Priority: Gamepad) ---
            if self.gamepad:
                g_throt, g_steer = self.gamepad.get_drive_command()
                self.set_drive(g_throt, g_steer)
            else:
                self.set_drive(0, 0) # Safety stop if no gamepad logic

            # --- 2. Perceptions (Camera) ---
            ret, frame = self.cam.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_counter += 1
            
            # --- 3. Telemetry Streaming (Send to Laptop) ---
            # Send every 3rd frame (approx 10 FPS) to save bandwidth/latency
            if frame_counter % 3 == 0:
                _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                
                # Payload: Image + Rover State
                payload = {
                    'img_base64': base64.b64encode(jpg).decode(),
                    'throttle': self.throttle_val,
                    'steer_real': -self.car.steering, 
                    'racer': 'run' # Keep alive status
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
