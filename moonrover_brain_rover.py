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
SERVER_IP = "172.20.10.8" 
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

        # 2. Setup Camera (GStreamer Split Pipeline for Streaming + Capture)
        # Pipeline: Argus -> Tee -> [Queue -> H.264 Enc -> RTP -> UDP Sink] 
        #                        -> [Queue -> AppSink (for OpenCV)]
        
        # NOTE: 172.20.10.8 is the Server IP
        udp_port = 5000
        
        gst_pipeline = (
            "nvarguscamerasrc sensor-id=0 ! "
            "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1, format=NV12 ! " # High Res Source
            "tee name=t ! "
            "queue ! "
            "nvv4l2h264enc bitrate=2000000 control-rate=1 iframeinterval=30 ! " # H.264 Encode (HW)
            "rtph264pay ! "
            "udpsink host=192.168.0.104 port=5000 sync=false async=false " # Stream to Server
            "t. ! "
            "queue ! "
            "nvvidconv ! video/x-raw, width=1280, height=720, format=BGRx ! "
            "videoconvert ! video/x-raw, format=BGR ! "
            "appsink drop=true max-buffers=1" # Local Access
        )
        
        print(f">> Launching Stream to {SERVER_IP}:{udp_port}...")
        self.cam = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cam.isOpened():
             print("WARNING: GStreamer failed, failing back to V4L2 (No Streaming)")
             self.cam = cv2.VideoCapture(0)
             
        # No resize needed here anymore as we don't HTTP stream
        # But we might keep it for faster local processing if needed?
        # Actually local processing is just checking commands.
        # Recording logic uses the full frame from self.cam.read() which is 1280x720 now.
        
        # 3. State
        self.is_running = False
        self.throttle_val = 0.0
        self.steering_raw = 0.0
        self.server_throttle = 0.0
        self.server_steering = 0.0
        
        # Mission Recording
        self.recording_active = False
        self.mission_folder = None
        self.mission_frames_dir = "/tmp/mission_frames"
        self.frame_save_counter = 0

        
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
            
    def _handle_mission_recording(self, frame, mission_active, mission_folder):
        """Handle local recording of high-quality frames during mission"""
        if mission_active and mission_folder:
            # START or CONTINUE RECORDING
            if not self.recording_active:
                print(f">> Starting Mission Recording: {mission_folder}")
                self.recording_active = True
                self.mission_folder = mission_folder
                self.frame_save_counter = 0
                
                # Cleanup old temp frames
                if os.path.exists(self.mission_frames_dir):
                    import shutil
                    shutil.rmtree(self.mission_frames_dir)
                os.makedirs(self.mission_frames_dir, exist_ok=True)
            
            # Save EVERY frame (30 FPS) for best SfM quality
            ts = int(time.time() * 1000)
            filename = f"{self.mission_frames_dir}/frame_{self.frame_save_counter:05d}_{ts}.jpg"
            try:
                # Save at high quality (95) - full 1280x720 for SfM
                cv2.imwrite(filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            except Exception as e:
                print(f"Frame Save Error: {e}")
                
            self.frame_save_counter += 1
            
        elif not mission_active and self.recording_active:
            # STOP RECORDING
            print(">> Mission Ended. Stopping Recording.")
            self.recording_active = False
            
            last_folder = self.mission_folder
            self.mission_folder = None
            
            # Trigger Upload (Async)
            base_folder = last_folder if last_folder else "unknown_mission"
            threading.Thread(target=self._zip_and_upload, args=(base_folder,)).start()

    def _zip_and_upload(self, mission_folder):
        """Zip frames and upload to server"""
        import shutil
        print(">> Zipping Mission Frames...")
        try:
            # Create zip file
            zip_path = "/tmp/mission_data"
            shutil.make_archive(zip_path, 'zip', self.mission_frames_dir)
            zip_file = zip_path + ".zip"
            
            print(f">> Uploading {zip_file} to {SERVER_URL}/upload_sfm_data...")
            
            # Upload
            with open(zip_file, 'rb') as f:
                files = {'file': (f'{mission_folder}.zip', f, 'application/zip')}
                data = {'mission_folder': mission_folder}
                requests.post(f"{SERVER_URL}/upload_sfm_data", files=files, data=data, timeout=30)
                
            print(">> Upload Complete!")
        except Exception as e:
            print(f"Upload Failed: {e}")

    
    def update_server_command(self):
        """Check for server commands (driving + capture)"""
        try:
            resp = requests.get(API_COMMAND, timeout=0.1)
            data = resp.json()
            
            # Update driving command
            self.server_throttle = float(data.get('throttle', 0.0))
            self.server_steering = float(data.get('steering', 0.0))
            
            # Update mission status
            mission_active = data.get('mission_active', False)
            mission_folder = data.get('mission_folder', None)
            
            return data.get('capture', False), mission_active, mission_folder

        except:
            # Failsafe: Stop rover if communication is lost
            self.server_throttle = 0.0
            self.server_steering = 0.0
            return False, False, None

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
                capture_req, m_active, m_folder = self.update_server_command()
                
                # Handle HiRes Capture (Manual)
                if capture_req:
                    self.send_hires_capture(frame)
                    
                # Store mission state for continuous recording
                self._mission_active = m_active
                self._mission_folder = m_folder
            
            # Handle Mission Recording (on EVERY frame for better SfM)
            if hasattr(self, '_mission_active'):
                self._handle_mission_recording(frame, self._mission_active, self._mission_folder)


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
            
            # --- 4. Telemetry Streaming (Send to Laptop) ---
            # Send image via HTTP base64 for YOLO processing on server
            if frame_counter % 2 == 0:  # ~15 FPS (can go faster with smaller images)
                # Resize to 416x416 (YOLO input size) for faster transmission
                frame_small = cv2.resize(frame, (416, 416))
                
                # Encode frame to JPEG
                _, buf = cv2.imencode('.jpg', frame_small, [cv2.IMWRITE_JPEG_QUALITY, 75])
                img_b64 = base64.b64encode(buf).decode('utf-8')
                
                payload = {
                    'throttle': self.throttle_val,
                    'steer_real': self.steering_raw,
                    'racer': 'run',
                    'img_base64': img_b64
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
