/**
 * 交易模块 · Zustand 状态管理
 * @date 2026-04-24
 */

import { create } from 'zustand'
import type { PortfolioData, RiskStatusData } from '../types/macro'
import { fetchPortfolio } from '../api/trading'
import { fetchRiskStatus } from '../api/risk'
import { validateRiskStatusData } from '../utils/tradingValidators'

interface TradingState {
  /** 持仓数据 */
  portfolio: PortfolioData | null
  portfolioLoading: boolean
  loadPortfolio: () => Promise<void>

  /** 风控状态 */
  riskStatus: RiskStatusData | null
  riskLoading: boolean
  loadRiskStatus: () => Promise<void>

  /** 自动刷新间隔（ms），0=不刷新 */
  refreshInterval: number
  setRefreshInterval: (ms: number) => void

  /** 错误 */
  error: string | null
  clearError: () => void
}

export const useTradingStore = create<TradingState>((set) => ({
  portfolio: null,
  portfolioLoading: false,
  loadPortfolio: async () => {
    set({ portfolioLoading: true, error: null })
    try {
      const data = await fetchPortfolio()
      set({ portfolio: data, portfolioLoading: false })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载持仓数据失败'
      set({ error: msg, portfolioLoading: false })
    }
  },

  riskStatus: null,
  riskLoading: false,
  loadRiskStatus: async () => {
    set({ riskLoading: true, error: null })
    try {
      const raw = await fetchRiskStatus()
      const result = validateRiskStatusData(raw)
      if (result.valid && result.data) {
        set({ riskStatus: result.data, riskLoading: false })
      } else {
        console.warn('[tradingStore] RiskStatusData 校验失败:', result.errors)
        set({ error: `风控数据格式错误: ${result.errors.join('; ')}`, riskLoading: false })
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载风控状态失败'
      set({ error: msg, riskLoading: false })
    }
  },

  refreshInterval: 30000,
  setRefreshInterval: (ms) => set({ refreshInterval: ms }),

  error: null,
  clearError: () => set({ error: null }),
}))
