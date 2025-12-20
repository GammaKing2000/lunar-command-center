import { useTelemetry } from '@/hooks/useTelemetry';
import { Header } from './dashboard/Header';
import { StatusBar } from './dashboard/StatusBar';
import { LiveVisionPanel } from './dashboard/LiveVisionPanel';
// import { TacticalMap } from './dashboard/TacticalMap';
import { TelemetryDeck } from './dashboard/TelemetryDeck';

import { useState, useEffect } from 'react';
import { socket } from '@/hooks/useTelemetry'; // Assume socket is exported or we need to access it

// ... imports ...

export function MissionControl() {
  const { telemetry, isConnected, missionTime, positionHistory, depthHistory } = useTelemetry();
  const [kinematicsMode, setKinematicsMode] = useState<'jetracer' | 'ugv'>('jetracer');
  const [moonyLoading, setMoonyLoading] = useState(false);

  const toggleKinematics = (mode: 'jetracer' | 'ugv') => {
    setKinematicsMode(mode);
    socket.emit('set_kinematics', { mode });
  };

  const handleMoonyClick = async () => {
    setMoonyLoading(true);
    try {
      const pose = telemetry?.telemetry?.pose ?? { x: 0, y: 0, theta: 0 };
      const craters =
        telemetry?.perception?.map_craters ??
        telemetry?.perception?.live_craters ??
        [];

      const res = await fetch('/chat/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pose, craters }),
      });
      const data = await res.json();
      if (data?.status === 'ok') {
        window.alert(`Moony — Decision: ${data.decision}\n\n${data.explanation}`);
      } else {
        window.alert(`Moony error: ${data?.message ?? 'unknown error'}`);
      }
    } catch (err: any) {
      window.alert(`Moony request failed: ${err?.message ?? err}`);
    } finally {
      setMoonyLoading(false);
    }
  };

  return (
    <div className="p-4 lg:p-6 h-[calc(100vh-40px)] overflow-auto">
      <div className="max-w-[1800px] mx-auto space-y-4">
        {/* Header with Extra Controls */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
             <Header missionTime={missionTime} />
             
             {/* Kinematics Toggle */}
             <div className="flex items-center gap-2 bg-card/50 p-1 rounded-lg border border-border/50 backdrop-blur-sm">
                <span className="text-[10px] px-2 text-muted-foreground font-mono">CHASSIS</span>
                <button 
                    onClick={() => toggleKinematics('jetracer')}
                    className={`px-3 py-1 text-xs font-bold rounded transition-colors ${kinematicsMode === 'jetracer' ? 'bg-primary text-primary-foreground shadow-glow' : 'text-muted-foreground hover:text-foreground'}`}
                >
                    JETRACER
                </button>
                <div className="w-[1px] h-4 bg-border/50" />
                <button 
                     onClick={() => toggleKinematics('ugv')}
                     className={`px-3 py-1 text-xs font-bold rounded transition-colors ${kinematicsMode === 'ugv' ? 'bg-primary text-primary-foreground shadow-glow' : 'text-muted-foreground hover:text-foreground'}`}
                >
                    UGV
                </button>
             </div>
             
             {/* Map Reset & Moony Button */}
             <div className="flex items-center gap-2">
               <button
                  onClick={() => {
                      console.log('Resetting Map...');
                      socket.emit('reset_map', {});
                  }}
                  className="px-3 py-1 bg-destructive/20 hover:bg-destructive/40 text-destructive border border-destructive/50 rounded text-xs font-bold transition-colors"
               >
                  RESET MAP
               </button>

               <button
                 onClick={handleMoonyClick}
                 disabled={moonyLoading}
                 className={`px-3 py-1 text-xs font-bold rounded transition-colors ${moonyLoading ? 'opacity-60 cursor-wait' : 'bg-amber-500 text-white hover:brightness-95'}`}
               >
                 {moonyLoading ? 'Moony...' : 'Moony'}
               </button>
             </div>
        </div>

        {/* Status Bar */}
        <StatusBar 
          isConnected={isConnected} 
          step={telemetry?.step}
        />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100vh-230px)]">
          {/* Left Column - Live Vision */}
          <div className="lg:col-span-3 h-full">
            <LiveVisionPanel
              imageBase64={telemetry?.img_base64 || null}
              craters={telemetry?.perception?.live_craters || []}
              resolution={telemetry?.perception?.resolution || [416, 416]}
              isConnected={isConnected}
            />
          </div>

          {/* Right Column - Controls & Telemetry */}
          <div className="h-full">
            <TelemetryDeck
              throttle={telemetry?.telemetry?.throttle || 0}
              steering={telemetry?.telemetry?.steering || 0}
              mapCraters={telemetry?.perception?.map_craters || []}
              liveCraters={telemetry?.perception?.live_craters || []}
              currentPose={telemetry?.telemetry?.pose || null}
              detectionFiles={telemetry?.perception?.detection_files || []}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
