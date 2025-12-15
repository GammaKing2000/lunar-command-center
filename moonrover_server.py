import os
import json
import logging
from threading import Thread, Event
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MoonServer')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moon_rover_secret'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

# State
web_command = {'racer': 'run'}
shared_data = {}
step = 0
step_broadcast = 0
broadcast_event = Event()

@app.route('/')
def index():
    return "Moon Rover Mission Control Server is Running."

@app.route('/jetson_command', methods=['GET'])
def get_jetson_command():
    cmd = request.args.get('racer')
    if cmd:
        web_command['racer'] = cmd
        logger.info(f"Command update: {cmd}")
    return jsonify(web_command)

@app.route('/display', methods=['POST'])
def receive_telemetry():
    global step, shared_data
    
    # 1. Extract Raw Data
    img_base64 = request.form.get('img_base64', '')
    throttle = request.form.get('throttle', type=float, default=0.0)
    steer_real = request.form.get('steer_real', type=float, default=0.0)
    
    # 2. Parse JSON fields
    def parse_json(key, default):
        raw = request.form.get(key, default)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except:
                return default
        return raw

    pose = parse_json('pose', {'x': 0, 'y': 0, 'theta': 0})
    craters = parse_json('craters', [])
    map_craters = parse_json('map_craters', [])
    
    # 3. Update State
    step += 1
    shared_data = {
        'step': step,
        'img_base64': img_base64,
        'telemetry': {
            'throttle': throttle,
            'steering': steer_real,
            'pose': pose
        },
        'perception': {
            'live_craters': craters,
            'map_craters': map_craters
        }
    }
    
    broadcast_event.set()
    return jsonify({'status': 'ok', 'command': web_command['racer']})

def broadcast_loop():
    global step_broadcast
    while True:
        broadcast_event.wait()
        broadcast_event.clear()
        
        if shared_data and step_broadcast < step:
            # Emit to frontend
            socketio.emit('telemetry_update', shared_data)
            step_broadcast = step

# Start Background Thread
bg_thread = Thread(target=broadcast_loop, daemon=True)
bg_thread.start()

@socketio.on('connect')
def handle_connect():
    logger.info("Frontend Client Connected")

@socketio.on('send_command')
def handle_frontend_command(data):
    # Allow frontend to send commands via socket too
    cmd = data.get('command')
    if cmd:
        web_command['racer'] = cmd
        logger.info(f"Socket Command: {cmd}")

if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible from LAN
    socketio.run(app, host='0.0.0.0', port=8485)
