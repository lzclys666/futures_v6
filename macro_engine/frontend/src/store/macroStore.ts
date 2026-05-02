/**
 * 宏观打分模块 · Zustand 状态管理
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import { create } from 'zustand'
import type {
  MacroSignal,
  MacroSignalSummary,
  FactorDetail,
  ScoreHistoryPoint,
} from '../types/macro'
import { fetchSignal, fetchAllSignals, fetchFactorDetail, fetchScoreHistory } from '../api/macro'

// ---------- State 类型 ----------

interface MacroState {
  // 当前选中品种
  selectedSymbol: string
  setSelectedSymbol: (symbol: string) => void

  // 全品种列表
  allSignals: MacroSignalSummary[]
  allSignalsLoading: boolean
  loadAllSignals: () => Promise<void>

  // 单品种信号
  currentSignal: MacroSignal | null
  currentSignalLoading: boolean
  loadSignal: (symbol: string) => Promise<void>

  // 因子明细
  factorDetails: FactorDetail[]
  factorDetailsLoading: boolean
  loadFactorDetails: (symbol: string) => Promise<void>

  // 历史打分
  scoreHistory: ScoreHistoryPoint[]
  scoreHistoryLoading: boolean
  loadScoreHistory: (symbol: string, days?: number) => Promise<void>

  // 全局错误
  error: string | null
  clearError: () => void
}

// ---------- Store ----------

export const useMacroStore = create<MacroState>((set, get) => ({
  // ---- 当前选中品种 ----
  selectedSymbol: 'RU',
  setSelectedSymbol: (symbol) => {
    set({ selectedSymbol: symbol })
    // 【修复·严重问题4】切换品种只加载当前品种数据，不再浪费 API 调用获取全品种列表
    get().loadSignal(symbol)
    get().loadFactorDetails(symbol)
    get().loadScoreHistory(symbol)
  },

  // ---- 全品种信号 ----
  allSignals: [],
  allSignalsLoading: false,
  loadAllSignals: async () => {
    set({ allSignalsLoading: true, error: null })
    try {
      const data = await fetchAllSignals()
      set({ allSignals: data, allSignalsLoading: false })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载全品种信号失败'
      set({ error: msg, allSignalsLoading: false })
    }
  },

  // ---- 单品种信号 ----
  currentSignal: null,
  currentSignalLoading: false,
  loadSignal: async (symbol) => {
    set({ currentSignalLoading: true, error: null })
    try {
      const data = await fetchSignal(symbol)
      set({ currentSignal: data, currentSignalLoading: false })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载信号失败'
      set({ error: msg, currentSignalLoading: false })
    }
  },

  // ---- 因子明细 ----
  factorDetails: [],
  factorDetailsLoading: false,
  loadFactorDetails: async (symbol) => {
    set({ factorDetailsLoading: true, error: null })
    try {
      const data = await fetchFactorDetail(symbol)
      set({ factorDetails: data, factorDetailsLoading: false })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载因子明细失败'
      set({ error: msg, factorDetailsLoading: false })
    }
  },

  // ---- 历史打分 ----
  scoreHistory: [],
  scoreHistoryLoading: false,
  loadScoreHistory: async (symbol, days = 30) => {
    set({ scoreHistoryLoading: true, error: null })
    try {
      const data = await fetchScoreHistory(symbol, days)
      set({ scoreHistory: data, scoreHistoryLoading: false })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载历史打分失败'
      set({ error: msg, scoreHistoryLoading: false })
    }
  },

  // ---- 错误处理 ----
  error: null,
  clearError: () => set({ error: null }),
}))
