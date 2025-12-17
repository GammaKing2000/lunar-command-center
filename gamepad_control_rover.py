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
    # XInput only works on Windows - OSError thrown on Linux
    pass

if not HAS_XINPUT:
    try:
        from inputs import get_gamepad, devices
        HAS_INPUTS = True
    except ImportError:
        pass

class GamepadController:
    """
    Reads inputs from a connected Gamepad (e.g. PS4/PS5/Xbox/EvoFox).
    Maps axes to throttle and steering.
    Supports both XInput (Windows) and inputs library (Linux).
    """
    def __init__(self, deadzone=0.1, max_steer=1.0, max_throttle=0.3):
        self.throttle = 0.0
        self.steering = 0.0
        self.running = False
        self.thread = None
        self.deadzone = deadzone
        self.max_steer = max_steer
        self.max_throttle = max_throttle
        
        # State Mapping
        self._norm_lx = 0.0
        self._norm_ly = 0.0
        self._trig_l = 0.0
        self._trig_r = 0.0
        
        # Detect library
        if HAS_XINPUT:
            print("Using XInput (Windows)")
        elif HAS_INPUTS:
            print("Using inputs library (Linux)")
        else:
            print("WARNING: No gamepad library available!")

    def start(self):
        """Start the input reading thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(">> Gamepad Controller Thread Started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def get_drive_command(self):
        """
        Returns (throttle, steering)
        Throttle: -1.0 (Backward) to 1.0 (Forward)
        Steering: -1.0 (Left) to 1.0 (Right)
        """
        # Steering from Left Stick X
        steer_cmd = self._norm_lx * self.max_steer
        
        # Throttle logic: R2 - L2
        fwd = self._trig_r
        bwd = self._trig_l
        throt_cmd = (fwd - bwd) * self.max_throttle
        
        # Fallback: If triggers aren't used, use Left Stick Y
        if abs(throt_cmd) < 0.01:
             throt_cmd = self._norm_ly * self.max_throttle

        return throt_cmd, steer_cmd

    def _run_loop(self):
        if HAS_XINPUT:
            self._run_xinput_loop()
        elif HAS_INPUTS:
            self._run_inputs_loop()
        else:
            print("ERROR: No gamepad library available!")

    def _run_xinput_loop(self):
        """XInput-based loop for Windows"""
        while self.running:
            try:
                # Get state from first connected controller
                state = XInput.get_state(0)
                
                # Left Stick (normalized -1 to 1)
                lx = state.Gamepad.sThumbLX / 32767.0
                ly = state.Gamepad.sThumbLY / 32767.0
                
                self._norm_lx = self._apply_deadzone(lx)
                self._norm_ly = self._apply_deadzone(ly)
                
                # Triggers (normalized 0 to 1)
                self._trig_l = state.Gamepad.bLeftTrigger / 255.0
                self._trig_r = state.Gamepad.bRightTrigger / 255.0
                
                time.sleep(0.01)
            except Exception as e:
                time.sleep(0.5)

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
            print("Fallback: Reading directly from /dev/input/js0")
            self._run_direct_joystick()
        else:
            print("ERROR: No joystick device found!")

    def _run_inputs_events(self):
        """Read using inputs library"""
        from inputs import get_gamepad
        while self.running:
            try:
                events = get_gamepad()
                for event in events:
                    self._process_inputs_event(event)
            except Exception as e:
                time.sleep(0.5)

    def _run_direct_joystick(self):
        """Direct read from /dev/input/js0 - Linux only"""
        import struct
        
        JS_EVENT_SIZE = 8  # sizeof(struct js_event)
        JS_EVENT_BUTTON = 0x01
        JS_EVENT_AXIS = 0x02
        
        try:
            with open('/dev/input/js0', 'rb') as js:
                while self.running:
                    event = js.read(JS_EVENT_SIZE)
                    if event:
                        # Unpack: time(4 bytes), value(2 bytes), type(1 byte), number(1 byte)
                        _, value, ev_type, number = struct.unpack('IhBB', event)
                        
                        # Handle axis events
                        if ev_type & JS_EVENT_AXIS:
                            normalized = value / 32767.0
                            
                            if number == 0:  # Left Stick X
                                self._norm_lx = self._apply_deadzone(normalized)
                            elif number == 1:  # Left Stick Y
                                self._norm_ly = self._apply_deadzone(-normalized)
                            elif number == 2:  # Left Trigger
                                self._trig_l = (normalized + 1.0) / 2.0  # Convert -1..1 to 0..1
                            elif number == 5:  # Right Trigger
                                self._trig_r = (normalized + 1.0) / 2.0
        except Exception as e:
            print(f"Joystick error: {e}")

    def _process_inputs_event(self, event):
        MAX_ABS = 32767.0
        MAX_TRIG = 255.0
        
        if event.code == 'ABS_X':
            self._norm_lx = self._apply_deadzone(event.state / MAX_ABS)
        elif event.code == 'ABS_Y':
            self._norm_ly = self._apply_deadzone(-event.state / MAX_ABS)
        elif event.code == 'ABS_Z':
            self._trig_l = event.state / MAX_TRIG
        elif event.code == 'ABS_RZ':
            self._trig_r = event.state / MAX_TRIG

    def _apply_deadzone(self, val):
        if abs(val) < self.deadzone:
            return 0.0
        return val


# Test mode
if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("GAMEPAD DEBUG MODE")
    print("=" * 50)
    
    if HAS_XINPUT:
        print("\nUsing XInput (Windows)")
        print("Checking for controllers...")
        
        connected = XInput.get_connected()
        print(f"Connected controllers: {connected}")
        
        if not any(connected):
            print("\nNo XInput controller found!")
            print("Make sure your EvoFox controller is connected.")
            sys.exit(1)
        
        print("\n" + "=" * 50)
        print("LIVE CONTROLLER STATE (Press Ctrl+C to exit)")
        print("=" * 50)
        
        try:
            while True:
                state = XInput.get_state(0)
                
                lx = state.Gamepad.sThumbLX / 32767.0
                ly = state.Gamepad.sThumbLY / 32767.0
                lt = state.Gamepad.bLeftTrigger / 255.0
                rt = state.Gamepad.bRightTrigger / 255.0
                
                print(f"LX: {lx:+.2f} | LY: {ly:+.2f} | LT: {lt:.2f} | RT: {rt:.2f}", end='\r')
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nExiting.")
    
    elif HAS_INPUTS:
        print("\nUsing inputs library (Linux)")
        import os
        
        # Check if inputs lib detects gamepads
        try:
            from inputs import devices
            print(f"inputs library found: {len(devices.gamepads)} gamepads")
        except:
            pass
        
        # Check if joystick device exists
        if os.path.exists('/dev/input/js0'):
            print("Found /dev/input/js0 - testing direct read...")
            print("\n" + "=" * 50)
            print("LIVE CONTROLLER STATE (Press Ctrl+C to exit)")
            print("=" * 50)
            
            import struct
            JS_EVENT_SIZE = 8
            JS_EVENT_AXIS = 0x02
            
            axis_names = {0: 'LX', 1: 'LY', 2: 'LT', 3: 'RX', 4: 'RY', 5: 'RT'}
            axis_values = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            
            try:
                with open('/dev/input/js0', 'rb') as js:
                    while True:
                        event = js.read(JS_EVENT_SIZE)
                        if event:
                            _, value, ev_type, number = struct.unpack('IhBB', event)
                            if ev_type & JS_EVENT_AXIS and number in axis_values:
                                axis_values[number] = value / 32767.0
                                
                                # Print current state
                                out = " | ".join([f"{axis_names.get(i, '?')}: {axis_values[i]:+.2f}" for i in range(6)])
                                print(out, end='\r')
            except KeyboardInterrupt:
                print("\nExiting.")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("No joystick device found at /dev/input/js0")
    
    else:
        print("ERROR: No gamepad library available!")
        print("Install: pip install XInput-Python  (Windows)")
        print("     or: pip install inputs  (Linux)")
