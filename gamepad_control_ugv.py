"""
UGV Beast PT Gamepad Controller
Waveshare UGV Beast PT with Jetson Orin Nano

Controller Mapping:
- Left Stick X/Y: Chassis movement (differential drive)
- Right Stick X/Y: PTZ Camera Pan/Tilt
- LT/RT: Speed limiter
- D-Pad Up/Down: Main LED toggle
- D-Pad Left/Right: Chassis LED toggle
- A Button: Center PTZ
- B Button: Emergency Stop
- X Button: Auto-stabilize camera (toggle)
- Y Button: Horn/Buzzer

Supports: XInput (Windows), direct /dev/input/js0 (Linux)
"""

import threading
import time
import math

# Try XInput first (Windows), fallback to inputs (Linux)
HAS_XINPUT = False
HAS_INPUTS = False

try:
    import XInput
    HAS_XINPUT = True
except (ImportError, OSError):
    pass

if not HAS_XINPUT:
    try:
        from inputs import get_gamepad, devices
        HAS_INPUTS = True
    except ImportError:
        pass


class UGVGamepadController:
    """
    Gamepad controller for Waveshare UGV Beast PT.
    Outputs commands for chassis, PTZ, and accessories.
    """
    
    def __init__(self, deadzone=0.15, max_speed=0.35):
        # Movement state
        self.left_wheel = 0.0  # -1.0 to 1.0
        self.right_wheel = 0.0
        
        # PTZ state
        self.pan_direction = 0   # -1 (left), 0 (stop), 1 (right)
        self.tilt_direction = 0  # -1 (down), 0 (stop), 1 (up)
        self.ptz_speed = 50      # 0-100
        
        # Accessory state
        self.main_led = False
        self.chassis_led = False
        self.center_ptz = False  # One-shot trigger
        self.emergency_stop = False
        self.stabilize_camera = False
        self.horn = False
        
        # Config
        self.deadzone = deadzone
        self.max_speed = max_speed  # m/s (UGV max is 0.35)
        self.speed_multiplier = 1.0  # Controlled by triggers
        
        # Raw inputs
        self._lx = 0.0
        self._ly = 0.0
        self._rx = 0.0
        self._ry = 0.0
        self._lt = 0.0
        self._rt = 0.0
        
        # Button states (for edge detection)
        self._buttons = {}
        self._prev_buttons = {}
        
        # Thread control
        self.running = False
        self.thread = None
        
        # Detect library
        if HAS_XINPUT:
            print("[UGV Gamepad] Using XInput (Windows)")
        elif HAS_INPUTS:
            print("[UGV Gamepad] Using inputs library (Linux)")
        else:
            print("[UGV Gamepad] WARNING: No gamepad library!")

    def start(self):
        """Start the input reading thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[UGV Gamepad] Controller thread started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def get_chassis_command(self):
        """
        Returns (left_speed, right_speed) in m/s
        Uses differential drive: left stick controls arcade-style
        """
        # Arcade drive mixing
        forward = self._ly * self.max_speed * self.speed_multiplier
        turn = self._lx * self.max_speed * self.speed_multiplier * 0.7
        
        left = forward + turn
        right = forward - turn
        
        # Clamp to max speed
        left = max(-self.max_speed, min(self.max_speed, left))
        right = max(-self.max_speed, min(self.max_speed, right))
        
        return left, right

    def get_ptz_command(self):
        """
        Returns (pan_dir, tilt_dir, speed)
        pan_dir: -1 (left), 0 (stop), 1 (right)
        tilt_dir: -1 (down), 0 (stop), 1 (up)
        """
        # Convert analog to direction
        pan = 0
        if self._rx > 0.5:
            pan = 1
        elif self._rx < -0.5:
            pan = -1
            
        tilt = 0
        if self._ry > 0.5:
            tilt = 1
        elif self._ry < -0.5:
            tilt = -1
        
        # Speed based on stick magnitude
        speed = int(max(abs(self._rx), abs(self._ry)) * 100)
        speed = max(20, min(100, speed))  # Clamp 20-100
        
        return pan, tilt, speed

    def get_led_state(self):
        """Returns (main_led_on, chassis_led_on)"""
        return self.main_led, self.chassis_led

    def should_center_ptz(self):
        """Returns True once when A button pressed (one-shot)"""
        if self.center_ptz:
            self.center_ptz = False
            return True
        return False

    def is_emergency_stop(self):
        """Returns True if B button held"""
        return self.emergency_stop

    def _run_loop(self):
        if HAS_XINPUT:
            self._run_xinput_loop()
        elif HAS_INPUTS:
            self._run_linux_loop()
        else:
            print("[UGV Gamepad] ERROR: No gamepad library!")

    def _run_xinput_loop(self):
        """XInput-based loop for Windows"""
        while self.running:
            try:
                state = XInput.get_state(0)
                gp = state.Gamepad
                
                # Sticks (normalized -1 to 1)
                self._lx = self._apply_deadzone(gp.sThumbLX / 32767.0)
                self._ly = self._apply_deadzone(gp.sThumbLY / 32767.0)
                self._rx = self._apply_deadzone(gp.sThumbRX / 32767.0)
                self._ry = self._apply_deadzone(gp.sThumbRY / 32767.0)
                
                # Triggers (normalized 0 to 1)
                self._lt = gp.bLeftTrigger / 255.0
                self._rt = gp.bRightTrigger / 255.0
                
                # Speed multiplier: RT = boost, LT = slow
                self.speed_multiplier = 0.5 + (self._rt * 0.5) - (self._lt * 0.3)
                self.speed_multiplier = max(0.2, min(1.0, self.speed_multiplier))
                
                # Buttons (using XInput button masks)
                buttons = gp.wButtons
                
                # D-Pad toggle LEDs (edge detection)
                if self._button_pressed(buttons, 0x0001):  # D-Pad Up
                    self.main_led = not self.main_led
                if self._button_pressed(buttons, 0x0002):  # D-Pad Down
                    self.main_led = not self.main_led
                if self._button_pressed(buttons, 0x0004):  # D-Pad Left
                    self.chassis_led = not self.chassis_led
                if self._button_pressed(buttons, 0x0008):  # D-Pad Right
                    self.chassis_led = not self.chassis_led
                
                # A Button = Center PTZ
                if self._button_pressed(buttons, 0x1000):
                    self.center_ptz = True
                
                # B Button = Emergency Stop (held)
                self.emergency_stop = bool(buttons & 0x2000)
                
                # X Button = Toggle stabilization
                if self._button_pressed(buttons, 0x4000):
                    self.stabilize_camera = not self.stabilize_camera
                
                # Y Button = Horn (held)
                self.horn = bool(buttons & 0x8000)
                
                self._prev_buttons = buttons
                time.sleep(0.02)
                
            except Exception as e:
                time.sleep(0.5)

    def _run_linux_loop(self):
        """Direct joystick read for Linux"""
        import os
        import struct
        
        if not os.path.exists('/dev/input/js0'):
            print("[UGV Gamepad] ERROR: /dev/input/js0 not found!")
            return
        
        JS_EVENT_SIZE = 8
        JS_EVENT_BUTTON = 0x01
        JS_EVENT_AXIS = 0x02
        
        try:
            with open('/dev/input/js0', 'rb') as js:
                while self.running:
                    event = js.read(JS_EVENT_SIZE)
                    if event:
                        _, value, ev_type, number = struct.unpack('IhBB', event)
                        
                        if ev_type & JS_EVENT_AXIS:
                            normalized = value / 32767.0
                            
                            if number == 0:  # Left Stick X
                                self._lx = self._apply_deadzone(normalized)
                            elif number == 1:  # Left Stick Y (inverted)
                                self._ly = self._apply_deadzone(-normalized)
                            elif number == 3:  # Right Stick X
                                self._rx = self._apply_deadzone(normalized)
                            elif number == 4:  # Right Stick Y (inverted)
                                self._ry = self._apply_deadzone(-normalized)
                            elif number == 2:  # Left Trigger
                                self._lt = (normalized + 1.0) / 2.0
                            elif number == 5:  # Right Trigger
                                self._rt = (normalized + 1.0) / 2.0
                                
                            # Update speed multiplier
                            self.speed_multiplier = 0.5 + (self._rt * 0.5) - (self._lt * 0.3)
                            self.speed_multiplier = max(0.2, min(1.0, self.speed_multiplier))
                        
                        elif ev_type & JS_EVENT_BUTTON:
                            btn_name = f"btn_{number}"
                            was_pressed = self._buttons.get(btn_name, 0)
                            self._buttons[btn_name] = value
                            
                            # Edge detection (button just pressed)
                            if value == 1 and was_pressed == 0:
                                if number == 0:  # A
                                    self.center_ptz = True
                                elif number == 2:  # X
                                    self.stabilize_camera = not self.stabilize_camera
                                elif number == 11:  # D-Pad Up
                                    self.main_led = not self.main_led
                                elif number == 12:  # D-Pad Down
                                    self.main_led = not self.main_led
                                elif number == 13:  # D-Pad Left
                                    self.chassis_led = not self.chassis_led
                                elif number == 14:  # D-Pad Right
                                    self.chassis_led = not self.chassis_led
                            
                            # Held buttons
                            if number == 1:  # B = Emergency Stop
                                self.emergency_stop = bool(value)
                            elif number == 3:  # Y = Horn
                                self.horn = bool(value)
                                
        except Exception as e:
            print(f"[UGV Gamepad] Error: {e}")

    def _apply_deadzone(self, val):
        if abs(val) < self.deadzone:
            return 0.0
        return val

    def _button_pressed(self, current, mask):
        """Check if button was just pressed (edge detection)"""
        was_pressed = bool(self._prev_buttons & mask) if hasattr(self, '_prev_buttons') and isinstance(self._prev_buttons, int) else False
        is_pressed = bool(current & mask)
        return is_pressed and not was_pressed


# Test mode
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("UGV BEAST PT GAMEPAD TEST")
    print("=" * 60)
    
    controller = UGVGamepadController()
    controller.start()
    
    print("\nControls:")
    print("  Left Stick  : Drive (arcade style)")
    print("  Right Stick : PTZ Camera")
    print("  LT/RT       : Slow/Boost")
    print("  D-Pad U/D   : Toggle Main LED")
    print("  D-Pad L/R   : Toggle Chassis LED")
    print("  A           : Center PTZ")
    print("  B           : Emergency Stop")
    print("  X           : Toggle Stabilize")
    print("  Y           : Horn")
    print("\nPress Ctrl+C to exit\n")
    
    try:
        while True:
            left, right = controller.get_chassis_command()
            pan, tilt, ptz_spd = controller.get_ptz_command()
            main_led, chassis_led = controller.get_led_state()
            
            status = f"Wheels: L={left:+.2f} R={right:+.2f} | "
            status += f"PTZ: P={pan:+d} T={tilt:+d} | "
            status += f"LED: M={'ON' if main_led else 'off'} C={'ON' if chassis_led else 'off'} | "
            status += f"E-STOP: {'!!!' if controller.is_emergency_stop() else 'ok'}"
            
            print(status, end='\r')
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
        controller.stop()
