import { useState, useEffect } from 'react';
import { Clock, Calendar, Database, ChevronRight, AlertCircle, Search, Target, Camera } from 'lucide-react';
import { PanelWrapper } from '@/components/dashboard/PanelWrapper';

interface MissionSummary {
  id: string;
  folder: string;
  task: string;
  startTime: number;
  duration: number;
  distance: number;
  findings: {
    craters: number;
    aliens: number;
  };
  snapshot_count: number;
}

interface MissionHistoryProps {
  onSelectMission: (folder: string) => void;
  onBack: () => void;
}

export function MissionHistory({ onSelectMission, onBack }: MissionHistoryProps) {
  const [history, setHistory] = useState<MissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      // Ensure we hit the python server
      const response = await fetch('http://localhost:8485/mission/history');
      const data = await response.json();
      
      if (data.status === 'ok') {
        setHistory(data.history);
      } else {
        setError(data.message || 'Failed to fetch history');
      }
    } catch (err) {
      setError('Could not connect to Mission Server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredHistory = history.filter(item => 
    item.task.toLowerCase().includes(search.toLowerCase()) || 
    item.id.toLowerCase().includes(search.toLowerCase())
  );

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold tracking-wider flex items-center gap-3">
          <Database className="w-8 h-8 text-primary" />
          MISSION ARCHIVES
        </h1>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-lg bg-card/50 border border-border/50 hover:bg-card transition-colors font-mono text-sm"
        >
          BACK TO DASHBOARD
        </button>
      </div>

      <div className="flex-1 min-h-0 container mx-auto max-w-5xl">
        <PanelWrapper title="Past Missions" className="h-full flex flex-col">
           {/* Toolbar */}
           <div className="p-4 border-b border-border/30 flex gap-4">
             <div className="relative flex-1">
               <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
               <input 
                 type="text"
                 placeholder="Search mission ID, task..."
                 className="w-full bg-space-black/50 border border-border/50 rounded-lg pl-9 pr-4 py-2 text-sm font-mono focus:outline-none focus:border-primary/50"
                 value={search}
                 onChange={(e) => setSearch(e.target.value)}
               />
             </div>
             <button
                onClick={fetchHistory} 
                className="px-4 py-2 bg-primary/20 text-primary border border-primary/30 rounded-lg text-sm font-bold hover:bg-primary/30 transition-colors"
              >
                REFRESH
              </button>
           </div>

           {/* Content */}
           <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
             {loading ? (
               <div className="flex flex-col items-center justify-center h-full text-muted-foreground animate-pulse gap-2">
                 <Database className="w-8 h-8" />
                 <span className="font-mono text-xs">RETRIEVING ARCHIVES...</span>
               </div>
             ) : error ? (
               <div className="flex flex-col items-center justify-center h-full text-destructive gap-2">
                 <AlertCircle className="w-8 h-8" />
                 <span className="font-mono text-sm">{error}</span>
                 <button onClick={fetchHistory} className="mt-2 text-primary underline text-xs">Retry</button>
               </div>
             ) : filteredHistory.length === 0 ? (
               <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                 <div className="w-16 h-16 rounded-full bg-muted/20 flex items-center justify-center mb-2">
                   <Database className="w-8 h-8 alpha-50" />
                 </div>
                 <p className="font-mono">NO MISSIONS FOUND</p>
               </div>
             ) : (
               <div className="space-y-3">
                 {filteredHistory.map((mission) => (
                   <div 
                     key={mission.folder}
                     onClick={() => onSelectMission(mission.folder)}
                     className="group flex flex-col md:flex-row md:items-center gap-4 p-4 rounded-xl bg-card/30 border border-border/30 hover:border-primary/50 hover:bg-card/50 transition-all cursor-pointer"
                   >
                     {/* Icon & ID */}
                     <div className="flex items-center gap-4 min-w-[200px]">
                       <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                         <Target className="w-5 h-5 text-primary" />
                       </div>
                       <div>
                         <h3 className="font-bold text-foreground group-hover:text-primary transition-colors">{mission.task}</h3>
                         <p className="text-xs font-mono text-muted-foreground">{mission.id}</p>
                       </div>
                     </div>

                     {/* Stats */}
                     <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
                       <div className="flex items-center gap-2 text-sm text-muted-foreground">
                         <Calendar className="w-4 h-4" />
                         <span>{new Date(mission.startTime * 1000).toLocaleDateString()}</span>
                       </div>
                       <div className="flex items-center gap-2 text-sm text-muted-foreground">
                         <Clock className="w-4 h-4" />
                         <span>{formatDuration(mission.duration)}</span>
                       </div>
                       <div className="flex items-center gap-2">
                         <span className="text-xs font-mono text-muted-foreground">DIST:</span>
                         <span className="font-mono font-bold text-foreground">{(mission.distance * 100).toFixed(0)}cm</span>
                       </div>
                       <div className="flex items-center gap-2">
                         <Camera className="w-4 h-4 text-muted-foreground" />
                         <span className="font-mono font-bold text-foreground">{mission.snapshot_count}</span>
                         <span className="text-xs text-muted-foreground">imgs</span>
                       </div>
                     </div>

                     {/* Arrow */}
                     <div className="hidden md:flex items-center justify-end w-8">
                       <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                     </div>
                   </div>
                 ))}
               </div>
             )}
           </div>
        </PanelWrapper>
      </div>
    </div>
  );
}
