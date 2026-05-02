/**
 * 宏观打分模块 · 运行时数据校验工具
 * @date 2026-04-24
 */

import type { MacroSignal, FactorDetail, ScoreHistoryPoint, PortfolioData, RiskStatusData } from '../types/macro'

/** 校验错误 */
export interface ValidationError {
  field: string
  expected: string
  actual: unknown
  message: string
}

/** 校验结果 */
export interface ValidationResult<T> {
  valid: boolean
  data?: T
  errors: ValidationError[]
}

/** 类型守卫：FactorDetail */
export function isFactorDetail(obj: unknown): obj is FactorDetail {
  if (!obj || typeof obj !== 'object') return false
  const f = obj as Record<string, unknown>
  return (
    typeof f.factorCode === 'string' &&
    typeof f.factorName === 'string' &&
    ['positive', 'negative', 'neutral'].includes(f.direction as string) &&
    typeof f.rawValue === 'number' &&
    typeof f.normalizedScore === 'number' &&
    typeof f.weight === 'number' &&
    typeof f.contribution === 'number'
  )
}

/** 类型守卫：MacroSignal（兼容 score 和 compositeScore 两种字段名） */
export function isMacroSignal(obj: unknown): obj is MacroSignal {
  if (!obj || typeof obj !== 'object') return false
  const s = obj as Record<string, unknown>
  return (
    typeof s.symbol === 'string' &&
    (typeof s.compositeScore === 'number' || typeof s.score === 'number') &&
    ['LONG', 'NEUTRAL', 'SHORT'].includes(s.direction as string) &&
    typeof s.updatedAt === 'string' &&
    Array.isArray(s.factors) &&
    s.factors.every(isFactorDetail)
  )
}

/** 类型守卫：ScoreHistoryPoint */
export function isScoreHistoryPoint(obj: unknown): obj is ScoreHistoryPoint {
  if (!obj || typeof obj !== 'object') return false
  const p = obj as Record<string, unknown>
  return (
    typeof p.date === 'string' &&
    typeof p.score === 'number' &&
    ['LONG', 'NEUTRAL', 'SHORT'].includes(p.direction as string)
  )
}

/** 类型守卫：PortfolioData */
export function isPortfolioData(obj: unknown): obj is PortfolioData {
  if (!obj || typeof obj !== 'object') return false
  const p = obj as Record<string, unknown>
  return (
    typeof p.date === 'string' &&
    typeof p.totalEquity === 'number' &&
    typeof p.availableCash === 'number' &&
    Array.isArray(p.positions) &&
    typeof p.totalPositionPct === 'number' &&
    typeof p.dailyPnl === 'number' &&
    typeof p.dailyReturn === 'number'
  )
}

/** 类型守卫：RiskStatusData */
export function isRiskStatusData(obj: unknown): obj is RiskStatusData {
  if (!obj || typeof obj !== 'object') return false
  const r = obj as Record<string, unknown>
  return (
    typeof r.date === 'string' &&
    ['正常', '告警', '触发'].includes(r.overallStatus as string) &&
    Array.isArray(r.levels) &&
    typeof r.equity === 'number' &&
    typeof r.drawdown === 'number' &&
    typeof r.updatedAt === 'string'
  )
}

/** 校验 MacroSignal（严格模式，兼容 score/compositeScore） */
export function validateMacroSignal(data: unknown): ValidationResult<MacroSignal> {
  const errors: ValidationError[] = []

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: [{ field: 'root', expected: 'object', actual: typeof data, message: '数据必须是对象' }] }
  }

  const s = data as Record<string, unknown>

  // symbol
  if (typeof s.symbol !== 'string' || s.symbol.length === 0) {
    errors.push({ field: 'symbol', expected: 'non-empty string', actual: s.symbol, message: 'symbol 必须是有效的品种代码' })
  }

  // compositeScore（兼容 score 字段）
  const score = s.compositeScore ?? s.score
  if (typeof score !== 'number' || score < -1 || score > 1) {
    errors.push({ field: 'compositeScore', expected: 'number in [-1, 1]', actual: score, message: 'compositeScore 必须在 [-1, 1] 范围内' })
  }

  // direction
  if (!['LONG', 'NEUTRAL', 'SHORT'].includes(s.direction as string)) {
    errors.push({ field: 'direction', expected: 'LONG | NEUTRAL | SHORT', actual: s.direction, message: 'direction 必须是有效的信号方向' })
  }

  // updatedAt
  if (typeof s.updatedAt !== 'string') {
    errors.push({ field: 'updatedAt', expected: 'ISO date string', actual: s.updatedAt, message: 'updatedAt 必须是 ISO 日期字符串' })
  }

  // factors
  if (!Array.isArray(s.factors)) {
    errors.push({ field: 'factors', expected: 'FactorDetail[]', actual: s.factors, message: 'factors 必须是数组' })
  } else {
    s.factors.forEach((f, i) => {
      if (!isFactorDetail(f)) {
        errors.push({ field: `factors[${i}]`, expected: 'FactorDetail', actual: f, message: `factors[${i}] 格式不正确` })
      }
    })
  }

  if (errors.length === 0 && isMacroSignal(s)) {
    return { valid: true, data: s, errors: [] }
  }

  return { valid: false, errors }
}

/** 校验 API 响应 */
export function validateApiResponse<T>(
  data: unknown,
  validator: (d: unknown) => ValidationResult<T>
): ValidationResult<T> {
  if (!data || typeof data !== 'object') {
    return { valid: false, errors: [{ field: 'root', expected: 'ApiResponse', actual: typeof data, message: '响应必须是对象' }] }
  }

  const resp = data as Record<string, unknown>

  if (typeof resp.code !== 'number') {
    return { valid: false, errors: [{ field: 'code', expected: 'number', actual: resp.code, message: 'code 必须是数字' }] }
  }

  if (resp.code !== 0) {
    return { valid: false, errors: [{ field: 'code', expected: '0', actual: resp.code, message: `API 错误: ${resp.message || '未知错误'}` }] }
  }

  return validator(resp.data)
}
