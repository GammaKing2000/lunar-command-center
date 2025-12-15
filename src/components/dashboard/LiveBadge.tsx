interface LiveBadgeProps {
  isConnected: boolean;
}

export function LiveBadge({ isConnected }: LiveBadgeProps) {
  if (!isConnected) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-bold uppercase tracking-wider rounded bg-destructive/20 border border-destructive/50 text-destructive">
        <div className="w-2 h-2 rounded-full bg-destructive" />
        <span>OFFLINE</span>
      </div>
    );
  }

  return (
    <div className="live-badge">
      <div className="live-dot" />
      <span>LIVE SIGNAL</span>
    </div>
  );
}
