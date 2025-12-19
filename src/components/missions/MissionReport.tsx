import { CheckCircle, Download, ArrowLeft, Clock, Route, Target, Camera, Box, AlertCircle } from 'lucide-react';
import { PanelWrapper } from '@/components/dashboard/PanelWrapper';
import type { MissionReport as MissionReportType } from '@/types/telemetry';

interface MissionReportProps {
  report: MissionReportType & { folder?: string };
  onReturn: () => void;
}

export function MissionReport({ report, onReturn }: MissionReportProps) {
  const duration = report.endTime 
    ? Math.round((report.endTime.getTime() - report.startTime.getTime()) / 1000)
    : 0;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <div className="relative overflow-hidden rounded-xl border border-success/30 bg-gradient-to-r from-success/10 via-success/5 to-transparent p-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-success/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-xl bg-success/20 border border-success/30 flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-success" />
            </div>
            <div>
              <h1 className="text-3xl font-display font-bold tracking-wider text-success">MISSION COMPLETE</h1>
              <p className="text-sm text-muted-foreground font-mono mt-1">
                {report.task} • ID: {report.id}
              </p>
            </div>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={() => {/* Export logic */}}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 transition-colors font-mono text-sm"
            >
              <Download className="w-4 h-4" />
              EXPORT
            </button>
            <button
              onClick={onReturn}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-card/50 border border-border/50 text-foreground hover:bg-card transition-colors font-mono text-sm"
            >
              <ArrowLeft className="w-4 h-4" />
              NEW MISSION
            </button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-card/50 border border-border/30 backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-primary/20">
              <Route className="w-5 h-5 text-primary" />
            </div>
            <span className="text-xs text-muted-foreground font-mono">DISTANCE</span>
          </div>
          <p className="text-3xl font-mono font-bold text-foreground">{report.totalDistance}<span className="text-lg text-muted-foreground">cm</span></p>
        </div>
        
        <div className="p-4 rounded-xl bg-card/50 border border-border/30 backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-warning/20">
              <Clock className="w-5 h-5 text-warning" />
            </div>
            <span className="text-xs text-muted-foreground font-mono">DURATION</span>
          </div>
          <p className="text-3xl font-mono font-bold text-foreground">{formatDuration(duration)}</p>
        </div>
        
        <div className="p-4 rounded-xl bg-card/50 border border-border/30 backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-destructive/20">
              <Target className="w-5 h-5 text-destructive" />
            </div>
            <span className="text-xs text-muted-foreground font-mono">CRATERS</span>
          </div>
          <p className="text-3xl font-mono font-bold text-foreground">{report.findings.craters}</p>
        </div>
        
        <div className="p-4 rounded-xl bg-card/50 border border-border/30 backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-success/20">
              <AlertCircle className="w-5 h-5 text-success" />
            </div>
            <span className="text-xs text-muted-foreground font-mono">ALIENS</span>
          </div>
          <p className="text-3xl font-mono font-bold text-foreground">{report.findings.aliens}</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Findings Gallery */}
        <PanelWrapper title="Detection Gallery" badge={<Camera className="w-4 h-4 text-primary" />}>
          <div className="p-4 max-h-[400px] overflow-y-auto">
            {(report.detailed_findings && report.detailed_findings.length > 0) ? (
              <div className="space-y-3">
                {report.detailed_findings.map((finding, i) => {
                  const isAlien = finding.type.toLowerCase().includes('alien');
                  const isCrater = finding.type.toLowerCase().includes('crater');
                  
                  return (
                    <div 
                      key={i}
                      className="flex gap-4 p-3 rounded-lg bg-card/50 border border-border/30 hover:border-primary/50 transition-colors"
                    >
                      {/* Thumbnail */}
                      <div className="w-20 h-20 shrink-0 rounded-lg overflow-hidden border border-border/50 bg-muted/30">
                        <img 
                          src={`/detections/${report.folder || ''}/${finding.snapshot}`}
                          alt={finding.type}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      
                      {/* Details */}
                      <div className="flex-1 flex flex-col justify-center">
                        {/* Type Badge */}
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold uppercase ${
                            isAlien 
                              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' 
                              : 'bg-destructive/20 text-destructive border border-destructive/30'
                          }`}>
                            {finding.type}
                          </span>
                        </div>
                        
                        {/* Crater-specific info */}
                        {isCrater && finding.radius_m > 0 && (
                          <div className="flex items-center gap-4 text-sm font-mono">
                            <div>
                              <span className="text-muted-foreground">Radius: </span>
                              <span className="text-primary font-bold">{(finding.radius_m * 100).toFixed(1)}cm</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Est. Diameter: </span>
                              <span className="text-primary font-bold">{(finding.radius_m * 200).toFixed(1)}cm</span>
                            </div>
                          </div>
                        )}
                        
                        {/* Alien info */}
                        {isAlien && (
                          <p className="text-sm text-muted-foreground font-mono">
                            Alien specimen detected
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : report.snapshots.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {report.snapshots.map((snapshot, i) => (
                  <div 
                    key={i}
                    className="aspect-square rounded-lg overflow-hidden border border-border/30 bg-card/30 hover:border-primary/50 transition-colors cursor-pointer group"
                  >
                    <img 
                      src={snapshot.startsWith('data:') ? snapshot : `/detections/${report.folder || ''}/${snapshot}`}
                      alt={`Detection ${i + 1}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Camera className="w-12 h-12 text-muted-foreground/30 mb-3" />
                <p className="text-muted-foreground font-mono text-sm">No detections captured</p>
              </div>
            )}
          </div>
        </PanelWrapper>

        {/* 3D Reconstruction Placeholder */}
        <PanelWrapper title="3D Surface Reconstruction" badge={<Box className="w-4 h-4 text-primary" />}>
          <div className="p-4">
            <div className="relative aspect-video rounded-lg bg-gradient-to-br from-card/50 to-muted/20 border border-dashed border-border/50 flex flex-col items-center justify-center overflow-hidden">
              {/* Placeholder visualization */}
              <div className="absolute inset-0 opacity-20">
                <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {/* Grid pattern */}
                  {Array.from({ length: 10 }).map((_, i) => (
                    <line 
                      key={`v-${i}`}
                      x1={i * 10} y1="0" x2={i * 10} y2="100"
                      stroke="hsl(var(--primary))"
                      strokeWidth="0.2"
                    />
                  ))}
                  {Array.from({ length: 10 }).map((_, i) => (
                    <line 
                      key={`h-${i}`}
                      x1="0" y1={i * 10} x2="100" y2={i * 10}
                      stroke="hsl(var(--primary))"
                      strokeWidth="0.2"
                    />
                  ))}
                </svg>
              </div>
              
              <Box className="w-16 h-16 text-primary/50 mb-4 animate-pulse" />
              <p className="text-muted-foreground font-mono text-sm mb-2">Structure from Motion</p>
              <span className="text-[10px] px-2 py-1 rounded bg-muted/30 text-muted-foreground font-mono">
                COMING SOON
              </span>
            </div>
          </div>
        </PanelWrapper>
      </div>

      {/* Mission Log Summary */}
      <PanelWrapper title="Mission Log" className="max-h-[300px]">
        <div className="p-3 max-h-[200px] overflow-y-auto font-mono text-xs space-y-0.5 bg-space-black/30 rounded-lg m-2">
          {report.logs.map((log, i) => (
            <div key={i} className="text-muted-foreground hover:text-foreground transition-colors">
              {log}
            </div>
          ))}
        </div>
      </PanelWrapper>
    </div>
  );
}
