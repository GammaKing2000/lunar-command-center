import { useMemo } from 'react';

interface TelemetryGaugeProps {
  label: string;
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  showCenter?: boolean;
  icon?: React.ReactNode;
}

export function TelemetryGauge({ 
  label, 
  value, 
  min = -1, 
  max = 1, 
  unit = '', 
  showCenter = true,
  icon
}: TelemetryGaugeProps) {
  const range = max - min;
  const normalizedValue = (value - min) / range;
  const percentage = Math.max(0, Math.min(100, normalizedValue * 100));
  
  const isNegative = value < 0;
  const absPercentage = Math.abs(value) / Math.max(Math.abs(min), Math.abs(max)) * 50;

  // Generate tick marks
  const ticks = useMemo(() => {
    const tickCount = 21;
    return Array.from({ length: tickCount }, (_, i) => {
      const position = (i / (tickCount - 1)) * 100;
      const isMajor = i % 5 === 0;
      const isCenter = i === Math.floor(tickCount / 2);
      return { position, isMajor, isCenter };
    });
  }, []);

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          {icon && <span className="text-muted-foreground">{icon}</span>}
          <span className="data-label">{label}</span>
        </div>
        <span className={`data-value text-xl font-bold tracking-tight ${
          isNegative ? 'text-[hsl(var(--warning))] text-glow-warning' : 'text-primary text-glow-cyan'
        }`}>
          {value >= 0 ? '+' : ''}{value.toFixed(2)}{unit}
        </span>
      </div>
      
      {/* Gauge container */}
      <div className="relative">
        {/* Tick marks */}
        <div className="absolute -top-1 left-0 right-0 flex justify-between px-0">
          {ticks.map((tick, i) => (
            <div 
              key={i}
              className={`w-px transition-colors ${
                tick.isCenter 
                  ? 'h-2 bg-foreground/70' 
                  : tick.isMajor 
                    ? 'h-1.5 bg-muted-foreground/50' 
                    : 'h-1 bg-muted-foreground/25'
              }`}
            />
          ))}
        </div>

        {/* Main gauge track */}
        <div className="gauge-track mt-2">
          {showCenter ? (
            <>
              {/* Center line */}
              <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-foreground/60 z-10" />
              
              {/* Fill from center */}
              {isNegative ? (
                <div 
                  className="gauge-fill-reverse rounded-r-none"
                  style={{ 
                    left: `${50 - absPercentage}%`,
                    width: `${absPercentage}%`,
                  }}
                />
              ) : (
                <div 
                  className="gauge-fill rounded-l-none"
                  style={{ 
                    left: '50%',
                    width: `${absPercentage}%`,
                  }}
                />
              )}

              {/* Active indicator dot */}
              <div 
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-foreground shadow-lg z-20 transition-all duration-200"
                style={{ 
                  left: `calc(${50 + (value / Math.max(Math.abs(min), Math.abs(max)) * 50)}% - 6px)`,
                }}
              />
            </>
          ) : (
            <>
              <div 
                className="gauge-fill"
                style={{ width: `${percentage}%` }}
              />
              <div 
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-foreground shadow-lg z-20 transition-all duration-200"
                style={{ 
                  left: `calc(${percentage}% - 6px)`,
                }}
              />
            </>
          )}
        </div>
        
        {/* Labels */}
        <div className="flex justify-between mt-1 text-[10px] text-muted-foreground font-mono">
          <span>{min.toFixed(1)}</span>
          {showCenter && <span className="text-foreground/70">0</span>}
          <span>{max.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}