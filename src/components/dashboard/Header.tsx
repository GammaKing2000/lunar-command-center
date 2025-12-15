import { MissionClock } from './MissionClock';
import { Moon, Rocket } from 'lucide-react';

interface HeaderProps {
  missionTime: number;
}

export function Header({ missionTime }: HeaderProps) {
  return (
    <header className="flex items-center justify-between gap-4">
      {/* Logo & Title */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-transparent border border-primary/30 flex items-center justify-center">
            <Moon className="w-6 h-6 text-primary" />
          </div>
          <Rocket className="absolute -bottom-1 -right-1 w-5 h-5 text-primary rotate-45" />
        </div>
        
        <div className="flex flex-col">
          <h1 className="font-display text-xl font-bold tracking-wider text-glow-cyan text-primary">
            LUNAR ROVER
          </h1>
          <span className="text-xs font-mono text-muted-foreground tracking-widest">
            MISSION CONTROL v1.0
          </span>
        </div>
      </div>

      {/* Mission Clock */}
      <MissionClock seconds={missionTime} />
    </header>
  );
}
