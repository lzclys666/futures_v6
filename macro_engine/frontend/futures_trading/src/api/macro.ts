import { apiGet, factorGet } from './client';
import type { MacroSignal, SignalBrief, ScorePoint, IcHeatmapData, SignalSystemData } from '../types/macro';
import type { SymbolCode } from '../types';
import { TRADING_SYMBOLS } from '../constants/symbols';

/** 获取最新信号 (端口 8000) */
export function fetchMacroSignal(symbol: SymbolCode) {
  return apiGet<MacroSignal>(`/api/macro/signal/${symbol}`);
}

/** 获取历史走势 (端口 8000) */
export function fetchScoreHistory(symbol: SymbolCode, days = 30) {
  return apiGet<ScorePoint[]>(`/api/macro/score-history/${symbol}`, { days });
}

/** 获取所有品种信号摘要 (端口 8000) */
export function fetchAllSignals() {
  return Promise.all(
    ([...TRADING_SYMBOLS] as SymbolCode[]).map(s => fetchMacroSignal(s)),
  ).then(results => {
    const signals: SignalBrief[] = [];
    for (const r of results) {
      if (r.success && r.data != null) {
        const d = r.data;
        // 品种中文名映射 — 仅覆盖 TRADING_SYMBOLS（5个）
    const nameMap: Record<string, string> = { RB: '螺纹钢', JM: '焦煤', NI: '镍', RU: '橡胶', ZN: '锌' };
        signals.push({
          symbol: d.symbol,
          symbolName: nameMap[d.symbol] || d.symbol,
          compositeScore: d.score,
          date: d.timestamp?.slice(0, 10) || '',
          signal: d.signal,
          strength: d.strength,
        });
      }
    }
    return signals;
  });
}

// ==================== 因子分析 API (端口 8001) ====================

/** 获取 IC 热力图 */
export function fetchIcHeatmap(symbols: string[] = [...TRADING_SYMBOLS], lookback = 60, holdPeriod = 5) {
  return factorGet<IcHeatmapData>('/api/ic/heatmap', {
    symbols: symbols.join(','),
    lookback,
    hold_period: holdPeriod,
  });
}

/** 获取最优参数 IC 热力图 */
export function fetchIcHeatmapOptimal(symbols: string[] = [...TRADING_SYMBOLS]) {
  return factorGet<IcHeatmapData>('/api/ic/heatmap/optimal', {
    symbols: symbols.join(','),
  });
}

/** 获取单品种信号评分 */
export function fetchSignal(symbol: string) {
  return factorGet<SignalSystemData>(`/api/signal/${symbol.toUpperCase()}`);
}

/** 批量获取信号评分 */
export function fetchBatchSignals(symbols: string[] = [...TRADING_SYMBOLS]) {
  return factorGet<{ signals: SignalSystemData[]; count: number; updatedAt: string }>('/api/signal', {
    symbols: symbols.join(','),
  });
}
