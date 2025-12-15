import { useTelemetry } from '@/hooks/useTelemetry';
import { Header } from './dashboard/Header';
import { StatusBar } from './dashboard/StatusBar';
import { LiveVisionPanel } from './dashboard/LiveVisionPanel';
import { TacticalMap } from './dashboard/TacticalMap';
import { TelemetryDeck } from './dashboard/TelemetryDeck';

export function MissionControl() {
  const { telemetry, isConnected, missionTime, positionHistory, depthHistory } = useTelemetry();

  return (
    <div className="min-h-screen bg-background grid-bg p-4 lg:p-6">
      <div className="max-w-[1800px] mx-auto space-y-4">
        {/* Header */}
        <Header missionTime={missionTime} />

        {/* Status Bar */}
        <StatusBar 
          isConnected={isConnected} 
          step={telemetry?.step}
        />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - Live Vision */}
          <div className="lg:col-span-2 h-[400px] lg:h-[500px]">
            <LiveVisionPanel
              imageBase64={telemetry?.img_base64 || null}
              craters={telemetry?.perception?.live_craters || []}
              isConnected={isConnected}
            />
          </div>

          {/* Right Column - Tactical Map */}
          <div className="h-[400px] lg:h-[500px]">
            <TacticalMap
              currentPose={telemetry?.telemetry?.pose || null}
              positionHistory={positionHistory}
              mapCraters={telemetry?.perception?.map_craters || []}
            />
          </div>
        </div>

        {/* Bottom Row - Telemetry Deck */}
        <div className="h-[200px]">
          <TelemetryDeck
            throttle={telemetry?.telemetry?.throttle || 0}
            steering={telemetry?.telemetry?.steering || 0}
            depthHistory={depthHistory}
          />
        </div>
      </div>
    </div>
  );
}
