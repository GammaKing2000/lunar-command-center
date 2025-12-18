import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { TelemetryPayload, Pose } from '@/types/telemetry';

const SOCKET_URL = 'http://192.168.1.8:8485';

// Singleton socket instance
export const socket = io(SOCKET_URL, {
  transports: ['websocket', 'polling'],
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  autoConnect: true
});

interface UseTelemetryReturn {
  telemetry: TelemetryPayload | null;
  isConnected: boolean;
  missionTime: number;
  positionHistory: Pose[];
  depthHistory: { time: number; depth: number }[];
}

export function useTelemetry(): UseTelemetryReturn {
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [missionTime, setMissionTime] = useState(0);
  const [positionHistory, setPositionHistory] = useState<Pose[]>([]);
  const [depthHistory, setDepthHistory] = useState<{ time: number; depth: number }[]>([]);
  
  const missionStartRef = useRef<number>(Date.now());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const updateDepthHistory = useCallback((craters: TelemetryPayload['perception']['live_craters']) => {
    if (craters.length > 0) {
      const avgDepth = craters.reduce((sum, c) => sum + c.depth, 0) / craters.length;
      setDepthHistory(prev => {
        const newEntry = { time: Date.now(), depth: avgDepth };
        const updated = [...prev, newEntry];
        return updated.slice(-50);
      });
    }
  }, []);

  useEffect(() => {
    // Mission clock
    intervalRef.current = setInterval(() => {
      setMissionTime(Math.floor((Date.now() - missionStartRef.current) / 1000));
    }, 1000);

    function onConnect() {
      console.log('Connected to Mission Control Server');
      setIsConnected(true);
    }

    function onDisconnect() {
      console.log('Disconnected from Mission Control Server');
      setIsConnected(false);
    }

    function onTelemetryUpdate(data: TelemetryPayload) {
      setTelemetry(data);
      
      // Update position history
      if (data.telemetry?.pose) {
        setPositionHistory(prev => {
          const updated = [...prev, data.telemetry.pose];
          return updated.slice(-100); 
        });
      }

      // Update depth history
      if (data.perception?.live_craters) {
        updateDepthHistory(data.perception.live_craters);
      }
    }

    function onMapReset() {
      console.log('Received Map Reset Signal - Clearing History');
      setPositionHistory([]);
      setDepthHistory([]);
      // Telemetry itself will update on next packet
    }

    // Bind events
    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('telemetry_update', onTelemetryUpdate);
    socket.on('map_reset', onMapReset);

    // Initial check
    if (socket.connected) onConnect();

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('telemetry_update', onTelemetryUpdate);
      socket.off('map_reset', onMapReset);
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
