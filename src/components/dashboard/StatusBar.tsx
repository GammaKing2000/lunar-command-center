import { Wifi, WifiOff, Radio, Cpu, Battery } from 'lucide-react';

interface StatusBarProps {
  isConnected: boolean;
  step?: number;
}

export function StatusBar({ isConnected, step }: StatusBarProps) {
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
          <span className="text-xs font-mono">192.168.2.109:8485</span>
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
        {/* System Status */}
        <div className="flex items-center gap-2">
          <Battery className="w-4 h-4 text-bio-green" />
          <span className="text-xs font-mono text-muted-foreground">SYS OK</span>
        </div>

        {/* Timestamp */}
        <span className="text-xs font-mono text-muted-foreground">
          {new Date().toLocaleTimeString('en-US', { hour12: false })}
        </span>
      </div>
    </div>
  );
}
