import os
import json
import logging
import base64
import cv2
import numpy as np
import time
from threading import Thread, Event, Lock
from flask import Flask, request, jsonify
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
mapper = MapManagerLaptop(width_m=1.2, height_m=1.92) if MapManagerLaptop else None

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

@app.route('/')
def index():
    return "Moon Rover Mission Control Server (BRAIN ACTIVE)"

@app.route('/jetson_command', methods=['GET'])
def get_jetson_command():
    cmd = request.args.get('racer')
    if cmd:
        web_command['racer'] = cmd
        logger.info(f"Command update: {cmd}")
    return jsonify(web_command)

@app.route('/display', methods=['POST'])
def receive_telemetry():
    global step, shared_data, last_telemetry_time
    
    current_time = time.time()
    dt = current_time - last_telemetry_time
    last_telemetry_time = current_time
    
    # 1. Extract Raw Data from Rover
    img_b64_raw = request.form.get('img_base64', '')
    throttle = request.form.get('throttle', type=float, default=0.0)*(-1)
    steer_real = request.form.get('steer_real', type=float, default=0.0)
    
    # Decode Image
    img = None
    if img_b64_raw and vision:
        try:
            # Fix padding if necessary (though usually standard b64 is fine)
            img_bytes = base64.b64decode(img_b64_raw)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"Image Decode Error: {e}")

    # 2. Run Laptop-Side Perception
    global yolo_frame_counter, cached_craters, cached_annotated_b64
    
    # A. Vision (Object Detection) - Run YOLO every 5th frame for performance
    live_craters = cached_craters
    annotated_b64 = img_b64_raw  # Default to raw image
    
    if img is not None:
        yolo_frame_counter += 1
        
        if vision and yolo_frame_counter % 1 == 0:  # Real-time: every frame
            # Run YOLO on this frame
            live_craters, annotated_frame = vision.process_frame(img)
            cached_craters = live_craters
            
            # Re-encode annotated image for the Dashboard
            _, buf = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            cached_annotated_b64 = base64.b64encode(buf).decode()
            annotated_b64 = cached_annotated_b64
        elif cached_annotated_b64:
            # Use cached YOLO output for non-YOLO frames
            annotated_b64 = cached_annotated_b64
        else:
            # No YOLO yet, just send raw frame with minimal re-encode
            _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 60])
            annotated_b64 = base64.b64encode(buf).decode()

    # B. Mapping (SLAM)
    map_status = {'pose': {'x':0,'y':0,'theta':0}, 'craters': []}
    
    if mapper:
        # Update Pose (Dead Reckoning)
        mapper.update_pose(throttle, steer_real, dt)
        
        # Update Map with new crater detections
        # Note: Vision returns 'box' and 'depth'. Mapper needs this.
        if img is not None:
             h, w = img.shape[:2]
             mapper.update_craters(live_craters, w)
             
        map_status = mapper.get_status()

    # 3. Update State for Frontend
    with state_lock:
        step += 1
        shared_data = {
            'step': step,
            'img_base64': annotated_b64, # Show the detections on the UI
            'telemetry': {
                'throttle': throttle,
                'steering': steer_real,
                'pose': map_status['pose']
            },
            'perception': {
                'live_craters': live_craters,
                'map_craters': map_status['craters'],
                'resolution': [img.shape[1], img.shape[0]] if img is not None else [640, 640]
            }
        }
    
    broadcast_event.set()
    return jsonify({'status': 'ok', 'command': web_command['racer']})

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

# Start Background Thread
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

if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible from LAN
    print(">> Starting Mission Control Server...")
    socketio.run(app, host='0.0.0.0', port=8485)
