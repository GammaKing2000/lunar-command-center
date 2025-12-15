import math
import numpy as np

class MapManager:
    """
    Handles 2D Localization (Dead Reckoning) and Mapping (Grid).
    World Coordinates:
      X: 0 to 2.0 meters (Width)
      Y: 0 to 3.0 meters (Length)
      Theta: 0 is pointing along positive Y axis? Or X? 
             Let's use Standard Math: 0 is East (Positive X), 90 is North (Positive Y).
             Start pos: (1.0, 0.2, 90 deg) -> Center bottom, facing up.
    """
    def __init__(self, width_m=2.0, height_m=3.0, grid_res_cm=2.0):
        # Map Config
        self.width_m = width_m
        self.height_m = height_m
        self.res_cm = grid_res_cm  # resolution in cm/pixel
        self.cols = int((width_m * 100) / grid_res_cm)
        self.rows = int((height_m * 100) / grid_res_cm)
        
        # The Map Grid: 0 = Unexplored, 1 = Clear, 2+ = Obstacle/Crater Depth
        # For simplicity, we can store 'depth' in cm. 0=Flat.
        self.grid = np.zeros((self.cols, self.rows), dtype=np.float32)
        
        # Rover Pose
        self.x = 1.0  # Start Middle X
        self.y = 0.2  # Start Near Bottom Y
        self.theta = math.pi / 2  # Facing Up (90 deg)
        
        # Stored Craters (Global List)
        # Each dict: {'id': n, 'x': x_world, 'y': y_world, 'radius': r, 'depth': d}
        self.craters = []
        self.crater_id_counter = 0

    def update_pose(self, throttle, steering, dt):
        """
        Update position based on simple bicycle model or diff drive approx.
        Throttle -> Speed (Approx calibration needed)
        Steering -> Angular Velocity
        """
        # --- CALIBRATION CONSTANTS (GUESSES) ---
        MAX_SPEED_MPS = 0.8  # Meters per second at full throttle
        MAX_TURN_RADPS = 2.5 # Radians per second at full steer
        
        speed = throttle * MAX_SPEED_MPS
        omega = steering * MAX_TURN_RADPS
        
        # Motion Model
        # x_new = x + v * cos(theta) * dt
        # y_new = y + v * sin(theta) * dt
        # theta_new = theta + omega * dt
        
        self.x += speed * math.cos(self.theta) * dt
        self.y += speed * math.sin(self.theta) * dt
        self.theta += omega * dt
        
        # Clamp to bounds
        self.x = max(0, min(self.width_m, self.x))
        self.y = max(0, min(self.height_m, self.y))

    def add_unique_crater(self, rel_x_m, rel_y_m, radius_m, depth_m):
        """
        Add a crater if it's new (not close to existing ones).
        rel_x, rel_y: Position relative to camera/robot.
        We need to transform this to Global Coordinates.
        
        Robot Local Frame:
          X_local: Forward
          Y_local: Left (Standard robotics)
          
        Wait, usually:
          X is Forward, Y is Left.
          Z is Up.
          
        But visual detection gives us pixel coords.
          X_pixel (horizontal) -> corresponds to -Y_local (Left/Right)
          Y_pixel (vertical distance) -> corresponds to X_local (Forward)
        """
        
        # Transform Local -> Global
        # global_pos = robot_pos + R(theta) * local_pos
        # local_pos = (d_forward, d_left)
        
        # Let's assume passed rel_x_m is FORWARD distance
        # Let's assume passed rel_y_m is LATERAL distance (Left is positive)
        
        d_fwd = rel_x_m
        d_lat = rel_y_m
        
        # Rotation Matrix
        # global_dx = d_fwd * cos(theta) - d_lat * sin(theta)
        # global_dy = d_fwd * sin(theta) + d_lat * cos(theta)
        
        gx = self.x + (d_fwd * math.cos(self.theta) - d_lat * math.sin(self.theta))
        gy = self.y + (d_fwd * math.sin(self.theta) + d_lat * math.cos(self.theta))
        
        # Check uniqueness (simple distance threshold)
        for c in self.craters:
            dist = math.hypot(c['x'] - gx, c['y'] - gy)
            if dist < 0.2: # Same crater if within 20cm
                # Update existing (Average?)
                # c['depth'] = max(c['depth'], depth_m)
                return
        
        # Add new
        self.craters.append({
            'id': self.crater_id_counter,
            'x': float(gx),
            'y': float(gy),
            'radius': float(radius_m),
            'depth': float(depth_m)
        })
        self.crater_id_counter += 1
        
        # Mark on grid (Simple Circle Drawing)
        self._rasterize_crater(gx, gy, radius_m, depth_m)

    def _rasterize_crater(self, cx, cy, radius, depth):
        # Convert to grid indices
        gx_idx = int((cx / self.width_m) * self.cols)
        gy_idx = int((cy / self.height_m) * self.rows)
        r_idx = int((radius * 100) / self.res_cm)
        
        # Naive bounding box
        x0 = max(0, gx_idx - r_idx)
        x1 = min(self.cols, gx_idx + r_idx)
        y0 = max(0, gy_idx - r_idx)
        y1 = min(self.rows, gy_idx + r_idx)
        
        for ix in range(x0, x1):
            for iy in range(y0, y1):
                if (ix - gx_idx)**2 + (iy - gy_idx)**2 <= r_idx**2:
                    self.grid[ix, iy] = depth

    def get_status_dict(self):
        return {
            'pose': {'x': self.x, 'y': self.y, 'theta': self.theta},
            'craters': self.craters
        }
