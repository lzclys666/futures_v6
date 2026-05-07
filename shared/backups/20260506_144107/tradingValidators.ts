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

/** 校验 RiskStatusData */
export function validateRiskStatusData(data: unknown): { valid: boolean; errors: string[]; data?: RiskStatusData } {
  const errors: string[] = []

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: ['数据必须是对象'] }
  }

  const r = data as Record<string, unknown>

  if (typeof r.date !== 'string') errors.push('date 必须是字符串')
  if (!['PASS', 'WARN', 'BLOCK'].includes(r.overallStatus as string)) {
    errors.push('overallStatus 必须是 PASS|WARN|BLOCK')
  }
  if (!Array.isArray(r.rules)) errors.push('rules 必须是数组')

  if (errors.length > 0) {
    return { valid: false, errors }
  }

  if (isRiskStatusData(r)) {
    return { valid: true, errors: [], data: r }
  }

  return { valid: false, errors: ['RiskStatusData 结构不完整'] }
}
