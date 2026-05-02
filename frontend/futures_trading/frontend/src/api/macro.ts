import { createClient } from './client'
import type {
  MacroSignal,
  MacroSignalSummary,
  FactorDetail,
  ScoreHistoryPoint,
} from '../types/macro'
import { isScoreHistoryPoint } from '../utils/validators'

/** 统一 axios 客户端（复用 client.ts 拦截器，自动处理 code/data 解包和错误） */
const http = createClient('/api/signal')

/**
 * 后端 → 前端字段适配
 *
 * 后端返回字段与前端类型定义的差异：
 * - score → compositeScore
 * - HIGH/MEDIUM/LOW → high/medium/low  (confidence)
 * - contributionPolarity → direction (positive/negative/neutral)
 * - icValue → factorIc
 */

/** 因子级适配：后端 Factor → 前端 FactorDetail */
function _adaptFactor(o: Record<string, unknown>): FactorDetail {
  const rawDir = o.contributionPolarity ?? o.direction ?? 'neutral'
  const dir: 'positive' | 'negative' | 'neutral' =
    (rawDir === 'positive' || rawDir === 'negative' || rawDir === 'neutral') ? rawDir : 'neutral'
  const factorIcRaw = o.icValue ?? o.factorIc ?? null
  const factorIcNum = factorIcRaw != null ? Number(factorIcRaw) : NaN
  return {
    factorCode:      o.factorCode as string,
    factorName:      o.factorName as string,
    direction:       dir,
    rawValue:        o.rawValue as number,
    normalizedScore: o.normalizedScore as number,
    weight:          o.weight as number,
    contribution:    o.contribution as number,
    factorIc:        Number.isFinite(factorIcNum) ? factorIcNum : null,
  }
}

/** 信号级适配：后端 Signal → 前端 MacroSignal */
function _adaptSignal(o: Record<string, unknown>): MacroSignal {
  const rawConf = o.confidence as string | undefined
  const confidence = rawConf ? rawConf.toLowerCase() as 'high' | 'medium' | 'low' : undefined
  const factorsRaw = (o.factors ?? []) as Record<string, unknown>[]
  return {
    symbol:          o.symbol as string,
    compositeScore:  (o.score ?? o.compositeScore) as number,
    direction:       o.direction as 'LONG' | 'NEUTRAL' | 'SHORT',
    updatedAt:       (o.updatedAt ?? o.updated_at ?? '') as string,
    factors:         factorsRaw.map(_adaptFactor),
    confidence,
  }
}

/** 信号摘要适配：后端 Signal → 前端 MacroSignalSummary */
function _adaptSignalSummary(o: Record<string, unknown>): MacroSignalSummary {
  return {
    symbol:          o.symbol as string,
    compositeScore:  (o.score ?? o.compositeScore) as number,
    direction:       o.direction as 'LONG' | 'NEUTRAL' | 'SHORT',
    updatedAt:       (o.updatedAt ?? o.updated_at ?? '') as string,
  }
}

const USE_MOCK = false // 2026-04-29: 后端 /api/signal/* 已就绪

// ---------- Mock 数据（仅在 USE_MOCK=true 时使用） ----------

const MOCK_SIGNAL: MacroSignal = {
  symbol: 'RU',
  direction: 'LONG',
  compositeScore: 0.45,
  confidence: 'high',
  updatedAt: new Date().toISOString(),
  factors: [
    { factorCode: 'F1', factorName: '基差因子', rawValue: 120, normalizedScore: 0.6, weight: 0.15, contribution: 0.09, direction: 'positive' },
    { factorCode: 'F2', factorName: '动量因子', rawValue: 0.8, normalizedScore: 0.4, weight: 0.2, contribution: 0.08, direction: 'positive' },
    { factorCode: 'F3', factorName: '波动率因子', rawValue: 15, normalizedScore: -0.3, weight: 0.1, contribution: -0.03, direction: 'negative' },
    { factorCode: 'AU_AG_ratio_diff', factorName: '金银比因子', rawValue: 85.5, normalizedScore: 0.5, weight: 0.12, contribution: 0.06, direction: 'positive' },
  ],
}

const MOCK_ALL_SIGNALS: MacroSignalSummary[] = [
  { symbol: 'RU', direction: 'LONG', compositeScore: 0.45, updatedAt: new Date().toISOString() },
  { symbol: 'AG', direction: 'SHORT', compositeScore: -0.32, updatedAt: new Date().toISOString() },
  { symbol: 'AU', direction: 'NEUTRAL', compositeScore: 0.05, updatedAt: new Date().toISOString() },
  { symbol: 'CU', direction: 'LONG', compositeScore: 0.28, updatedAt: new Date().toISOString() },
]

const MOCK_HISTORY: ScoreHistoryPoint[] = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toISOString().slice(0, 10),
  score: Math.sin(i * 0.5) * 0.4 + Math.random() * 0.2 - 0.1,
  direction: Math.sin(i * 0.5) > 0 ? 'LONG' : 'SHORT',
}))

// ---------- API ----------

/**
 * 获取单品种信号
 * GET /api/signal/{symbol}
 */
export async function fetchSignal(symbol: string): Promise<MacroSignal> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300))
    return { ...MOCK_SIGNAL, symbol }
  }
  const res = await http.get<unknown>(`/${symbol}`)
  const data = res.data as Record<string, unknown>
  return _adaptSignal(data)
}

/**
 * 获取全品种信号摘要
 * GET /api/signal/all/latest → 从 signals 数组提取 MacroSignalSummary[]
 */
export async function fetchAllSignals(): Promise<MacroSignalSummary[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return MOCK_ALL_SIGNALS
  }
  const res = await http.get<unknown>('/all/latest')
  const data = res.data as Record<string, unknown>
  const signals = data.signals as Record<string, unknown>[] | undefined
  if (!Array.isArray(signals)) {
    throw new Error('全品种信号格式错误：期望 signals 数组')
  }
  return signals.map(_adaptSignalSummary)
}

/**
 * 获取单品种因子明细
 * GET /api/signal/{symbol}/factors
 */
export async function fetchFactorDetail(symbol: string): Promise<FactorDetail[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250))
    return MOCK_SIGNAL.factors
  }
  const res = await http.get<unknown>(`/${symbol}/factors`)
  const data = res.data as Record<string, unknown>
  const factors = data.factors as Record<string, unknown>[] | undefined
  if (!Array.isArray(factors)) {
    throw new Error('因子明细格式错误：期望 factors 数组')
  }
  return factors.map(_adaptFactor)
}

/**
 * 获取历史打分序列
 * GET /api/signal/{symbol}/history
 */
export async function fetchScoreHistory(
  symbol: string,
  days: number = 30,
): Promise<ScoreHistoryPoint[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return MOCK_HISTORY.slice(-days)
  }
  const res = await http.get<unknown>(`/${symbol}/history`, {
    params: { days },
  })
  const data = res.data as Record<string, unknown>
  const history = data.history as Record<string, unknown>[] | undefined
  if (!Array.isArray(history)) {
    throw new Error('历史数据格式错误：期望 history 数组')
  }
  // 适配后端字段: date(YYYYMMDD) → date(YYYY-MM-DD), score保留
  const adapted: ScoreHistoryPoint[] = history.map((item) => {
    const rawDate = item.date as string
    // 后端返回 YYYYMMDD，前端需要 YYYY-MM-DD
    const formattedDate = rawDate.length === 8
      ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
      : rawDate
    return {
      date: formattedDate,
      score: item.score as number,
      direction: item.direction as 'LONG' | 'NEUTRAL' | 'SHORT',
    }
  })
  const valid = adapted.filter(isScoreHistoryPoint)
  if (valid.length !== adapted.length) {
    console.warn(`历史数据校验: ${adapted.length - valid.length} 条记录格式异常`)
  }
  return valid
}
