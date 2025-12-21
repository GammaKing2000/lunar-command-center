import { useState } from 'react';
// import { Database, ChevronRight } from 'lucide-react'; // Moved to MissionSetup
import { MissionSetup } from '@/components/missions/MissionSetup';
import { MissionExecution } from '@/components/missions/MissionExecution';
import { MissionReport } from '@/components/missions/MissionReport';
import { useTelemetry } from '@/hooks/useTelemetry';
import { MissionHistory } from '@/components/missions/MissionHistory';
import type { MissionReport as MissionReportType } from '@/types/telemetry';

export type MissionPhase = 'setup' | 'execution' | 'report';

const Missions = () => {
  const { telemetry, isConnected } = useTelemetry();
  const [phase, setPhase] = useState<MissionPhase | 'history'>('setup');
  const [missionConfig, setMissionConfig] = useState<{ task: string; distance: number } | null>(null);
  const [completedReport, setCompletedReport] = useState<(MissionReportType & { folder?: string }) | null>(null);

  const handleStartMission = (task: string, distance: number) => {
    setMissionConfig({ task, distance });
    setPhase('execution');
  };

  const handleMissionComplete = (report: MissionReportType) => {
    setCompletedReport(report);
    setPhase('report');
  };

  const handleReturnToSetup = () => {
    setMissionConfig(null);
    setCompletedReport(null);
    setPhase('setup');
  };

  const handleSelectHistory = async (folder: string) => {
    try {
       const response = await fetch(`http://localhost:8485/mission/report?folder=${folder}`);
       const data = await response.json();
       if (data.status === 'ok') {
         const report = {
            ...data.report,
            startTime: new Date(data.report.startTime * 1000),
            endTime: new Date(data.report.endTime * 1000)
         };
         setCompletedReport(report);
         setPhase('report');
       }
    } catch (e) {
      console.error("Failed to load report", e);
    }
  };

  return (
    <div className="p-4 lg:p-6 h-[calc(100vh-40px)] overflow-auto">
      <div className="max-w-[1800px] mx-auto">
        {phase === 'setup' && (
          <>
             <MissionSetup 
                onStartMission={handleStartMission}
                onShowHistory={() => setPhase('history')}
                isConnected={isConnected}
             />
          </>
        )}
        
        {phase === 'history' && (
            <MissionHistory 
                onSelectMission={handleSelectHistory}
                onBack={handleReturnToSetup}
            />
        )}
        
        {phase === 'execution' && missionConfig && (
          <MissionExecution
            task={missionConfig.task}
            targetDistance={missionConfig.distance}
            missionStatus={telemetry?.mission_status || null}
            imageBase64={telemetry?.img_base64 || null}
            onComplete={handleMissionComplete}
            onAbort={handleReturnToSetup}
          />
        )}
        
        {phase === 'report' && completedReport && (
          <MissionReport
            report={completedReport}
            onReturn={() => {
                // Return to history if we came from there (optional, but for now just go back to setup)
                // Or better: check if we have a missionConfig (meaning we just ran one) vs viewing old one
                if (missionConfig) {
                    handleReturnToSetup();
                } else {
                    setPhase('history');
                }
            }}
          />
        )}
      </div>
    </div>
  );
};

export default Missions;
