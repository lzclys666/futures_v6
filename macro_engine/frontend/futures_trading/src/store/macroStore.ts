import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { IcHeatmapData, SignalSystemData, MacroSignal, SignalBrief } from '../types/macro';
import type { SymbolCode } from '../types/trading';
import { TRADING_SYMBOLS } from '../constants/symbols';
import * as macroApi from '../api/macro';

interface MacroState {
  currentSymbol: SymbolCode;
  signal: MacroSignal | null;
  signals: SignalBrief[];
  scoreHistory: Array<{ date: string; score: number }>;
  
  // 因子分析数据 (端口 8001)
  icHeatmap: IcHeatmapData | null;
  signalSystem: SignalSystemData | null;
  batchSignals: SignalSystemData[];
  
  loading: boolean;
  error: string | null;
  
  setSymbol: (s: SymbolCode) => void;
  fetchSignal: () => Promise<void>;
  fetchAllSignals: () => Promise<void>;
  fetchScoreHistory: (days?: number) => Promise<void>;
  
  // 因子分析 actions
  fetchIcHeatmap: (symbols?: string[]) => Promise<void>;
  fetchSignalSystem: (symbol: string) => Promise<void>;
  fetchBatchSignals: (symbols?: string[]) => Promise<void>;
}

/**
 * 宏观信号 Store — 信号摘要 + 历史持久化
 */
export const useMacroStore = create<MacroState>()(
  persist(
    (set, get) => ({
  currentSymbol: 'RB',
  signal: null,
  signals: [],
  scoreHistory: [],
  
  // 因子分析数据
  icHeatmap: null,
  signalSystem: null,
  batchSignals: [],
  
  loading: false,
  error: null,

  setSymbol: (s) => {
    set({ currentSymbol: s });
    get().fetchSignal();
    get().fetchScoreHistory();
  },

  fetchSignal: async () => {
    set({ loading: true, error: null });
    try {
      const res = await macroApi.fetchMacroSignal(get().currentSymbol);
      if (res.success) set({ signal: res.data });
    } catch (e) {
      set({ error: String(e) });
    } finally {
      set({ loading: false });
    }
  },

  fetchAllSignals: async () => {
    try {
      const data = await macroApi.fetchAllSignals();
      set({ signals: data });
    } catch (e) {
      console.error('[macroStore] fetchAllSignals:', e);
    }
  },

  fetchScoreHistory: async (days = 30) => {
    try {
      const res = await macroApi.fetchScoreHistory(get().currentSymbol, days);
      if (res.success) set({ scoreHistory: res.data });
    } catch (e) {
      console.error('[macroStore] fetchScoreHistory:', e);
    }
  },
  
  // 因子分析 actions
  fetchIcHeatmap: async (symbols = [...TRADING_SYMBOLS]) => {
    set({ loading: true, error: null });
    try {
      const data = await macroApi.fetchIcHeatmap(symbols);
      set({ icHeatmap: data, loading: false });
    } catch (e) {
      console.error('[macroStore] fetchIcHeatmap:', e);
      set({ error: String(e), loading: false });
    }
  },
  
  fetchSignalSystem: async (symbol: string) => {
    try {
      const data = await macroApi.fetchSignal(symbol);
      set({ signalSystem: data });
    } catch (e) {
      console.error('[macroStore] fetchSignalSystem:', e);
    }
  },
  
  fetchBatchSignals: async (symbols = [...TRADING_SYMBOLS]) => {
    try {
      const data = await macroApi.fetchBatchSignals(symbols);
      set({ batchSignals: data.signals });
    } catch (e) {
      console.error('[macroStore] fetchBatchSignals:', e);
    }
  },
    }),
    {
      name: 'futures-macro-store',
      partialize: (state) => ({
        currentSymbol: state.currentSymbol,
        signals: state.signals,
        scoreHistory: state.scoreHistory.slice(-60),
        icHeatmap: state.icHeatmap,
      }),
    }
  )
);
