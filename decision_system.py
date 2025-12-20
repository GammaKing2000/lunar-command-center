# decision_system.py

import math

class DecisionSystem:
    def __init__(self, safe_margin=0.5):
        self.safe_margin = safe_margin

    def decide(self, pose, craters):
        x, y, theta = pose['x'], pose['y'], pose['theta']

        front, left, right = [], [], []

        for c in craters:
            dx = c['x'] - x
            dy = c['y'] - y

            dist = math.hypot(dx, dy)
            angle = math.atan2(dy, dx) - theta

            # Normalize
            angle = math.atan2(math.sin(angle), math.cos(angle))

            if abs(angle) < 0.35:
                front.append((dist, c))
            elif angle > 0:
                left.append((dist, c))
            else:
                right.append((dist, c))

        # Rule-based decision
        if any(d < c['radius'] + self.safe_margin for d, c in front):
            left_clear = not any(d < c['radius'] + self.safe_margin for d, c in left)
            right_clear = not any(d < c['radius'] + self.safe_margin for d, c in right)

            if left_clear:
                return "turn_left"
            elif right_clear:
                return "turn_right"
            else:
                return "stop"

        return "go_straight"
