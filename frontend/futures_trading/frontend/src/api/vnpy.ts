/**
 * VNpy Bridge API 封装
 * @author Lucy
 * @date 2026-04-27
 */

import { createClient } from './client'
import type { VnpyStatus, VnpyAccount, VnpyPosition, VnpyOrder } from '../types/vnpy'
import { MOCK_ACCOUNT, MOCK_POSITIONS } from '../mock/portfolioMock'

const USE_MOCK = true // VNpy 后端未就绪，启用 Mock 展示

// ---------- Mock 数据 ----------

const MOCK_VNPY_STATUS: VnpyStatus = {
  state: 'connected',
  gatewayName: 'CTP',
  loggedIn: true,
  lastHeartbeat: new Date().toISOString(),
  version: '3.9.0',
}

const MOCK_VNPY_ACCOUNT: VnpyAccount = MOCK_ACCOUNT
const MOCK_VNPY_POSITIONS: VnpyPosition[] = MOCK_POSITIONS

const MOCK_VNPY_ORDERS: VnpyOrder[] = [
  { orderId: '1', symbol: 'RU2501', direction: 'LONG', offset: 'OPEN', price: 14500, volume: 2, tradedVolume: 2, status: '全部成交', orderTime: '09:30:00' },
  { orderId: '2', symbol: 'AG2502', direction: 'SHORT', offset: 'OPEN', price: 5800, volume: 3, tradedVolume: 3, status: '全部成交', orderTime: '09:35:00' },
]

// ---------- API ----------

const client = createClient('/api/vnpy')

/** GET /api/vnpy/status → VNpy 网关状态 */
export async function fetchVnpyStatus(): Promise<VnpyStatus> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 150))
    return MOCK_VNPY_STATUS
  }
  const res = await client.get<VnpyStatus>('/status')
  return res.data
}

/** GET /api/vnpy/account → 账户信息 */
export async function fetchVnpyAccount(): Promise<VnpyAccount> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return MOCK_VNPY_ACCOUNT
  }
  const res = await client.get<VnpyAccount>('/account')
  return res.data
}

/** GET /api/vnpy/positions → 持仓列表 */
export async function fetchVnpyPositions(): Promise<VnpyPosition[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return MOCK_VNPY_POSITIONS
  }
  const res = await client.get<VnpyPosition[]>('/positions')
  return res.data
}

/** GET /api/vnpy/orders → 订单列表 */
export async function fetchVnpyOrders(): Promise<VnpyOrder[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 150))
    return MOCK_VNPY_ORDERS
  }
  const res = await client.get<VnpyOrder[]>('/orders')
  return res.data
}

/** POST /api/trading/order → 下单 */
export async function submitOrder(params: {
  symbol: string
  direction: 'LONG' | 'SHORT'
  price: number
  volume: number
}): Promise<{ orderId: string; message: string }> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300))
    return { orderId: `MOCK-${Date.now()}`, message: '模拟下单成功' }
  }
  const res = await client.post('/order', params)
  return res.data
}

/** POST /api/trading/order/{id}/cancel → 撤单 */
export async function cancelOrder(orderId: string): Promise<{ success: boolean; message: string }> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return { success: true, message: '模拟撤单成功' }
  }
  const res = await client.post(`/order/${orderId}/cancel`)
  return res.data
}
