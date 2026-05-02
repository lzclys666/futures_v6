/**
 * Event Bus 类型定义
 * 与后端 event_bus.py 保持同步
 * @author Lucy (UI Designer)
 * @date 2026-04-22
 */

// ---------- 事件类型 ----------
export type EventType =
  | 'BUG_DISCOVERED'
  | 'DEPLOYMENT_SUCCESS'
  | 'DEPLOYMENT_FAILED'
  | 'NEW_FACTOR_ADDED'
  | 'SYSTEM_BOOTSTRAP_COMPLETE'

// ---------- 事件载荷 ----------

export interface BugDiscoveredPayload {
  bugId: string          // 格式: BUG_YYYYMMDD_序号
  symbol?: string        // 涉及品种（可选）
  factorCode?: string    // 涉及因子（可选）
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
  filePath?: string       // 代码文件路径
  codeSnippet?: string    // 问题代码片段
  affectedInterface?: string  // 受影响接口，如 I001/I002
}

export interface DeploymentPayload {
  version: string
  deployedAt: string     // ISO8601
  deployedBy: string      // Agent ID
  target: string         // 部署目标环境
}

export interface NewFactorPayload {
  symbol: string
  factorCode: string
  factorName: string
  direction: 'positive' | 'negative' | 'neutral'
  weight: number
  addedBy: string         // Agent ID
  reason?: string        // 添加原因/依据
}

// ---------- 统一事件结构 ----------
export interface SystemEvent {
  event_type: EventType
  timestamp: string       // ISO8601
  payload: BugDiscoveredPayload | DeploymentPayload | NewFactorPayload | Record<string, unknown>
}
