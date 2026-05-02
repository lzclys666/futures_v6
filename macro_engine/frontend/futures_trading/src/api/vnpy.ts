import { apiGet, apiPost, apiDelete } from './client';
import type { AccountInfo, VnpyStatus } from '../types/vnpy';
import type { Position, Order } from '../types/trading';

/** VNpy 网关状态 */
export function fetchVnpyStatus() {
  return apiGet<VnpyStatus>('/api/vnpy/status');
}

/** 账户信息 */
export function fetchAccount() {
  return apiGet<AccountInfo>('/api/vnpy/account');
}

/** 持仓列表 */
export function fetchPositions() {
  return apiGet<Position[]>('/api/vnpy/positions');
}

/** 订单列表 */
export function fetchOrders() {
  return apiGet<Order[]>('/api/vnpy/orders');
}

/** 下单 — 对齐后端 POST /api/trading/order */
export function placeOrder(body: { symbol: string; exchange?: string; direction: string; offset?: string; volume: number; price: number; orderType?: string }) {
  // offset 默认 OPEN（前端不传时后端兼容处理）
  return apiPost<{ vtOrderId: string }>('/api/trading/order', {
    ...body,
    offset: body.offset ?? 'OPEN',
  });
}

/** 撤单 — 对齐后端 DELETE /api/trading/order/{vtOrderId} */
export function cancelOrder(vtOrderId: string) {
  return apiDelete<{ success: boolean }>(`/api/trading/order/${vtOrderId}`);
}

/** 健康检查 — 检测后端是否可达 */
export function healthCheck() {
  return apiGet<{ status: string }>('/api/health');
}
