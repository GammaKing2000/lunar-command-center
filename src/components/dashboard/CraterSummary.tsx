import { useMemo } from 'react';
import { PanelWrapper } from './PanelWrapper';
import { LiveCrater, MapCrater, Pose } from '@/types/telemetry';
import { AlertTriangle, Circle, Target } from 'lucide-react';

interface CraterSummaryProps {
  craters: MapCrater[];
  liveCraters?: LiveCrater[];
  currentPose: Pose | null;
}

// Determine danger level based on depth and proximity
function getDangerLevel(depth: number, distance: number | null): 'low' | 'medium' | 'high' | 'critical' {
  const depthScore = depth > 1.0 ? 3 : depth > 0.5 ? 2 : depth > 0.2 ? 1 : 0;
  const distanceScore = distance === null ? 0 : distance < 1.0 ? 3 : distance < 2.0 ? 2 : distance < 5.0 ? 1 : 0;
  
  if (depthScore >= 3 || distanceScore >= 3) return 'critical';
  if (depthScore + distanceScore >= 4) return 'high';
  if (depthScore + distanceScore >= 2) return 'medium';
  return 'low';
}

const dangerColors = {
  low: 'text-bio-green',
  medium: 'text-yellow-400',
  high: 'text-orange-500',
  critical: 'text-destructive',
};

const dangerBgColors = {
  low: 'bg-bio-green/20 border-bio-green/40',
  medium: 'bg-yellow-400/20 border-yellow-400/40',
  high: 'bg-orange-500/20 border-orange-500/40',
  critical: 'bg-destructive/20 border-destructive/40',
};

export function CraterSummary({ liveCraters = [] }: CraterSummaryProps) {
  // Use liveCraters directly
  const sortedCraters = useMemo(() => {
    return liveCraters
      .map((crater, index) => {
        // live crater 'depth' is actually distance from camera in current vision system logic
        // But we want 'depth' of the crater. 
        // Wait, looking at vision_system.py: 
        // "depth" field in detection_data is "dist_m" (distance from camera).
        // Actual crater depth is not currently calculated by vision system, only implied by size?
        // Let's assume the user wants the "depth" value shown on video (which is distance)
        // AND the radius.
        
        // Actually, looking at vision_system.py:
        // detection_data = { ..., 'depth': float(dist_m) } -> this is DISTANCE
        // It does not calculate physical depth of crater.
        // So we will display what we have.
        
        const distance = crater.depth; // This is distance from camera
        const radius = crater.radius_m || 0.5; // Default if missing
        
        return {
           id: crater.track_id ?? index + 1,
           depth: distance, // We'll label this as DISTANCE/DEPTH as per video
           radius: radius,
           distance: distance,
           danger: getDangerLevel(0.5, distance), // Placeholder depth for danger calc
           label: crater.label
        };
      })
      .sort((a, b) => a.distance - b.distance);
  }, [liveCraters]);

  const stats = useMemo(() => {
    if (liveCraters.length === 0) return null;
    const distances = liveCraters.map(c => c.depth);
    return {
      total: liveCraters.length,
      minDistance: Math.min(...distances),
      maxRadius: Math.max(...liveCraters.map(c => c.radius_m || 0)),
      criticalCount: sortedCraters.filter(c => c.danger === 'critical' || c.danger === 'high').length,
    };
  }, [liveCraters, sortedCraters]);

  return (
    <PanelWrapper 
      title="Crater Detection" 
      badge={
        <div className="flex items-center gap-2">
          <Target className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-mono text-primary font-bold">{liveCraters.length}</span>
        </div>
      }
    >
      <div className="h-full overflow-hidden p-2">
        {liveCraters.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-muted-foreground">
            <Circle className="w-8 h-8 opacity-30" />
            <span className="text-xs font-mono">NO CRATERS DETECTED</span>
          </div>
        ) : (
          <div className="flex flex-col h-full gap-2">
            {/* Stats Summary */}
            {stats && (
              <div className="flex items-center justify-between text-[10px] font-mono px-1 pb-1 border-b border-border/30">
                <span className="text-muted-foreground">
                  TOTAL: <span className="text-foreground font-bold">{stats.total}</span>
                </span>
                <span className="text-muted-foreground">
                  MIN DIST: <span className="text-primary">{stats.minDistance.toFixed(2)}m</span>
                </span>
                <span className="text-muted-foreground">
                  MAX RAD: <span className="text-foreground">{stats.maxRadius.toFixed(2)}m</span>
                </span>
              </div>
            )}

            {/* Crater List */}
            <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin">
              {sortedCraters.map((crater, index) => (
                <div 
                  key={`${crater.id}-${index}`}
                  className={`flex items-center justify-between px-2 py-1 rounded border ${dangerBgColors[crater.danger]} transition-colors`}
                >
                  {/* ID & Label */}
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold font-mono ${dangerColors[crater.danger]}`}>
                      {typeof crater.id === 'number' && crater.id > 9000 ? `C${index+1}` : `T${crater.id}`}
                    </span>
                    <span className="text-[10px] text-muted-foreground uppercase">{crater.label}</span>
                  </div>

                  {/* Radius */}
                  <div className="flex items-center gap-1 text-[10px] font-mono">
                    <span className="text-muted-foreground">R:</span>
                    <span className="text-foreground">{crater.radius.toFixed(2)}m</span>
                  </div>

                  {/* Distance (using depth field from vision system) */}
                  <div className="flex items-center gap-1 text-[10px] font-mono">
                    <span className="text-muted-foreground">DIST:</span>
                    <span className={crater.distance < 1.0 ? 'text-destructive' : 'text-foreground'}>
                      {crater.distance.toFixed(2)}m
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PanelWrapper>
  );
}
