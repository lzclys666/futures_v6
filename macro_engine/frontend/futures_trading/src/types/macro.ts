/**
 * 宏观因子相关类型定义
 * 对应后端 API: http://localhost:8000
 * 
 * 类型契约：以 API 实际响应为唯一真值（2026-05-01）
 */

/** 信号强度枚举 */
export type SignalStrength = 'STRONG_SELL' | 'SELL' | 'NEUTRAL' | 'BUY' | 'STRONG_BUY';

/** 市场状态枚举 */
export type MarketRegime = 'TRENDING' | 'RANGING' | 'VOLATILE' | 'UNKNOWN';

/** 因子分解项 */
export interface FactorBreakdown {
  factorName: string;
  rawScore: number;      // 原始得分 0-100
  weight: number;        // 权重 0-1
  contribution: number;  // 加权贡献
  direction: 'positive' | 'negative' | 'neutral';
}

/** 宏观信号 — 对应 Python MacroSignal（与 API 实际响应完全对齐） */
export interface MacroSignal {
  symbol: string;
  compositeScore: number;   // 综合得分，-1~1
  direction: 'LONG' | 'NEUTRAL' | 'SHORT';
  updatedAt: string;        // ISO 8601
  factors: FactorDetail[];  // 因子明细数组
}

/** 信号摘要（用于列表展示） */
export interface SignalBrief {
  symbol: string;
  date: string;
  compositeScore: number;
  signal: string;     // 注意：API /api/macro/signal/all 不返回此字段，仅用于内部展示
  strength: string;   // 注意：API 不返回此字段
}

/** 分数点 */
export interface ScorePoint {
  date: string;
  score: number;
}

/** 信号系统数据 — YIYI 因子分析服务（端口 8002）*/
export interface SignalSystemData {
  symbol: string;
  compositeScore: number;       // 综合评分（YIYI 实际返回 0-100）
  signalStrength: SignalStrength;
  confidence: number;          // 置信度 0-100
  /** 因子贡献分解，YIYI 尚未填充（5/15 后就绪）*/
  factorDetails: FactorDetail[];
  regime: MarketRegime;
  timestamp: string;            // ISO 8601
}

/** 因子贡献项 — 对应 Python FactorDetail（与 API 实际响应完全对齐，2026-05-01） */
export interface FactorDetail {
  factorCode: string;           // 因子代码
  factorName: string;           // 因子名称
  direction: 'positive' | 'negative' | 'neutral';  // 因子方向
  rawValue: number;             // 原始值
  normalizedScore: number;      // 归一化得分
  weight: number;               // 因子权重 0-1
  contribution: number;          // 贡献度
  factorIc?: number;            // IC 值（可选）
}

/** IC 热力图数据 */
export interface IcHeatmapData {
  factors: string[];           // 因子名称列表
  symbols: string[];           // 品种代码列表
  icMatrix: number[][];        // IC 值矩阵 [factor][symbol]
  lookbackPeriod: number;      // 回看周期
  holdPeriod: number;          // 持有周期
  updatedAt: string;           // ISO 8601
}

/** 批量信号响应 */
export interface BatchSignalsResponse {
  signals: SignalSystemData[];
  count: number;
  updatedAt: string;
}
