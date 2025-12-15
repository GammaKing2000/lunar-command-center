import { useMemo } from 'react';
import { PanelWrapper } from './PanelWrapper';
import { Pose, MapCrater } from '@/types/telemetry';
import { Map } from 'lucide-react';

interface TacticalMapProps {
  currentPose: Pose | null;
  positionHistory: Pose[];
  mapCraters: MapCrater[];
}

const MAP_WIDTH = 300;
const MAP_HEIGHT = 200;
const WORLD_WIDTH = 3; // 3 meters
const WORLD_HEIGHT = 2; // 2 meters

function worldToScreen(x: number, y: number): { sx: number; sy: number } {
  const sx = (x / WORLD_WIDTH) * MAP_WIDTH;
  const sy = MAP_HEIGHT - (y / WORLD_HEIGHT) * MAP_HEIGHT; // Flip Y axis
  return { sx, sy };
}

export function TacticalMap({ currentPose, positionHistory, mapCraters }: TacticalMapProps) {
  const gridLines = useMemo(() => {
    const lines = [];
    // Vertical lines (every 0.5m)
    for (let x = 0; x <= WORLD_WIDTH; x += 0.5) {
      const { sx } = worldToScreen(x, 0);
      lines.push(
        <line
          key={`v-${x}`}
          x1={sx}
          y1={0}
          x2={sx}
          y2={MAP_HEIGHT}
          stroke="hsl(var(--grid-line))"
          strokeWidth={x % 1 === 0 ? 1 : 0.5}
          opacity={x % 1 === 0 ? 0.4 : 0.2}
        />
      );
    }
    // Horizontal lines (every 0.5m)
    for (let y = 0; y <= WORLD_HEIGHT; y += 0.5) {
      const { sy } = worldToScreen(0, y);
      lines.push(
        <line
          key={`h-${y}`}
          x1={0}
          y1={sy}
          x2={MAP_WIDTH}
          y2={sy}
          stroke="hsl(var(--grid-line))"
          strokeWidth={y % 1 === 0 ? 1 : 0.5}
          opacity={y % 1 === 0 ? 0.4 : 0.2}
        />
      );
    }
    return lines;
  }, []);

  const trail = useMemo(() => {
    if (positionHistory.length < 2) return null;
    
    const points = positionHistory.map(p => {
      const { sx, sy } = worldToScreen(p.x, p.y);
      return `${sx},${sy}`;
    }).join(' ');

    return (
      <polyline
        points={points}
        fill="none"
        stroke="hsl(var(--hud-cyan))"
        strokeWidth={2}
        strokeOpacity={0.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    );
  }, [positionHistory]);

  const roverMarker = useMemo(() => {
    if (!currentPose) return null;

    const { sx, sy } = worldToScreen(currentPose.x, currentPose.y);
    // Triangle pointing in direction of theta
    // theta=0 is facing right (positive X), we need to adjust for SVG coordinate system
    const angle = -currentPose.theta * (180 / Math.PI) + 90; // Convert to degrees and adjust

    return (
      <g transform={`translate(${sx}, ${sy}) rotate(${angle})`}>
        {/* Glow effect */}
        <polygon
          points="0,-12 8,8 -8,8"
          fill="hsl(var(--hud-cyan))"
          opacity={0.3}
          filter="blur(4px)"
        />
        {/* Rover triangle */}
        <polygon
          points="0,-10 6,6 -6,6"
          fill="hsl(var(--hud-cyan))"
          stroke="hsl(var(--hud-cyan-glow))"
          strokeWidth={2}
        />
        {/* Center dot */}
        <circle r={2} fill="hsl(var(--foreground))" />
      </g>
    );
  }, [currentPose]);

  const craterMarkers = useMemo(() => {
    return mapCraters.map((crater, index) => {
      const { sx, sy } = worldToScreen(crater.x, crater.y);
      const radiusPixels = (crater.radius / WORLD_WIDTH) * MAP_WIDTH;

      return (
        <g key={crater.id || index}>
          {/* Crater fill */}
          <circle
            cx={sx}
            cy={sy}
            r={Math.max(radiusPixels, 5)}
            fill="hsl(var(--alert-red))"
            fillOpacity={0.3}
            stroke="hsl(var(--alert-red))"
            strokeWidth={1}
          />
          {/* Crater label */}
          <text
            x={sx}
            y={sy - radiusPixels - 5}
            textAnchor="middle"
            fontSize={8}
            fill="hsl(var(--alert-red))"
            fontFamily="JetBrains Mono"
          >
            C{crater.id || index + 1}
          </text>
        </g>
      );
    });
  }, [mapCraters]);

  return (
    <PanelWrapper 
      title="Tactical Map" 
      badge={
        <span className="text-xs font-mono text-muted-foreground">
          {WORLD_WIDTH}m × {WORLD_HEIGHT}m
        </span>
      }
      className="h-full"
    >
      <div className="relative w-full h-full flex items-center justify-center">
        {currentPose ? (
          <svg
            width={MAP_WIDTH}
            height={MAP_HEIGHT}
            viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
            className="border border-border/30 rounded bg-space-black/50"
          >
            {/* Grid */}
            {gridLines}

            {/* Trail */}
            {trail}

            {/* Craters */}
            {craterMarkers}

            {/* Rover */}
            {roverMarker}
          </svg>
        ) : (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <Map className="w-12 h-12 opacity-30" />
            <span className="text-xs font-mono">NO POSITION DATA</span>
          </div>
        )}

        {/* Coordinate Display */}
        {currentPose && (
          <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-space-black/70 text-xs font-mono">
            <div className="flex justify-between text-muted-foreground">
              <span>X: <span className="text-foreground">{currentPose.x.toFixed(3)}m</span></span>
              <span>Y: <span className="text-foreground">{currentPose.y.toFixed(3)}m</span></span>
              <span>θ: <span className="text-foreground">{(currentPose.theta * (180/Math.PI)).toFixed(1)}°</span></span>
            </div>
          </div>
        )}
      </div>
    </PanelWrapper>
  );
}
