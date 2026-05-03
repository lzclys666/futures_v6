/**
 * 宏观打分模块 · TypeScript 类型定义
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import type { RiskRuleStatus } from './risk'

// ---------- 信号方向 ----------
// LONG: compositeScore > 0.15, NEUTRAL: -0.15 ≤ compositeScore ≤ 0.15, SHORT: compositeScore < -0.15
export type SignalDirection = 'LONG' | 'NEUTRAL' | 'SHORT'

// ---------- 因子明细 ----------
export interface FactorDetail {
  /** 因子代码，如 RU_TS_ROLL_YIELD */
  factorCode: string
  /** 因子中文名称 */
  factorName: string
  /** 因子方向：正贡献/负贡献/中性（由 contribution 决定） */
  direction: 'positive' | 'negative' | 'neutral'
  /** 因子原始值（未标准化） */
  rawValue: number
  /** 标准化后得分 [-1, 1] */
  normalizedScore: number
  /** 因子权重（0~1） */
  weight: number
  /** 因子贡献 = normalizedScore * weight */
  contribution: number
  /** 因子 IC 值（API 实际字段名：factorIc，非 null） */
  factorIc?: number
}

// ---------- 单品种信号 ----------
export interface MacroSignal {
  /** 品种代码，如 RU */
  symbol: string
  /** 最新打分（加权综合得分，-1~1） */
  compositeScore: number
  /** 信号方向 */
  direction: SignalDirection
  /** 更新时间（ISO 字符串） */
  updatedAt: string
  /** 因子列表（后端返回 factorDetails） */
  factorDetails: FactorDetail[]
  /** 信号强度（可选，用于信号系统 API） */
  signalStrength?: 'strong' | 'moderate' | 'weak'
  /** 置信度（可选） */
  confidence?: 'high' | 'medium' | 'low'
  /** 市场状态（后端返回 regime） */
  regime?: string
}

// ---------- 全品种信号列表项 ----------
export interface MacroSignalSummary {
  symbol: string
  compositeScore: number
  direction: SignalDirection
  updatedAt: string
}

// ---------- 历史打分序列（ECharts 用） ----------
export interface ScoreHistoryPoint {
  date: string  // YYYY-MM-DD
  score: number
  direction: SignalDirection
  /** 当日品种数量（可选） */
  symbolCount?: number
}

// ---------- 组件 Props ----------

export interface FactorCardProps {
  factor: FactorDetail
}

export interface SignalChartProps {
  symbol: string
  history: ScoreHistoryPoint[]
  loading?: boolean
}

export interface WeightTableProps {
  factors: FactorDetail[]
}

export interface MacroDashboardProps {
  /** 当前选中品种，默认 RU */
  defaultSymbol?: string
}

// ---------- 全局配置类型 ----------

/** ConfigProvider 主题配置 */
export interface MacroConfig {
  /** 是否跟随操作系统深色模式（自动主题） */
  darkAlgorithm: boolean
}

// ---------- SignalDailyReport 类型 ----------

/** SignalDailyReport 置信度等级 */
export type ConfidenceLevel = '高' | '中' | '低'

/** SignalDailyReport Props */
export interface SignalDailyReportProps {
  /** 默认品种，默认 AG */
  defaultSymbol?: string
}

/** 金银比因子原始数据（从 factors 数组中提取 AU_AG_ratio_diff） */
export interface GoldSilverRatioData {
  rawValue: number
  normalizedScore: number
  weight: number
  contribution: number
  factorIc: number | null
}

// ---------- API 响应结构 ----------

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// ---------- 持仓看板类型 ----------

export interface PositionItem {
  /** 品种代码 */
  symbol: string
  /** 中文名称 */
  name?: string
  /** 持仓方向 */
  direction: SignalDirection
  /** 持仓比例 % */
  positionPct: number
  /** 手数 */
  lots: number
  /** 开仓价 */
  entryPrice: number | null
  /** 当前价 */
  currentPrice: number | null
  /** 浮动盈亏 */
  unrealizedPnl: number | null
}

export interface PortfolioData {
  /** 日期 */
  date: string
  /** 总资金 */
  totalEquity: number
  /** 可用资金 */
  availableCash: number
  /** 持仓列表 */
  positions: PositionItem[]
  /** 总持仓比例 % */
  totalPositionPct: number
  /** 当日盈亏 */
  dailyPnl: number
  /** 当日收益率 */
  dailyReturn: number
  /** 当前回撤 */
  currentDrawdown: number
  /** 最大回撤 */
  maxDrawdown: number
}

export interface RiskLevelItem {
  level: string
  name: string
  status: '正常' | '告警' | '触发'
  value: string | null
  threshold: string | null
  message?: string | null
}

export interface RiskStatusData {
  date: string
  overallStatus: 'PASS' | 'WARN' | 'BLOCK'
  rules: RiskRule[]
  triggeredCount: number
  circuitBreaker: boolean
  updatedAt: string
}
