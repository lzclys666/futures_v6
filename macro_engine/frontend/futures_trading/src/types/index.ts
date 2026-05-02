// 类型统一导出 - 避免循环引用，直接从源文件导入
export type { ApiResponse } from './api';

export type { SymbolCode, OrderDirection, OrderType, OrderStatus, Position, Order, PrecheckRequest, PrecheckResult } from './trading';

export type { IcHeatmapData, SignalSystemData, FactorBreakdown, SignalStrength, MarketRegime, BatchSignalsResponse, MacroSignal, SignalBrief, ScorePoint } from './macro';

export type { RiskStatus, RiskRuleStatus, RiskRuleConfig, RiskConfigTemplate, StressTestRequest, StressTestResult, KellyInput, KellyResult, DispositionState, Severity, RuleId, RiskProfile } from './risk';

export type { UserProfile, PerformanceSummary, EquityPoint, NotificationPrefs, AvatarUploadResponse } from './user';

export type { AuditRecord, AuditLogQuery, AuditLogResponse, AuditSummary, AuditLevel, AuditAction } from './audit';

/**
 * 品种元数据列表
 * ⚠️ 新代码请使用 constants/symbols.ts 的 SYMBOL_OPTIONS
 * 此处保留用于向后兼容及贵金属/有色品种（AU/AG/CU/AL）
 */
export const SYMBOL_LIST = [
  { code: 'RB' as const, name: '螺纹钢' },
  { code: 'JM' as const, name: '焦煤' },
  { code: 'NI' as const, name: '镍' },
  { code: 'RU' as const, name: '橡胶' },
  { code: 'ZN' as const, name: '锌' },
  { code: 'I' as const, name: '铁矿石' },
  { code: 'AU' as const, name: '黄金' },
  { code: 'AG' as const, name: '白银' },
  { code: 'CU' as const, name: '铜' },
  { code: 'AL' as const, name: '铝' },
] as const;

export const SYMBOL_CODES = SYMBOL_LIST.map(s => s.code);
