import math
import numpy as np

class MapManagerLaptop:
    """
    Laptop-side SLAM / Mapping.
    Receives Telemetry (Throttle/Steer) and Vision Data.
    Updates Global Map.
    """
    def __init__(self, width_m=5.0, height_m=5.0, grid_res_cm=2.0, kinematics='jetracer'):
        # Increased map size for "Mission Control" view
        self.width_m = width_m
        self.height_m = height_m
        self.res_cm = grid_res_cm 
        self.kinematics = kinematics # 'jetracer' or 'ugv'
        
        self.cols = int((width_m * 100) / grid_res_cm)
        self.rows = int((height_m * 100) / grid_res_cm)
        
        self.grid = np.zeros((self.cols, self.rows), dtype=np.float32)
        
        # Rover Pose (Start at Bottom-Right Corner)
        # Margin of 20cm from edges to keep it visible
        self.x = width_m - 0.2
        self.y = 0.2
        self.theta = math.pi / 2 # Facing North
        
        self.craters = []
        self.crater_id_counter = 0

    def set_kinematics(self, mode):
        if mode in ['jetracer', 'ugv']:
            self.kinematics = mode
            print(f">> Switched Kinematics to: {mode}")

    def reset_map(self):
        """Reset the map state: clear craters and reset pose."""
        self.craters = []
        self.crater_id_counter = 0
        self.grid = np.zeros((self.cols, self.rows), dtype=np.float32)
        
        # Reset Pose to Start (Bottom-Right)
        self.x = self.width_m - 0.2
        self.y = 0.2
        self.theta = math.pi / 2 # Facing North
        print(">> Map Reset!")

    def update_pose(self, throttle, steering, dt):
        """
        Dead Reckoning.
        TODO: Fuse with visual odometry if available.
        """
        # Calibration (Rover specific)
        # Based on measurement: 1.1m in 3s @ 0.3 throttle → 1.1/3/0.3 = 1.22 m/s
        MAX_SPEED_MPS = 1.22
        v = throttle * MAX_SPEED_MPS
        
        # --- KINEMATICS LOGIC ---
        if self.kinematics == 'jetracer':
            # Ackermann Steering: Constant Radius, so w scales with v
            # w = v / R 
            # Curvature k = 1/R
            
            # Calibrated Turn Radii:
            # Right: R = 1.085m → k = 0.922
            # Left:  R = 1.43m  → k = 0.699
            
            CURVATURE_RIGHT = 1.0 / 1.085
            CURVATURE_LEFT  = 1.0 / 1.43
            
            w = 0.0
            if abs(v) > 0.01: # Only turn if moving
                if steering > 0: # LEFT
                    k = steering * CURVATURE_LEFT
                    w = v * k
                else: # RIGHT
                    k = abs(steering) * CURVATURE_RIGHT
                    w = -v * k
            
        else:
            # UGV / Skid Steer
            # Can rotate in place (v=0 is fine)
            MAX_TURN_RIGHT_RADPS = 1.124 # Reusing these as rough max rot speeds
            MAX_TURN_LEFT_RADPS  = 0.853
            
            if steering > 0: # LEFT
                w = steering * MAX_TURN_LEFT_RADPS
            else: # RIGHT
                w = steering * MAX_TURN_RIGHT_RADPS
                if steering < 0: w = -w
                
        # Update State
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        self.theta += w * dt
        
        # Keep in bounds
        self.x = max(0, min(self.width_m, self.x))
        self.y = max(0, min(self.height_m, self.y))

    def update_craters(self, visible_craters, img_width):
        """
        Fuse new detections into the map.
        visible_craters: List of dicts {box, depth, label, track_id (optional)}
        """
        MID_PIX = img_width / 2.0
        
        for c in visible_craters:
            box = c['box'] # [x1, y1, x2, y2]
            depth = c['depth']
            label = c.get('label', 'crater')
            track_id = c.get('track_id', None)  # Use track_id if available
            observation_count = c.get('observation_count', 1)
            
            x_cen = (box[0] + box[2]) / 2.0
            
            # 1. Project to Local Frame (Robot is Origin)
            x_norm = (x_cen - MID_PIX) / MID_PIX
            
            # FOV approx 60 deg -> +/- 30 deg -> +/- 0.5 rad
            angle_offset = -x_norm * 0.5 # Negate: Left on screen is +Angle
            
            d_robot = depth
            
            # Local Point:
            loc_x = d_robot * math.cos(angle_offset)
            loc_y = d_robot * math.sin(angle_offset)
            
            # 2. Transform to Global Map
            gx = self.x + (loc_x * math.cos(self.theta) - loc_y * math.sin(self.theta))
            gy = self.y + (loc_x * math.sin(self.theta) + loc_y * math.cos(self.theta))
            
            # Use segmentation-derived radius if available, else use defaults
            radius = c.get('radius_m', None)
            if radius is None:
                radius = 0.3  # Default
                if label == 'alien': radius = 0.2
                elif label == 'water-sight': radius = 0.4
            
            self._add_unique_landmark(gx, gy, radius, label, track_id, observation_count)

    def _add_unique_landmark(self, x, y, radius, label, track_id=None, observation_count=1):
        """
        Add or update a landmark using track_id for deduplication.
        Landmarks are locked after MAX_OBSERVATIONS to prevent drift.
        """
        MAX_OBSERVATIONS = 10  # Lock position after this many observations
        MERGE_RADIUS = 0.6
        
        # If we have a track_id, use that for deduplication (most reliable)
        if track_id is not None:
            for c in self.craters:
                if c.get('track_id') == track_id:
                    # Check if locked
                    if c.get('locked', False):
                        return  # Don't update locked landmarks
                    
                    # Update position (weighted average)
                    c['x'] = c['x'] * 0.7 + x * 0.3
                    c['y'] = c['y'] * 0.7 + y * 0.3
                    c['observation_count'] = c.get('observation_count', 1) + 1
                    
                    # Lock after enough observations
                    if c['observation_count'] >= MAX_OBSERVATIONS:
                        c['locked'] = True
                        print(f">> Landmark {c['id']} LOCKED at ({c['x']:.2f}, {c['y']:.2f})")
                    
                    return  # Merged
        
        # Fallback: position-based merge for landmarks without track_id
        for c in self.craters:
            if c.get('label', 'crater') != label:
                continue
            if c.get('locked', False):
                continue  # Don't merge into locked landmarks
                
            dist = math.hypot(c['x'] - x, c['y'] - y)
            if dist < MERGE_RADIUS:
                c['x'] = c['x'] * 0.7 + x * 0.3
                c['y'] = c['y'] * 0.7 + y * 0.3
                return  # Merged
        
        # Create new landmark
        self.craters.append({
            'id': self.crater_id_counter,
            'x': x,
            'y': y,
            'radius': radius,
            'label': label,
            'track_id': track_id,
            'observation_count': 1,
            'locked': False
        })
        self.crater_id_counter += 1
        print(f">> New Landmark {self.crater_id_counter - 1}: {label} at ({x:.2f}, {y:.2f})")

    def get_status(self):
        return {
            'pose': {'x': self.x, 'y': self.y, 'theta': self.theta},
            'craters': self.craters
        }
