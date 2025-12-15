# Moon Rover Mission Control Dashboard

A futuristic, sci-fi mission control interface for monitoring and controlling a lunar rover. Built with React, Tailwind CSS, and Socket.IO.

![Dashboard Preview](https://img.shields.io/badge/Status-Active-cyan)

## Features

- **Live Vision Panel** - Real-time video feed from the rover with HUD overlay, crosshairs, and crater detection bounding boxes
- **Tactical Map** - 2D top-down view showing rover position, heading, movement trail, and detected craters
- **Telemetry Deck** - Real-time gauges for throttle and steering, plus a rolling depth chart
- **Mission Clock** - Elapsed mission time in T+ HH:MM:SS format
- **Status Bar** - Connection status, data step counter, and system health

## Tech Stack

- React 18 + TypeScript
- Tailwind CSS with custom sci-fi theme
- Socket.IO for real-time telemetry
- Recharts for data visualization
- Lucide React icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Start the development server
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Backend Server

The dashboard connects to a Socket.IO server at `http://192.168.2.109:8485`. To run the backend:

```bash
# Install Python dependencies
pip install flask flask-cors flask-socketio

# Run the server
python moonrover_server.py
```

## Telemetry Data Format

The dashboard receives `telemetry_update` events with the following payload:

```json
{
  "img_base64": "base64-encoded-image",
  "telemetry": {
    "throttle": -1.0 to 1.0,
    "steering": -1.0 to 1.0,
    "pose": { "x": meters, "y": meters, "theta": radians }
  },
  "perception": {
    "live_craters": [{ "box": [x, y, w, h], "depth": meters }],
    "map_craters": [{ "x": meters, "y": meters, "radius": meters }]
  }
}
```

## Configuration

To change the Socket.IO server address, update the URL in `src/hooks/useTelemetry.ts`:

```typescript
const socket = io('http://YOUR_SERVER_IP:8485');
```

## Project Structure

```
src/
├── components/
│   ├── dashboard/
│   │   ├── LiveVisionPanel.tsx  # Video feed with HUD
│   │   ├── TacticalMap.tsx      # 2D rover map
│   │   ├── TelemetryDeck.tsx    # Gauges and charts
│   │   ├── DepthChart.tsx       # Rolling depth graph
│   │   └── ...
│   └── MissionControl.tsx       # Main layout
├── hooks/
│   └── useTelemetry.ts          # Socket.IO connection
├── types/
│   └── telemetry.ts             # TypeScript interfaces
└── index.css                    # Theme and styles
```

## License

MIT
