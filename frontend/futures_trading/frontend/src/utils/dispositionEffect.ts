/**
 * 处置效应（Disposition Effect）检测工具
 * @author Lucy
 * @date 2026-05-06
 *
 * 行为金融学：投资者倾向于过早卖出盈利头寸，过久持有亏损头寸。
 * 检测条件（满足任一触发提醒）：
 *   1. 盈利 > 10% 且持仓时间 < 3天 → 过早止盈倾向
 *   2. 亏损 > 15% 且持仓时间 > 30天 → 过久持有亏损
 */

import type { VnpyPosition } from '../types/vnpy'

/** 风险等级 */
export type DispositionRiskLevel = 'NONE' | 'WARN' | 'HIGH'

/** 告警类型 */
export type DispositionAlertType = 'EARLY_PROFIT' | 'LOSS_HOLDING'

/** 建议操作 */
export type DispositionAction = 'TAKE_PROFIT' | 'STOP_LOSS' | 'HOLD'

/** 持仓风险评估结果 */
export interface PositionRiskAssessment {
  symbol: string
  direction: 'LONG' | 'SHORT'
  pnlRate: number
  holdDays: number
  riskLevel: DispositionRiskLevel
  alertType: DispositionAlertType | null
  suggestedAction: DispositionAction
  reason: string
}

// ─── 阈值配置（与后端 risk_rules.yaml R11_DISPOSITION_EFFECT 对齐）───
const THRESHOLDS = {
  /** 盈利触发阈值 */
  PROFIT_PCT: 0.10,
  /** 盈利时最大持仓天数（低于此天数触发） */
  PROFIT_MAX_DAYS: 3,
  /** 亏损触发阈值 */
  LOSS_PCT: -0.15,
  /** 亏损时最小持仓天数（高于此天数触发） */
  LOSS_MIN_DAYS: 30,
} as const

/**
 * 计算持仓天数（从开仓日期到现在的天数差）
 * @param openDate 开仓日期 ISO 字符串，若无则回退到 updatedAt
 */
export function calcHoldDays(openDate?: string, updatedAt?: string): number {
  const start = openDate ?? updatedAt
  if (!start) return 0
  const diff = Date.now() - new Date(start).getTime()
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)))
}

/**
 * 评估单个持仓的处置效应风险
 * @param position 持仓数据
 * @param holdDays 持仓天数（可选，默认从 updatedAt 推算）
 */
export function assessPosition(
  position: Pick<VnpyPosition, 'symbol' | 'direction' | 'pnlRate' | 'unrealizedPnl' | 'updatedAt'>,
  holdDays?: number,
): PositionRiskAssessment {
  const days = holdDays ?? calcHoldDays(undefined, position.updatedAt)
  const rate = position.pnlRate

  // 条件 1：盈利 > 10% 且持仓 < 3天 → 过早止盈倾向
  if (rate > THRESHOLDS.PROFIT_PCT && days < THRESHOLDS.PROFIT_MAX_DAYS) {
    return {
      symbol: position.symbol,
      direction: position.direction,
      pnlRate: rate,
      holdDays: days,
      riskLevel: 'HIGH',
      alertType: 'EARLY_PROFIT',
      suggestedAction: 'HOLD',
      reason: `盈利 ${(rate * 100).toFixed(1)}%，但仅持仓 ${days} 天，存在过早止盈倾向。建议继续持有，让利润奔跑。`,
    }
  }

  // 条件 2：亏损 > 15% 且持仓 > 30天 → 过久持有亏损
  if (rate < THRESHOLDS.LOSS_PCT && days > THRESHOLDS.LOSS_MIN_DAYS) {
    return {
      symbol: position.symbol,
      direction: position.direction,
      pnlRate: rate,
      holdDays: days,
      riskLevel: 'HIGH',
      alertType: 'LOSS_HOLDING',
      suggestedAction: 'STOP_LOSS',
      reason: `亏损 ${(rate * 100).toFixed(1)}%，已持仓 ${days} 天，存在过久持有亏损倾向。建议评估止损。`,
    }
  }

  // 接近阈值时给 WARN
  if (
    (rate > THRESHOLDS.PROFIT_PCT * 0.8 && days < THRESHOLDS.PROFIT_MAX_DAYS + 2) ||
    (rate < THRESHOLDS.LOSS_PCT * 0.8 && days > THRESHOLDS.LOSS_MIN_DAYS - 5)
  ) {
    return {
      symbol: position.symbol,
      direction: position.direction,
      pnlRate: rate,
      holdDays: days,
      riskLevel: 'WARN',
      alertType: rate > 0 ? 'EARLY_PROFIT' : 'LOSS_HOLDING',
      suggestedAction: 'HOLD',
      reason: `盈亏 ${(rate * 100).toFixed(1)}%，持仓 ${days} 天，接近处置效应阈值，请关注。`,
    }
  }

  return {
    symbol: position.symbol,
    direction: position.direction,
    pnlRate: rate,
    holdDays: days,
    riskLevel: 'NONE',
    alertType: null,
    suggestedAction: 'HOLD',
    reason: '',
  }
}

/**
 * 批量评估所有持仓，返回需要告警的列表（riskLevel !== 'NONE'）
 */
export function assessAllPositions(
  positions: Pick<VnpyPosition, 'symbol' | 'direction' | 'pnlRate' | 'unrealizedPnl' | 'updatedAt'>[],
  holdDaysMap?: Record<string, number>,
): PositionRiskAssessment[] {
  return positions
    .map((p) => assessPosition(p, holdDaysMap?.[`${p.symbol}-${p.direction}`]))
    .filter((a) => a.riskLevel !== 'NONE')
    .sort((a, b) => {
      // HIGH 优先于 WARN
      if (a.riskLevel !== b.riskLevel) return a.riskLevel === 'HIGH' ? -1 : 1
      // 同级按绝对盈亏率排序
      return Math.abs(b.pnlRate) - Math.abs(a.pnlRate)
    })
}
