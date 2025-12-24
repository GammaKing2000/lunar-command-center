"""
UGV Beast PT Gamepad Controller
Waveshare UGV Beast PT with Jetson Orin Nano

Controller Mapping:
- Left Stick X: Steering
- R2 (RT): Throttle (Forward)
- L2 (LT): Brake/Reverse
- Right Stick X/Y: PTZ Camera Pan/Tilt
- D-Pad Up/Down: Main LED toggle
- D-Pad Left/Right: Chassis LED toggle
- A Button: Center PTZ
- B Button: Emergency Stop
- X Button: Auto-stabilize camera (toggle)
- Y Button: Custom Reset PTZ (-10, 0)

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
        
        # PTZ state (Angle-based control)
        self.ptz_pan_angle = 0.0    # Current target pan angle (-180 to +180)
        self.ptz_tilt_angle = 0.0   # Current target tilt angle (-45 to +90)
        self._ptz_changed = False    # Flag to track if PTZ needs update
        
        # Accessory state
        self.main_led = False
        self.chassis_led = False
        self.center_ptz = False  # One-shot trigger
        self.custom_ptz_reset = False # One-shot trigger (Y button)
        self.emergency_stop = False
        self.stabilize_camera = False
        self.horn = False # Removed/Unused for now
        
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
        print("[UGV Gamepad] Controller thread started (v1.2 Racing+Fallback)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def get_chassis_command(self):
        """
        Returns (left_speed, right_speed) in m/s
        Racing Style:
        - R2 (RT): Accel/Forward
        - L2 (LT): Brake/Reverse
        - Left Stick X: Steering
        """
        # Calculate net linear speed from triggers (0.0 to 1.0)
        # RT is forward, LT is reverse
        # INVERTED: Swap sign to fix direction
        net_throttle = -(self._rt - self._lt)
        
        # Base linear velocity
        linear_v = net_throttle * self.max_speed
        
        # Steering from Left Stick X (-1.0 to 1.0)
        # INVERTED: Swap sign to fix direction
        turn_v = -self._lx * self.max_speed * 0.7
        
        left = linear_v + turn_v
        right = linear_v - turn_v
        
        # Clamp to max speed
        left = max(-self.max_speed, min(self.max_speed, left))
        right = max(-self.max_speed, min(self.max_speed, right))
        
        return left, right

    def get_ptz_angles(self):
        """
        Returns (pan_angle, tilt_angle, changed)
        Uses right stick to adjust PTZ angles incrementally.
        pan_angle: -180 to +180
        tilt_angle: -45 to +90
        changed: True if angles changed since last call
        """
        # Adjust angles based on stick position (degrees per call)
        PAN_RATE = 2.0   # degrees per frame when stick is fully deflected
        TILT_RATE = 1.5
        
        if abs(self._rx) > 0.2:
            self.ptz_pan_angle += self._rx * PAN_RATE
            self._ptz_changed = True
        if abs(self._ry) > 0.2:
            self.ptz_tilt_angle += self._ry * TILT_RATE
            self._ptz_changed = True
        
        # Clamp to valid ranges
        self.ptz_pan_angle = max(-180.0, min(180.0, self.ptz_pan_angle))
        self.ptz_tilt_angle = max(-45.0, min(90.0, self.ptz_tilt_angle))
        
        # Return and reset changed flag
        changed = self._ptz_changed
        self._ptz_changed = False
        
        return self.ptz_pan_angle, self.ptz_tilt_angle, changed
    
    def reset_ptz_angles(self, pan=0.0, tilt=0.0):
        """Reset PTZ angles to specific values"""
        self.ptz_pan_angle = pan
        self.ptz_tilt_angle = tilt
        self._ptz_changed = True

    def get_led_state(self):
        """Returns (main_led_on, chassis_led_on)"""
        return self.main_led, self.chassis_led

    def should_center_ptz(self):
        """Returns True once when A button pressed (one-shot)"""
        if self.center_ptz:
            self.center_ptz = False
            return True
        return False
        
    def should_reset_ptz_custom(self):
        """Returns True once when Y button pressed (one-shot) to go to -10, 0"""
        if self.custom_ptz_reset:
            self.custom_ptz_reset = False
            return True
        return False

    def is_emergency_stop(self):
        """Returns True if B button held"""
        return self.emergency_stop

    def _run_loop(self):
        # 1. Try 'inputs' library if available
        if HAS_INPUTS:
            self._run_inputs_loop()
        else:
            # 2. Fallback to direct Linux file read
            print("[UGV Gamepad] 'inputs' library not found. Trying direct /dev/input/js0...")
            self._run_direct_joystick()

    def _run_inputs_loop(self):
        """inputs library loop for Linux - with fallback to direct read"""
        import os
        
        # Check if inputs library found the gamepad
        try:
            from inputs import devices
            if devices.gamepads:
                self._run_inputs_events()
                return
        except:
            pass
        
        # Fallback: Direct joystick device read
        if os.path.exists('/dev/input/js0'):
            print("[UGV Gamepad] Fallback: Reading directly from /dev/input/js0")
            self._run_direct_joystick() # Kept as legacy fallback just in case
        else:
            print("[UGV Gamepad] ERROR: No joystick device found!")

    def _run_inputs_events(self):
        """Read using inputs library (preferred for Linux)"""
        from inputs import get_gamepad
        while self.running:
            try:
                events = get_gamepad()
                for event in events:
                    self._process_inputs_event(event)
            except Exception as e:
                time.sleep(0.5)

    def _process_inputs_event(self, event):
        """Process a single event from inputs library"""
        MAX_ABS = 32767.0
        MAX_TRIG = 255.0
        
        # Map event codes to our internal state
        if event.code == 'ABS_X':
            self._lx = self._apply_deadzone(event.state / MAX_ABS)
        elif event.code == 'ABS_Y':
            self._ly = self._apply_deadzone(-event.state / MAX_ABS) # Inverted
        elif event.code == 'ABS_RX':
            self._rx = self._apply_deadzone(event.state / MAX_ABS)
        elif event.code == 'ABS_RY':
            self._ry = self._apply_deadzone(-event.state / MAX_ABS) # Inverted
        elif event.code == 'ABS_Z':
            self._lt = event.state / MAX_TRIG
        elif event.code == 'ABS_RZ':
            self._rt = event.state / MAX_TRIG
        elif event.code.startswith('BTN_'):
            # Handle buttons
            # We need to map inputs' button names to our logic
            # This is tricky as 'inputs' returns names like BTN_SOUTH (A), BTN_EAST (B) etc.
            # simpler approach: just map standard codes if possible, or use the direct struct fallback 
            # if we want exact 1:1 with previous logic.
            # However, the user specifically asked to use the method from rover.py
            # Rover.py ONLY handles axes in _process_inputs_event (lines 180-188). 
            # It seems the Rover script doesn't handle buttons via 'inputs' lib? 
            # Wait, let me check rover.py again. 
            # Rover.py lines 180-188 only handle ABS_X, ABS_Y, ABS_Z, ABS_RZ.
            
            # Since UGV needs buttons (A, B, X, Y, D-Pad), we must implement button handling here too.
            val = event.state
            if event.code == 'BTN_SOUTH': # A
                if val: self.center_ptz = True
            elif event.code == 'BTN_EAST': # B
                self.emergency_stop = bool(val)
            elif event.code == 'BTN_NORTH': # X
                if val: self.stabilize_camera = not self.stabilize_camera
            elif event.code == 'BTN_WEST': # Y
                if val: self.custom_ptz_reset = True
            
            # D-Pad is often ABS_HAT0X / ABS_HAT0Y in 'inputs' lib
            elif event.code == 'ABS_HAT0Y':
                if event.state == -1: self.main_led = not self.main_led # Up
                elif event.state == 1: self.main_led = not self.main_led # Down
            elif event.code == 'ABS_HAT0X':
                if event.state == -1: self.chassis_led = not self.chassis_led # Left
                elif event.state == 1: self.chassis_led = not self.chassis_led # Right
            else:
                # Debug: Print unhandled events to find D-Pad codes
                if event.ev_type != 'Sync': # Ignore sync events
                    print(f"[Debug] Unknown Event: Code={event.code}, State={event.state}, Type={event.ev_type}")

    def _run_direct_joystick(self):
        """Direct joystick read for Linux (Fallback/Legacy)"""
        # This is the original _run_linux_loop renamed
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
                print(f"[UGV Gamepad] Successfully opened /dev/input/js0")
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
                        
                        elif ev_type & JS_EVENT_BUTTON:
                            # Edge detection (button just pressed)
                            if value == 1:
                                if number == 0:  # A
                                    self.center_ptz = True
                                elif number == 3:  # Y
                                    self.custom_ptz_reset = True
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
                                
        except PermissionError:
            print("[UGV Gamepad] ERROR: Permission denied accessing /dev/input/js0")
            print("Action: Run with 'sudo' OR add user to input group: 'sudo usermod -a -G input $USER'")
        except Exception as e:
            print(f"[UGV Gamepad] Error: {e}")

    # _run_linux_loop removed (superseded by _run_inputs_loop)

    def _apply_deadzone(self, val):
        if abs(val) < self.deadzone:
            return 0.0
        return val

    # _button_pressed removed (unused)

# Test mode
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("UGV BEAST PT GAMEPAD TEST")
    print("=" * 60)
    
    controller = UGVGamepadController()
    controller.start()
    
    print("\nControls:")
    print("  Left Stick X: Steer")
    print("  R2 (RT)     : Throttle")
    print("  L2 (LT)     : Reverse/Brake")
    print("  Right Stick : PTZ Camera")
    print("  D-Pad U/D   : Toggle Main LED")
    print("  D-Pad L/R   : Toggle Chassis LED")
    print("  A           : Center PTZ")
    print("  B           : Emergency Stop")
    print("  X           : Toggle Stabilize")
    print("  Y           : Custom Preset (-10, 0)")
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
