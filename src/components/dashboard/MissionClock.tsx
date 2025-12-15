import { Clock } from 'lucide-react';

interface MissionClockProps {
  seconds: number;
}

export function MissionClock({ seconds }: MissionClockProps) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const formatNumber = (n: number) => n.toString().padStart(2, '0');

  return (
    <div className="glass-panel chamfer p-4">
      <div className="flex items-center gap-3">
        <Clock className="w-5 h-5 text-primary" />
        <div className="flex flex-col">
          <span className="data-label text-[10px]">Mission Time</span>
          <div className="flex items-baseline gap-0.5">
            <span className="text-xs text-muted-foreground">T+</span>
            <span className="font-display text-2xl font-bold tracking-wider text-glow-cyan text-primary">
              {formatNumber(hours)}:{formatNumber(minutes)}:{formatNumber(secs)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
