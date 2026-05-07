/**
 * 风控 WebSocket Hook
 * 连接 /ws/risk 接收实时风控状态推送（每 5 秒）
 * 自动重连（指数退避）+ 心跳 ping（每 30 秒）
 * @author Lucy
 * @date 2026-05-06
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { RiskSeverity, RiskRuleStatus } from '../types/risk'

// ---------- 类型定义 ----------

/** WebSocket 推送的风控状态数据（后端 /ws/risk 推送格式） */
interface WsRiskData {
  overallStatus: RiskSeverity
  rules: RiskRuleStatus[]
  updatedAt: string
}

/** WebSocket 推送消息 */
interface WsRiskMessage {
  type: 'risk_status_update'
  data: WsRiskData
}

/** Hook 返回值 */
export interface UseRiskWebSocketResult {
  /** 最新风控状态（WebSocket 推送），未连接时为 null */
  riskStatus: WsRiskData | null
  /** WebSocket 是否已连接 */
  connected: boolean
  /** 连接错误信息 */
  error: string | null
}

// ---------- 配置 ----------

/** WebSocket 基础 URL（与后端 ws://localhost:8000/ws/risk 对齐） */
function getWsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // 开发环境直连后端 8000，生产环境跟随当前 host
  const isDev = window.location.port === '5173' || window.location.hostname === 'localhost'
  const host = isDev ? 'localhost:8000' : window.location.host
  return `${proto}//${host}/ws/risk`
}

/** 初始重连延迟（ms） */
const RECONNECT_BASE_MS = 1000
/** 最大重连延迟（ms） */
const RECONNECT_MAX_MS = 30000
/** 心跳间隔（ms） */
const HEARTBEAT_MS = 30_000

// ---------- Hook ----------

export function useRiskWebSocket(): UseRiskWebSocketResult {
  const [riskStatus, setRiskStatus] = useState<WsRiskData | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // refs 用于 cleanup，避免 stale closure
  const wsRef = useRef<WebSocket | null>(null)
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const mountedRef = useRef(true)

  /** 清除心跳定时器 */
  const clearHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
  }, [])

  /** 清除重连定时器 */
  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  /** 启动心跳：每 30 秒发送 ping */
  const startHeartbeat = useCallback((ws: WebSocket) => {
    clearHeartbeat()
    heartbeatRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, HEARTBEAT_MS)
  }, [clearHeartbeat])

  /** 安排重连（指数退避） */
  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return
    clearReconnect()

    const attempt = reconnectAttemptRef.current
    const delay = Math.min(RECONNECT_BASE_MS * Math.pow(2, attempt), RECONNECT_MAX_MS)
    reconnectAttemptRef.current = attempt + 1

    reconnectTimerRef.current = setTimeout(() => {
      if (mountedRef.current) {
        connect()
      }
    }, delay)
  }, [clearReconnect])

  /** 建立 WebSocket 连接 */
  const connect = useCallback(() => {
    if (!mountedRef.current) return

    // 关闭已有连接
    if (wsRef.current) {
      wsRef.current.onclose = null // 避免触发重连
      wsRef.current.close()
      wsRef.current = null
    }
    clearHeartbeat()

    const url = getWsUrl()
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      setConnected(true)
      setError(null)
      reconnectAttemptRef.current = 0 // 重置重连计数
      startHeartbeat(ws)
      // 连接成功后立即请求最新状态
      ws.send('get_status')
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      const raw = event.data as string

      // 忽略 pong 响应
      if (raw === 'pong') return

      try {
        const msg = JSON.parse(raw) as WsRiskMessage
        if (msg.type === 'risk_status_update' && msg.data) {
          setRiskStatus(msg.data)
          setError(null)
        }
      } catch {
        // 非 JSON 消息忽略
      }
    }

    ws.onerror = () => {
      if (!mountedRef.current) return
      setError('WebSocket 连接错误')
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setConnected(false)
      clearHeartbeat()
      wsRef.current = null
      scheduleReconnect()
    }
  }, [clearHeartbeat, startHeartbeat, scheduleReconnect])

  // 挂载时连接，卸载时断开
  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      clearReconnect()
      clearHeartbeat()
      if (wsRef.current) {
        wsRef.current.onclose = null // 阻止 onclose 触发重连
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect, clearReconnect, clearHeartbeat])

  return { riskStatus, connected, error }
}
