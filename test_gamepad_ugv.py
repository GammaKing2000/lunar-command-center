#!/usr/bin/env python3
"""
UGV Gamepad Test Script
Simple test script to control UGV with gamepad and debug inputs.

Run: sudo python3 test_gamepad_ugv.py
"""

import time
import json
import serial
import threading

# --- Configuration ---
SERIAL_PORT = "/dev/ttyTHS1"
SERIAL_BAUD = 115200

# --- ESP32 Controller (Minimal) ---
class ESP32Controller:
    def __init__(self, port=SERIAL_PORT, baud=SERIAL_BAUD):
        self.serial = None
        self.connected = False
        self.lock = threading.Lock()
        
    def connect(self):
        try:
            self.serial = serial.Serial(port=SERIAL_PORT, baudrate=SERIAL_BAUD, timeout=0.1)
            self.connected = True
            print(f"[ESP32] Connected to {SERIAL_PORT}")
            # Init chassis type
            self.send_command({"T": 900, "main": 2, "module": 0})
            return True
        except Exception as e:
            print(f"[ESP32] Failed to connect: {e}")
            return False
    
    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
    
    def send_command(self, cmd_dict):
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
    
    def set_chassis(self, left, right):
        return self.send_command({"T": 1, "L": round(left, 3), "R": round(right, 3)})
    
    def gimbal_ctrl(self, pan_angle, tilt_angle, speed=0, acc=0):
        """Control gimbal with absolute angles (matching Waveshare API)"""
        return self.send_command({
            "T": 133,
            "X": round(pan_angle),
            "Y": round(tilt_angle),
            "SPD": speed,
            "ACC": acc
        })
    
    def set_leds(self, main_on, chassis_on, brightness=255):
        return self.send_command({
            "T": 132,
            "IO4": brightness if chassis_on else 0,
            "IO5": brightness if main_on else 0
        })
    
    def stop(self):
        self.set_chassis(0, 0)


# --- Gamepad Import ---
try:
    from gamepad_control_ugv import UGVGamepadController
    HAS_GAMEPAD = True
except ImportError:
    HAS_GAMEPAD = False
    print("ERROR: gamepad_control_ugv.py not found!")


# --- Main Test Loop ---
if __name__ == "__main__":
    print("=" * 60)
    print("UGV GAMEPAD TEST - Direct Control (PTZ Angle Mode)")
    print("=" * 60)
    
    if not HAS_GAMEPAD:
        print("Cannot run without gamepad_control_ugv.py")
        exit(1)
    
    # Connect ESP32
    esp32 = ESP32Controller()
    if not esp32.connect():
        print("WARNING: Running without ESP32 (commands won't be sent)")
    
    # Start Gamepad
    gamepad = UGVGamepadController()
    gamepad.start()
    
    print("\nControls:")
    print("  R2 (RT)     : Throttle (Forward)")
    print("  L2 (LT)     : Reverse/Brake")
    print("  Left Stick X: Steering")
    print("  Right Stick : PTZ Camera (Angle Mode)")
    print("  D-Pad       : Toggle LEDs")
    print("  A           : Center PTZ (0, 0)")
    print("  Y           : Custom PTZ (-10, 0)")
    print("  B           : Emergency Stop (hold)")
    print("\nPress Ctrl+C to exit\n")
    
    try:
        frame = 0
        last_ptz_pan = 0
        last_ptz_tilt = 0
        
        while True:
            frame += 1
            
            # Get gamepad state
            left, right = gamepad.get_chassis_command()
            pan_angle, tilt_angle, ptz_changed = gamepad.get_ptz_angles()
            main_led, chassis_led = gamepad.get_led_state()
            e_stop = gamepad.is_emergency_stop()
            
            # Send commands to ESP32
            if e_stop:
                esp32.stop()
                left = right = 0
            else:
                esp32.set_chassis(left, right)
                
                # Only send PTZ command when angles actually change
                if ptz_changed:
                    esp32.gimbal_ctrl(pan_angle, tilt_angle, speed=0, acc=0)
                
                # Handle PTZ centering (A button)
                if gamepad.should_center_ptz():
                    gamepad.reset_ptz_angles(0, 0)
                    esp32.gimbal_ctrl(0, 0, speed=0, acc=0)
                    print("[PTZ] Centering (0, 0)!")
                    
                # Handle custom PTZ reset (Y button)
                if gamepad.should_reset_ptz_custom():
                    gamepad.reset_ptz_angles(-10, 0)
                    esp32.gimbal_ctrl(-10, 0, speed=0, acc=0)
                    print("[PTZ] Custom Reset (-10, 0)!")
                
                # LED control
                esp32.set_leds(main_led, chassis_led)
            
            # Print status every 10 frames
            if frame % 10 == 0:
                status = f"L={left:+.2f} R={right:+.2f} | "
                status += f"PTZ Pan={pan_angle:+.0f}° Tilt={tilt_angle:+.0f}° | "
                status += f"LED M={'ON' if main_led else 'off'} C={'ON' if chassis_led else 'off'} | "
                status += f"E-STOP: {'!!!' if e_stop else 'ok'}"
                print(status)
            
            time.sleep(0.02)  # 50 Hz
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        esp32.stop()
        esp32.set_leds(False, False)
        esp32.disconnect()
        gamepad.stop()
        print("Done.")
