import threading
import time
import math

# Try importing inputs, but don't crash if missing (allows running mock on PC)
try:
    from inputs import get_gamepad, devices
    HAS_INPUTS_LIB = True
except ImportError:
    HAS_INPUTS_LIB = False

class GamepadController:
    """
    Reads inputs from a connected Gamepad (e.g. PS4/PS5/Xbox).
    Maps axes to throttle and steering.
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
        self._norm_rx = 0.0
        self._norm_ly = 0.0
        self._norm_ry = 0.0
        self._trig_l = 0.0
        self._trig_r = 0.0
        
        # Check connectivity
        if HAS_INPUTS_LIB:
            try:
                # Just check if any gamepads are connected
                if not devices.gamepads:
                    print("WARNING: No Gamepad found via 'inputs' library.")
            except Exception as e:
                print(f"WARNING: Error checking gamepads: {e}")

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
        # Mixing Logic:
        # Use Right Trigger (R2) for Gas, Left Trigger (L2) for Brake/Reverse?
        # Or simple Left Stick Y for throttle?
        # Let's use:
        #   Left Stick X -> Steering
        #   Right Trigger -> Forward Throttle
        #   Left Trigger -> Backward Throttle
        
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
        if not HAS_INPUTS_LIB:
            print("ERROR: 'inputs' library not installed. Gamepad disabled.")
            return

        while self.running:
            try:
                events = get_gamepad()
                for event in events:
                    self._process_event(event)
            except Exception as e:
                # e.g. unplugged
                # print(f"Gamepad Error: {e}")
                time.sleep(0.5)

    def _process_event(self, event):
        # Normalize to -1.0 ... 1.0 or 0.0 ... 1.0
        MAX_ABS = 32767.0
        MAX_TRIG = 255.0
        
        if event.code == 'ABS_X': # Left Stick X
            self._norm_lx = self._apply_deadzone(event.state / MAX_ABS)
        elif event.code == 'ABS_Y': # Left Stick Y
            # Y is usually inverted (Up is negative)
            self._norm_ly = self._apply_deadzone(-event.state / MAX_ABS)
        elif event.code == 'ABS_RX': # Right Stick X
            self._norm_rx = self._apply_deadzone(event.state / MAX_ABS)
        elif event.code == 'ABS_RY': # Right Stick Y
            self._norm_ry = self._apply_deadzone(-event.state / MAX_ABS)
        elif event.code == 'ABS_Z': # Left Trigger (L2)
            self._trig_l = event.state / MAX_TRIG
        elif event.code == 'ABS_RZ': # Right Trigger (R2)
            self._trig_r = event.state / MAX_TRIG

    def _apply_deadzone(self, val):
        if abs(val) < self.deadzone:
            return 0.0
        return val

# Code for testing locally without full robot
if __name__ == "__main__":
    pad = GamepadController()
    pad.start()
    try:
        while True:
            t, s = pad.get_drive_command()
            print(f"Throttle: {t:.2f} | Steering: {s:.2f}", end='\r')
            time.sleep(0.1)
    except KeyboardInterrupt:
        pad.stop()
