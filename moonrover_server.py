import os
import json
import logging
import base64
import subprocess
import cv2
import numpy as np
import time
import sys
from threading import Thread, Event, Lock
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO

# Import Smart Modules
try:
    from vision_system import VisionSystem
    print("✓ Vision Module Import OK")
except ImportError:
    VisionSystem = None
    print("! Vision Module NOT Found")

try:
    from mapping_system_laptop import MapManagerLaptop
    print("✓ Mapping Module Import OK")
except ImportError:
    MapManagerLaptop = None
    print("! Mapping Module NOT Found")

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MoonServer')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moon_rover_secret'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Systems Initialization ---
vision = VisionSystem() if VisionSystem else None
# Increased map size to 6m x 6m to support longer missions (e.g. 200cm+)
mapper = MapManagerLaptop(width_m=6.0, height_m=6.0) if MapManagerLaptop else None

# --- State ---
web_command = {'racer': 'run'}
shared_data = {}
step = 0
step_broadcast = 0
broadcast_event = Event()
state_lock = Lock()

last_telemetry_time = time.time()
yolo_frame_counter = 0
cached_craters = []
cached_annotated_b64 = None
cached_raw_frame = None  # Store raw frame for capture endpoint

# High-res capture state
capture_pending = False
capture_metadata = {}  # {"box": [...], "label": "..."}
last_capture_time = 0.0 # Cooldown for auto-capture

# Mission State

# Mission State
class MissionManager:
    def __init__(self):
        self.active = False
        self.task = "IDLE" 
        self.start_time = None
        self.start_pose = None
        
        # Linear Mission State
        self.target_distance = 0.0
        self.current_distance = 0.0
        
        # Rectangle Mission State
        self.mission_type = "linear" # 'linear' | 'rectangle'
        self.rect_state = "IDLE" # LEG_LONG, TURN_1, LEG_SHORT, TURN_2
        self.rect_leg_start_pose = None
        
        # General
        self.save_report = True
        self.findings = {'craters': 0, 'aliens': 0}
        self.detailed_findings = [] # List of {type, radius_m, timestamp, snapshot}
        self.snapshots = []
        self.message = "Ready"
        self.progress = 0
        self.mission_folder = None  # e.g. 'mission_100cm_1'
        self.mission_id = None
        self.captured_track_ids = set()  # Track IDs already captured

    def start_mission(self, distance_cm, current_pose, mission_type="linear", save_report=True):
        self.active = True
        self.mission_type = mission_type
        self.save_report = save_report
        self.start_time = time.time()
        self.start_pose = current_pose # {'x': x, 'y': y, 'theta': t}
        self.captured_track_ids = set()
        self.findings = {'craters': 0, 'aliens': 0}
        self.detailed_findings = []
        self.snapshots = []
        
        if mission_type == "linear":
            self.task = "Linear Traverse"
            self.target_distance = distance_cm / 100.0 # Convert cm to meters
            self.current_distance = 0.0
            self.message = f"Starting traverse: {distance_cm}cm"
        elif mission_type == "rectangle":
            self.task = "Rectangular Patrol"
            self.target_distance = 0 # Infinite
            self.rect_state = "LEG_LONG"
            self.rect_leg_start_pose = current_pose
            self.rect_state_start_time = time.time() # Initialize timer
            self.message = "Starting Rectangular Patrol"
        
        self.progress = 0
        
        if self.save_report:
            # Generate unique mission folder name
            prefix = "mission" if mission_type == "linear" else "patrol"
            dist_str = f"{int(distance_cm)}cm" if mission_type == "linear" else "rect"
            base_folder = f"{prefix}_{dist_str}"
            counter = 1
            while os.path.exists(f"public/reports/{base_folder}_{counter}"):
                counter += 1
            self.mission_folder = f"{base_folder}_{counter}"
            self.mission_id = self.mission_folder
            
            # Create folders
            os.makedirs(f"public/reports/{self.mission_folder}", exist_ok=True)
            os.makedirs(f"public/detections/{self.mission_folder}", exist_ok=True)
            logger.info(f"Mission Started: {self.task} -> {self.mission_folder}")
        else:
            self.mission_folder = None
            self.mission_id = f"temp_{int(time.time())}"
            logger.info(f"Mission Started (No Report): {self.task}")

    def normalize_angle(self, angle):
        """Normalize angle to -180 to 180"""
        while angle > 180: angle -= 360
        while angle < -180: angle += 360
        return angle

    def get_angle_diff(self, target, current):
        diff = target - current
        return self.normalize_angle(diff)

    def update(self, current_pose, dt):
        global step
        if not self.active: return {'throttle': 0, 'steering': 0}

        # --- RECTANGLE MISSION LOGIC ---
        if self.mission_type == "rectangle":
            current_time = time.time()
            
            # Initialize state timer if needed
            if not hasattr(self, 'rect_state_start_time') or self.rect_state_start_time is None:
                self.rect_state_start_time = current_time

            elapsed_state = current_time - self.rect_state_start_time
            
            throttle = 0.0
            steering = 0.0
            state = self.rect_state
            
            # Constants
            LONG_LEG_DURATION = 15.0
            SHORT_LEG_DURATION = 5.0
            TURN_DURATION = 1.5 # As tuned by user
            
            if state == "LEG_LONG":
                self.message = f"Patrol: Long Leg ({elapsed_state:.1f}s / {LONG_LEG_DURATION}s)"
                if elapsed_state >= LONG_LEG_DURATION:
                    self.rect_state = "TURN_1"
                    self.rect_state_start_time = current_time
                    logger.info("Leg Long Complete. Switching to TURN_1")
                else:
                    throttle = -0.16
                    steering = 0.0
                    
            elif state == "TURN_1" or state == "TURN_2":
                self.message = f"Patrol: Turning Right ({elapsed_state:.1f}s / {TURN_DURATION}s)"
                if elapsed_state >= TURN_DURATION:
                     next_state = "LEG_SHORT" if state == "TURN_1" else "LEG_LONG"
                     self.rect_state = next_state
                     self.rect_state_start_time = current_time
                     logger.info(f"Turn Complete. Switching to {next_state}")
                else:
                    throttle = 0.0
                    steering = 1.0 # Right Turn
            
            elif state == "LEG_SHORT":
                self.message = f"Patrol: Short Leg ({elapsed_state:.1f}s / {SHORT_LEG_DURATION}s)"
                if elapsed_state >= SHORT_LEG_DURATION:
                    self.rect_state = "TURN_2"
                    self.rect_state_start_time = current_time
                    logger.info("Leg Short Complete. Switching to TURN_2")
                else:
                    throttle = -0.16
                    steering = 0.0
            
            return {'throttle': throttle, 'steering': steering}


        # --- LINEAR MISSION LOGIC ---
        # 1. Update Distance
        if self.start_pose and current_pose:
            dx = current_pose['x'] - self.start_pose['x']
            dy = current_pose['y'] - self.start_pose['y']
            self.current_distance = np.sqrt(dx*dx + dy*dy)
            
            # Update Progress
            if self.target_distance > 0:
                self.progress = min(100, int((self.current_distance / self.target_distance) * 100))

        # 2. Check Completion
        if self.current_distance >= self.target_distance:
            self.complete_mission()
            return {'throttle': 0, 'steering': 0}

        # 3. Control Logic (Linear Traverse)
        # Kickstart: heavier throttle for first 0.2s to overcome static friction
        elapsed = time.time() - self.start_time
        throttle = -0.2 if elapsed < 0.4 else -0.16
        
        self.message = f"Traversing... {self.current_distance:.2f}m / {self.target_distance:.2f}m"
        return {'throttle': throttle, 'steering': 0} # Drive straight

    def complete_mission(self):
        self.active = False
        self.message = "Mission Complete"
        self.progress = 100
        logger.info("Mission Complete")
        
        if not self.save_report:
            return None
        
        # Generate Report
        report = {
            'id': self.mission_id,
            'task': self.task,
            'startTime': self.start_time,
            'endTime': time.time(),
            'totalDistance': float(self.current_distance),
            'findings': self.findings,
            'detailed_findings': self.detailed_findings,
            'snapshots': self.snapshots,
            'logs': [f"Mission started at {self.start_time}", "Traverse completed successfully."]
        }
        
        # Save Report to mission folder
        report_path = f"public/reports/{self.mission_folder}/report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved: {report_path}")
            
        return report

    def abort(self):
        self.active = False
        self.message = "Mission Aborted"
        logger.info("Mission Aborted")
        
        if not self.save_report:
            self.mission_folder = None
            return

        # Discard collected data
        if self.mission_folder:
            detections_folder = f"public/detections/{self.mission_folder}"
            for filename in self.snapshots:
                try:
                    filepath = os.path.join(detections_folder, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        logger.info(f"Discarded snapshot: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting snapshot {filename}: {e}")
            
            # Remove empty folders
            try:
                if os.path.exists(detections_folder) and not os.listdir(detections_folder):
                    os.rmdir(detections_folder)
                reports_folder = f"public/reports/{self.mission_folder}"
                if os.path.exists(reports_folder) and not os.listdir(reports_folder):
                    os.rmdir(reports_folder)
            except Exception as e:
                logger.error(f"Error cleaning up folders: {e}")
        
        self.snapshots = []
        self.detailed_findings = []
        self.findings = {'craters': 0, 'aliens': 0}
        self.mission_folder = None
        self.mission_id = None

mission_manager = MissionManager()

# Detections folder path (in public for frontend access)
DETECTIONS_FOLDER = 'public/detections'

@app.route('/')
def index():
    return "Moon Rover Mission Control Server (BRAIN ACTIVE)"

@app.route('/reports/<path:filename>')
def serve_reports(filename):
    from flask import send_from_directory
    return send_from_directory('public/reports', filename)
    
@app.route('/detections/<path:filename>')
def serve_detections(filename):
    from flask import send_from_directory
    return send_from_directory('public/detections', filename)

@app.route('/jetson_command', methods=['GET'])
def get_jetson_command():
    global capture_pending
    cmd = request.args.get('racer')
    if cmd:
        web_command['racer'] = cmd
        logger.info(f"Command update: {cmd}")
    
    # Include capture flag in response
    response = dict(web_command)
    if capture_pending:
        response['capture'] = True
        capture_pending = False  # Reset after sending
        
    # Include mission status
    response['mission_active'] = mission_manager.active
    if mission_manager.active and mission_manager.mission_folder:
        response['mission_folder'] = mission_manager.mission_folder
    
    return jsonify(response)

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    """Generator function for MJPEG"""
    global cached_annotated_b64
    while True:
        # We can reuse the cached annotated jpeg from the vision loop
        if cached_annotated_b64_buffer:
             yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + cached_annotated_b64_buffer + b'\r\n')
        time.sleep(0.04) # Limit to 25 FPS stream

@app.route('/display', methods=['POST'])
def receive_telemetry():
    global step, shared_data, last_telemetry_time
    global cached_craters, cached_annotated_b64, cached_raw_frame, cached_annotated_b64_buffer
    
    current_time = time.time()
    dt = current_time - last_telemetry_time
    last_telemetry_time = current_time
    
    # 1. Extract Telemetry from Rover
    throttle = request.form.get('throttle', type=float, default=0.0)*(-1)
    steer_real = request.form.get('steer_real', type=float, default=0.0)
    battery = request.form.get('battery', type=float, default=0.0)
    battery_percent = request.form.get('battery_percent', type=int, default=0)
    img_b64_raw = request.form.get('img_base64', '')
    
    # 2. Process Image if available (HTTP streaming mode)
    if img_b64_raw and vision:
        try:
            # Decode base64 image
            img_data = base64.b64decode(img_b64_raw)
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is not None:
                # Run YOLO Detection
                live_craters, annotated_frame = vision.process_frame(img)
                
                cached_craters = live_craters
                cached_raw_frame = img.copy()
                
                # Encode annotated frame for WebSocket broadcast
                _, buf = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                cached_annotated_b64_buffer = buf.tobytes()
                cached_annotated_b64 = base64.b64encode(buf).decode()
                
                # Auto-Capture during mission
                if mission_manager.active:
                    process_auto_capture(live_craters, img)
        except Exception as e:
            print(f"Image processing error: {e}")
    
    # B. Mapping (SLAM)
    # (Same mapping logic as before)

    # B. Mapping (SLAM)
    map_status = {'pose': {'x':0,'y':0,'theta':0}, 'craters': []}
    
    if mapper:
        # Update Pose (Dead Reckoning)
        mapper.update_pose(throttle, steer_real, dt)
        
        # Update Map with new crater detections
        # Note: Vision returns 'box' and 'depth'. Mapper needs this.
        # Update Map with new crater detections
        # Note: Vision returns 'box' and 'depth'. Mapper needs this.
        # Use Cached Raw Frame (from continuous vision loop) which corresponds to live_craters
        if cached_raw_frame is not None:
             h, w = cached_raw_frame.shape[:2]
             mapper.update_craters(cached_craters, w)
             
        map_status = mapper.get_status()

    # C. Mission Control Logic
    mission_cmd = {'throttle': 0, 'steering': 0}
    if mission_manager.active:
        # Override manual control
        mission_cmd = mission_manager.update(map_status['pose'], dt)
        throttle = mission_cmd['throttle']
        steer_real = mission_cmd['steering']
        # Note: We update `web_command` so the next /jetson_command poll picks it up
        web_command['throttle'] = throttle
        web_command['steering'] = steer_real
        web_command['racer'] = 'run'

        # D. Auto-Capture Logic
        # Capture craters/aliens only once per track_id, at optimal distance (0.20-0.35m)
        global last_capture_time
        CAPTURE_MIN_DIST = 0.20  # meters
        CAPTURE_MAX_DIST = 0.51  # meters
        
        # Log all detections during mission for debugging
        mission_log_path = f"public/reports/{mission_manager.mission_folder}/mission_log.txt" if mission_manager.mission_folder else "mission_log.txt"
        
        if cached_craters:
            with open(mission_log_path, 'a') as mlog:
                mlog.write(f"\n[{time.strftime('%H:%M:%S')}] Frame - Dist: {mission_manager.current_distance:.3f}m, Progress: {mission_manager.progress}%\n")
                mlog.write(f"  Detections: {len(cached_craters)}, Already Captured IDs: {mission_manager.captured_track_ids}\n")
                
                for i, target in enumerate(cached_craters):
                    track_id = target.get('track_id')
                    depth = target.get('depth', 0.0)
                    label = target.get('label', 'unknown')
                    radius = target.get('radius_m', 0.0)
                    
                    mlog.write(f"  [{i}] ID:{track_id}, Label:{label}, Depth:{depth:.3f}m, Radius:{radius:.3f}m\n")
                    
                    # Check capture eligibility
                    if track_id is None:
                        mlog.write(f"      -> SKIP: No track_id\n")
                    elif track_id in mission_manager.captured_track_ids:
                        mlog.write(f"      -> SKIP: Already captured\n")
                    elif depth < CAPTURE_MIN_DIST:
                        mlog.write(f"      -> SKIP: Too close ({depth:.2f}m < {CAPTURE_MIN_DIST}m)\n")
                    elif depth > CAPTURE_MAX_DIST:
                        mlog.write(f"      -> SKIP: Too far ({depth:.2f}m > {CAPTURE_MAX_DIST}m)\n")
                    else:
                        mlog.write(f"      -> ELIGIBLE for capture!\n")
        
        if cached_craters and cached_raw_frame is not None:
            for target in cached_craters:
                track_id = target.get('track_id')
                depth = target.get('depth', 0.0)
                
                # Skip if no track_id or already captured
                if track_id is None or track_id in mission_manager.captured_track_ids:
                    continue
                
                # Only capture when in optimal distance range
                if CAPTURE_MIN_DIST <= depth <= CAPTURE_MAX_DIST:
                    # Perform Instant Server-Side Capture
                    capture_success = process_server_capture(cached_raw_frame, target)
                    
                    if capture_success:
                        mission_manager.captured_track_ids.add(track_id)
                        # Update message so frontend shows detection in logs
                        mission_manager.message = f"Detected: {target['label']} at {depth:.2f}m"
                        logger.info(f"Auto-Capture: {target['label']} (ID:{track_id}, dist:{depth:.2f}m)")
                        
                        # Log capture to mission log
                        with open(mission_log_path, 'a') as mlog:
                            mlog.write(f"  *** CAPTURED: ID:{track_id}, {target['label']}, {depth:.2f}m ***\n")
                        
                        break  # Only capture one per frame to avoid overload

    # 3. Update State for Frontend
    with state_lock:
        step += 1
        shared_data = {
            'step': step,
            'img_base64': cached_annotated_b64 if cached_annotated_b64 else "", # Show the detections on the UI
            'telemetry': {
                'throttle': throttle,
                'steering': steer_real,
                'pose': map_status['pose'],
                'battery': battery,
                'battery_percent': battery_percent
            },
            'perception': {
                'live_craters': cached_craters,
                'map_craters': map_status['craters'],
                'resolution': [cached_raw_frame.shape[1], cached_raw_frame.shape[0]] if cached_raw_frame is not None else [1280, 720],
                'detection_files': sorted([f for f in os.listdir(DETECTIONS_FOLDER) if f.endswith('.jpg')], reverse=True)[:10] if os.path.exists(DETECTIONS_FOLDER) else []
            },
            'mission_status': {
                'active': mission_manager.active,
                'task': mission_manager.task,
                'progress': mission_manager.progress,
                'message': mission_manager.message
            }
        }
    
    broadcast_event.set()
    return jsonify({'status': 'ok', 'command': web_command['racer']})

cached_annotated_b64_buffer = None # Raw bytes for MJPEG

def vision_processing_loop():
    """Vision processing is now done in receive_telemetry for HTTP streaming mode.
    This function is kept for backward compatibility but does nothing."""
    print(">> Vision processing integrated into HTTP telemetry handler")


def process_auto_capture(live_craters, frame):
    """Check and perform auto-capture"""
    CAPTURE_MIN_DIST = 0.20
    CAPTURE_MAX_DIST = 0.51
    
    for target in live_craters:
        track_id = target.get('track_id')
        depth = target.get('depth', 0.0)
        
        if track_id is None or track_id in mission_manager.captured_track_ids:
            continue
            
        if CAPTURE_MIN_DIST <= depth <= CAPTURE_MAX_DIST:
             capture_success = process_server_capture(frame, target)
             if capture_success:
                 mission_manager.captured_track_ids.add(track_id)
                 mission_manager.message = f"Detected: {target['label']} at {depth:.2f}m"
                 logger.info(f"Auto-Capture: {target['label']} (ID:{track_id})")
                 break

# Start Background Threads
vision_thread = Thread(target=vision_processing_loop, daemon=True)
vision_thread.start()

def broadcast_loop():
    global step_broadcast
    while True:
        broadcast_event.wait()
        broadcast_event.clear()
        
        data_to_send = None
        with state_lock:
            if shared_data and step_broadcast < step:
                data_to_send = shared_data
                step_broadcast = step
        
        if data_to_send:
            # Emit to frontend
            socketio.emit('telemetry_update', data_to_send)

bg_thread = Thread(target=broadcast_loop, daemon=True)
bg_thread.start()

@socketio.on('connect')
def handle_connect():
    logger.info("Frontend Client Connected")

@socketio.on('send_command')
def handle_frontend_command(data):
    cmd = data.get('command')
    if cmd:
        web_command['racer'] = cmd
        logger.info(f"Socket Command: {cmd}")

@socketio.on('control')
def handle_control(data):
    global web_command
    # data: {'throttle': X, 'steering': Y}
    # We store this to command the rover
    web_command['throttle'] = float(data.get('throttle', 0))
    web_command['steering'] = float(data.get('steering', 0))

@socketio.on('set_kinematics')
def handle_kinematics(data):
    # data: {'mode': 'jetracer' | 'ugv'}
    mode = data.get('mode', 'jetracer')
    if mapper:
        mapper.set_kinematics(mode)
    print(f"Server: Set Kinematics to {mode}")

@socketio.on('reset_map')
def handle_reset_map(data):
    if mapper:
        mapper.reset_map()
    if vision:
        vision.reset_tracker()  # Also reset the object tracker
    # Broadcast to all clients to clear their local history (trails, graphs)
    socketio.emit('map_reset') 
    print("Server: Map Reset Command Received & Broadcasted")

@app.route('/capture', methods=['POST'])
def capture_detection():
    """Request a high-res capture from the rover"""
    global capture_pending, capture_metadata
    
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON body'}), 400
    
    box = data.get('box')  # [x1, y1, x2, y2]
    label = data.get('label', 'unknown')
    radius_m = data.get('radius_m', 0.0) # Extract radius if available
    
    if not box or len(box) != 4:
        return jsonify({'status': 'error', 'message': 'Invalid box'}), 400
    
    # Set pending flag for rover to pick up
    capture_metadata = {'box': box, 'label': label, 'radius_m': radius_m}
    capture_pending = True
    logger.info(f"Capture requested for {label} at {box}")
    
    return jsonify({'status': 'pending', 'message': 'Capture request sent to rover'})

@app.route('/hires_capture', methods=['POST'])
def receive_hires_capture():
    """Receive high-res capture from rover and save cropped ROI"""
    global capture_metadata
    
    img_b64 = request.form.get('hires_image', '')
    if not img_b64:
        return jsonify({'status': 'error', 'message': 'No image data'}), 400
    
    try:
        img_bytes = base64.b64decode(img_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        hires_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.error(f"HiRes Decode Error: {e}")
        return jsonify({'status': 'error', 'message': 'Decode failed'}), 400
    
    # Get metadata
    box = capture_metadata.get('box', [0, 0, 100, 100])
    label = capture_metadata.get('label', 'unknown')
    
    # Scale box from 416x416 to high-res dimensions
    h_hires, w_hires = hires_frame.shape[:2]
    scale_x = w_hires / 416
    scale_y = h_hires / 416
    
    x1 = int(box[0] * scale_x)
    y1 = int(box[1] * scale_y)
    x2 = int(box[2] * scale_x)
    y2 = int(box[3] * scale_y)
    
    # Clamp
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w_hires, x2), min(h_hires, y2)
    
    if x2 <= x1 or y2 <= y1:
        return jsonify({'status': 'error', 'message': 'Invalid crop region'}), 400
    
    cropped = hires_frame[y1:y2, x1:x2]
    
    # Save
    os.makedirs(DETECTIONS_FOLDER, exist_ok=True)
    safe_label = label.replace(' ', '_').lower()
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_label}_{timestamp}_hires.jpg"
    filepath = os.path.join(DETECTIONS_FOLDER, filename)
    
    cv2.imwrite(filepath, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info(f"HiRes Captured: {filepath} ({cropped.shape[1]}x{cropped.shape[0]})")
    
    # Track findings if mission active
    if mission_manager.active:
        mission_manager.snapshots.append(filename)
        
        # Get metadata
        radius_m = capture_metadata.get('radius_m', 0.0)
        
        # Detailed Finding Entry
        finding_entry = {
            'type': label,
            'radius_m': float(radius_m),
            'timestamp': time.time(),
            'snapshot': filename
        }
        mission_manager.detailed_findings.append(finding_entry)

        # Classify finding for report stats
        if 'alien' in label.lower():
            mission_manager.findings['aliens'] += 1
        else:
            mission_manager.findings['craters'] += 1
    
    capture_metadata = {}  # Clear metadata
    return jsonify({'status': 'ok', 'filename': filename})

@app.route('/mission/start', methods=['POST'])
def start_mission():
    data = request.get_json()
    dist_cm = float(data.get('distance_cm', 100))
    mission_type = data.get('type', 'linear')
    save_report = data.get('save_report', True)
    
    current_pose = shared_data.get('telemetry', {}).get('pose', {'x':0, 'y':0, 'theta':0})
    
    mission_manager.start_mission(dist_cm, current_pose, mission_type=mission_type, save_report=save_report)
    return jsonify({'status': 'ok', 'message': 'Mission Started'})

@app.route('/mission/stop', methods=['POST'])
def stop_mission():
    mission_manager.abort()
    # Force stop rover
    web_command['throttle'] = 0.0
    web_command['steering'] = 0.0
    return jsonify({'status': 'ok', 'message': 'Mission Aborted & Data Discarded'})

@app.route('/mission/report', methods=['GET'])
def get_mission_report():
    """Get a mission report JSON file. Defaults to latest, or specific folder if provided."""
    try:
        reports_dir = 'public/reports'
        folder = request.args.get('folder')
        
        if not os.path.exists(reports_dir):
            return jsonify({'status': 'error', 'message': 'No reports found'}), 404
            
        if folder:
            # Security check: prevent directory traversal
            if '..' in folder or '/' in folder or '\\' in folder:
                 return jsonify({'status': 'error', 'message': 'Invalid folder name'}), 400
            
            report_path = os.path.join(reports_dir, folder, 'report.json')
            if not os.path.exists(report_path):
                return jsonify({'status': 'error', 'message': 'Report not found'}), 404
            
            target_folder = folder
        else:
            # Find latest
            folders = [f for f in os.listdir(reports_dir) if os.path.isdir(os.path.join(reports_dir, f))]
            if not folders:
                return jsonify({'status': 'error', 'message': 'No report folders found'}), 404
            
            # Sort by modification time (newest first)
            folders.sort(key=lambda f: os.path.getmtime(os.path.join(reports_dir, f)), reverse=True)
            target_folder = folders[0]
            report_path = os.path.join(reports_dir, target_folder, 'report.json')
            
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        # Add folder info for frontend
        report_data['folder'] = target_folder
        
        return jsonify({'status': 'ok', 'report': report_data})
    except Exception as e:
        logger.error(f"Error fetching report: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/mission/history', methods=['GET'])
def get_mission_history():
    """Get list of all past missions with basic summary"""
    try:
        reports_dir = 'public/reports'
        if not os.path.exists(reports_dir):
             return jsonify({'status': 'ok', 'history': []})
        
        history = []
        folders = [f for f in os.listdir(reports_dir) if os.path.isdir(os.path.join(reports_dir, f))]
        
        for folder in folders:
            try:
                report_path = os.path.join(reports_dir, folder, 'report.json')
                if os.path.exists(report_path):
                    with open(report_path, 'r') as f:
                        data = json.load(f)
                        
                    # Extract summary data
                    history.append({
                        'id': data.get('id', folder),
                        'folder': folder,
                        'task': data.get('task', 'Unknown Mission'),
                        'startTime': data.get('startTime', 0),
                        'duration': data.get('endTime', 0) - data.get('startTime', 0),
                        'distance': data.get('totalDistance', 0),
                        'findings': data.get('findings', {'craters': 0, 'aliens': 0}),
                        'snapshot_count': len(data.get('snapshots', []))
                    })
            except Exception as e:
                logger.warning(f"Error reading report in {folder}: {e}")
                continue
        
        # Sort by start time (newest first)
        history.sort(key=lambda x: x['startTime'], reverse=True)
        
        return jsonify({'status': 'ok', 'history': history})
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



def process_server_capture(frame, metadata):
    """Save a crop from the given frame directly on the server."""
    try:
        if frame is None: return False
        
        box = metadata.get('box', [0, 0, 100, 100])
        label = metadata.get('label', 'unknown')
        
        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]
        
        # Calculate box dimensions
        box_w = x2 - x1
        box_h = y2 - y1
        
        # Expand by 10% on each side for more context
        padding_x = box_w * 0.1
        padding_y = box_h * 0.1
        
        x1_expanded = x1 - padding_x
        y1_expanded = y1 - padding_y
        x2_expanded = x2 + padding_x
        y2_expanded = y2 + padding_y
        
        # Clamp to frame boundaries
        x1_final = max(0, int(x1_expanded))
        y1_final = max(0, int(y1_expanded))
        x2_final = min(w, int(x2_expanded))
        y2_final = min(h, int(y2_expanded))
        
        if x2_final <= x1_final or y2_final <= y1_final: return False
        
        cropped = frame[y1_final:y2_final, x1_final:x2_final]
        
        # Determine save folder
        if mission_manager.active and mission_manager.mission_folder:
            save_folder = f"public/detections/{mission_manager.mission_folder}"
        else:
            save_folder = DETECTIONS_FOLDER
        
        os.makedirs(save_folder, exist_ok=True)
        safe_label = label.replace(' ', '_').lower()
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_label}_{timestamp}_capture.jpg"
        filepath = os.path.join(save_folder, filename)
        
        cv2.imwrite(filepath, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        # Track findings if mission active
        if mission_manager.active:
            mission_manager.snapshots.append(filename)
            
            radius_m = metadata.get('radius_m', 0.0)
            
            finding_entry = {
                'type': label,
                'radius_m': float(radius_m),
                'timestamp': time.time(),
                'snapshot': filename
            }
            mission_manager.detailed_findings.append(finding_entry)
            
            if 'alien' in label.lower():
                mission_manager.findings['aliens'] += 1
            else:
                mission_manager.findings['craters'] += 1
                
        return True
    except Exception as e:
        logger.error(f"Server Capture Failed: {e}")
        return False

if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible from LAN
    print(">> Starting Mission Control Server...")
    socketio.run(app, host='0.0.0.0', port=8485)
