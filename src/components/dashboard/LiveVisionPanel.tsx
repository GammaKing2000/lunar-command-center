import { PanelWrapper } from './PanelWrapper';
import { LiveBadge } from './LiveBadge';
import { LiveCrater } from '@/types/telemetry';
import { Camera, Target, Crosshair } from 'lucide-react';

interface LiveVisionPanelProps {
  imageBase64: string | null;
  craters: LiveCrater[];
  isConnected: boolean;
}

export function LiveVisionPanel({ imageBase64, craters, isConnected }: LiveVisionPanelProps) {
  return (
    <PanelWrapper 
      title="Live Vision Feed" 
      badge={<LiveBadge isConnected={isConnected} />}
      className="h-full"
    >
      <div className="relative w-full h-full bg-space-black rounded overflow-hidden flex items-center justify-center">
        {/* Video Feed Container - maintains 1:1 aspect ratio (416x416) */}
        <div className="relative aspect-square h-full max-w-full">
          {/* Video Feed */}
          {imageBase64 ? (
            <img 
              src={`data:image/jpeg;base64,${imageBase64}`}
              alt="Rover Camera Feed"
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-space-black">
              <div className="relative">
                <Camera className="w-20 h-20 text-muted-foreground/20" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-3 h-3 rounded-full bg-primary/50 animate-ping" />
                </div>
              </div>
              <span className="text-sm text-muted-foreground font-mono tracking-wider">AWAITING SIGNAL...</span>
            </div>
          )}

          {/* Scanlines overlay */}
          <div className="absolute inset-0 scanlines pointer-events-none" />

          {/* HUD Crosshair - Enhanced */}
          <div className="hud-crosshair">
            <div className="hud-crosshair-inner" />
            <div className="hud-crosshair-outer" />
          </div>

          {/* Corner Brackets - Enhanced */}
          <div className="absolute top-3 left-3">
            <svg width="32" height="32" className="text-primary/70">
              <path d="M0 12 L0 0 L12 0" stroke="currentColor" strokeWidth="2" fill="none" />
              <path d="M0 8 L0 0 L8 0" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.5" />
            </svg>
          </div>
          <div className="absolute top-3 right-3">
            <svg width="32" height="32" className="text-primary/70">
              <path d="M20 0 L32 0 L32 12" stroke="currentColor" strokeWidth="2" fill="none" />
              <path d="M24 0 L32 0 L32 8" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.5" />
            </svg>
          </div>
          <div className="absolute bottom-3 left-3">
            <svg width="32" height="32" className="text-primary/70">
              <path d="M0 20 L0 32 L12 32" stroke="currentColor" strokeWidth="2" fill="none" />
              <path d="M0 24 L0 32 L8 32" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.5" />
            </svg>
          </div>
          <div className="absolute bottom-3 right-3">
            <svg width="32" height="32" className="text-primary/70">
              <path d="M20 32 L32 32 L32 20" stroke="currentColor" strokeWidth="2" fill="none" />
              <path d="M24 32 L32 32 L32 24" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.5" />
            </svg>
          </div>

          {/* Target reticles at intersections */}
          <div className="absolute top-1/4 left-1/4 w-4 h-4 border border-primary/30 rounded-full" />
          <div className="absolute top-1/4 right-1/4 w-4 h-4 border border-primary/30 rounded-full" />
          <div className="absolute bottom-1/4 left-1/4 w-4 h-4 border border-primary/30 rounded-full" />
          <div className="absolute bottom-1/4 right-1/4 w-4 h-4 border border-primary/30 rounded-full" />

          {/* Crater Bounding Boxes */}
          {craters.map((crater, index) => {
            const [x, y, w, h] = crater.box;
            return (
              <div
                key={index}
                className="crater-box"
                style={{
                  left: `${(x / 416) * 100}%`,
                  top: `${(y / 416) * 100}%`,
                  width: `${(w / 416) * 100}%`,
                  height: `${(h / 416) * 100}%`,
                }}
              >
                <span className="crater-label">
                  <Target className="w-3 h-3 inline mr-1" />
                  {crater.label || 'CRATER'} {crater.depth.toFixed(2)}m
                </span>
                {/* Corner markers */}
                <div className="absolute -top-0.5 -left-0.5 w-2 h-2 border-t-2 border-l-2 border-[hsl(var(--crater-glow))]" />
                <div className="absolute -top-0.5 -right-0.5 w-2 h-2 border-t-2 border-r-2 border-[hsl(var(--crater-glow))]" />
                <div className="absolute -bottom-0.5 -left-0.5 w-2 h-2 border-b-2 border-l-2 border-[hsl(var(--crater-glow))]" />
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 border-b-2 border-r-2 border-[hsl(var(--crater-glow))]" />
              </div>
            );
          })}

          {/* Scan Line Effect - Enhanced */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div 
              className="absolute left-0 right-0 h-[3px] bg-gradient-to-r from-transparent via-primary/40 to-transparent animate-scan"
              style={{ 
                boxShadow: '0 0 20px 5px hsl(var(--hud-cyan) / 0.3)',
              }}
            />
          </div>

          {/* Status Bar - Enhanced */}
          <div className="absolute bottom-0 left-0 right-0 px-4 py-2 bg-gradient-to-t from-space-black/95 via-space-black/80 to-transparent">
            <div className="flex justify-between items-center text-xs font-mono">
              <div className="flex items-center gap-3 text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <Crosshair className="w-3 h-3 text-primary" />
                  416×416
                </span>
                <span className="text-primary/80">YOLO-SEG</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  craters.length > 0 
                    ? 'bg-primary/20 text-primary border border-primary/30' 
                    : 'bg-muted text-muted-foreground'
                }`}>
                  {craters.length} DETECTION{craters.length !== 1 ? 'S' : ''}
                </span>
              </div>
            </div>
          </div>

          {/* Recording indicator */}
          {isConnected && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1 bg-space-black/60 rounded-full border border-primary/20">
              <div className="w-2 h-2 rounded-full bg-destructive animate-pulse" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-wider">REC</span>
            </div>
          )}
        </div>
      </div>
    </PanelWrapper>
  );
}