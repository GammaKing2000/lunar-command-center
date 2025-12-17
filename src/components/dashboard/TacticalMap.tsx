import { useMemo } from 'react';
import { PanelWrapper } from './PanelWrapper';
import { Pose, MapCrater } from '@/types/telemetry';
import { Map, Compass } from 'lucide-react';

interface TacticalMapProps {
  currentPose: Pose | null;
  positionHistory: Pose[];
  mapCraters: MapCrater[];
}

const MAP_WIDTH = 320;
const MAP_HEIGHT = 220;
const WORLD_WIDTH = 3; // 3 meters
const WORLD_HEIGHT = 2; // 2 meters

function worldToScreen(x: number, y: number): { sx: number; sy: number } {
  const sx = (x / WORLD_WIDTH) * MAP_WIDTH;
  const sy = MAP_HEIGHT - (y / WORLD_HEIGHT) * MAP_HEIGHT;
  return { sx, sy };
}

export function TacticalMap({ currentPose, positionHistory, mapCraters }: TacticalMapProps) {
  const gridLines = useMemo(() => {
    const lines = [];
    // Vertical lines (every 0.5m)
    for (let x = 0; x <= WORLD_WIDTH; x += 0.5) {
      const { sx } = worldToScreen(x, 0);
      const isMajor = x % 1 === 0;
      lines.push(
        <line
          key={`v-${x}`}
          x1={sx}
          y1={0}
          x2={sx}
          y2={MAP_HEIGHT}
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={isMajor ? 0.8 : 0.4}
          opacity={isMajor ? 0.3 : 0.15}
        />
      );
    }
    // Horizontal lines (every 0.5m)
    for (let y = 0; y <= WORLD_HEIGHT; y += 0.5) {
      const { sy } = worldToScreen(0, y);
      const isMajor = y % 1 === 0;
      lines.push(
        <line
          key={`h-${y}`}
          x1={0}
          y1={sy}
          x2={MAP_WIDTH}
          y2={sy}
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={isMajor ? 0.8 : 0.4}
          opacity={isMajor ? 0.3 : 0.15}
        />
      );
    }
    return lines;
  }, []);

  const trail = useMemo(() => {
    if (positionHistory.length < 2) return null;
    
    // Create gradient trail effect
    const segments = [];
    for (let i = 1; i < positionHistory.length; i++) {
      const prev = worldToScreen(positionHistory[i-1].x, positionHistory[i-1].y);
      const curr = worldToScreen(positionHistory[i].x, positionHistory[i].y);
      const opacity = 0.1 + (i / positionHistory.length) * 0.6;
      
      segments.push(
        <line
          key={`trail-${i}`}
          x1={prev.sx}
          y1={prev.sy}
          x2={curr.sx}
          y2={curr.sy}
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={2}
          strokeOpacity={opacity}
          strokeLinecap="round"
        />
      );
    }

    return <g>{segments}</g>;
  }, [positionHistory]);

  const roverMarker = useMemo(() => {
    if (!currentPose) return null;

    const { sx, sy } = worldToScreen(currentPose.x, currentPose.y);
    const angle = -currentPose.theta * (180 / Math.PI) + 90;

    return (
      <g transform={`translate(${sx}, ${sy})`}>
        {/* Outer glow pulse */}
        <circle
          r={18}
          fill="none"
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={1}
          opacity={0.3}
          className="animate-ping"
          style={{ animationDuration: '2s' }}
        />
        
        {/* Detection range circle */}
        <circle
          r={25}
          fill="hsl(var(--hud-cyan))"
          fillOpacity={0.05}
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={0.5}
          strokeDasharray="4 2"
          opacity={0.4}
        />

        <g transform={`rotate(${angle})`}>
          {/* Glow effect */}
          <polygon
            points="0,-14 10,10 -10,10"
            fill="hsl(var(--hud-cyan))"
            opacity={0.4}
            filter="url(#roverGlow)"
          />
          {/* Rover body */}
          <polygon
            points="0,-12 8,8 -8,8"
            fill="hsl(var(--hud-cyan))"
            stroke="hsl(var(--foreground))"
            strokeWidth={1.5}
          />
          {/* Direction indicator */}
          <line
            x1={0}
            y1={-12}
            x2={0}
            y2={-20}
            stroke="hsl(var(--foreground))"
            strokeWidth={2}
            strokeLinecap="round"
          />
        </g>
        
        {/* Center dot */}
        <circle r={3} fill="hsl(var(--foreground))" />
      </g>
    );
  }, [currentPose]);

  const craterMarkers = useMemo(() => {
    return mapCraters.map((crater, index) => {
      const { sx, sy } = worldToScreen(crater.x, crater.y);
      const radiusPixels = Math.max((crater.radius / WORLD_WIDTH) * MAP_WIDTH, 8);

      return (
        <g key={crater.id || index}>
          {/* Crater outer ring */}
          <circle
            cx={sx}
            cy={sy}
            r={radiusPixels + 3}
            fill="none"
            stroke="hsl(var(--hud-cyan))"
            strokeWidth={0.5}
            strokeDasharray="2 2"
            opacity={0.3}
          />
          {/* Crater fill */}
          <circle
            cx={sx}
            cy={sy}
            r={radiusPixels}
            fill="url(#craterGradient)"
            stroke="hsl(var(--hud-cyan))"
            strokeWidth={1.5}
            opacity={0.7}
          />
          {/* Crater center */}
          <circle
            cx={sx}
            cy={sy}
            r={2}
            fill="hsl(var(--hud-cyan))"
            opacity={0.8}
          />
          {/* Crater label */}
          <text
            x={sx}
            y={sy - radiusPixels - 8}
            textAnchor="middle"
            fontSize={9}
            fontWeight="bold"
            fill="hsl(var(--hud-cyan))"
            fontFamily="JetBrains Mono"
            opacity={0.9}
          >
            C{crater.id || index + 1}
          </text>
        </g>
      );
    });
  }, [mapCraters]);

  // Compass rose component
  const compassRose = useMemo(() => (
    <g transform={`translate(${MAP_WIDTH - 30}, 30)`}>
      <circle r={20} fill="hsl(var(--space-black))" fillOpacity={0.6} stroke="hsl(var(--hud-cyan))" strokeWidth={0.5} opacity={0.5} />
      <text y={-8} textAnchor="middle" fontSize={8} fill="hsl(var(--hud-cyan))" fontFamily="Orbitron" fontWeight="bold">N</text>
      <text y={12} textAnchor="middle" fontSize={6} fill="hsl(var(--muted-foreground))" fontFamily="Orbitron">S</text>
      <text x={-10} y={2} textAnchor="middle" fontSize={6} fill="hsl(var(--muted-foreground))" fontFamily="Orbitron">W</text>
      <text x={10} y={2} textAnchor="middle" fontSize={6} fill="hsl(var(--muted-foreground))" fontFamily="Orbitron">E</text>
      <polygon points="0,-15 -3,-8 3,-8" fill="hsl(var(--hud-cyan))" />
    </g>
  ), []);

  // Scale bar
  const scaleBar = useMemo(() => {
    const meterInPixels = MAP_WIDTH / WORLD_WIDTH;
    return (
      <g transform={`translate(10, ${MAP_HEIGHT - 15})`}>
        <line x1={0} y1={0} x2={meterInPixels} y2={0} stroke="hsl(var(--hud-cyan))" strokeWidth={2} />
        <line x1={0} y1={-3} x2={0} y2={3} stroke="hsl(var(--hud-cyan))" strokeWidth={1} />
        <line x1={meterInPixels} y1={-3} x2={meterInPixels} y2={3} stroke="hsl(var(--hud-cyan))" strokeWidth={1} />
        <text x={meterInPixels / 2} y={-6} textAnchor="middle" fontSize={8} fill="hsl(var(--hud-cyan))" fontFamily="JetBrains Mono">1m</text>
      </g>
    );
  }, []);

  return (
    <PanelWrapper 
      title="Tactical Map" 
      badge={
        <div className="flex items-center gap-2">
          <Compass className="w-3.5 h-3.5 text-primary opacity-60" />
          <span className="text-xs font-mono text-muted-foreground">
            {WORLD_WIDTH}m × {WORLD_HEIGHT}m
          </span>
        </div>
      }
      className="h-full"
    >
      <div className="relative w-full h-full flex items-center justify-center p-2">
        {currentPose ? (
          <svg
            width="100%"
            height="100%"
            viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
            preserveAspectRatio="xMidYMid meet"
            className="rounded-sm"
            style={{
              background: 'linear-gradient(180deg, hsl(var(--space-black)) 0%, hsl(var(--panel-bg)) 100%)'
            }}
          >
            {/* Definitions */}
            <defs>
              <filter id="roverGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <radialGradient id="craterGradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="hsl(var(--hud-cyan))" stopOpacity="0.3" />
                <stop offset="70%" stopColor="hsl(var(--hud-cyan))" stopOpacity="0.15" />
                <stop offset="100%" stopColor="hsl(var(--hud-cyan))" stopOpacity="0.05" />
              </radialGradient>
              <linearGradient id="trailGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="hsl(var(--hud-cyan))" stopOpacity="0.1" />
                <stop offset="100%" stopColor="hsl(var(--hud-cyan))" stopOpacity="0.8" />
              </linearGradient>
            </defs>

            {/* Map border glow */}
            <rect
              x={1}
              y={1}
              width={MAP_WIDTH - 2}
              height={MAP_HEIGHT - 2}
              fill="none"
              stroke="hsl(var(--hud-cyan))"
              strokeWidth={1}
              opacity={0.3}
              rx={2}
            />

            {/* Grid */}
            {gridLines}

            {/* Trail */}
            {trail}

            {/* Craters */}
            {craterMarkers}

            {/* Rover */}
            {roverMarker}

            {/* Compass Rose */}
            {compassRose}

            {/* Scale Bar */}
            {scaleBar}
          </svg>
        ) : (
          <div className="flex flex-col items-center gap-3 text-muted-foreground">
            <div className="relative">
              <Map className="w-16 h-16 opacity-20" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-ping" />
              </div>
            </div>
            <span className="text-xs font-mono tracking-wider">AWAITING POSITION DATA</span>
          </div>
        )}

        {/* Coordinate Display - Enhanced */}
        {currentPose && (
          <div className="absolute bottom-0 left-0 right-0 px-3 py-2 bg-gradient-to-t from-space-black/90 via-space-black/70 to-transparent">
            <div className="flex justify-between items-center text-xs font-mono">
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">X:</span>
                <span className="text-primary text-glow-cyan">{currentPose.x.toFixed(3)}m</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Y:</span>
                <span className="text-primary text-glow-cyan">{currentPose.y.toFixed(3)}m</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">θ:</span>
                <span className="text-primary text-glow-cyan">{(currentPose.theta * (180/Math.PI)).toFixed(1)}°</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </PanelWrapper>
  );
}