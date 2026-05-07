/**
 * 持仓看板 · 运行时数据校验
 * @date 2026-04-24
 */

import type { PortfolioData, RiskStatusData } from '../types/macro'
import { isPortfolioData, isRiskStatusData } from '../utils/validators'

/** 校验 PortfolioData */
export function validatePortfolioData(data: unknown): { valid: boolean; errors: string[]; data?: PortfolioData } {
  const errors: string[] = []

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: ['数据必须是对象'] }
  }

  const p = data as Record<string, unknown>

  if (typeof p.date !== 'string') errors.push('date 必须是字符串')
  if (typeof p.totalEquity !== 'number' || p.totalEquity < 0) errors.push('totalEquity 必须是非负数')
  if (typeof p.availableCash !== 'number' || p.availableCash < 0) errors.push('availableCash 必须是非负数')
  if (!Array.isArray(p.positions)) errors.push('positions 必须是数组')

  if (errors.length > 0) {
    return { valid: false, errors }
  }

  if (isPortfolioData(p)) {
    return { valid: true, errors: [], data: p }
  }

  return { valid: false, errors: ['PortfolioData 结构不完整'] }
}

/**
 * 校验并规范化 RiskStatusData
 * 兼容两种格式：
 *   1. 新格式（后端已转换）：{ overallStatus, rules, ... }
 *   2. 旧格式（vnpy_bridge 原始）：{ status, active_rules, levels, ... }
 * 同时兼容 API 包装层 { code, message, data } 和直接数据
 */
export function validateRiskStatusData(data: unknown): { valid: boolean; errors: string[]; data?: RiskStatusData } {
  const errors: string[] = []

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: ['数据必须是对象'] }
  }

  // 兼容 API 包装层 { code, message, data }
  const raw = data as Record<string, unknown>
  const r: Record<string, unknown> =
    'code' in raw && 'data' in raw && typeof raw.data === 'object' && raw.data !== null
      ? (raw.data as Record<string, unknown>)
      : raw

  // --- 字段规范化：旧格式 → 新格式 ---
  // status → overallStatus
  if (!('overallStatus' in r) && 'status' in r) {
    const s = r.status as string
    r.overallStatus = s === 'normal' ? 'PASS' : s === 'warning' ? 'WARN' : s === 'danger' ? 'BLOCK' : s
  }
  // active_rules / levels → rules
  if (!('rules' in r)) {
    if ('active_rules' in r && Array.isArray(r.active_rules)) {
      r.rules = r.active_rules
    } else if ('levels' in r && Array.isArray(r.levels)) {
      r.rules = r.levels
    }
  }

  // --- 字段校验 ---
  if (typeof r.date !== 'string') errors.push('date 必须是字符串')
  if (!['PASS', 'WARN', 'BLOCK'].includes(r.overallStatus as string)) {
    errors.push(`overallStatus 必须是 PASS|WARN|BLOCK，实际值: ${r.overallStatus}`)
  }
  if (!Array.isArray(r.rules)) errors.push('rules 必须是数组')

  // 补全可选字段默认值
  if (typeof r.triggeredCount !== 'number') r.triggeredCount = 0
  if (typeof r.circuitBreaker !== 'boolean') r.circuitBreaker = false
  if (typeof r.updatedAt !== 'string') r.updatedAt = new Date().toISOString()
  if (typeof r.date !== 'string') r.date = new Date().toISOString().slice(0, 10)

  if (errors.length > 0) {
    return { valid: false, errors }
  }

  if (isRiskStatusData(r)) {
    return { valid: true, errors: [], data: r }
  }

  return { valid: false, errors: ['RiskStatusData 结构不完整'] }
}
