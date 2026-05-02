import type { IcHeatmapData, SignalSystemData } from '../types/macro';

/** IC 热力图 Mock 数据
 * 颜色映射：红 = 负 IC，绿 = 正 IC（符合中国市场习惯）
 */
export const mockIcHeatmap: IcHeatmapData = {
  factors: [
    '库存变化', '基差率', '现货升贴水', '产量同比', '开工率',
    '表观消费', '出口量', '进口量', '利润', '产能利用率',
    '库存天数', '库销比', '价格动量', '波动率', '期限结构',
    '持仓量', '成交量', '资金流向', '宏观利率', '汇率',
    'PMI', 'CPI', 'PPI', '房地产投资', '基建投资', '汽车销量'
  ],
  symbols: ['RB', 'HC', 'I', 'J'],
  icMatrix: [
    // RB    HC     I      J
    [0.15,  0.12,  0.08,  0.05],   // 库存变化
    [-0.22, -0.18, -0.15, -0.10],  // 基差率
    [0.35,  0.28,  0.20,  0.15],   // 现货升贴水
    [-0.08, -0.05, -0.12, -0.18],  // 产量同比
    [0.10,  0.08,  0.05,  0.03],   // 开工率
    [0.25,  0.20,  0.15,  0.10],   // 表观消费
    [-0.15, -0.12, -0.20, -0.25],  // 出口量
    [0.05,  0.03,  0.08,  0.12],   // 进口量
    [0.18,  0.15,  0.10,  0.08],   // 利润
    [-0.10, -0.08, -0.05, -0.03],  // 产能利用率
    [0.30,  0.25,  0.18,  0.12],   // 库存天数
    [-0.20, -0.15, -0.10, -0.08],  // 库销比
    [0.40,  0.35,  0.25,  0.20],   // 价格动量
    [-0.12, -0.10, -0.08, -0.05],  // 波动率
    [0.22,  0.18,  0.12,  0.10],   // 期限结构
    [0.08,  0.06,  0.04,  0.03],   // 持仓量
    [0.15,  0.12,  0.08,  0.05],   // 成交量
    [0.05,  0.04,  0.03,  0.02],   // 资金流向
    [-0.18, -0.15, -0.12, -0.10],  // 宏观利率
    [0.10,  0.08,  0.06,  0.05],   // 汇率
    [0.12,  0.10,  0.08,  0.06],   // PMI
    [-0.05, -0.04, -0.03, -0.02],  // CPI
    [0.08,  0.06,  0.05,  0.04],   // PPI
    [0.20,  0.18,  0.15,  0.12],   // 房地产投资
    [0.15,  0.12,  0.10,  0.08],   // 基建投资
    [0.10,  0.08,  0.06,  0.05],   // 汽车销量
  ],
  lookbackPeriod: 60,
  holdPeriod: 5,
  updatedAt: '2026-04-26T15:30:00Z',
};

/** 信号系统 Mock 数据
 * UI: 仪表盘（当前信号）+ 列表（历史信号）
 */
export const mockSignalSystem: Record<string, SignalSystemData> = {
  RB: {
    symbol: 'RB',
    compositeScore: 72.5,
    signalStrength: 'BUY',
    confidence: 78.5,
    factorBreakdown: [
      { factorName: '库存变化', rawScore: 75, weight: 0.08, contribution: 5.2, direction: 'positive' },
      { factorName: '基差率', rawScore: 35, weight: 0.12, contribution: -8.5, direction: 'negative' },
      { factorName: '现货升贴水', rawScore: 85, weight: 0.15, contribution: 12.8, direction: 'positive' },
      { factorName: '产量同比', rawScore: 40, weight: 0.10, contribution: -6.2, direction: 'negative' },
      { factorName: '开工率', rawScore: 65, weight: 0.07, contribution: 4.5, direction: 'positive' },
    ],
    regime: 'TRENDING',
    timestamp: '2026-04-26T15:30:00Z',
  },
  HC: {
    symbol: 'HC',
    compositeScore: 45.2,
    signalStrength: 'NEUTRAL',
    confidence: 62.3,
    factorBreakdown: [
      { factorName: '库存变化', rawScore: 42, weight: 0.08, contribution: -2.5, direction: 'negative' },
      { factorName: '基差率', rawScore: 58, weight: 0.12, contribution: 5.8, direction: 'positive' },
      { factorName: '现货升贴水', rawScore: 55, weight: 0.15, contribution: 3.2, direction: 'positive' },
      { factorName: '产量同比', rawScore: 38, weight: 0.10, contribution: -4.5, direction: 'negative' },
      { factorName: '开工率', rawScore: 52, weight: 0.07, contribution: 1.8, direction: 'positive' },
    ],
    regime: 'RANGING',
    timestamp: '2026-04-26T15:30:00Z',
  },
  I: {
    symbol: 'I',
    compositeScore: 28.5,
    signalStrength: 'SELL',
    confidence: 71.2,
    factorBreakdown: [
      { factorName: '库存变化', rawScore: 25, weight: 0.08, contribution: -6.8, direction: 'negative' },
      { factorName: '基差率', rawScore: 20, weight: 0.12, contribution: -8.2, direction: 'negative' },
      { factorName: '现货升贴水', rawScore: 55, weight: 0.15, contribution: 2.5, direction: 'positive' },
      { factorName: '产量同比', rawScore: 30, weight: 0.10, contribution: -5.5, direction: 'negative' },
      { factorName: '开工率', rawScore: 28, weight: 0.07, contribution: -3.2, direction: 'negative' },
    ],
    regime: 'VOLATILE',
    timestamp: '2026-04-26T15:30:00Z',
  },
  J: {
    symbol: 'J',
    compositeScore: 85.2,
    signalStrength: 'STRONG_BUY',
    confidence: 82.5,
    factorBreakdown: [
      { factorName: '库存变化', rawScore: 88, weight: 0.08, contribution: 8.5, direction: 'positive' },
      { factorName: '基差率', rawScore: 82, weight: 0.12, contribution: 10.2, direction: 'positive' },
      { factorName: '现货升贴水', rawScore: 90, weight: 0.15, contribution: 12.5, direction: 'positive' },
      { factorName: '产量同比', rawScore: 35, weight: 0.10, contribution: -3.2, direction: 'negative' },
      { factorName: '开工率', rawScore: 78, weight: 0.07, contribution: 6.8, direction: 'positive' },
    ],
    regime: 'TRENDING',
    timestamp: '2026-04-26T15:30:00Z',
  },
};

/** 历史信号列表（用于信号系统列表展示） */
export const mockSignalHistory = [
  { symbol: 'RB', date: '2026-04-26', signalStrength: 'BUY', compositeScore: 72.5 },
  { symbol: 'RB', date: '2026-04-25', signalStrength: 'BUY', compositeScore: 68.2 },
  { symbol: 'RB', date: '2026-04-24', signalStrength: 'NEUTRAL', compositeScore: 55.8 },
  { symbol: 'RB', date: '2026-04-23', signalStrength: 'NEUTRAL', compositeScore: 48.5 },
  { symbol: 'RB', date: '2026-04-22', signalStrength: 'SELL', compositeScore: 35.2 },
  { symbol: 'HC', date: '2026-04-26', signalStrength: 'NEUTRAL', compositeScore: 45.2 },
  { symbol: 'HC', date: '2026-04-25', signalStrength: 'NEUTRAL', compositeScore: 42.8 },
  { symbol: 'HC', date: '2026-04-24', signalStrength: 'SELL', compositeScore: 38.5 },
  { symbol: 'I', date: '2026-04-26', signalStrength: 'SELL', compositeScore: 28.5 },
  { symbol: 'I', date: '2026-04-25', signalStrength: 'SELL', compositeScore: 32.1 },
  { symbol: 'J', date: '2026-04-26', signalStrength: 'STRONG_BUY', compositeScore: 85.2 },
  { symbol: 'J', date: '2026-04-25', signalStrength: 'BUY', compositeScore: 75.8 },
];
