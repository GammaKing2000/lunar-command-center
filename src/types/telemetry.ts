export interface Pose {
  x: number;
  y: number;
  theta: number;
}

export interface Telemetry {
  throttle: number;
  steering: number;
  pose: Pose;
}

export interface LiveCrater {
  label?: string;
  box: [number, number, number, number]; // [x, y, w, h]
  depth: number;
  radius_m?: number;
  track_id?: number;
}

export interface MapCrater {
  id?: number;
  x: number;
  y: number;
  radius: number;
  depth?: number;
  label?: string;
}

export interface Perception {
  live_craters: LiveCrater[];
  map_craters: MapCrater[];
  resolution?: [number, number];
  detection_files?: string[];
}

export interface TelemetryPayload {
  step?: number;
  img_base64: string;
  telemetry: Telemetry;
  perception: Perception;
}
