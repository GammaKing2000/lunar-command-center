import { useMemo } from 'react';
import { PanelWrapper } from './PanelWrapper';
import { TrendingDown } from 'lucide-react';

interface DepthChartProps {
  depthHistory: { time: number; depth: number }[];
}

const CHART_WIDTH = 280;
const CHART_HEIGHT = 80;
const MAX_POINTS = 30;

export function DepthChart({ depthHistory }: DepthChartProps) {
  const chartPath = useMemo(() => {
    if (depthHistory.length < 2) return null;

    const recentData = depthHistory.slice(-MAX_POINTS);
    const maxDepth = Math.max(...recentData.map(d => d.depth), 0.5);
    
    const points = recentData.map((d, i) => {
      const x = (i / (MAX_POINTS - 1)) * CHART_WIDTH;
      const y = CHART_HEIGHT - (d.depth / maxDepth) * (CHART_HEIGHT - 10);
      return `${x},${y}`;
    });

    return {
      line: `M ${points.join(' L ')}`,
      area: `M 0,${CHART_HEIGHT} L ${points.join(' L ')} L ${CHART_WIDTH},${CHART_HEIGHT} Z`,
      maxDepth,
      currentDepth: recentData[recentData.length - 1]?.depth || 0,
    };
  }, [depthHistory]);

  return (
    <PanelWrapper 
      title="Depth Analysis" 
      badge={
        chartPath ? (
          <span className="text-sm font-mono text-primary">
            {chartPath.currentDepth.toFixed(3)}m
          </span>
        ) : null
      }
    >
      <div className="relative h-full flex items-center justify-center">
        {chartPath ? (
          <svg
            width={CHART_WIDTH}
            height={CHART_HEIGHT}
            viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
            className="overflow-visible"
          >
            {/* Grid lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
              <line
                key={i}
                x1={0}
                y1={CHART_HEIGHT * ratio}
                x2={CHART_WIDTH}
                y2={CHART_HEIGHT * ratio}
                stroke="hsl(var(--grid-line))"
                strokeWidth={0.5}
                opacity={0.3}
              />
            ))}

            {/* Area fill */}
            <path
              d={chartPath.area}
              fill="url(#depthGradient)"
              opacity={0.3}
            />

            {/* Line */}
            <path
              d={chartPath.line}
              fill="none"
              stroke="hsl(var(--hud-cyan))"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Current value dot */}
            <circle
              cx={CHART_WIDTH}
              cy={CHART_HEIGHT - (chartPath.currentDepth / chartPath.maxDepth) * (CHART_HEIGHT - 10)}
              r={4}
              fill="hsl(var(--hud-cyan))"
              className="animate-pulse-glow"
            />

            {/* Gradient definition */}
            <defs>
              <linearGradient id="depthGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="hsl(var(--hud-cyan))" stopOpacity={0.5} />
                <stop offset="100%" stopColor="hsl(var(--hud-cyan))" stopOpacity={0} />
              </linearGradient>
            </defs>
          </svg>
        ) : (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <TrendingDown className="w-8 h-8 opacity-30" />
            <span className="text-xs font-mono">NO DEPTH DATA</span>
          </div>
        )}

        {/* Y-axis labels */}
        {chartPath && (
          <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-[10px] font-mono text-muted-foreground -translate-x-8">
            <span>{chartPath.maxDepth.toFixed(2)}m</span>
            <span>0m</span>
          </div>
        )}
      </div>
    </PanelWrapper>
  );
}
