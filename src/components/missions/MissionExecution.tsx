import { useState, useEffect, useRef } from 'react';
import { Rocket, Square, Camera, Terminal, AlertTriangle, CheckCircle, Activity } from 'lucide-react';
import { PanelWrapper } from '@/components/dashboard/PanelWrapper';
import { socket } from '@/hooks/useTelemetry';
import type { MissionStatus, MissionReport } from '@/types/telemetry';

interface MissionExecutionProps {
  task: string;
  targetDistance: number;
  missionStatus: MissionStatus | null;
  imageBase64: string | null;
  onComplete: (report: MissionReport) => void;
  onAbort: () => void;
}

export function MissionExecution({
  task,
  targetDistance,
  missionStatus,
  imageBase64,
  onComplete,
  onAbort,
}: MissionExecutionProps) {
  const [logs, setLogs] = useState<{ time: string; message: string; type: 'info' | 'success' | 'warning' }[]>([]);
  const [startTime] = useState<Date>(new Date());
  const [findings, setFindings] = useState({ craters: 0, aliens: 0 });
  const [snapshots, setSnapshots] = useState<string[]>([]);
  const logContainerRef = useRef<HTMLDivElement>(null);
  
  // Simulate/track progress
  const progress = missionStatus?.progress ?? 0;
  const isActive = missionStatus?.active ?? true;
  const statusMessage = missionStatus?.message ?? 'Initializing systems...';

  // Add logs based on status changes
  useEffect(() => {
    if (missionStatus?.message) {
      const now = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [...prev.slice(-50), { 
        time: now, 
        message: missionStatus.message,
        type: missionStatus.message.includes('Detected') ? 'success' 
            : missionStatus.message.includes('Warning') ? 'warning' 
            : 'info'
      }]);
    }
  }, [missionStatus?.message]);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Listen for mission events
  useEffect(() => {
    function onMissionLog(data: { message: string; type?: 'info' | 'success' | 'warning' }) {
      const now = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [...prev.slice(-50), { time: now, message: data.message, type: data.type || 'info' }]);
    }

    function onDetection(data: { label: string; snapshot?: string }) {
      if (data.label?.toLowerCase().includes('crater')) {
        setFindings(prev => ({ ...prev, craters: prev.craters + 1 }));
      } else if (data.label?.toLowerCase().includes('alien')) {
        setFindings(prev => ({ ...prev, aliens: prev.aliens + 1 }));
      }
      if (data.snapshot) {
        setSnapshots(prev => [...prev, data.snapshot!]);
      }
    }

    function onMissionComplete(data: { success: boolean }) {
      const report: MissionReport = {
        id: `mission-${Date.now()}`,
        task,
        startTime,
        endTime: new Date(),
        totalDistance: targetDistance,
        findings,
        snapshots,
        logs: logs.map(l => `[${l.time}] ${l.message}`),
      };
      onComplete(report);
    }

    socket.on('mission_log', onMissionLog);
    socket.on('detection', onDetection);
    socket.on('mission_complete', onMissionComplete);

    // Initial log
    setLogs([{ 
      time: new Date().toLocaleTimeString('en-US', { hour12: false }), 
      message: `Mission "${task}" initiated. Target: ${targetDistance}cm`,
      type: 'info'
    }]);

    return () => {
      socket.off('mission_log', onMissionLog);
      socket.off('detection', onDetection);
      socket.off('mission_complete', onMissionComplete);
    };
  }, [task, targetDistance, startTime, findings, snapshots, logs, onComplete]);

  const handleAbort = () => {
    socket.emit('abort_mission', {});
    onAbort();
  };

  return (
    <div className="space-y-6">
      {/* Mission Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-lg bg-warning/20 border border-warning/30 flex items-center justify-center animate-pulse">
              <Rocket className="w-6 h-6 text-warning" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-display font-bold tracking-wider">MISSION ACTIVE</h1>
              <Activity className="w-5 h-5 text-warning animate-pulse" />
            </div>
            <p className="text-sm text-muted-foreground font-mono">{task} • Target: {targetDistance}cm</p>
          </div>
        </div>
        
        <button
          onClick={handleAbort}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-destructive/20 border border-destructive/50 text-destructive hover:bg-destructive/30 transition-colors font-mono text-sm"
        >
          <Square className="w-4 h-4" />
          ABORT MISSION
        </button>
      </div>

      {/* Progress Section */}
      <PanelWrapper title="Mission Progress" badge={<span className="text-warning font-mono">{progress}%</span>}>
        <div className="p-4 space-y-4">
          {/* Progress Bar */}
          <div className="relative h-8 rounded-lg bg-muted/30 overflow-hidden border border-border/50">
            <div 
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary via-primary to-warning transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
            <div 
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary/50 to-warning/50 blur-md transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="font-mono font-bold text-foreground text-shadow-lg">{progress}% COMPLETE</span>
            </div>
          </div>

          {/* Status Message */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-card/30 border border-border/30">
            <div className="w-2 h-2 rounded-full bg-warning animate-pulse" />
            <span className="font-mono text-sm text-muted-foreground">{statusMessage}</span>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 rounded-lg bg-card/30 border border-border/30 text-center">
              <p className="text-2xl font-mono font-bold text-primary">{findings.craters}</p>
              <p className="text-[10px] text-muted-foreground font-mono">CRATERS</p>
            </div>
            <div className="p-3 rounded-lg bg-card/30 border border-border/30 text-center">
              <p className="text-2xl font-mono font-bold text-success">{findings.aliens}</p>
              <p className="text-[10px] text-muted-foreground font-mono">ALIENS</p>
            </div>
            <div className="p-3 rounded-lg bg-card/30 border border-border/30 text-center">
              <p className="text-2xl font-mono font-bold text-foreground">{snapshots.length}</p>
              <p className="text-[10px] text-muted-foreground font-mono">SNAPSHOTS</p>
            </div>
          </div>
        </div>
      </PanelWrapper>

      {/* Live Feed & Terminal */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Mini Video Feed */}
        <PanelWrapper title="Live Feed" badge={<Camera className="w-4 h-4 text-primary" />}>
          <div className="p-2">
            <div className="relative aspect-square max-w-[300px] mx-auto rounded-lg overflow-hidden border border-border/50">
              {imageBase64 ? (
                <img 
                  src={`data:image/jpeg;base64,${imageBase64}`}
                  alt="Live Feed"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-space-black">
                  <Camera className="w-12 h-12 text-muted-foreground/30" />
                </div>
              )}
              {/* Recording indicator */}
              <div className="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-1 rounded bg-destructive/80 backdrop-blur-sm">
                <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                <span className="text-[10px] font-mono text-white">REC</span>
              </div>
            </div>
          </div>
        </PanelWrapper>

        {/* Terminal Logs */}
        <PanelWrapper title="Mission Terminal" badge={<Terminal className="w-4 h-4 text-primary" />}>
          <div 
            ref={logContainerRef}
            className="h-[300px] overflow-y-auto p-3 font-mono text-xs space-y-1 bg-space-black/50 rounded-lg m-2"
          >
            {logs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-muted-foreground shrink-0">[{log.time}]</span>
                <span className={
                  log.type === 'success' ? 'text-success' 
                  : log.type === 'warning' ? 'text-warning'
                  : 'text-foreground'
                }>
                  {log.message}
                </span>
              </div>
            ))}
            <div className="flex items-center gap-1 text-muted-foreground animate-pulse">
              <span>▌</span>
            </div>
          </div>
        </PanelWrapper>
      </div>
    </div>
  );
}
