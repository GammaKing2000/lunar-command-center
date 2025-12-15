import { PanelWrapper } from './PanelWrapper';
import { LiveBadge } from './LiveBadge';
import { LiveCrater } from '@/types/telemetry';
import { Camera } from 'lucide-react';

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
      <div className="relative w-full h-full bg-space-black rounded overflow-hidden scanlines">
        {/* Video Feed */}
        {imageBase64 ? (
          <img 
            src={`data:image/jpeg;base64,${imageBase64}`}
            alt="Rover Camera Feed"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <Camera className="w-16 h-16 text-muted-foreground/30" />
            <span className="text-sm text-muted-foreground font-mono">AWAITING SIGNAL...</span>
          </div>
        )}

        {/* HUD Crosshair */}
        <div className="hud-crosshair" />

        {/* Corner Brackets */}
        <div className="absolute top-2 left-2 w-6 h-6 border-l-2 border-t-2 border-hud-cyan/60" />
        <div className="absolute top-2 right-2 w-6 h-6 border-r-2 border-t-2 border-hud-cyan/60" />
        <div className="absolute bottom-2 left-2 w-6 h-6 border-l-2 border-b-2 border-hud-cyan/60" />
        <div className="absolute bottom-2 right-2 w-6 h-6 border-r-2 border-b-2 border-hud-cyan/60" />

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
                {crater.label || 'CRATER'} {crater.depth.toFixed(2)}m
              </span>
            </div>
          );
        })}

        {/* Scan Line Effect */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div 
            className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-hud-cyan/30 to-transparent animate-scan"
            style={{ top: 0 }}
          />
        </div>

        {/* Status Bar */}
        <div className="absolute bottom-0 left-0 right-0 px-3 py-1.5 bg-gradient-to-t from-space-black/90 to-transparent">
          <div className="flex justify-between text-xs font-mono text-muted-foreground">
            <span>416×416 • YOLO-SEG</span>
            <span>{craters.length} DETECTION{craters.length !== 1 ? 'S' : ''}</span>
          </div>
        </div>
      </div>
    </PanelWrapper>
  );
}
