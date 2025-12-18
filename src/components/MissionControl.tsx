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

  const toggleKinematics = (mode: 'jetracer' | 'ugv') => {
    setKinematicsMode(mode);
    socket.emit('set_kinematics', { mode });
  };

  return (
    <div className="min-h-screen bg-background grid-bg p-4 lg:p-6">
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
             
             {/* Map Reset Button */}
             <button
                onClick={() => {
                    console.log('Resetting Map...');
                    socket.emit('reset_map', {});
                }}
                className="px-3 py-1 bg-destructive/20 hover:bg-destructive/40 text-destructive border border-destructive/50 rounded text-xs font-bold transition-colors"
             >
                RESET MAP
             </button>
        </div>

        {/* Status Bar */}
        <StatusBar 
          isConnected={isConnected} 
          step={telemetry?.step}
        />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100vh-180px)]">
          {/* Left Column - Live Vision */}
          <div className="lg:col-span-3 h-full">
            <LiveVisionPanel
              imageBase64={telemetry?.img_base64 || null}
              craters={telemetry?.perception?.live_craters || []}
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
            />
          </div>
        </div>
      </div>
    </div>
  );
}
