/**
 * 交易模块 · TypeScript 类型定义
 * @author Lucy
 * @date 2026-04-27
 */

/** 下单方向 */
export type OrderDirection = 'LONG' | 'SHORT'

/** 开平方向 */
export type Offset = 'OPEN' | 'CLOSE' | 'CLOSETODAY' | 'CLOSEYESTERDAY'

/** 订单状态 */
export type OrderStatus =
  | 'PENDING'
  | 'SUBMITTING'
  | 'NOT_TRADED'
  | 'PART_TRADED'
  | 'ALL_TRADED'
  | 'CANCELLED'
  | 'REJECTED'

/** 订单类型 */
export type OrderType = 'LIMIT' | 'MARKET' | 'STOP'

/** 下单请求 */
export interface OrderRequest {
  symbol: string
  direction: OrderDirection
  price: number
  volume: number
  order_type: OrderType
  offset: Offset
  /** 止损/止盈价（可选） */
  stopPrice?: number
}

/** 下单响应 */
export interface OrderResponse {
  orderId: string
  symbol: string
  direction: OrderDirection
  price: number
  volume: number
  tradedVolume: number
  status: OrderStatus
  createdAt: string
  updatedAt: string
  message?: string
  /** 是否成功（可选，兼容旧数据） */
  success?: boolean
}

/** 撤单响应 */
export interface CancelOrderResponse {
  orderId: string
  success: boolean
  message?: string
}

/** 实时行情数据 */
export interface MarketData {
  symbol: string
  lastPrice: number
  bidPrice1: number
  askPrice1: number
  bidVolume1: number
  askVolume1: number
  volume: number
  openPrice: number
  highPrice: number
  lowPrice: number
  preClose: number
  updateTime: string
}
