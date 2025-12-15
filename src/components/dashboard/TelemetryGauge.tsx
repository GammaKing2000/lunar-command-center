interface TelemetryGaugeProps {
  label: string;
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  showCenter?: boolean;
}

export function TelemetryGauge({ 
  label, 
  value, 
  min = -1, 
  max = 1, 
  unit = '', 
  showCenter = true 
}: TelemetryGaugeProps) {
  const range = max - min;
  const normalizedValue = (value - min) / range;
  const percentage = Math.max(0, Math.min(100, normalizedValue * 100));
  
  const isNegative = value < 0;
  const absPercentage = Math.abs(value) / Math.max(Math.abs(min), Math.abs(max)) * 50;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-baseline">
        <span className="data-label">{label}</span>
        <span className="data-value text-lg font-bold">
          {value >= 0 ? '+' : ''}{value.toFixed(2)}{unit}
        </span>
      </div>
      
      <div className="gauge-track h-3">
        {showCenter ? (
          <>
            {/* Center line */}
            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-muted-foreground/50 z-10" />
            
            {/* Fill from center */}
            {isNegative ? (
              <div 
                className="gauge-fill-reverse"
                style={{ 
                  left: `${50 - absPercentage}%`,
                  width: `${absPercentage}%`,
                }}
              />
            ) : (
              <div 
                className="gauge-fill"
                style={{ 
                  left: '50%',
                  width: `${absPercentage}%`,
                }}
              />
            )}
          </>
        ) : (
          <div 
            className="gauge-fill"
            style={{ width: `${percentage}%` }}
          />
        )}
      </div>
      
      <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
        <span>{min.toFixed(1)}</span>
        {showCenter && <span>0</span>}
        <span>{max.toFixed(1)}</span>
      </div>
    </div>
  );
}
