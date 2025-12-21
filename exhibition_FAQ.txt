LUNAR COMMAND CENTER - EXHIBITION TECHNICAL ANSWERS
===================================================

GENERAL ARCHITECTURE
--------------------
1. What is the high-level architecture of this system?
   ANSWER: The system follows a Client-Server-Rover architecture:
   - **Rover (Edge)**: A Jetson Nano-based robot that handles low-level hardware control (motors, servos) and captures video. It runs `moonrover_brain_rover.py`.
   - **Server (Processing Core)**: A Flask-based Python server (`moonrover_server.py`) running on a laptop. It acts as the central brain, processing the heavy Computer Vision workloads (YOLOv8, SLAM, 3D Reconstruction), managing mission state, and hosting the web interface.
   - **Frontend (UI)**: A React-based Single Page Application (SPA) that provides the Mission Control dashboard, displaying the live video feed, telemetry charts, and the 3D map.

2. Why did you select this specific technology stack (React, Flask, Jetson Nano)?
   ANSWER:
   - **React/Vite**: Chosen for its component-based architecture which is ideal for complex dashboards like Mission Control. It allows efficient updates of high-frequency telemetry data without reloading the page.
   - **Flask**: A lightweight Python web framework that easily integrates with PyTorch and standard AI libraries. It simplifies bridging the gap between the AI backend and the web frontend.
   - **Jetson Nano**: Selected for the rover because it provides GPU acceleration for edge inference (if needed) and standardized GPIO interfaces (Jetson.GPIO) for motor control, offering a balance between power and performance.

3. How do the different components (Rover, Server, Frontend) communicate?
   ANSWER:
   - **Video**: Transmitted via HTTP Streaming (MJPEG) for low latency and broad compatibility.
   - **Telemetry & Control**: Uses **Socket.IO** (WebSockets) for real-time, bi-directional communication. The Frontend sends control commands (throttle, steering) to the Server, which forwards them to the Rover. Conversely, the Rover sends sensor data to the Server, which broadcasts it to the Frontend.

COMMUNICATION & NETWORKING
--------------------------
4. How is the live video feed transmitted from the rover to the browser?
   ANSWER: The system uses a continuous **MJPEG (Motion JPEG)** stream served over HTTP (`/video_feed` endpoint). The server captures frames, processes them (adds AI overlays), encodes them as JPEG, and pushes them to the browser as a multipart HTTP response (`multipart/x-mixed-replace`).

5. Why did you choose HTTP streaming over standard protocols like RTSP or WebRTC?
   ANSWER: While WebRTC offers lower latency for audio/video, **MJPEG over HTTP** was chosen for its simplicity and robustness in a prototyping environment. It requires no complex signaling servers (STUN/TURN), is natively supported by standard HTML `<img>` tags, and allows easy interception of frames on the server for per-frame Computer Vision processing before display. The latency (<100ms on LAN) is sufficient for this application.

6. What is the end-to-end latency of the system?
   ANSWER: The system is designed for low latency teleoperation.
   - **Control Latency**: ~20-50ms (Gamepad -> Server -> Rover).
   - **Video Latency**: ~100-150ms (Camera -> Server AI Processing -> Browser).
   This is achieved by using low-overhead MJPEG streaming and efficient threading in Python.

7. How do you synchronize telemetry data with the video feed?
   ANSWER: In `moonrover_server.py`, the `receive_telemetry` endpoint acts as the primary synchronization loop. When the rover sends a packet (containing both the latest image frame and sensor data), the server processes them together. The resulting AI detection data is bundled with the telemetry into a single state object (`shared_data`) and broadcast to the frontend, ensuring the map and gauges update in lockstep with the visual feed.

COMPUTER VISION & AI
--------------------
8. How does the Crater Detection algorithm work?
   ANSWER: We use **YOLOv8 (You Only Look Once)**, a state-of-the-art object detection model.
   - **Training**: It was fine-tuned on a custom dataset of lunar analogs (rocks, craters) to recognize classes like `crater`, `alien`, and `water-sight`.
   - **Inference**: The `VisionSystem` class loads the `.pt` model and runs inference on every incoming frame. It utilizes the GPU (CUDA) on the laptop server for real-time performance (~30 FPS).
   - **Segmentation**: The model also predicts segmentation masks (polygons), allowing us to calculate the precise area and shape of detected objects, not just their bounding boxes.

9. Is the object detection running on the Edge (Jetson) or the Server?
   ANSWER: Currently, it is running on the **Server (Laptop)**.
   - **Reasoning**: While the Jetson Nano is capable of running lighter models, the Laptop's discrete GPU offers significantly higher throughput. Offloading the heavy lifting to the server allows the rover to remain lightweight and energy-efficient, dedicating its resources to motor control and video streaming.

10. How do you estimate the **physical distance** of a detected crater from the rover?
    ANSWER: We use **Inverse Projective Mapping (IPM)**, specifically a geometric heuristic based on the "flat ground assumption". 
    - Since the camera is at a fixed height and angle, pixels lower in the image (higher Y-coordinate) correspond to points closer to the rover.
    - We map the normalized Y-coordinate of the object's base to real-world distance using a calibrated function: `Distance = K / (y_normalized)`. `K` is a constant derived from the camera's mounting geometry.

11. How is the actual **radius/size** of the crater calculated from the 2D bounding box?
    ANSWER:
    1. **Pixel Area**: We count the pixels in the segmentation mask returned by YOLO.
    2. **Projection**: We estimate a "meters-per-pixel" ratio at the object's calculated distance. `m_per_px ≈ Distance / (Focal_Length_Scale)`.
    3. **Real Area**: `Area_m2 = Area_pixels * (m_per_px)^2`.
    4. **Radius**: Assuming a circular approximation, `Radius = sqrt(Area_m2 / π)`.

12. What specific mathematical formulas are used for the 2D-to-3D projection (pinhole camera model)?
    ANSWER: The system simplifies the classic Pinhole Camera Model. For a point on the ground:
    - $Z$ (Depth) $\approx H / \tan(\theta + \alpha)$
    - Where $H$ is camera height, $\theta$ is camera tilt angle, and $\alpha$ is the angular offset of the pixel from the optical center.
    - In our simplified code (`vision_system.py`), this is approximated as `dist_m = DEPTH_CALIBRATION_K / y_norm`, where `y_norm` represents the vertical position in the frame.

13. How does the camera's height and tilt angle affect the geometric calculations?
    ANSWER: They are fundamental calibration parameters:
    - **Height (10cm)**: Determines the scale. A higher camera sees further but with less ground resolution.
    - **Tilt (75°)**: Defines the Field of View's intersection with the ground.
    - These values are hardcoded in `vision_system.py` (`CAMERA_HEIGHT_M`, `CAMERA_ANGLE_DEG`). If these physical parameters change on the rover, the software constant `K` must be recalibrated, or distance estimates will be incorrect.

14. Can you explain the 3D Reconstruction pipeline?
    ANSWER: The pipeline consists of two stages triggered via the `/upload_sfm_data` endpoint:
    1. **Structure from Motion (SfM)** using **COLMAP**: This analyzes a sequence of 2D images to find common features (SIFT), matches them, and mathematically reconstructs the sparse 3D point cloud and camera poses (`sfm_processor.py`).
    2. **3D Gaussian Splatting**: Using the sparse cloud from COLMAP, we train a Gaussian Splatting model (`gaussian_splatting_worker.py`). This represents the scene as millions of 3D Gaussians (blobs with color/opacity), allowing for photorealistic real-time rendering.

15. What is Gaussian Splatting and why did you use it for this project?
    ANSWER: **3D Gaussian Splatting** is a modern rendering technique (released 2023) that represents 3D scenes as soft, ellipsoidal particles rather than triangles (meshes) or neural networks (NeRFs).
    - **Why**: It offers **faster training** than NeRFs (minutes vs hours) and **real-time web rendering** (60fps+ via WebGL/WebGPU). This makes it perfect for allowing exhibition visitors to interactively explore the reconstructed lunar surface in the browser.

16. How does the system handle feature matching in low-texture lunar environments?
    ANSWER: Lunar surfaces are notoriously difficult for computer vision due to lack of color and repetitive textures.
    - We rely on **COLMAP's SIFT features**, which are robust to scale and rotation.
    - We ensure the captured dataset has high overlap (>80%) between frames.
    - In the `MapManagerLaptop`, we use a tracking algorithm (`object_tracker.py`) that uses **IoU (Intersection over Union)** to track specific landmarks (craters) across frames, creating a persistent map even if the visual odometry drifts.

HARDWARE & CONTROL
------------------
17. How is the rover's rigorous movement logic implemented?
    ANSWER: The movement logic supports two kinematic models (`mapping_system_laptop.py`):
    - **Ackermann (JetRacer)**: Used for car-like steering. $AngularVelocity = Velocity / Radius$.
    - **Differential Drive (UGV)**: Used for tank-like steering (skid steer).
    - The `MissionManager` in `moonrover_server.py` implements a state machine for autonomous missions (e.g., "drive straight 100cm"), employing a feedback loop that monitors estimated distance traveled and adjusts throttle to maintain a straight path.

18. How do you interface with the hardware sensors (Voltage, Current)?
    ANSWER: The Rover uses Python's SMBus library to communicate with I2C sensors.
    - **INA219**: A dedicated high-side DC current and voltage sensor module. It provides precise measurements of the battery state, which are read by `moonrover_brain_rover.py` and sent in the telemetry packet.

19. How does the gamepad control signal reach the motors?
    ANSWER:
    1. **Capture**: `gamepad_control_rover.py` reads the physical controller using `XInput` (Windows) or `inputs` (Linux).
    2. **Transmission**: Inputs are normalized (-1.0 to 1.0) and sent via HTTP/SocketIO to `moonrover_server.py`.
    3. **Routing**: The server updates the 'web_command' state.
    4. **Execution**: The rover polls the server, receives the command, and drives the **PCA9685 PWM driver** (via I2C) to set the duty cycle for the steering servo and DC motor controller (ESC).

CHALLENGES & OPTIMIZAITON
-------------------------
20. What was the most difficult technical challenge you faced?
    ANSWER: **Integrating the 3D Reconstruction pipeline automation.** Bridging the gap between a raw zip file upload from the frontend and a fully trained `.splat` model required chaining multiple complex processes (Unzipping -> COLMAP SfM -> Torch Training). Managing the dependencies (CUDA, PyTorch, COLMAP) and handling failure cases (e.g., "not enough features") within a headless server environment was significantly complex.

21. How did you optimize the system for performance and low latency?
    ANSWER:
    - **Async/Threading**: The server uses separate threads for Video Capture, telemetry broadcasting, and Mission logic to ensure the video stream never blocks the control signals.
    - **Resolution Scaling**: Vision processing runs on 640x640 images (optimal for YOLO), while the display stream is compressed to ensure smooth transmission.
    - **Lazy Loading**: The frontend only requests heavy assets (like report logs or detection images) when the user actively navigates to those tabs.

22. How did you ensure cross-platform compatibility between Linux (Rover) and Windows (Server)?
    ANSWER:
    - **Conditional Imports**: Files like `gamepad_control_rover.py` actively check for OS-specific libraries (`XInput` for Windows vs `inputs` for Linux) and load the correct one dynamically.
    - **Path Handling**: We use `os.path.join` everywhere to handle the difference between forward slashes `/` (Linux) and backslashes `\` (Windows).
    - **Encoding**: We handle standard Unicode/ASCII issues in logging (replacing checkmarks `✓` with `[OK]` on non-compatible terminals) to prevent crashes on Windows consoles.
