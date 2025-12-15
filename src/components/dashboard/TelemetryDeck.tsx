import { PanelWrapper } from './PanelWrapper';
import { TelemetryGauge } from './TelemetryGauge';
import { DepthChart } from './DepthChart';
import { Gauge, Navigation } from 'lucide-react';

interface TelemetryDeckProps {
  throttle: number;
  steering: number;
  depthHistory: { time: number; depth: number }[];
}

export function TelemetryDeck({ throttle, steering, depthHistory }: TelemetryDeckProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
      {/* Throttle & Steering */}
      <PanelWrapper 
        title="Drive Control" 
        badge={<Gauge className="w-4 h-4 text-primary" />}
        className="lg:col-span-1"
      >
        <div className="space-y-6 pt-2">
          <TelemetryGauge
            label="THROTTLE"
            value={throttle}
            min={-1}
            max={1}
            showCenter={true}
          />
          
          <TelemetryGauge
            label="STEERING"
            value={steering}
            min={-1}
            max={1}
            showCenter={true}
          />

          {/* Direction Indicator */}
          <div className="flex items-center justify-center gap-4 pt-2">
            <div className="flex flex-col items-center">
              <Navigation 
                className={`w-8 h-8 transition-all duration-150 ${
                  steering < -0.1 ? 'text-primary -rotate-45' : 'text-muted-foreground/30'
                }`}
              />
              <span className="text-[10px] text-muted-foreground">LEFT</span>
            </div>
            
            <div className="flex flex-col items-center">
              <div 
                className={`w-6 h-8 rounded transition-all duration-150 ${
                  throttle > 0.1 
                    ? 'bg-primary shadow-glow-cyan' 
                    : throttle < -0.1 
                      ? 'bg-destructive shadow-glow-red' 
                      : 'bg-muted-foreground/30'
                }`}
              />
              <span className="text-[10px] text-muted-foreground">
                {throttle > 0.1 ? 'FWD' : throttle < -0.1 ? 'REV' : 'STOP'}
              </span>
            </div>
            
            <div className="flex flex-col items-center">
              <Navigation 
                className={`w-8 h-8 transition-all duration-150 ${
                  steering > 0.1 ? 'text-primary rotate-45' : 'text-muted-foreground/30'
                }`}
              />
              <span className="text-[10px] text-muted-foreground">RIGHT</span>
            </div>
          </div>
        </div>
      </PanelWrapper>

      {/* Depth Chart */}
      <div className="lg:col-span-2">
        <DepthChart depthHistory={depthHistory} />
      </div>
    </div>
  );
}
