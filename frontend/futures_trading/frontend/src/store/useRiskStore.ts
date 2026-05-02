/**
 * 风控状态管理
 * 轮询策略：每 10s 刷新风控状态
 * @author Lucy
 * @date 2026-04-27
 */

import { create } from 'zustand'
import type { RiskRule, RiskStatusResponse, KellyResponse, StressTestReport } from '../types/risk'
import { fetchRiskStatus, fetchRiskRules, calculateKelly, runStressTest, simulateRisk } from '../api/risk'

interface RiskState {
  /** 风控状态总览 */
  status: RiskStatusResponse | null
  statusLoading: boolean

  /** 风控规则配置 */
  rules: RiskRule[]
  rulesLoading: boolean

  /** 凯利计算结果 */
  kellyResult: KellyResponse | null
  kellyLoading: boolean

  /** 压力测试报告 */
  stressReport: StressTestReport | null
  stressLoading: boolean

  /** 风控预检结果 */
  precheckResult: { pass: boolean; violations: Array<{ ruleId: string; message: string; severity: string }> } | null
  precheckLoading: boolean

  /** 轮询 */
  pollTimer: ReturnType<typeof setInterval> | null

  // ---- 动作 ----
  loadStatus: () => Promise<void>
  loadRules: () => Promise<void>
  updateRiskRule: (params: Partial<RiskRule> & { ruleId: string }) => Promise<void>
  runKelly: (params: { symbol: string; winRate: number; avgWin: number; avgLoss: number; capital: number; fraction?: number }) => Promise<void>
  runStressTest: (params: { symbol: string; scenarios?: string[] }) => Promise<void>
  precheckOrder: (params: { symbol: string; direction: 'LONG' | 'SHORT'; price: number; volume: number }) => Promise<boolean>
  startPolling: (intervalMs?: number) => void
  stopPolling: () => void

  error: string | null
  clearError: () => void
}

export const useRiskStore = create<RiskState>((set, get) => ({
  status: null,
  statusLoading: false,
  rules: [],
  rulesLoading: false,
  kellyResult: null,
  kellyLoading: false,
  stressReport: null,
  stressLoading: false,
  precheckResult: null,
  precheckLoading: false,
  pollTimer: null,
  error: null,

  loadStatus: async () => {
    set({ statusLoading: true })
    try {
      const status = await fetchRiskStatus()
      set({ status, statusLoading: false, error: null })
    } catch (e) {
      set({ statusLoading: false, status: null })
    }
  },

  loadRules: async () => {
    set({ rulesLoading: true })
    try {
      const rules = await fetchRiskRules()
      set({ rules, rulesLoading: false })
    } catch {
      set({ rulesLoading: false, rules: [] })
    }
  },

  updateRiskRule: async (params) => {
    set({ rulesLoading: true })
    try {
      // TODO: 调用后端 API 更新规则
      // await updateRiskRuleApi(params)
      // 本地更新
      const current = get().rules
      const updated = current.map((r) =>
        r.ruleId === params.ruleId ? { ...r, ...params } : r
      )
      set({ rules: updated, rulesLoading: false })
    } catch {
      set({ rulesLoading: false })
    }
  },

  runKelly: async (params) => {
    set({ kellyLoading: true })
    try {
      const result = await calculateKelly(params)
      set({ kellyResult: result, kellyLoading: false })
    } catch {
      set({ kellyLoading: false })
    }
  },

  runStressTest: async (params) => {
    set({ stressLoading: true })
    try {
      const report = await runStressTest(params)
      set({ stressReport: report, stressLoading: false })
    } catch {
      set({ stressLoading: false })
    }
  },

  precheckOrder: async (params) => {
    set({ precheckLoading: true })
    try {
      const result = await simulateRisk(params)
      set({ precheckResult: result, precheckLoading: false })
      return result.pass
    } catch {
      set({ precheckLoading: false })
      return false
    }
  },

  startPolling: (intervalMs = 10000) => {
    get().stopPolling()
    const timer = setInterval(() => {
      get().loadStatus()
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
