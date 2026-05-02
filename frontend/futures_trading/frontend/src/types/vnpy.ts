/**
 * VNpy 桥接模块 · TypeScript 类型定义
 * @author Lucy
 * @date 2026-04-27
 */

/** VNpy 连接状态 */
export type VnpyConnectionState = 'connected' | 'disconnected' | 'connecting' | 'error'

/** VNpy 网关状态（/api/vnpy/status） */
export interface VnpyStatus {
  /** 连接状态 */
  state: VnpyConnectionState
  /** 网关名称 */
  gatewayName: string
  /** 是否已登录 */
  loggedIn: boolean
  /** 最后心跳时间 */
  lastHeartbeat: string
  /** 错误信息 */
  error?: string
  /** 版本号 */
  version?: string
}

/** VNpy 账户信息（/api/vnpy/account） */
export interface VnpyAccount {
  accountId: string
  /** 总资产 */
  balance: number
  /** 可用资金 */
  available: number
  /** 冻结保证金 */
  frozen: number
  /** 浮动盈亏 */
  unrealizedPnl: number
  /** 已实现盈亏 */
  realizedPnl: number
  /** 总盈亏 */
  totalPnl: number
  /** 收益率 */
  returnRate: number
  /** 保证金占用率 */
  marginRatio: number
  /** 更新时间 */
  updatedAt: string
}

/** VNpy 持仓（/api/vnpy/positions） */
export interface VnpyPosition {
  symbol: string
  direction: 'LONG' | 'SHORT'
  volume: number
  /** 昨仓 */
  ydVolume: number
  /** 今仓 */
  tdVolume: number
  /** 可平量 */
  available: number
  /** 开仓均价 */
  avgPrice: number
  /** 当前价 */
  lastPrice: number
  /** 浮动盈亏 */
  unrealizedPnl: number
  /** 保证金 */
  margin: number
  /** 盈亏率 */
  pnlRate: number
  /** 更新时间 */
  updatedAt: string
}

/** VNpy 订单（/api/vnpy/orders） */
export interface VnpyOrder {
  orderId: string
  symbol: string
  direction: 'LONG' | 'SHORT'
  offset: 'OPEN' | 'CLOSE' | 'CLOSE_TODAY' | 'CLOSE_YESTERDAY'
  price: number
  volume: number
  tradedVolume: number
  status: string
  orderTime: string
  cancelTime?: string
  /** 订单备注 */
  reference?: string
}
