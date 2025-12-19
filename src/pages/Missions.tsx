import { useState } from 'react';
import { MissionSetup } from '@/components/missions/MissionSetup';
import { MissionExecution } from '@/components/missions/MissionExecution';
import { MissionReport } from '@/components/missions/MissionReport';
import { useTelemetry } from '@/hooks/useTelemetry';
import type { MissionReport as MissionReportType } from '@/types/telemetry';

export type MissionPhase = 'setup' | 'execution' | 'report';

const Missions = () => {
  const { telemetry, isConnected } = useTelemetry();
  const [phase, setPhase] = useState<MissionPhase>('setup');
  const [missionConfig, setMissionConfig] = useState<{ task: string; distance: number } | null>(null);
  const [completedReport, setCompletedReport] = useState<MissionReportType | null>(null);

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

  return (
    <div className="p-4 lg:p-6 h-[calc(100vh-40px)] overflow-auto">
      <div className="max-w-[1800px] mx-auto">
        {phase === 'setup' && (
          <MissionSetup 
            onStartMission={handleStartMission}
            isConnected={isConnected}
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
            onReturn={handleReturnToSetup}
          />
        )}
      </div>
    </div>
  );
};

export default Missions;
