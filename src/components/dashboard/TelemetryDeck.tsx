import { PanelWrapper } from './PanelWrapper';
import { TelemetryGauge } from './TelemetryGauge';
import { DepthChart } from './DepthChart';
import { Gauge, Navigation, ArrowUp, ArrowDown, Circle } from 'lucide-react';

interface TelemetryDeckProps {
  throttle: number;
  steering: number;
  depthHistory: { time: number; depth: number }[];
}

export function TelemetryDeck({ throttle, steering, depthHistory }: TelemetryDeckProps) {
  const throttleDirection = throttle > 0.1 ? 'FWD' : throttle < -0.1 ? 'REV' : 'IDLE';
  const steeringDirection = steering > 0.1 ? 'RIGHT' : steering < -0.1 ? 'LEFT' : 'CENTER';
  
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
      {/* Throttle & Steering */}
      <PanelWrapper 
        title="Drive Control" 
        badge={<Gauge className="w-4 h-4 text-primary animate-pulse" />}
        className=""
      >
        <div className="space-y-5 p-1">
          <TelemetryGauge
            label="THROTTLE"
            value={throttle}
            min={-1}
            max={1}
            showCenter={true}
            icon={throttle > 0 ? <ArrowUp className="w-3.5 h-3.5" /> : throttle < 0 ? <ArrowDown className="w-3.5 h-3.5" /> : <Circle className="w-3 h-3" />}
          />
          
          <TelemetryGauge
            label="STEERING"
            value={steering}
            min={-1}
            max={1}
            showCenter={true}
            icon={<Navigation className="w-3.5 h-3.5" />}
          />

          {/* Direction Indicator - Enhanced */}
          <div className="flex items-center justify-center gap-6 pt-1">
            {/* Left indicator */}
            <div className={`flex flex-col items-center transition-all duration-200 ${
              steering < -0.1 ? 'opacity-100 scale-110' : 'opacity-40 scale-100'
            }`}>
              <div className={`relative p-2 rounded-lg ${
                steering < -0.1 ? 'bg-primary/20 border border-primary/40' : 'bg-muted/30'
              }`}>
                <Navigation 
                  className={`w-6 h-6 transition-all duration-200 -rotate-90 ${
                    steering < -0.1 ? 'text-primary' : 'text-muted-foreground'
                  }`}
                />
                {steering < -0.1 && (
                  <div className="absolute inset-0 bg-primary/10 rounded-lg animate-ping" />
                )}
              </div>
              <span className="text-[10px] mt-1 font-mono text-muted-foreground">LEFT</span>
            </div>
            
            {/* Center/Throttle indicator */}
            <div className="flex flex-col items-center">
              <div className={`relative w-10 h-12 rounded-lg border-2 flex items-center justify-center transition-all duration-200 ${
                throttle > 0.1 
                  ? 'border-primary bg-primary/20 shadow-glow-cyan' 
                  : throttle < -0.1 
                    ? 'border-[hsl(var(--warning))] bg-[hsl(var(--warning))]/20' 
                    : 'border-muted-foreground/30 bg-muted/20'
              }`}>
                {throttle > 0.1 ? (
                  <ArrowUp className="w-5 h-5 text-primary" />
                ) : throttle < -0.1 ? (
                  <ArrowDown className="w-5 h-5 text-[hsl(var(--warning))]" />
                ) : (
                  <Circle className="w-3 h-3 text-muted-foreground" />
                )}
              </div>
              <span className={`text-[10px] mt-1 font-mono font-bold ${
                throttle > 0.1 
                  ? 'text-primary' 
                  : throttle < -0.1 
                    ? 'text-[hsl(var(--warning))]' 
                    : 'text-muted-foreground'
              }`}>
                {throttleDirection}
              </span>
            </div>
            
            {/* Right indicator */}
            <div className={`flex flex-col items-center transition-all duration-200 ${
              steering > 0.1 ? 'opacity-100 scale-110' : 'opacity-40 scale-100'
            }`}>
              <div className={`relative p-2 rounded-lg ${
                steering > 0.1 ? 'bg-primary/20 border border-primary/40' : 'bg-muted/30'
              }`}>
                <Navigation 
                  className={`w-6 h-6 transition-all duration-200 rotate-90 ${
                    steering > 0.1 ? 'text-primary' : 'text-muted-foreground'
                  }`}
                />
                {steering > 0.1 && (
                  <div className="absolute inset-0 bg-primary/10 rounded-lg animate-ping" />
                )}
              </div>
              <span className="text-[10px] mt-1 font-mono text-muted-foreground">RIGHT</span>
            </div>
          </div>
        </div>
      </PanelWrapper>

      {/* Depth Chart */}
      <div className="h-full">
        <DepthChart depthHistory={depthHistory} />
      </div>
    </div>
  );
}