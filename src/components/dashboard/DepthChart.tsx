import { useMemo } from 'react';
import { PanelWrapper } from './PanelWrapper';
import { TrendingDown, Activity } from 'lucide-react';

interface DepthChartProps {
  depthHistory: { time: number; depth: number }[];
}

const CHART_WIDTH = 320;
const CHART_HEIGHT = 100;
const MAX_POINTS = 40;
const PADDING = { top: 10, right: 10, bottom: 20, left: 10 };

export function DepthChart({ depthHistory }: DepthChartProps) {
  const chartData = useMemo(() => {
    if (depthHistory.length < 2) return null;

    const recentData = depthHistory.slice(-MAX_POINTS);
    const maxDepth = Math.max(...recentData.map(d => d.depth), 0.5);
    const minDepth = Math.min(...recentData.map(d => d.depth), 0);
    const range = maxDepth - minDepth || 0.5;
    
    const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
    const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
    
    const points = recentData.map((d, i) => {
      const x = PADDING.left + (i / (MAX_POINTS - 1)) * innerWidth;
      const y = PADDING.top + innerHeight - ((d.depth - minDepth) / range) * innerHeight;
      return { x, y, depth: d.depth };
    });

    const linePath = `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}`;
    const areaPath = `M ${PADDING.left},${PADDING.top + innerHeight} L ${points.map(p => `${p.x},${p.y}`).join(' L ')} L ${points[points.length - 1].x},${PADDING.top + innerHeight} Z`;

    return {
      linePath,
      areaPath,
      points,
      maxDepth,
      minDepth,
      currentDepth: recentData[recentData.length - 1]?.depth || 0,
      avgDepth: recentData.reduce((sum, d) => sum + d.depth, 0) / recentData.length,
    };
  }, [depthHistory]);

  // Grid lines
  const gridLines = useMemo(() => {
    const lines = [];
    const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
    const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
    
    // Horizontal lines
    for (let i = 0; i <= 4; i++) {
      const y = PADDING.top + (i / 4) * innerHeight;
      lines.push(
        <line
          key={`h-${i}`}
          x1={PADDING.left}
          y1={y}
          x2={CHART_WIDTH - PADDING.right}
          y2={y}
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={0.5}
          opacity={i === 4 ? 0.4 : 0.15}
        />
      );
    }
    
    // Vertical lines
    for (let i = 0; i <= 8; i++) {
      const x = PADDING.left + (i / 8) * innerWidth;
      lines.push(
        <line
          key={`v-${i}`}
          x1={x}
          y1={PADDING.top}
          x2={x}
          y2={PADDING.top + innerHeight}
          stroke="hsl(var(--hud-cyan))"
          strokeWidth={0.5}
          opacity={0.1}
        />
      );
    }
    
    return lines;
  }, []);

  return (
    <PanelWrapper 
      title="Depth Analysis" 
      badge={
        chartData ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Activity className="w-3 h-3 text-primary animate-pulse" />
              <span className="text-sm font-mono font-bold text-primary text-glow-cyan">
                {chartData.currentDepth.toFixed(3)}m
              </span>
            </div>
          </div>
        ) : null
      }
    >
      <div className="relative h-full flex items-center justify-center p-2">
        {chartData ? (
          <div className="relative w-full h-full">
            <svg
              width="100%"
              height="100%"
              viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
              preserveAspectRatio="xMidYMid meet"
              className="overflow-visible"
            >
              <defs>
                {/* Enhanced gradient */}
                <linearGradient id="depthAreaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="hsl(var(--hud-cyan))" stopOpacity={0.4} />
                  <stop offset="50%" stopColor="hsl(var(--hud-cyan))" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="hsl(var(--hud-cyan))" stopOpacity={0.02} />
                </linearGradient>
                
                {/* Line glow effect */}
                <filter id="lineGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* Dot glow */}
                <filter id="dotGlow" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Grid */}
              {gridLines}

              {/* Area fill */}
              <path
                d={chartData.areaPath}
                fill="url(#depthAreaGradient)"
              />

              {/* Main line with glow */}
              <path
                d={chartData.linePath}
                fill="none"
                stroke="hsl(var(--hud-cyan))"
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                filter="url(#lineGlow)"
              />

              {/* Current value dot with glow */}
              {chartData.points.length > 0 && (
                <g>
                  <circle
                    cx={chartData.points[chartData.points.length - 1].x}
                    cy={chartData.points[chartData.points.length - 1].y}
                    r={8}
                    fill="hsl(var(--hud-cyan))"
                    opacity={0.3}
                    filter="url(#dotGlow)"
                  />
                  <circle
                    cx={chartData.points[chartData.points.length - 1].x}
                    cy={chartData.points[chartData.points.length - 1].y}
                    r={5}
                    fill="hsl(var(--hud-cyan))"
                    stroke="hsl(var(--foreground))"
                    strokeWidth={2}
                  />
                </g>
              )}

              {/* Y-axis labels */}
              <text
                x={PADDING.left - 2}
                y={PADDING.top + 4}
                textAnchor="end"
                fontSize={8}
                fill="hsl(var(--muted-foreground))"
                fontFamily="JetBrains Mono"
              >
                {chartData.maxDepth.toFixed(2)}m
              </text>
              <text
                x={PADDING.left - 2}
                y={CHART_HEIGHT - PADDING.bottom}
                textAnchor="end"
                fontSize={8}
                fill="hsl(var(--muted-foreground))"
                fontFamily="JetBrains Mono"
              >
                {chartData.minDepth.toFixed(2)}m
              </text>
            </svg>

            {/* Stats overlay */}
            <div className="absolute top-1 right-1 flex flex-col items-end gap-0.5 text-[9px] font-mono text-muted-foreground">
              <span>AVG: <span className="text-foreground">{chartData.avgDepth.toFixed(3)}m</span></span>
              <span>MAX: <span className="text-foreground">{chartData.maxDepth.toFixed(3)}m</span></span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-muted-foreground">
            <div className="relative">
              <TrendingDown className="w-12 h-12 opacity-20" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-ping" />
              </div>
            </div>
            <span className="text-xs font-mono tracking-wider">AWAITING DEPTH DATA</span>
          </div>
        )}
      </div>
    </PanelWrapper>
  );
}