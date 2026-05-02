/**
 * WebSocket 统一服务 — 连接 VNpyBridge 实时推送
 *
 * 特性:
 * - 自动重连（指数退避，1s→2s→4s…→30s 上限）
 * - 心跳保活（15s ping，30s 超时断连）
 * - 事件订阅/退订模式
 * - 连接状态回调
 *
 * 对应后端: ws://localhost:8000/ws/vnpy (VNpyBridge API v1.0 方式二)
 */

/** WebSocket 连接状态 */
export type WsConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

/** VNpy WebSocket 消息帧（后端→前端推送） */
export interface WsTradingMessage {
  type: 'position' | 'order' | 'trade' | 'account' | 'risk_event' | 'log' | 'pong';
  payload: unknown;
  timestamp: string;
}

/** 前端→后端请求帧 */
export interface WsClientMessage {
  type: 'subscribe' | 'unsubscribe' | 'ping' | 'get_status' | 'get_positions' | 'get_account' | 'get_strategies' | 'start_strategy' | 'stop_strategy';
  events?: string[];
  strategy?: string;
}

/** 事件类型 */
export type WsEventType = 'position' | 'order' | 'trade' | 'account' | 'risk_event' | 'log';

/** 消息处理器 */
type MessageHandler = (msg: WsTradingMessage) => void;

/** 连接状态变更回调 */
type StateHandler = (state: WsConnectionState) => void;

const WS_URL = 'ws://localhost:8000/ws/vnpy';
const PING_INTERVAL = 15_000;
const PONG_TIMEOUT = 30_000;
const INITIAL_RECONNECT_DELAY = 1_000;
const MAX_RECONNECT_DELAY = 30_000;

class WsService {
  private ws: WebSocket | null = null;
  private state: WsConnectionState = 'disconnected';
  private handlers = new Map<WsEventType, Set<MessageHandler>>();
  private stateHandlers = new Set<StateHandler>();
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private pongTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = INITIAL_RECONNECT_DELAY;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private subscribedEvents = new Set<WsEventType>();

  /** 获取当前连接状态 */
  get connectionState(): WsConnectionState {
    return this.state;
  }

  /** 连接到 WebSocket 服务器 */
  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.setState('connecting');
    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        this.setState('connected');
        this.reconnectDelay = INITIAL_RECONNECT_DELAY;
        this.startHeartbeat();

        // 重连后重新订阅之前的事件
        if (this.subscribedEvents.size > 0) {
          this.send({ type: 'subscribe', events: Array.from(this.subscribedEvents) });
        }
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: WsTradingMessage = JSON.parse(event.data as string);

          // 处理 pong
          if (msg.type === 'pong') {
            this.resetPongTimer();
            return;
          }

          // 分发到订阅的 handler
          const typeHandlers = this.handlers.get(msg.type as WsEventType);
          if (typeHandlers) {
            typeHandlers.forEach(h => h(msg));
          }
        } catch {
          console.warn('[WS] Failed to parse message');
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        if (this.state === 'connected' || this.state === 'connecting') {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        // onclose will fire after onerror
        console.warn('[WS] Connection error');
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  /** 断开连接 */
  disconnect(): void {
    this.clearReconnect();
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.onclose = null; // 防止触发重连
      this.ws.close();
      this.ws = null;
    }
    this.setState('disconnected');
  }

  /** 订阅事件类型 */
  subscribe(events: WsEventType[], handler: MessageHandler): () => void {
    events.forEach(e => {
      if (!this.handlers.has(e)) {
        this.handlers.set(e, new Set());
      }
      this.handlers.get(e)!.add(handler);
      this.subscribedEvents.add(e);
    });

    if (this.state === 'connected') {
      this.send({ type: 'subscribe', events });
    }

    // 返回退订函数
    return () => {
      events.forEach(e => {
        const set = this.handlers.get(e);
        if (set) {
          set.delete(handler);
          if (set.size === 0) {
            this.handlers.delete(e);
            this.subscribedEvents.delete(e);
          }
        }
      });
      if (this.state === 'connected') {
        this.send({ type: 'unsubscribe', events });
      }
    };
  }

  /** 监听连接状态变更 */
  onStateChange(handler: StateHandler): () => void {
    this.stateHandlers.add(handler);
    // 立即通知当前状态
    handler(this.state);
    return () => { this.stateHandlers.delete(handler); };
  }

  /** 发送消息到服务端 */
  send(msg: WsClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  /** 请求最新数据（拉模式） */
  requestData(): void {
    if (this.state !== 'connected') return;
    this.send({ type: 'get_positions' });
    this.send({ type: 'get_account' });
  }

  /* ─── 内部 ─── */

  private setState(state: WsConnectionState): void {
    if (this.state !== state) {
      this.state = state;
      this.stateHandlers.forEach(h => h(state));
    }
  }

  private startHeartbeat(): void {
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
        this.pongTimer = setTimeout(() => {
          console.warn('[WS] Pong timeout, reconnecting…');
          this.ws?.close();
        }, PONG_TIMEOUT);
      }
    }, PING_INTERVAL);
  }

  private stopHeartbeat(): void {
    if (this.pingTimer) { clearInterval(this.pingTimer); this.pingTimer = null; }
    if (this.pongTimer) { clearTimeout(this.pongTimer); this.pongTimer = null; }
  }

  private resetPongTimer(): void {
    if (this.pongTimer) { clearTimeout(this.pongTimer); this.pongTimer = null; }
  }

  private scheduleReconnect(): void {
    this.setState('reconnecting');
    this.clearReconnect();
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY);
      this.connect();
    }, this.reconnectDelay);
  }

  private clearReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

/** 全局单例 */
export const wsService = new WsService();

export default wsService;
