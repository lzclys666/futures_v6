/**
 * 宏观打分模块 · API 封装
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 *
 * ⚠️ 字段映射说明（Mimo API V1.0 → 前端类型契约 V1.0）：
 *   Mimo 后端：snake_case + 中文 factor_direction（"正向"/"反向"）
 *   前端类型：camelCase + 英文 direction（"positive"/"negative"/"neutral"）
 *   转换逻辑在 _adaptFactor 中自动完成。
 */

import axios from 'axios'
import type {
  MacroSignal,
  MacroSignalSummary,
  FactorDetail,
  ScoreHistoryPoint,
} from '../types/macro'

const BASE_URL = '/api/macro'

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  // Mimo API 返回 snake_case + 中文字段；前端统一用 camelCase
  transformResponse: [
    (raw) => {
      try {
        const j = JSON.parse(raw)
        // 外层 ApiResponse { code, message, data } → 直接返回 data
        if (j.data !== undefined) {
          return _adapt(j.data)
        }
        return _adapt(j)
      } catch {
        // 非 JSON 响应（如后端 404/5xx 返回 HTML）交给 interceptor 处理
        return raw
      }
    },
  ],
})

// 【修复·严重问题1】HTTP 错误拦截器：非 2xx 响应统一返回结构化错误
http.interceptors.response.use(
  (response) => response,
  (error) => {
    // 优先从响应体提取结构化错误信息
    const data = error.response?.data
    let message = error.message
    let code = error.response?.status || 500
    if (data && typeof data === 'object') {
      const d = data as Record<string, unknown>
      if (typeof d.message === 'string') message = d.message
      if (typeof d.code === 'number') code = d.code
    }
    return Promise.reject({ code, message, data: null })
  }
)

// ---------------------------------------------------------------------------
// 字段适配：snake_case → camelCase + 中文 direction → 英文 direction
// ---------------------------------------------------------------------------

// 注意：_dirZhToEn 已废弃；API 现直接返回英文 direction ("positive"/"negative"/"neutral")

/** 递归适配 snake_case API 字段 → camelCase TypeScript 字段 */
function _adapt(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(_adapt)
  if (obj === null || typeof obj !== 'object') return obj

  const o = obj as Record<string, unknown>

  // 因子明细：兼容 snake_case (factor_code/factor_value/factor_weight) 和 camelCase (factorCode/normalizedScore/weight)
  if ('factor_code' in o || 'factorCode' in o) {
    // Mimo FastAPI 实际返回 camelCase: factorCode, normalizedScore, weight, contributionPolarity
    const fv = (o['factor_value'] ?? o.normalizedScore ?? o['normalizedScore']) as number
    const fw = (o['factor_weight'] ?? o.weight ?? o['weight']) as number
    // contributionPolarity 直接用英文 ("positive"/"negative"/"neutral")，不需要 _dirZhToEn 转换
    // 兼容 factorDirection/factor_direction/contributionPolarity 三种字段名
    const rawDir = o.contributionPolarity ?? o.factorDirection ?? o['factor_direction']
    const dir: 'positive' | 'negative' | 'neutral' = (rawDir === 'positive' || rawDir === 'negative') ? rawDir : 'neutral'
    return {
      factorCode:       o['factor_code'] ?? o.factorCode,
      factorName:       o['factor_name'] ?? o.factorName,
      direction:        dir,
      rawValue:         (o['raw_value'] ?? o.rawValue ?? fv) as number,
      normalizedScore:  fv,
      weight:           fw,
      contribution:     Math.round(fv * fw * 1e6) / 1e6, // 保留6位精度
    } as FactorDetail
  }

  // 单品种信号（顶层 compositeScore/direction 已正确）
  if ('compositeScore' in o && 'factors' in o) {
    return {
      ...o,
      // 【修复·严重问题5】factors 为 undefined 时返回空数组兜底
      factors: Array.isArray(o['factors']) ? _adapt(o['factors']) : [],
    }
  }

  // ScoreHistory / MacroSignalSummary：直接透传（字段已 camelCase）
  return o
}

// ---------------------------------------------------------------------------
// API 函数
// ---------------------------------------------------------------------------

/**
 * GET /api/macro/signal/{symbol} → 单品种最新信号（含因子明细）
 * Mimo: macro_api_server.py
 */
export async function fetchSignal(symbol: string): Promise<MacroSignal> {
  const res = await http.get<MacroSignal>(`/signal/${symbol}`)
  return res.data
}

/**
 * GET /api/macro/signal/all → 全品种信号列表
 * Mimo: macro_api_server.py
 */
export async function fetchAllSignals(): Promise<MacroSignalSummary[]> {
  const res = await http.get<MacroSignalSummary[]>('/signal/all')
  return res.data
}

/**
 * GET /api/macro/factor/{symbol} → 因子明细
 * Mimo: macro_api_server.py
 */
export async function fetchFactorDetail(symbol: string): Promise<FactorDetail[]> {
  const res = await http.get<FactorDetail[]>(`/factor/${symbol}`)
  return res.data
}

/**
 * GET /api/macro/score-history/{symbol}?days=30 → 历史打分序列
 * Mimo: macro_api_server.py
 * days: 默认 30，最大 90（Mimo 接口校验）
 */
export async function fetchScoreHistory(
  symbol: string,
  days: number = 30,
): Promise<ScoreHistoryPoint[]> {
  const res = await http.get<ScoreHistoryPoint[]>(`/score-history/${symbol}`, {
    params: { days },
  })
  return res.data
}
