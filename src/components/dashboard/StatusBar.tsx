import { Wifi, WifiOff, Radio, Cpu, Battery, BatteryCharging, BatteryWarning } from 'lucide-react';

interface StatusBarProps {
  isConnected: boolean;
  step?: number;
  battery?: number; // percentage (0-100)
}

export function StatusBar({ isConnected, step, battery }: StatusBarProps) {
  // Determine battery icon and color based on percentage
  const getBatteryStatus = (pct?: number) => {
    if (pct === undefined) return { icon: Battery, color: 'text-muted-foreground', text: 'N/A' };
    
    if (pct > 20) return { icon: Battery, color: 'text-bio-green', text: `${pct}%` };
    if (pct > 10) return { icon: BatteryWarning, color: 'text-yellow-500', text: `${pct}%` };
    return { icon: BatteryWarning, color: 'text-destructive', text: `${pct}%` };
  };

  const bat = getBatteryStatus(battery);
  const BatteryIcon = bat.icon;

  return (
    <div className="glass-panel flex items-center justify-between px-4 py-2">
      <div className="flex items-center gap-6">
        {/* Connection Status */}
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Wifi className="w-4 h-4 text-bio-green" />
          ) : (
            <WifiOff className="w-4 h-4 text-destructive" />
          )}
          <span className={`text-xs font-mono ${isConnected ? 'text-bio-green' : 'text-destructive'}`}>
            {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        </div>

        {/* Socket URL */}
        <div className="hidden sm:flex items-center gap-2 text-muted-foreground">
          <Radio className="w-3 h-3" />
          <span className="text-xs font-mono">172.20.10.8:8485</span>
        </div>

        {/* Step Counter */}
        {step !== undefined && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Cpu className="w-3 h-3" />
            <span className="text-xs font-mono">STEP: {step.toLocaleString()}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Battery Status */}
        <div className="flex items-center gap-2">
          <BatteryIcon className={`w-4 h-4 ${bat.color}`} />
          <span className="text-xs font-mono text-muted-foreground">BAT: {bat.text}</span>
        </div>

        {/* Timestamp */}
        <span className="text-xs font-mono text-muted-foreground">
          {new Date().toLocaleTimeString('en-US', { hour12: false })}
        </span>
      </div>
    </div>
  );
}
