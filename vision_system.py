import cv2
import time
import numpy as np
from ultralytics import YOLO

class VisionSystem:
    def __init__(self, model_path='yolov8n.pt'):
        print(f">> Initializing Vision System with {model_path}...")
        try:
            self.model = YOLO(model_path)
            print("✓ YOLO Model Loaded")
        except Exception as e:
            print(f"FAILED to load YOLO: {e}")
            self.model = None

        self.img_size = 640  # Standard YOLOv8 size
        
    def process_frame(self, img_bgr):
        if self.model is None or img_bgr is None:
            return [], img_bgr

        # Inference
        results = self.model(img_bgr, verbose=False, conf=0.25)
        
        craters = []
        annotated_frame = img_bgr.copy()
        
        for r in results:
            annotated_frame = r.plot() # Draw bboxes on frame
            
            for box in r.boxes:
                # box.xyxy is [x1, y1, x2, y2]
                xyxy = box.xyxy[0].cpu().numpy()
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = self.model.names[cls_id]
                
                # Check for 'crater' class (or generic classes if we haven't trained custom yet)
                # For this migration, we assume the model returns 'crater'.
                # IF using standard COCO model, we might simulate with 'bowl' or 'cup' for testing.
                
                # Custom logic:
                x1, y1, x2, y2 = xyxy
                width = x2 - x1
                height = y2 - y1
                
                # Depth Estimation (Simple heuristic as before)
                # Image Height = 416 (from rover) or 720. 
                h_img, w_img = img_bgr.shape[:2]
                
                # Normalize y_max (bottom of box) -> 1.0 is bottom of screen
                y_norm = y2 / h_img
                
                # Distance approx
                # 0.2m (very close) to 3.0m (horizon)
                dist_m = (1.0 - y_norm) * 3.0 + 0.2 
                if dist_m < 0: dist_m = 0.1
                
                craters.append({
                    'label': label,
                    'conf': conf,
                    'box': [float(x1), float(y1), float(x2), float(y2)],
                    'depth': float(dist_m)
                })
                
        return craters, annotated_frame
