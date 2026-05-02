/**
 * VNpy 连接状态管理
 * 轮询策略：每 5s 自动刷新状态/账户/持仓
 * @author Lucy
 * @date 2026-04-27
 */

import { create } from 'zustand'
import type { VnpyStatus, VnpyAccount, VnpyPosition, VnpyOrder } from '../types/vnpy'
import { fetchVnpyStatus, fetchVnpyAccount, fetchVnpyPositions, fetchVnpyOrders } from '../api/vnpy'

export interface VnpyState {
  /** 连接状态 */
  status: VnpyStatus | null
  statusLoading: boolean

  /** 账户信息 */
  account: VnpyAccount | null
  accountLoading: boolean

  /** 持仓列表 */
  positions: VnpyPosition[]
  positionsLoading: boolean

  /** 订单列表 */
  orders: VnpyOrder[]
  ordersLoading: boolean

  /** 轮询定时器 */
  pollTimer: ReturnType<typeof setInterval> | null

  // ---- 动作 ----
  loadStatus: () => Promise<void>
  loadAccount: () => Promise<void>
  loadPositions: () => Promise<void>
  loadOrders: () => Promise<void>
  /** 一次性加载全部 */
  loadAll: () => Promise<void>
  /** 开始轮询 */
  startPolling: (intervalMs?: number) => void
  /** 停止轮询 */
  stopPolling: () => void

  /** 错误 */
  error: string | null
  clearError: () => void
}

export const useVnpyStore = create<VnpyState>((set, get) => ({
  status: null,
  statusLoading: false,
  account: null,
  accountLoading: false,
  positions: [],
  positionsLoading: false,
  orders: [],
  ordersLoading: false,
  pollTimer: null,
  error: null,

  loadStatus: async () => {
    set({ statusLoading: true })
    try {
      const status = await fetchVnpyStatus()
      set({ status, statusLoading: false, error: null })
    } catch (e) {
      set({ statusLoading: false })
      // VNpy 未启动时不当作 error，只标记 disconnected
      if (e instanceof Error && e.message.includes('超时')) {
        set({ status: null })
      }
    }
  },

  loadAccount: async () => {
    set({ accountLoading: true })
    try {
      const account = await fetchVnpyAccount()
      set({ account, accountLoading: false })
    } catch {
      set({ accountLoading: false, account: null })
    }
  },

  loadPositions: async () => {
    set({ positionsLoading: true })
    try {
      const positions = await fetchVnpyPositions()
      set({ positions, positionsLoading: false })
    } catch {
      set({ positionsLoading: false, positions: [] })
    }
  },

  loadOrders: async () => {
    set({ ordersLoading: true })
    try {
      const orders = await fetchVnpyOrders()
      set({ orders, ordersLoading: false })
    } catch {
      set({ ordersLoading: false, orders: [] })
    }
  },

  loadAll: async () => {
    await Promise.all([
      get().loadStatus(),
      get().loadAccount(),
      get().loadPositions(),
    ])
  },

  startPolling: (intervalMs = 5000) => {
    get().stopPolling()
    const timer = setInterval(() => {
      get().loadStatus()
      get().loadAccount()
      get().loadPositions()
    }, intervalMs)
    set({ pollTimer: timer })
  },

  stopPolling: () => {
    const t = get().pollTimer
    if (t) {
      clearInterval(t)
      set({ pollTimer: null })
    }
  },

  clearError: () => set({ error: null }),
}))
