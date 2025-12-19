import { useState } from 'react';
import { Rocket, ArrowRight, Gauge, AlertTriangle, Radio } from 'lucide-react';
import { PanelWrapper } from '@/components/dashboard/PanelWrapper';
import { socket } from '@/hooks/useTelemetry';

interface MissionSetupProps {
  onStartMission: (task: string, distance: number) => void;
  isConnected: boolean;
}

export function MissionSetup({ onStartMission, isConnected }: MissionSetupProps) {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [distance, setDistance] = useState<number>(100);

  const handleExecute = () => {
    if (selectedTask && distance > 0) {
      // Emit mission start to backend
      socket.emit('start_mission', { 
        task: selectedTask, 
        distance_cm: distance 
      });
      onStartMission(selectedTask, distance);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
              <Rocket className="w-6 h-6 text-primary" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-primary animate-pulse" />
          </div>
          <div>
            <h1 className="text-2xl font-display font-bold tracking-wider">MISSION CONTROL</h1>
            <p className="text-sm text-muted-foreground font-mono">Automated Operations Center</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card/50 border border-border/50">
          <Radio className={`w-4 h-4 ${isConnected ? 'text-success' : 'text-destructive'}`} />
          <span className="text-xs font-mono text-muted-foreground">
            {isConnected ? 'ROVER ONLINE' : 'NO CONNECTION'}
          </span>
        </div>
      </div>

      {/* Mission Selection */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Mission Card */}
        <PanelWrapper title="Available Missions" className="h-fit">
          <div className="p-4 space-y-4">
            {/* Linear Traverse Mission */}
            <button
              onClick={() => setSelectedTask('Linear Traverse')}
              className={`w-full p-4 rounded-lg border transition-all duration-300 text-left group ${
                selectedTask === 'Linear Traverse'
                  ? 'bg-primary/20 border-primary/50 shadow-[0_0_20px_-5px_hsl(var(--primary)/0.4)]'
                  : 'bg-card/30 border-border/30 hover:border-primary/30 hover:bg-card/50'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg transition-colors ${
                  selectedTask === 'Linear Traverse' ? 'bg-primary/30' : 'bg-muted/50 group-hover:bg-primary/20'
                }`}>
                  <ArrowRight className="w-6 h-6 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-display font-bold tracking-wide text-foreground">LINEAR TRAVERSE</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Autonomous straight-line drive with obstacle detection and surface scanning.
                  </p>
                  <div className="flex items-center gap-3 mt-3">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-success/20 text-success font-mono">
                      OPERATIONAL
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      EST. TIME: ~{Math.ceil(distance / 5)}s
                    </span>
                  </div>
                </div>
              </div>
            </button>

            {/* More missions placeholder */}
            <div className="p-4 rounded-lg border border-dashed border-border/30 bg-muted/10">
              <div className="flex items-center gap-3 text-muted-foreground">
                <Gauge className="w-5 h-5" />
                <span className="text-sm font-mono">More missions coming soon...</span>
              </div>
            </div>
          </div>
        </PanelWrapper>

        {/* Configuration Panel */}
        <PanelWrapper title="Mission Configuration" className="h-fit">
          <div className="p-4 space-y-6">
            {selectedTask ? (
              <>
                {/* Selected Mission */}
                <div className="flex items-center gap-3 p-3 rounded-lg bg-primary/10 border border-primary/30">
                  <Rocket className="w-5 h-5 text-primary" />
                  <div>
                    <span className="text-xs text-muted-foreground font-mono">SELECTED:</span>
                    <p className="font-display font-bold tracking-wide text-primary">{selectedTask}</p>
                  </div>
                </div>

                {/* Distance Input */}
                <div className="space-y-3">
                  <label className="text-sm font-mono text-muted-foreground">
                    TARGET DISTANCE (cm)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      value={distance}
                      onChange={(e) => setDistance(Math.max(1, parseInt(e.target.value) || 0))}
                      min={1}
                      max={1000}
                      className="w-full px-4 py-3 rounded-lg bg-card/50 border border-border/50 text-2xl font-mono text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground font-mono">
                      cm
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {[50, 100, 200, 500].map((val) => (
                      <button
                        key={val}
                        onClick={() => setDistance(val)}
                        className={`flex-1 py-1.5 rounded text-xs font-mono transition-colors ${
                          distance === val
                            ? 'bg-primary/30 text-primary border border-primary/50'
                            : 'bg-muted/30 text-muted-foreground hover:bg-muted/50 border border-transparent'
                        }`}
                      >
                        {val}cm
                      </button>
                    ))}
                  </div>
                </div>

                {/* Execute Button */}
                <button
                  onClick={handleExecute}
                  disabled={!isConnected}
                  className={`w-full py-4 rounded-lg font-display font-bold tracking-wider text-lg transition-all duration-300 ${
                    isConnected
                      ? 'bg-warning hover:bg-warning/90 text-warning-foreground shadow-[0_0_30px_-5px_hsl(var(--warning)/0.5)] hover:shadow-[0_0_40px_-5px_hsl(var(--warning)/0.7)]'
                      : 'bg-muted/30 text-muted-foreground cursor-not-allowed'
                  }`}
                >
                  {isConnected ? (
                    <span className="flex items-center justify-center gap-2">
                      <Rocket className="w-5 h-5" />
                      EXECUTE MISSION
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <AlertTriangle className="w-5 h-5" />
                      ROVER OFFLINE
                    </span>
                  )}
                </button>

                {!isConnected && (
                  <p className="text-xs text-center text-muted-foreground font-mono">
                    Connect to rover to enable mission execution
                  </p>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-16 h-16 rounded-full bg-muted/20 flex items-center justify-center mb-4">
                  <Rocket className="w-8 h-8 text-muted-foreground/50" />
                </div>
                <p className="text-muted-foreground font-mono text-sm">
                  Select a mission to configure
                </p>
              </div>
            )}
          </div>
        </PanelWrapper>
      </div>
    </div>
  );
}
