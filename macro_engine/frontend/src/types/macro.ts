/**
 * 宏观打分模块 · TypeScript 类型定义
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

// ---------- 信号方向 ----------
// LONG: compositeScore > 0.15, NEUTRAL: -0.15 <= compositeScore <= 0.15, SHORT: compositeScore < -0.15
export type SignalDirection = 'LONG' | 'NEUTRAL' | 'SHORT'

// ---------- 因子明细 ----------
export interface FactorDetail {
  /** 因子代码，如 RU_TS_ROLL_YIELD */
  factorCode: string
  /** 因子中文名称 */
  factorName: string
  /** 因子方向：正贡献/负贡献/中性 */
  direction: 'positive' | 'negative' | 'neutral'
  /** 因子原始值（未标准化） */
  rawValue: number
  /** 标准化后得分 [-1, 1] */
  normalizedScore: number
  /** 因子权重（0~1） */
  weight: number
  /** 因子贡献 = normalizedScore * weight */
  contribution: number
  /** IC 值（API 实际字段名：factorIc，与 icValue 不同） */
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
  /** 因子列表 */
  factors: FactorDetail[]
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
  /** 持仓方向 */
  direction: SignalDirection
  /** 持仓比例 % */
  position_pct: number
  /** 手数 */
  lots: number
  /** 开仓价 */
  entry_price: number | null
  /** 当前价 */
  current_price: number | null
  /** 浮动盈亏 */
  unrealized_pnl: number | null
}

export interface PortfolioData {
  /** 日期 */
  date: string
  /** 总资金 */
  total_equity: number
  /** 可用资金 */
  available_cash: number
  /** 持仓列表 */
  positions: PositionItem[]
  /** 总持仓比例 % */
  total_position_pct: number
  /** 当日盈亏 */
  daily_pnl: number
  /** 当日收益率 */
  daily_return: number
  /** 当前回撤 */
  current_drawdown: number
  /** 最大回撤 */
  max_drawdown: number
}

export interface RiskLevelItem {
  level: string
  name: string
  status: '正常' | '告警' | '触发'
  value: string | null
  threshold: string | null
  message: string | null
}

export interface RiskStatusData {
  date: string
  overall_status: '正常' | '告警' | '触发'
  levels: RiskLevelItem[]
  equity: number
  drawdown: number
  drawdown_alert: number
  drawdown_stop: number
  drawdown_circuit: number
  updated_at: string
}

// ---------- 交易模块类型（新增） ----------

/** 订单状态 */
export type OrderStatus = 'pending' | 'submitted' | 'partial_filled' | 'filled' | 'cancelled' | 'rejected'

/** 订单方向 */
export type OrderDirection = 'BUY' | 'SELL'

/** 价格类型 */
export type PriceType = 'market' | 'limit' | 'stop'

/** 订单 */
export interface Order {
  /** 订单ID */
  id: string
  /** 品种代码 */
  symbol: string
  /** 方向 */
  direction: OrderDirection
  /** 手数 */
  lots: number
  /** 价格类型 */
  price_type: PriceType
  /** 委托价格（市价单为null） */
  price: number | null
  /** 订单状态 */
  status: OrderStatus
  /** 已成交手数 */
  filled_lots: number
  /** 创建时间 */
  created_at: string
  /** 更新时间 */
  updated_at: string
  /** 拒绝原因 */
  reject_reason?: string | null
}

/** 成交记录 */
export interface Trade {
  /** 成交ID */
  id: string
  /** 关联订单ID */
  order_id: string
  /** 品种代码 */
  symbol: string
  /** 方向 */
  direction: OrderDirection
  /** 成交手数 */
  lots: number
  /** 成交价格 */
  price: number
  /** 成交时间 */
  trade_time: string
  /** 手续费 */
  commission: number
}

/** 下单请求 */
export interface PlaceOrderRequest {
  symbol: string
  direction: OrderDirection
  lots: number
  price_type: PriceType
  price?: number | null
}

/** WebSocket 推送消息 */
export type WsMessageType = 'order_update' | 'trade_update' | 'position_update'

export interface WsMessage {
  type: WsMessageType
  data: unknown
  timestamp: string
}

export interface WsOrderUpdate {
  type: 'order_update'
  data: Order
  timestamp: string
}

export interface WsTradeUpdate {
  type: 'trade_update'
  data: Trade
  timestamp: string
}

export interface WsPositionUpdate {
  type: 'position_update'
  data: PositionItem
  timestamp: string
}
