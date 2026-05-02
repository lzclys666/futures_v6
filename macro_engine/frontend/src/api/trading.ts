/**
 * 交易模块 · API 封装
 * @date 2026-04-24
 */

import axios from 'axios'
import type {
  PortfolioData,
  RiskStatusData,
  Order,
  Trade,
  PlaceOrderRequest,
} from '../types/macro'

const http = axios.create({
  baseURL: '/api/trading',
  timeout: 10000,
  transformResponse: [
    (raw) => {
      try {
        const j = JSON.parse(raw)
        if (j.data !== undefined) return j.data
        return j
      } catch {
        return raw
      }
    },
  ],
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
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

/**
 * GET /api/trading/positions → 当前持仓
 */
export async function fetchPositions(): Promise<PortfolioData> {
  const res = await http.get<PortfolioData>('/positions')
  return res.data
}

/**
 * GET /api/trading/risk-status → 风控状态
 */
export async function fetchRiskStatus(): Promise<RiskStatusData> {
  const res = await http.get<RiskStatusData>('/risk-status')
  return res.data
}

/**
 * GET /api/trading/orders → 当日订单列表
 */
export async function fetchOrders(): Promise<Order[]> {
  const res = await http.get<Order[]>('/orders')
  return res.data
}

/**
 * GET /api/trading/trades → 当日成交记录
 */
export async function fetchTrades(): Promise<Trade[]> {
  const res = await http.get<Trade[]>('/trades')
  return res.data
}

/**
 * POST /api/trading/order → 下单
 */
export async function placeOrder(req: PlaceOrderRequest): Promise<Order> {
  const res = await http.post<Order>('/order', req)
  return res.data
}

/**
 * DELETE /api/trading/order → 平仓/撤单
 * @param symbol 品种代码
 * @param orderId 可选，指定订单ID
 */
export async function closePosition(symbol: string, orderId?: string): Promise<void> {
  await http.delete('/order', {
    params: { symbol, order_id: orderId },
  })
}
