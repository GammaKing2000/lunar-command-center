import { PanelWrapper } from './PanelWrapper';
import { LiveBadge } from './LiveBadge';
import { LiveCrater } from '@/types/telemetry';
import { Camera, Target, Crosshair } from 'lucide-react';
import { useState } from 'react';

interface LiveVisionPanelProps {
  imageBase64: string | null;
  craters: LiveCrater[];
  resolution: [number, number];
  isConnected: boolean;
}

export function LiveVisionPanel({ imageBase64, craters, resolution, isConnected }: LiveVisionPanelProps) {
  const [hoveredCraterId, setHoveredCraterId] = useState<number | null>(null);
  const [capturedId, setCapturedId] = useState<number | null>(null);

  const handleCapture = async (crater: LiveCrater, id: number) => {
    try {
      const response = await fetch('http://localhost:8485/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ box: crater.box, label: crater.label || 'unknown' }),
      });
      if (response.ok) {
        setCapturedId(id);
        setTimeout(() => setCapturedId(null), 1000); // Flash green for 1s
      }
    } catch (error) {
      console.error('Capture failed:', error);
    }
  };

  return (
    <PanelWrapper 
      title="Live Vision Feed" 
      badge={<LiveBadge isConnected={isConnected} />}
      className="h-full"
    >
      <div className="relative w-full h-full bg-space-black rounded overflow-hidden flex items-center justify-center">
        {/* Video Feed Container - maintains 1:1 aspect ratio (416x416 typically) */}
        <div className="relative aspect-square h-full max-w-full group">
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

          {/* Interactive Overlay Layer */}
          {/* This layer sits exactly on top of the image */}
          <div className="absolute inset-0">
             {craters.map((crater, index) => {
               // Calculate percentages based on backend resolution
               // box: [x1, y1, x2, y2]
               const [imgW, imgH] = resolution;
               const [x1, y1, x2, y2] = crater.box;
               
               const left = (x1 / imgW) * 100;
               const top = (y1 / imgH) * 100;
               const width = ((x2 - x1) / imgW) * 100;
               const height = ((y2 - y1) / imgH) * 100;
               const id = crater.track_id ?? index;

               return (
                 <div
                   key={`${id}-${index}`}
                   className="absolute group/crater"
                   style={{
                     left: `${left}%`,
                     top: `${top}%`,
                     width: `${width}%`,
                     height: `${height}%`,
                     // Invisible by default, but blocks pointer events
                     cursor: 'crosshair',
                   }}
                   onMouseEnter={() => setHoveredCraterId(id)}
                   onMouseLeave={() => setHoveredCraterId(null)}
                 >
                   {/* Optional: Add a subtle highlight on hover to verify hit detection */}
                   <div className="absolute inset-0 border border-primary/0 group-hover/crater:border-primary/50 transition-colors rounded-sm" />

                   {/* Tooltip Card - Positions automatically */}
                   <div className={`absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 transition-all duration-200 ${
                     hoveredCraterId === id ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
                   }`}>
                     <div className="bg-space-black/95 backdrop-blur-md border border-primary/30 text-sm p-3 rounded-lg shadow-2xl shadow-primary/20 min-w-[180px]">
                        <div className="flex items-center gap-3 mb-2 border-b border-white/10 pb-2">
                          {/* Status Circle */}
                          {crater.label?.toLowerCase() !== 'alien' && (
                             <div className={`w-3 h-3 rounded-full ${
                               (crater.radius_m || 0) < 0.03 ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' :
                               (crater.radius_m || 0) < 0.055 ? 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.6)]' :
                               'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
                             }`} />
                          )}
                          <span className="font-bold text-primary font-mono text-base">{crater.label?.toUpperCase() || 'UNKNOWN'}</span>
                          <span className="text-xs text-muted-foreground font-mono ml-auto">ID:{id}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs font-mono">
                          {/* Only show radius if NOT Alien */}
                          {crater.label?.toLowerCase() !== 'alien' && (
                            <>
                              <span className="text-muted-foreground">RADIUS:</span>
                              <span className="text-foreground text-right">{(crater.radius_m || 0).toFixed(2)}m</span>
                            </>
                          )}
                          
                          <span className="text-muted-foreground">DIST:</span>
                          <span className="text-foreground text-right">{crater.depth.toFixed(2)}m</span>
                        </div>
                        {/* Capture Button */}
                        <button
                          className={`mt-3 w-full py-1.5 px-3 rounded-md flex items-center justify-center gap-2 text-xs font-mono transition-all pointer-events-auto ${
                            capturedId === id
                              ? 'bg-green-500 text-white'
                              : 'bg-primary/20 hover:bg-primary/40 text-primary border border-primary/30'
                          }`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCapture(crater, id);
                          }}
                        >
                          <Camera className="w-3 h-3" />
                          {capturedId === id ? 'CAPTURED!' : 'CAPTURE'}
                        </button>
                     </div>
                     {/* Triangle pointer (Pointing Left) */}
                     <div className="absolute top-1/2 -translate-y-1/2 left-0 -translate-x-full w-0 h-0 border-t-[8px] border-t-transparent border-b-[8px] border-b-transparent border-r-[8px] border-r-primary/30" />
                   </div>
                 </div>
               );
             })}
          </div>

          {/* Scanlines overlay same as before */}
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
                  {resolution?.[0] || 416}×{resolution?.[1] || 416}
                </span>
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