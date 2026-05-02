import type { SymbolCode } from './trading';

/** 严重级别 */
export type Severity = 'PASS' | 'HIGH' | 'MEDIUM' | 'LOW';

/** 规则ID */
export type RuleId = string;

/** 风险画像 */
export type RiskProfile = 'conservative' | 'moderate' | 'aggressive';

/** 风控状态总览（来自 /api/risk/status） */
export interface RiskStatus {
  date: string;
  overall_status: Severity;  // 改：overall → overall_status（与后端对齐）
  overall?: Severity;        // 保留向后兼容
  levels: RiskLevelStatus[]; // 改：rules[] → levels[]（后端字段名）
  equity: number;
  drawdown: number;
  drawdown_alert?: number;
  drawdown_stop?: number;
  drawdown_circuit?: number;
  updated_at: string;
}

/** 与后端 levels 数组的子项类型 */
export interface RiskLevelStatus {
  level: string;
  name: string;
  status: 'normal' | 'warning' | 'critical';
  value?: string;
  threshold?: string;
  message?: string | null;
}

/**
 * 风控规则配置
 *
 * 字段说明：
 * - enabled:    规则是否启用（boolean）
 * - severity:    规则检查结果的严重级别（RiskRuleStatus 中使用）
 * - status:     已移除（与 enabled 概念重复，易混淆）
 */
export interface RiskRuleConfig {
  id: string;           // R1, R2, ...（后端已有）
  ruleId?: string;      // 改为可选（后端无此字段）
  name: string;
  description?: string; // 新增（后端有）
  layer?: number;       // 层级：1/2/3（后端 int）
  enabled: boolean;
  status?: string;      // 新增：normal/warning（后端有）
  threshold?: number;   // 改为可选（后端无此字段，level用string）
  currentValue?: number;
  unit?: string;
}

/** 风控配置模板 */
export interface RiskConfigTemplate {
  profile: RiskProfile;
  name: string;
  rules: RiskRuleConfig[];
}

/** 压力测试请求 */
export interface StressTestRequest {
  scenario: 'flash_crash' | 'volatility_spike' | 'liquidity_dryup' | 'correlated_drawdown' | 'custom';
  positions: Array<{ symbol: SymbolCode; direction: 'long' | 'short'; volume: number; avgPrice: number }>;
  customParams?: Record<string, number>;
}

/** 压力测试结果 */
export interface StressTestResult {
  scenarioName: string;
  totalPnl: number;
  remainingEquity: number;
  drawdownPct: number;
  survived: boolean;
  rating: Severity;
}

/** 凯利公式输入 */
export interface KellyInput {
  winRate: number;      // 0-1
  profitLossRatio: number;
  equity: number;
}

/** 凯利公式输出 */
export interface KellyResult {
  fullKelly: number;    // 全凯利仓位
  halfKelly: number;    // 半凯利
  volAdjusted: number;  // 波动率调整
  suggestion: string;
}

/** 处置效应状态 */
export interface DispositionState {
  triggered: boolean;
  symbolCode: SymbolCode;
  unrealizedPnl: number;
  holdingDays: number;
  options: Array<{
    id: 'reduce' | 'hold' | 'add';
    label: string;
    description: string;
  }>;
}
