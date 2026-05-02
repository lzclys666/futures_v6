/**
 * 品种常量 — 单一数据源
 * 所有品种相关配置集中在此，禁止散落硬编码
 *
 * 使用方式：
 * import { TRADING_SYMBOLS, SYMBOL_META, getSymbolLabel } from '@/constants/symbols';
 */

/** 交易品种（5个）*/
export const TRADING_SYMBOLS = ['RB', 'JM', 'NI', 'RU', 'ZN'] as const;
export type TradingSymbol = typeof TRADING_SYMBOLS[number];

/** 品种中文名 + 下拉框标签 */
export const SYMBOL_META: Record<TradingSymbol, { label: string; name: string; cnName: string }> = {
  RB: { label: '螺纹钢 (RB)', name: 'RB', cnName: '螺纹钢' },
  JM: { label: '焦煤 (JM)', name: 'JM', cnName: '焦煤' },
  NI: { label: '镍 (NI)', name: 'NI', cnName: '镍' },
  RU: { label: '橡胶 (RU)', name: 'RU', cnName: '橡胶' },
  ZN: { label: '锌 (ZN)', name: 'ZN', cnName: '锌' },
};

/** 下拉框选项（供 Select 组件直接使用）*/
export const SYMBOL_OPTIONS = Object.values(SYMBOL_META).map(m => ({
  value: m.name as TradingSymbol,
  label: m.label,
}));

/** 获取品种中文名 */
export function getSymbolCnName(code: TradingSymbol): string {
  return SYMBOL_META[code]?.cnName ?? code;
}

/** 获取品种下拉框标签 */
export function getSymbolLabel(code: TradingSymbol): string {
  return SYMBOL_META[code]?.label ?? code;
}

/** 因子名称常量 — IC 热力图 API 输出因子（carry 由 basis+import 合并）*/
export const FACTOR_NAMES = ['carry', 'reversal', 'volume', 'volatility', 'momentum'] as const;
export type FactorName = typeof FACTOR_NAMES[number];

/** momentum 因子数据暂缺（数据库无此字段）*/
export const PENDING_FACTORS: readonly FactorName[] = ['momentum'] as const;
