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
import numpy as np
from typing import List, Tuple
from jetracer.nvidia_racecar import NvidiaRacecar
from yoloDet_seg import YoloTRT_Seg

# New Modules
try:
    from gamepad_control import GamepadController
except ImportError:
    GamepadController = None
    print("WARNING: gamepad_control module not found.")

try:
    from mapping_system import MapManager
except ImportError:
    MapManager = None
    print("WARNING: mapping_system module not found.")

# --- Configuration ---
SERVER_IP = "192.168.2.109" 
SERVER_URL = f"http://{SERVER_IP}:8485"
API_DISPLAY = f"{SERVER_URL}/display"
API_COMMAND = f"{SERVER_URL}/jetson_command"

IMG_SIZE = 416
MID_PIX = IMG_SIZE / 2

# Classes
CATEGORIES = ['crater', 'alien', 'water-sight']

# Driving Parameters
SPD_NORMAL = 0.22      
SPD_AVOID = 0.18       
SPD_PAUSE = 0.0        

# --- Helper Classes ---

class FrameSender:
    """Async frame sender to prevent blocking the main loop"""
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
                    requests.post(API_DISPLAY, data=data_to_send, timeout=0.15)
                except:
                    pass
            else:
                time.sleep(0.01)

    def stop(self):
        self.running = False


class YoloOutput:
    def __init__(self, cate, conf, x_min, y_min, x_max, y_max):
        self.cate = cate
        self.conf = float(conf)
        self.x_min = float(x_min)
        self.y_min = float(y_min)
        self.x_max = float(x_max)
        self.y_max = float(y_max)
        self.x_cen = (x_min + x_max) / 2
        self.y_cen = (y_min + y_max) / 2
        self.width = x_max - x_min
        self.height = y_max - y_min
        
        # Depth Estimation (Heuristic: Width)
        # Assuming typical crater is 20cm wide.
        # If it takes up 100 pixels (1/4 screen), it's close.
        # k factor needs calibration.
        self.depth_est = (self.width / IMG_SIZE) * 20.0 # Dummy cm value
    
    def to_dict(self):
        return {
            'cate': self.cate,
            'label': self.cate,
            'conf': float(self.conf),
            'box': [float(self.x_min), float(self.y_min), float(self.x_max), float(self.y_max)],
            'depth': self.depth_est
        }

class MoonRoverBrain:
    def __init__(self):
        print(">> Initializing Moon Rover Brain...")
        
        # 1. Setup Model
        self.model_path = "MR_yolov5s.engine" 
        self.lib_path = "/home/jetson/tensorrtx_moon/yolov5/build/libmyplugins.so"
        
        try:
            self.detector = YoloTRT_Seg(self.lib_path, self.model_path, conf=0.1)
            print("✓ Engine Loaded Successfully!")
        except Exception as e:
            print(f"CRITICAL WARNING: Failed to load YoloTRT ({e}). Logic running blind.")
            self.detector = None

        # 2. Setup Systems
        self.car = NvidiaRacecar()
        self.frame_sender = FrameSender()
        
        # Gamepad
        self.gamepad = None
        if GamepadController:
            self.gamepad = GamepadController()
            self.gamepad.start()
            
        # Mapping
        self.map = None
        if MapManager:
            self.map = MapManager()

        # 3. Setup Camera
        gst = ("nvarguscamerasrc sensor-id=0 ! "
               "video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12 ! "
               "nvvidconv ! video/x-raw, width=416, height=416, format=BGRx ! "
               "videoconvert ! video/x-raw,format=BGR ! "
               "appsink drop=true max-buffers=1")
        self.cam = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
        if not self.cam.isOpened():
             print("WARNING: GStreamer failed, failing back to V4L2")
             self.cam = cv2.VideoCapture(0)
             
        # 4. State
        self.is_running = False
        self.web_command = 'pause'
        self.steer_calc = 0.0
        self.throttle_val = 0.0
        self.craters = []
        
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        print("✓ System Ready")

    def cleanup(self):
        print("Cleaning up...")
        self.set_drive(0, 0)
        self.frame_sender.stop()
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
        self.car.throttle = -throttle
        self.car.steering = -steering

    def _get_web_command(self):
        try:
            # We don't want to block often, maybe do this rarely or async
            # For now simplified
            pass 
        except Exception:
            pass
        return 'run' # Default to run to allow gamepad to take over

    def detect(self, frame):
        if not self.detector: return []
        
        result = self.detector.detect(frame)
        if isinstance(result, tuple): detections, _ = result
        else: detections = result
        
        craters = []
        for d in detections:
            cls_id = int(d['clsid'])
            if cls_id >= len(CATEGORIES): continue
            label = CATEGORIES[cls_id]
            if label == 'crater':
                box = d['box']
                obj = YoloOutput(label, d['conf'], box[0], box[1], box[2], box[3])
                craters.append(obj)
        return craters

    def run(self):
        print(">> Starting Main Loop...")
        self.is_running = True
        
        frame_counter = 0
        last_time = time.time()
        
        while self.is_running:
            # Time delta for dead reckoning
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # --- 1. Perceptions ---
            ret, frame = self.cam.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_counter += 1
            
            # Detection (freq divider for performance)
            if frame_counter % 3 == 0:
                self.craters = self.detect(frame)
                
                # Update Map with new craters
                if self.map:
                    for c in self.craters:
                        # Estimate relative position (naive)
                        # We need visual odometry or homography for real accuracy.
                        # Simple: Center X -> Angle, Y-Max -> Distance
                        
                        # Normalized X (-1 to 1)
                        x_norm = (c.x_cen - MID_PIX) / MID_PIX 
                        angle_rad = x_norm * 0.8 # Approx FOV
                        
                        # Distance (1.0 at bottom, 0.0 at top)
                        y_norm = c.y_max / IMG_SIZE
                        # Inverse projection: lower y_norm (higher in image) = further away
                        # dist approx 1 / y (very rough)
                        # Let's use simple linear mapping for 2m-3m range
                        dist_m = (1.0 - y_norm) * 2.0 + 0.2 
                        
                        # Convert to Robot Local X (Forward), Y (Left)
                        rel_x = dist_m 
                        rel_y = -math.tan(angle_rad) * dist_m 
                        
                        self.map.add_unique_crater(rel_x, rel_y, c.width/1000.0, c.depth_est)

            # --- 2. Control Logic ---
            # Priority: Gamepad > Auto
            manual_active = False
            
            if self.gamepad:
                g_throt, g_steer = self.gamepad.get_drive_command()
                if abs(g_throt) > 0.05 or abs(g_steer) > 0.05:
                    manual_active = True
                    self.set_drive(g_throt, g_steer)
            
            # Auto-Avoidance (Only if no manual input)
            if not manual_active:
                # Simple P-controller from previous code
                # ... (Simplified for brevity, can restore full logic if needed)
                # For now, just stop if no gamepad
                self.set_drive(0, 0)
            
            # --- 3. Mapping ---
            if self.map:
                self.map.update_pose(self.throttle_val, -self.car.steering, dt)

            # --- 4. Telemetry ---
            if frame_counter % 6 == 0:
                _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                
                status = {}
                if self.map:
                    status = self.map.get_status_dict()
                
                craters_json = [c.to_dict() for c in self.craters]
                
                payload = {
                    'img_base64': base64.b64encode(jpg).decode(),
                    'throttle': self.throttle_val,
                    'steer_real': -self.car.steering, 
                    'craters': json.dumps(craters_json),
                    'pose': json.dumps(status.get('pose', {})),
                    'map_craters': json.dumps(status.get('craters', []))
                }
                self.frame_sender.update(payload)
                
            # Rate limit
            # time.sleep(0.01)

if __name__ == "__main__":
    bot = MoonRoverBrain()
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        bot.cleanup()
