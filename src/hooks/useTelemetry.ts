import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { TelemetryPayload, Pose } from '@/types/telemetry';

const SOCKET_URL = 'http://192.168.2.109:8485';

interface UseTelemetryReturn {
  telemetry: TelemetryPayload | null;
  isConnected: boolean;
  missionTime: number;
  positionHistory: Pose[];
  depthHistory: { time: number; depth: number }[];
}

export function useTelemetry(): UseTelemetryReturn {
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [missionTime, setMissionTime] = useState(0);
  const [positionHistory, setPositionHistory] = useState<Pose[]>([]);
  const [depthHistory, setDepthHistory] = useState<{ time: number; depth: number }[]>([]);
  
  const socketRef = useRef<Socket | null>(null);
  const missionStartRef = useRef<number>(Date.now());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const updateDepthHistory = useCallback((craters: TelemetryPayload['perception']['live_craters']) => {
    if (craters.length > 0) {
      const avgDepth = craters.reduce((sum, c) => sum + c.depth, 0) / craters.length;
      setDepthHistory(prev => {
        const newEntry = { time: Date.now(), depth: avgDepth };
        const updated = [...prev, newEntry];
        // Keep last 50 entries
        return updated.slice(-50);
      });
    }
  }, []);

  useEffect(() => {
    // Mission clock
    intervalRef.current = setInterval(() => {
      setMissionTime(Math.floor((Date.now() - missionStartRef.current) / 1000));
    }, 1000);

    // Socket connection
    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current.on('connect', () => {
      console.log('Connected to Mission Control Server');
      setIsConnected(true);
    });

    socketRef.current.on('disconnect', () => {
      console.log('Disconnected from Mission Control Server');
      setIsConnected(false);
    });

    socketRef.current.on('telemetry_update', (data: TelemetryPayload) => {
      setTelemetry(data);
      
      // Update position history
      if (data.telemetry?.pose) {
        setPositionHistory(prev => {
          const updated = [...prev, data.telemetry.pose];
          return updated.slice(-100); // Keep last 100 positions
        });
      }

      // Update depth history
      if (data.perception?.live_craters) {
        updateDepthHistory(data.perception.live_craters);
      }
    });

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, [updateDepthHistory]);

  return {
    telemetry,
    isConnected,
    missionTime,
    positionHistory,
    depthHistory,
  };
}
