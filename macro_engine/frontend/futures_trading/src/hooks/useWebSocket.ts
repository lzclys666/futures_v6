/**
 * WebSocket React Hook — 统一连接生命周期管理
 *
 * 用法:
 *   const { connectionState, connected } = useWebSocket();
 *   const { positions } = useTradingData(); // 自动通过 WS 更新
 */

import { useEffect, useSyncExternalStore, useCallback } from 'react';
import { wsService, type WsConnectionState, type WsEventType, type WsTradingMessage } from '../services/wsService';

/** 连接状态 Hook */
export function useWebSocketState(): {
  connectionState: WsConnectionState;
  connected: boolean;
} {
  const state = useSyncExternalStore(
    (cb) => wsService.onStateChange(cb),
    () => wsService.connectionState,
  );

  return {
    connectionState: state,
    connected: state === 'connected',
  };
}

/** 数据订阅 Hook — 订阅指定事件类型，自动管理订阅生命周期 */
export function useWsSubscription(
  events: WsEventType[],
  onMessage: (msg: WsTradingMessage) => void,
): void {
  useEffect(() => {
    const unsub = wsService.subscribe(events, onMessage);
    return unsub;
  }, [events.join(','), onMessage]);
}

/**
 * 应用级 WebSocket 生命周期 Hook
 * 应在 App 或 MainLayout 级别调用一次
 */
export function useWebSocketLifecycle(): {
  connectionState: WsConnectionState;
  connected: boolean;
  reconnect: () => void;
} {
  const state = useSyncExternalStore(
    (cb) => wsService.onStateChange(cb),
    () => wsService.connectionState,
  );

  useEffect(() => {
    wsService.connect();
    return () => { wsService.disconnect(); };
  }, []);

  const reconnect = useCallback(() => {
    wsService.disconnect();
    wsService.connect();
  }, []);

  return {
    connectionState: state,
    connected: state === 'connected',
    reconnect,
  };
}
