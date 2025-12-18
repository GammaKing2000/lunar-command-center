"""
IoU-Based Multi-Object Tracker for Moon Rover SLAM

Tracks detected objects across frames using bounding box IoU matching.
Only returns confirmed tracks (seen for N consecutive frames) for mapping.
"""

import numpy as np
from collections import OrderedDict

# Track States
TENTATIVE = 0
CONFIRMED = 1
LOST = 2

class Track:
    """Represents a single tracked object"""
    _id_counter = 0
    
    def __init__(self, box, depth, label):
        Track._id_counter += 1
        self.track_id = Track._id_counter
        
        self.box = box  # [x1, y1, x2, y2]
        self.depth = depth
        self.label = label
        self.state = TENTATIVE
        
        self.hits = 1  # Number of consecutive frames matched
        self.misses = 0  # Number of consecutive frames not matched
        self.total_observations = 1
        
        # Store depth history for averaging
        self.depth_history = [depth]
    
    def update(self, box, depth):
        """Update track with new detection"""
        self.box = box
        self.depth = depth
        self.depth_history.append(depth)
        
        # Keep only last 10 depth readings
        if len(self.depth_history) > 10:
            self.depth_history.pop(0)
        
        self.hits += 1
        self.misses = 0
        self.total_observations += 1
    
    def mark_missed(self):
        """Mark track as not detected this frame"""
        self.misses += 1
        self.hits = 0  # Reset consecutive hits
    
    def get_average_depth(self):
        """Get averaged depth from history"""
        if not self.depth_history:
            return self.depth
        return sum(self.depth_history) / len(self.depth_history)
    
    def is_confirmed(self):
        return self.state == CONFIRMED
    
    def is_lost(self):
        return self.state == LOST

def compute_iou(box1, box2):
    """
    Compute IoU between two boxes.
    box format: [x1, y1, x2, y2]
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union_area = box1_area + box2_area - inter_area
    
    if union_area <= 0:
        return 0.0
    
    return inter_area / union_area


class ObjectTracker:
    """
    Multi-object tracker using IoU matching.
    
    Parameters:
        iou_threshold: Minimum IoU to consider a match (default: 0.3)
        min_hits_to_confirm: Frames needed to confirm a track (default: 3)
        max_misses_to_lose: Frames without match before losing track (default: 5)
    """
    
    def __init__(self, iou_threshold=0.3, min_hits_to_confirm=3, max_misses_to_lose=5):
        self.iou_threshold = iou_threshold
        self.min_hits_to_confirm = min_hits_to_confirm
        self.max_misses_to_lose = max_misses_to_lose
        
        self.tracks = []  # List of active tracks
    
    def update(self, detections):
        """
        Update tracker with new detections.
        
        Args:
            detections: List of dicts with 'box', 'depth', 'label'
        
        Returns:
            List of confirmed tracks (as dicts)
        """
        # 1. Match detections to existing tracks
        matched_track_ids = set()
        matched_det_ids = set()
        
        # Build cost matrix (negative IoU for Hungarian matching)
        if self.tracks and detections:
            iou_matrix = np.zeros((len(self.tracks), len(detections)))
            
            for t_idx, track in enumerate(self.tracks):
                for d_idx, det in enumerate(detections):
                    # Only match same-label objects
                    if track.label == det.get('label', 'crater'):
                        iou_matrix[t_idx, d_idx] = compute_iou(track.box, det['box'])
            
            # Greedy matching (simple but effective for small numbers)
            while True:
                max_iou = iou_matrix.max()
                if max_iou < self.iou_threshold:
                    break
                
                t_idx, d_idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
                
                # Update matched track
                det = detections[d_idx]
                self.tracks[t_idx].update(det['box'], det['depth'])
                
                matched_track_ids.add(t_idx)
                matched_det_ids.add(d_idx)
                
                # Mark row and column as used
                iou_matrix[t_idx, :] = 0
                iou_matrix[:, d_idx] = 0
        
        # 2. Mark unmatched tracks as missed
        for t_idx, track in enumerate(self.tracks):
            if t_idx not in matched_track_ids:
                track.mark_missed()
        
        # 3. Create new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_det_ids:
                new_track = Track(
                    box=det['box'],
                    depth=det['depth'],
                    label=det.get('label', 'crater')
                )
                self.tracks.append(new_track)
        
        # 4. Update track states
        for track in self.tracks:
            if track.state == TENTATIVE:
                if track.hits >= self.min_hits_to_confirm:
                    track.state = CONFIRMED
                    print(f">> Track {track.track_id} CONFIRMED ({track.label})")
            
            if track.misses >= self.max_misses_to_lose:
                track.state = LOST
        
        # 5. Remove lost tracks
        self.tracks = [t for t in self.tracks if t.state != LOST]
        
        # 6. Return confirmed tracks
        confirmed = []
        for track in self.tracks:
            if track.is_confirmed():
                confirmed.append({
                    'track_id': track.track_id,
                    'box': track.box,
                    'depth': track.get_average_depth(),
                    'label': track.label,
                    'observation_count': track.total_observations
                })
        
        return confirmed
    
    def reset(self):
        """Clear all tracks"""
        self.tracks = []
        Track._id_counter = 0
        print(">> Tracker Reset")
