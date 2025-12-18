import cv2
import time
import math
import numpy as np
from ultralytics import YOLO

# Import Object Tracker
try:
    from object_tracker import ObjectTracker
    HAS_TRACKER = True
except ImportError:
    HAS_TRACKER = False
    print("WARNING: object_tracker module not found, tracking disabled")

class VisionSystem:
    def __init__(self, model_path='best_small.pt', device='cuda'):
        print(f">> Initializing Vision System with {model_path} on {device}...")
        try:
            self.model = YOLO(model_path)
            # Move model to GPU
            self.device = device
            self.model.to(device)
            print(f"✓ YOLO Model Loaded on {device.upper()}")
        except Exception as e:
            print(f"FAILED to load YOLO on {device}: {e}")
            # Fallback to CPU
            try:
                self.model = YOLO(model_path)
                self.device = 'cpu'
                print("✓ YOLO Model Loaded on CPU (fallback)")
            except:
                self.model = None
                self.device = None

        self.img_size = 640
        
        # Initialize Object Tracker
        if HAS_TRACKER:
            self.tracker = ObjectTracker(
                iou_threshold=0.3,
                min_hits_to_confirm=3,
                max_misses_to_lose=5
            )
            print("✓ Object Tracker Initialized")
        else:
            self.tracker = None
        
    def process_frame(self, img_bgr):
        if self.model is None or img_bgr is None:
            return [], img_bgr

        h_img, w_img = img_bgr.shape[:2]
        
        # GPU Inference with segmentation
        results = self.model(img_bgr, verbose=False, conf=0.25, device=self.device)
        
        raw_detections = []
        annotated_frame = img_bgr.copy()
        
        for r in results:
            # Check if segmentation masks are available
            has_masks = r.masks is not None and len(r.masks) > 0
            
            for idx, box in enumerate(r.boxes):
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                
                cls_id = int(box.cls[0])
                
                # Skip class '1' (index 0)
                if cls_id == 0:
                    continue
                    
                conf = float(box.conf[0])
                label = self.model.names[cls_id]

                # Color based on label
                color = (0, 255, 0)  # Default green (crater)
                if label == 'boundary': color = (0, 165, 255)  # Orange
                elif label == 'water-sight': color = (255, 0, 0)  # Blue  
                elif label == 'alien': color = (255, 0, 255)  # Purple
                
                # === SEGMENTATION ===
                mask = None
                area_m2 = None
                radius_m = None
                y_max = y2  # Default to bounding box bottom
                
                if has_masks and idx < len(r.masks):
                    # Get mask for this detection
                    mask_data = r.masks[idx].data.cpu().numpy()[0]
                    
                    # Resize mask to image size (masks are often at model resolution)
                    mask = cv2.resize(mask_data, (w_img, h_img))
                    mask = (mask > 0.5).astype(np.uint8)
                    
                    # Draw semi-transparent mask overlay
                    colored_mask = np.zeros_like(annotated_frame)
                    colored_mask[:] = color
                    mask_3ch = cv2.merge([mask, mask, mask])
                    overlay = cv2.bitwise_and(colored_mask, colored_mask, mask=mask)
                    annotated_frame = cv2.addWeighted(annotated_frame, 1, overlay, 0.4, 0)
                    
                    # Draw mask contour
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(annotated_frame, contours, -1, color, 2)
                    
                    # === AREA CALCULATION ===
                    area_px = mask.sum()
                    
                    # Find lowest point of mask (y_max) for depth
                    mask_points = np.where(mask > 0)
                    if len(mask_points[0]) > 0:
                        y_max = int(mask_points[0].max())  # Maximum y = lowest on screen
                    
                    # === DEPTH ESTIMATION (from lowest mask point) ===
                    y_norm = y_max / h_img
                    if y_norm < 0.05:
                        dist_m = 5.0
                    else:
                        dist_m = 0.175 / y_norm
                    
                    if dist_m < 0: dist_m = 0.1
                    
                    # === AREA in m² ===
                    # Approximate: area_m2 = area_px * (meters_per_pixel)^2
                    # meters_per_pixel ≈ dist_m / focal_length_px (rough estimate)
                    # Using simplified: meters_per_pixel ≈ dist_m / (h_img/2)
                    m_per_px = dist_m / (h_img / 2)
                    area_m2 = area_px * (m_per_px ** 2)
                    
                    # === RADIUS ESTIMATION ===
                    # radius = sqrt(area / π)
                    radius_m = math.sqrt(area_m2 / math.pi) if area_m2 > 0 else 0.1
                    
                else:
                    # Fallback: use bounding box for depth (no box drawn)
                    y_norm = y2 / h_img
                    if y_norm < 0.05:
                        dist_m = 5.0
                    else:
                        dist_m = 0.175 / y_norm
                    
                    if dist_m < 0: dist_m = 0.1
                
                # Draw label with depth info (DISABLED FOR INTERACTIVE UI)
                # depth_str = f"{dist_m:.2f}m"
                # extra_info = ""
                # if radius_m is not None:
                #     extra_info = f" R:{radius_m:.2f}m"
                
                # cv2.putText(annotated_frame, f"{label} {depth_str}{extra_info}", (x1, y1 - 10), 
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Store detection
                detection_data = {
                    'label': label,
                    'conf': conf,
                    'box': [float(x1), float(y1), float(x2), float(y2)],
                    'depth': float(dist_m),
                }
                
                # Add segmentation data if available
                if area_m2 is not None:
                    detection_data['area_m2'] = float(area_m2)
                if radius_m is not None:
                    detection_data['radius_m'] = float(radius_m)
                    
                raw_detections.append(detection_data)
        
        # Run through tracker if available
        if self.tracker:
            confirmed_tracks = self.tracker.update(raw_detections)
            # --- 4. Sanitize for JSON (Remove Numpy Arrays) & Apply Classification ---
            sanitized_tracks = []
            for track in confirmed_tracks:
                t = track.copy()
                if 'contour' in t:
                    del t['contour']  # Remove contour (numpy array) before sending to frontend
                
                # Apply Size Classification for Craters
                # thresholds: small < 0.03m, 0.03 < medium < 0.055, large > 0.055
                if t['label'] == 'crater':
                    radius = t.get('radius_m', 0.0)
                    if radius < 0.03:
                        t['label'] = 'small crater'
                    elif radius < 0.055:
                        t['label'] = 'medium crater'
                    else:
                        t['label'] = 'large crater'

                sanitized_tracks.append(t)
                
            # Draw track IDs on confirmed tracks
            for track in confirmed_tracks:
                box = track['box']
                x1, y1, x2, y2 = map(int, box)
                track_id = track['track_id']
                
                # cv2.putText(annotated_frame, f"T{track_id}", (x1, y2 + 15),
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            return sanitized_tracks, annotated_frame
        else:
            return raw_detections, annotated_frame
    
    def reset_tracker(self):
        """Reset the object tracker (called on map reset)"""
        if self.tracker:
            self.tracker.reset()
