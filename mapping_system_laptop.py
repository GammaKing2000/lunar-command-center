import math
import numpy as np

class MapManagerLaptop:
    """
    Laptop-side SLAM / Mapping.
    Receives Telemetry (Throttle/Steer) and Vision Data.
    Updates Global Map.
    """
    def __init__(self, width_m=5.0, height_m=5.0, grid_res_cm=2.0):
        # Increased map size for "Mission Control" view
        self.width_m = width_m
        self.height_m = height_m
        self.res_cm = grid_res_cm 
        self.cols = int((width_m * 100) / grid_res_cm)
        self.rows = int((height_m * 100) / grid_res_cm)
        
        self.grid = np.zeros((self.cols, self.rows), dtype=np.float32)
        
        # Rover Pose (Start at Center)
        self.x = width_m / 2.0
        self.y = height_m / 2.0
        self.theta = math.pi / 2 # Facing North
        
        self.craters = []
        self.crater_id_counter = 0

    def update_pose(self, throttle, steering, dt):
        """
        Dead Reckoning.
        TODO: Fuse with visual odometry if available.
        """
        # Calibration (Rover specific)
        MAX_SPEED_MPS = 0.5 
        MAX_TURN_RADPS = 2.0 
        
        # Inverted steering logic if needed (Rover sent -steering?)
        # Let's assume input is standard: +Steer = Left Turn, +Throttle = Forward
        
        v = throttle * MAX_SPEED_MPS
        w = steering * MAX_TURN_RADPS
        
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        self.theta += w * dt
        
        # Keep in bounds
        self.x = max(0, min(self.width_m, self.x))
        self.y = max(0, min(self.height_m, self.y))

    def update_craters(self, visible_craters, img_width):
        """
        Fuse new detections into the map.
        visible_craters: List of dicts {box, depth}
        """
        MID_PIX = img_width / 2.0
        
        for c in visible_craters:
            box = c['box'] # [x1, y1, x2, y2]
            depth = c['depth']
            
            x_cen = (box[0] + box[2]) / 2.0
            
            # 1. Project to Local Frame (Robot is Origin)
            # Angle relative to heading
            # x_cen=0 -> Left, x_cen=Width -> Right ? 
            # Usual: Left is positive angle?
            # Let's assume standard Lens:
            # x_norm -1 (Left) to +1 (Right)
            x_norm = (x_cen - MID_PIX) / MID_PIX
            
            # FOV approx 60 deg -> +/- 30 deg -> +/- 0.5 rad
            angle_offset = -x_norm * 0.5 # Negate: Left on screen is +Angle
            
            # Polar to Cartesian (Local)
            # x_loc = dist * cos(offset)
            # y_loc = dist * sin(offset)
            # But "Forward" is X in Robot frame?
            
            d_robot = depth
            
            # Local Point:
            # X = Forward = d_robot * cos(angle_offset)
            # Y = Left = d_robot * sin(angle_offset)
            
            loc_x = d_robot * math.cos(angle_offset)
            loc_y = d_robot * math.sin(angle_offset)
            
            # 2. Transform to Global Map
            # Global = Pose + Rotate(Local)
            
            # Global X = Rx + Lx*cos(T) - Ly*sin(T)
            # Global Y = Ry + Lx*sin(T) + Ly*cos(T)
            
            gx = self.x + (loc_x * math.cos(self.theta) - loc_y * math.sin(self.theta))
            gy = self.y + (loc_x * math.sin(self.theta) + loc_y * math.cos(self.theta))
            
            # 3. Add/Merge
            self._add_unique_crater(gx, gy, 0.3) # Radius 30cm default

    def _add_unique_crater(self, x, y, radius):
        # Simple Euclidean merge
        for c in self.craters:
            if math.hypot(c['x'] - x, c['y'] - y) < 0.5: # 50cm merge radius
                return # Already known
        
        self.craters.append({
            'id': self.crater_id_counter,
            'x': x,
            'y': y,
            'radius': radius
        })
        self.crater_id_counter += 1

    def get_status(self):
        return {
            'pose': {'x': self.x, 'y': self.y, 'theta': self.theta},
            'craters': self.craters
        }
