/**
 * EventBus 前端监听器
 * 
 * 功能：
 * - 监听后端事件总线发布的事件（BUG_DISCOVERED / DEPLOYMENT_SUCCESS / DEPLOYMENT_FAILED / NEW_FACTOR_ADDED）
 * - 将事件转换为前端通知（AntD message）
 * - 更新全局状态（通过 zustand store）
 * 
 * 接入方式（等待程序员deep完成 event_bus.py 后启用）：
 * - 方式A: fetch 轮询 docs/events/YYYYMMDD.json（当前实现）
 * - 方式B: WebSocket（等 deep 提供端点后切换）
 * 
 * @author Lucy (UI Designer)
 * @date 2026-04-22
 */

import type { SystemEvent, EventType } from '../types/events'
import { message } from 'antd'

// ---------- 事件处理器签名 ----------
type EventHandler = (event: SystemEvent) => void

// ---------- 事件处理器注册表 ----------
const handlers: Partial<Record<EventType, EventHandler[]>> = {
  BUG_DISCOVERED: [],
  DEPLOYMENT_SUCCESS: [],
  DEPLOYMENT_FAILED: [],
  NEW_FACTOR_ADDED: [],
  SYSTEM_BOOTSTRAP_COMPLETE: [],
}

// ---------- 配置 ----------
const EVENT_POLL_INTERVAL_MS = 30_000  // 30秒轮询一次
const EVENT_JSON_BASE_URL = '/docs/events'  // 相对于 public 或代理配置

// ---------- 状态 ----------
let pollTimer: ReturnType<typeof setInterval> | null = null
let lastSeenTimestamp: string | null = null

// ---------------------------------------------------------------------------
// 公开 API
// ---------------------------------------------------------------------------

/**
 * 注册事件处理器
 * @param eventType 要监听的事件类型
 * @param handler 事件触发时的回调函数
 */
export function on(eventType: EventType, handler: EventHandler): void {
  const list = handlers[eventType]
  if (list && !list.includes(handler)) {
    list.push(handler)
  }
}

/**
 * 取消注册事件处理器
 */
export function off(eventType: EventType, handler: EventHandler): void {
  const list = handlers[eventType]
  if (list) {
    const idx = list.indexOf(handler)
    if (idx !== -1) list.splice(idx, 1)
  }
}

/**
 * 启动事件监听（fetch 轮询模式）
 * 幂等：多次调用只启动一个轮询 timer
 */
export function startListening(): void {
  if (pollTimer !== null) return
  // 立即执行一次，再开始周期轮询
  pollEvents()
  pollTimer = setInterval(pollEvents, EVENT_POLL_INTERVAL_MS)
}

/**
 * 停止事件监听
 */
export function stopListening(): void {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

/**
 * 手动触发一次轮询（不依赖 timer）
 */
export async function pollEvents(): Promise<void> {
  try {
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')  // YYYYMMDD
    const url = `${EVENT_JSON_BASE_URL}/${today}.json`
    const res = await fetch(url, { cache: 'no-cache' })  // 避免缓存

    if (!res.ok) {
      // 404 = 今天还没有事件文件，属正常情况
      if (res.status !== 404) {
        console.warn(`[EventBusListener] poll failed: ${res.status} ${res.statusText}`)
      }
      return
    }

    const events: SystemEvent[] = await res.json()
    if (!Array.isArray(events) || events.length === 0) return

    // 按时间戳过滤，只处理新事件
    const latest = events[events.length - 1]
    if (lastSeenTimestamp === null || latest.timestamp > lastSeenTimestamp) {
      lastSeenTimestamp = latest.timestamp
    }

    // 找出所有未处理的新事件（按顺序处理）
    const newEvents = events.filter(e => {
      if (lastSeenTimestamp === null) return true
      return e.timestamp > lastSeenTimestamp!
    })

    for (const event of newEvents) {
      dispatchEvent(event)
    }
  } catch (err) {
    console.error('[EventBusListener] poll error:', err)
  }
}

// ---------------------------------------------------------------------------
// 内部函数
// ---------------------------------------------------------------------------

/** 分发事件到已注册的处理函数 */
function dispatchEvent(event: SystemEvent): void {
  const list = handlers[event.event_type]
  if (!list || list.length === 0) return

  for (const handler of list) {
    try {
      handler(event)
    } catch (err) {
      console.error(`[EventBusListener] handler error for ${event.event_type}:`, err)
    }
  }

  // 默认前端通知（可根据事件类型定制）
  notifyUser(event)
}

/** 通过 AntD message 通知用户 */
function notifyUser(event: SystemEvent): void {
  const ts = new Date(event.timestamp).toLocaleString('zh-CN')

  switch (event.event_type) {
    case 'BUG_DISCOVERED': {
      const p = event.payload as { title: string; severity: string }
      message.warning({
        content: `[Bug登记] ${p.title} (${ts})`,
        duration: 5,
      })
      break
    }
    case 'DEPLOYMENT_SUCCESS': {
      const p = event.payload as { version: string; target: string }
      message.success({
        content: `✅ 部署成功 v${p.version} → ${p.target} (${ts})`,
        duration: 4,
      })
      break
    }
    case 'DEPLOYMENT_FAILED': {
      const p = event.payload as { version: string; target: string }
      message.error({
        content: `❌ 部署失败 v${p.version} → ${p.target} (${ts})`,
        duration: 6,
      })
      break
    }
    case 'NEW_FACTOR_ADDED': {
      const p = event.payload as { symbol: string; factorCode: string; factorName: string }
      message.info({
        content: `🆕 新因子 ${p.symbol}/${p.factorCode}：${p.factorName} (${ts})`,
        duration: 5,
      })
      break
    }
    case 'SYSTEM_BOOTSTRAP_COMPLETE': {
      message.info({
        content: `🔗 事件总线已就绪 (${ts})`,
        duration: 3,
      })
      break
    }
  }
}

// ---------------------------------------------------------------------------
// WebSocket 模式（等程序员deep提供端点后切换）
// ---------------------------------------------------------------------------
// 使用方式：
//   import { connectWebSocket } from '../services/EventBusListener'
//   connectWebSocket('ws://localhost:8000/events')
//
// export function connectWebSocket(url: string): void { ... }
