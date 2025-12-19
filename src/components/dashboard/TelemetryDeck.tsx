import { PanelWrapper } from './PanelWrapper';
import { TelemetryGauge } from './TelemetryGauge';
import { CraterSummary } from './CraterSummary';
import { DetectionsGallery } from './DetectionsGallery';
import { Gauge, Navigation, ArrowUp, ArrowDown, Circle } from 'lucide-react';
import { MapCrater, LiveCrater, Pose } from '@/types/telemetry';

interface TelemetryDeckProps {
  throttle: number;
  steering: number;
  mapCraters: MapCrater[];
  liveCraters: LiveCrater[];
  currentPose: Pose | null;
  detectionFiles: string[];
}

export function TelemetryDeck({ throttle, steering, mapCraters, liveCraters, currentPose, detectionFiles }: TelemetryDeckProps) {
  
  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Throttle & Steering */}
      <PanelWrapper 
        title="Drive Control" 
        badge={<Gauge className="w-4 h-4 text-primary animate-pulse" />}
        className="flex-shrink-0"
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
        </div>
      </PanelWrapper>

      {/* Crater Summary */}
      <div className="flex-1 min-h-0">
        <CraterSummary 
          craters={mapCraters} 
          liveCraters={liveCraters}
          currentPose={currentPose} 
        />
      </div>

      {/* Detections Gallery */}
      <div className="flex-1 min-h-0">
        <DetectionsGallery files={detectionFiles} />
      </div>
    </div>
  );
}