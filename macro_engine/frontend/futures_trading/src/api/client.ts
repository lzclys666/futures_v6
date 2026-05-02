import axios, { type AxiosInstance } from 'axios';
import type { ApiResponse } from '../types';

// ==================== 环境配置 ====================
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const IS_DEV = import.meta.env.DEV;

// ==================== Mock 数据配置 ====================
/** Mock 响应包装 */
const mockResponse = <T>(data: T): ApiResponse<T> => ({
  success: true,
  data,
  message: 'ok',
});

/** VNPy Mock 数据（端口 8000） */
const vnpyMocks: Record<string, () => unknown> = {
  '/api/vnpy/status': () => ({
    connected: true,
    gateway: 'CTP',
    gatewayStatus: 'connected',
    tradingDay: new Date().toISOString().slice(0, 10),
    marketSession: 'open',
    sessionEndTime: '15:00:00',
  }),
  '/api/vnpy/account': () => ({
    balance: 1_000_000,
    available: 850_000,
    frozen: 50_000,
    margin: 100_000,
    positionPnl: 12_500,
    closePnl: 45_000,
    riskRatio: 0.15,
  }),
  '/api/vnpy/positions': () => [
    { vtSymbol: 'RB2505', symbol: 'RB', exchange: 'SHFE', direction: 'long', volume: 10, avgPrice: 3500, lastPrice: 3600, unrealizedPnl: 10000, realizedPnl: 5000, margin: 35000, openTime: '2026-04-25 09:30:00' },
    { vtSymbol: 'J2505', symbol: 'J', exchange: 'DCE', direction: 'short', volume: 5, avgPrice: 2000, lastPrice: 1950, unrealizedPnl: 2500, realizedPnl: 1250, margin: 20000, openTime: '2026-04-25 10:15:00' },
  ],
  '/api/vnpy/orders': () => [
    { vt_orderid: 'ord_001', symbol: 'RB', exchange: 'SHFE', direction: 'buy', offset: 'open', volume: 5, price: 3550, orderType: 'limit', status: 'pending', insertTime: new Date().toISOString() },
    { vt_orderid: 'ord_002', symbol: 'HC', exchange: 'SHFE', direction: 'sell', offset: 'open', volume: 3, price: 3800, orderType: 'limit', status: 'filled', insertTime: new Date().toISOString() },
  ],
  '/api/trading/order': () => ({ vtOrderId: `ord_${Date.now()}` }),
  '/api/health': () => ({ status: 'ok' }),
};

/** 宏观因子 Mock 数据（端口 8000） */
const macroMocks: Record<string, () => unknown> = {
  '/api/macro/signal/RB': () => ({
    symbol: 'RB', score: 68.5, signal: 'BUY', strength: 'STRONG',
    factorDetails: [
      { factorName: '宏观因子', rawScore: 72, weight: 0.3, contribution: 21.6, direction: 'positive' },
      { factorName: '趋势因子', rawScore: 68, weight: 0.25, contribution: 17.0, direction: 'positive' },
      { factorName: '波动率', rawScore: 55, weight: 0.2, contribution: 11.0, direction: 'neutral' },
    ],
    timestamp: new Date().toISOString(),
  }),
  '/api/macro/signal/HC': () => ({
    symbol: 'HC', score: 55.2, signal: 'HOLD', strength: 'MODERATE',
    factorDetails: [
      { factorName: '宏观因子', rawScore: 52, weight: 0.3, contribution: 15.6, direction: 'neutral' },
    ],
    timestamp: new Date().toISOString(),
  }),
  '/api/macro/signal/J': () => ({
    symbol: 'J', score: 42.8, signal: 'SELL', strength: 'WEAK',
    factorDetails: [
      { factorName: '宏观因子', rawScore: 40, weight: 0.3, contribution: -12.0, direction: 'negative' },
    ],
    timestamp: new Date().toISOString(),
  }),
  '/api/macro/signal/JM': () => ({
    symbol: 'JM', score: 35.1, signal: 'SELL', strength: 'STRONG',
    factorDetails: [
      { factorName: '宏观因子', rawScore: 35, weight: 0.3, contribution: -19.5, direction: 'negative' },
    ],
    timestamp: new Date().toISOString(),
  }),
  '/api/macro/score-history/RB': () => Array.from({ length: 60 }, (_, i) => ({
    date: new Date(Date.now() - (59 - i) * 86400000).toISOString().slice(0, 10),
    score: +(50 + Math.sin(i * 0.3) * 20 + Math.random() * 10).toFixed(1),
  })),
  '/api/macro/score-history/JM': () => Array.from({ length: 60 }, (_, i) => ({
    date: new Date(Date.now() - (59 - i) * 86400000).toISOString().slice(0, 10),
    score: +(40 + Math.sin(i * 0.2) * 10 + Math.random() * 15).toFixed(1),
  })),
  '/api/macro/score-history/NI': () => Array.from({ length: 60 }, (_, i) => ({
    date: new Date(Date.now() - (59 - i) * 86400000).toISOString().slice(0, 10),
    score: +(48 + Math.sin(i * 0.25) * 18 + Math.random() * 8).toFixed(1),
  })),
  '/api/macro/score-history/RU': () => Array.from({ length: 60 }, (_, i) => ({
    date: new Date(Date.now() - (59 - i) * 86400000).toISOString().slice(0, 10),
    score: +(45 + Math.sin(i * 0.35) * 15 + Math.random() * 12).toFixed(1),
  })),
  '/api/macro/score-history/ZN': () => Array.from({ length: 60 }, (_, i) => ({
    date: new Date(Date.now() - (59 - i) * 86400000).toISOString().slice(0, 10),
    score: +(52 + Math.sin(i * 0.28) * 12 + Math.random() * 9).toFixed(1),
  })),
  '/api/macro/summary': () => ({
    RB: { compositeScore: 68.5, signal: 'BUY' },
    HC: { compositeScore: 55.2, signal: 'HOLD' },
    J: { compositeScore: 42.8, signal: 'SELL' },
    JM: { compositeScore: 35.1, signal: 'SELL' },
  }),
};

/** 风控 Mock 数据 */
const riskMocks: Record<string, () => unknown> = {
  '/api/risk/status': () => ({
    overall: 'LOW',
    passCount: 10,
    rules: [
      { ruleId: 'R5_VOLATILITY', name: '波动率', layer: 1, severity: 'PASS', currentValue: 0.015, threshold: 0.03, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R6_LIQUIDITY', name: '流动性', layer: 1, severity: 'PASS', currentValue: 1, threshold: 1, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R10_MACRO_CIRCUIT_BREAKER', name: '宏观熔断', layer: 1, severity: 'PASS', currentValue: 0, threshold: 1, message: '未触发', updatedAt: new Date().toISOString() },
      { ruleId: 'R2_DAILY_LOSS', name: '单日亏损', layer: 2, severity: 'PASS', currentValue: 0, threshold: 50000, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R7_CONSECUTIVE_LOSS', name: '连续亏损', layer: 2, severity: 'PASS', currentValue: 0, threshold: 3, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R11_DISPOSITION_EFFECT', name: '处置效应', layer: 2, severity: 'PASS', currentValue: 0, threshold: 1, message: '未触发', updatedAt: new Date().toISOString() },
      { ruleId: 'R1_SINGLE_SYMBOL', name: '单品种仓位', layer: 3, severity: 'PASS', currentValue: 20, threshold: 30, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R4_TOTAL_MARGIN', name: '总保证金', layer: 2, severity: 'PASS', currentValue: 25, threshold: 50, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R3_PRICE_LIMIT', name: '涨跌停', layer: 3, severity: 'PASS', currentValue: 0, threshold: 1, message: '正常', updatedAt: new Date().toISOString() },
      { ruleId: 'R8_TRADING_HOURS', name: '交易时间', layer: 3, severity: 'PASS', currentValue: 1, threshold: 1, message: '交易时段', updatedAt: new Date().toISOString() },
      { ruleId: 'R9_CAPITAL_SUFFICIENCY', name: '资金充足', layer: 3, severity: 'PASS', currentValue: 1, threshold: 0.8, message: '充足', updatedAt: new Date().toISOString() },
    ],
  }),
  '/api/risk/rules': () => ({
    rules: [
      { id: 'R1', ruleId: 'R1_SINGLE_SYMBOL', name: '单品种仓位', enabled: true, layer: 3, threshold: 30, currentValue: 20, unit: '%' },
      { id: 'R2', ruleId: 'R2_DAILY_LOSS', name: '单日亏损', enabled: true, layer: 2, threshold: 50000, currentValue: 0, unit: '¥' },
      { id: 'R3', ruleId: 'R3_PRICE_LIMIT', name: '涨跌停', enabled: true, layer: 3, threshold: 1, currentValue: 0, unit: '' },
      { id: 'R4', ruleId: 'R4_TOTAL_MARGIN', name: '总保证金', enabled: true, layer: 2, threshold: 50, currentValue: 25, unit: '%' },
      { id: 'R5', ruleId: 'R5_VOLATILITY', name: '波动率', enabled: true, layer: 1, threshold: 0.03, currentValue: 0.015, unit: '' },
      { id: 'R6', ruleId: 'R6_LIQUIDITY', name: '流动性', enabled: true, layer: 1, threshold: 1, currentValue: 1.5, unit: '' },
      { id: 'R7', ruleId: 'R7_CONSECUTIVE_LOSS', name: '连续亏损', enabled: true, layer: 3, threshold: 3, currentValue: 1, unit: '笔' },
      { id: 'R8', ruleId: 'R8_TRADING_HOURS', name: '交易时间', enabled: true, layer: 3, threshold: 1, currentValue: 1, unit: '' },
      { id: 'R9', ruleId: 'R9_CAPITAL_SUFFICIENCY', name: '资金充足', enabled: true, layer: 3, threshold: 1.5, currentValue: 2.0, unit: '倍' },
      { id: 'R10', ruleId: 'R10_MACRO_CIRCUIT_BREAKER', name: '宏观熔断', enabled: true, layer: 1, threshold: 0.5, currentValue: 0.72, unit: '' },
      { id: 'R11', ruleId: 'R11_DISPOSITION_EFFECT', name: '处置效应', enabled: true, layer: 3, threshold: 10, currentValue: 5, unit: '天' },
    ],
  }),
};

/** 因子分析 Mock 数据（端口 8001） */
const factorMocks: Record<string, () => unknown> = {
  '/api/ic/heatmap': () => ({
    factors: ['carry', 'reversal', 'volume', 'volatility', 'momentum'],
    symbols: ['RB', 'JM', 'NI', 'RU', 'ZN'],
    // 5因子 × 5品种，carry由basis+import合并，momentum暂缺填0
    icMatrix: [
      [0.18,  0.22, -0.12,  0.15,  0.00], // carry (basis+import合并)
      [-0.15, -0.08, -0.25, -0.12,  0.00], // reversal
      [0.08,  0.12,  0.05,  0.18,  0.00], // volume
      [0.22,  0.18,  0.30,  0.15,  0.00], // volatility
      [0.00,  0.00,  0.00,  0.00,  0.00], // momentum（暂缺）
    ],
    lookbackPeriod: 60,
    holdPeriod: 5,
    updatedAt: new Date().toISOString(),
  }),
  '/api/signal/RB': () => ({
    symbol: 'RB', compositeScore: 65.5, signalStrength: 'BUY', confidence: 72,
    factorDetails: [
      { factorName: 'carry', rawScore: 75, weight: 0.30, contribution: 22.5, direction: 'positive' },
      { factorName: 'reversal', rawScore: 45, weight: 0.20, contribution: -9.0, direction: 'negative' },
      { factorName: 'volatility', rawScore: 60, weight: 0.15, contribution: 9.0, direction: 'positive' },
    ],
    regime: 'TRENDING', timestamp: new Date().toISOString(),
  }),
  '/api/signal': () => ({
    signals: [
      { symbol: 'RB', compositeScore: 65.5, signalStrength: 'BUY', confidence: 72, factorDetails: [], regime: 'TRENDING', timestamp: new Date().toISOString() },
      { symbol: 'JM', compositeScore: 52.3, signalStrength: 'NEUTRAL', confidence: 58, factorDetails: [], regime: 'RANGING', timestamp: new Date().toISOString() },
      { symbol: 'NI', compositeScore: 71.8, signalStrength: 'BUY', confidence: 68, factorDetails: [], regime: 'TRENDING', timestamp: new Date().toISOString() },
      { symbol: 'RU', compositeScore: 38.5, signalStrength: 'SELL', confidence: 65, factorDetails: [], regime: 'VOLATILE', timestamp: new Date().toISOString() },
      { symbol: 'ZN', compositeScore: 55.2, signalStrength: 'NEUTRAL', confidence: 52, factorDetails: [], regime: 'RANGING', timestamp: new Date().toISOString() },
    ], count: 5, updatedAt: new Date().toISOString(),
  }),
};

/** 统一 Mock 映射 */
const ALL_MOCKS: Record<string, () => unknown> = {
  ...vnpyMocks,
  ...macroMocks,
  ...riskMocks,
  ...factorMocks,
};

// ==================== API Clients ====================
const vnpyClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

const factorClient = axios.create({
  baseURL: 'http://localhost:8002',  // YIYI 因子分析服务端口
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

const addInterceptors = (client: AxiosInstance, name: string) => {
  client.interceptors.response.use(
    res => res,
    err => {
      const msg = err.response?.data?.detail ?? err.message;
      console.error(`[${name}]`, err.config?.url, msg);
      return Promise.reject(err);
    },
  );
};

addInterceptors(vnpyClient, 'VNPy');
addInterceptors(factorClient, 'Factor');

// ==================== Mock-aware API 函数 ====================
function getMockData<T>(path: string): { data: T } | null {
  if (USE_MOCK && ALL_MOCKS[path]) {
    if (IS_DEV) console.log(`[Mock] ${path}`);
    return { data: ALL_MOCKS[path]() as T };
  }
  return null;
}

/** VNPy GET */
export async function vnpyGet<T>(path: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const mock = getMockData<T>(path);
  if (mock) return mockResponse(mock.data);
  const { data } = await vnpyClient.get<ApiResponse<T>>(path, { params });
  return data;
}

/** VNPy POST */
export async function vnpyPost<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  if (USE_MOCK && ALL_MOCKS[path]) {
    if (IS_DEV) console.log(`[Mock] POST ${path}`);
    return mockResponse(ALL_MOCKS[path]() as T);
  }
  const { data } = await vnpyClient.post<ApiResponse<T>>(path, body);
  return data;
}

/** VNPy PUT */
export async function vnpyPut<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  const mock = getMockData<T>(path);
  if (mock) return mockResponse(mock.data);
  const { data } = await vnpyClient.put<ApiResponse<T>>(path, body);
  return data;
}

/** VNPy DELETE */
export async function vnpyDelete<T>(path: string): Promise<ApiResponse<T>> {
  // Mock: 匹配 /api/trading/order/ 前缀
  if (USE_MOCK && path.startsWith('/api/trading/order/')) {
    if (IS_DEV) console.log(`[Mock] DELETE ${path}`);
    return mockResponse({ success: true } as T);
  }
  const { data } = await vnpyClient.delete<ApiResponse<T>>(path);
  return data;
}

/** Factor GET */
export async function factorGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const mock = getMockData<T>(path);
  if (mock) return mock.data;
  const { data } = await factorClient.get<T>(path, { params });
  return data;
}

/** Factor POST */
export async function factorPost<T>(path: string, body?: unknown): Promise<T> {
  const mock = getMockData<T>(path);
  if (mock) return mock.data;
  const { data } = await factorClient.post<T>(path, body);
  return data;
}

// 向后兼容别名
export const apiGet = vnpyGet;
export const apiPost = vnpyPost;
export const apiPut = vnpyPut;

export const apiDelete = vnpyDelete;

// 导出配置（供 UI 指示器使用）
export const IS_MOCK_MODE = USE_MOCK;
export default vnpyClient;
