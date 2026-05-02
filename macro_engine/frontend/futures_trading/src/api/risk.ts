import { apiGet, apiPost, apiPut } from './client';
import type { RiskStatus, RiskRuleConfig, StressTestRequest, StressTestResult, KellyInput, KellyResult, DispositionState } from '../types/risk';

/** 风控状态总览 */
export function fetchRiskStatus() {
  return apiGet<RiskStatus>('/api/trading/risk-status');
}

/** 风控规则列表 */
export function fetchRiskRules() {
  return apiGet<RiskRuleConfig[]>('/api/trading/risk-rules');
}

/** 更新风控规则 */
export function updateRiskRules(rules: RiskRuleConfig[]) {
  return apiPut<RiskRuleConfig[]>('/api/trading/rules', { rules });
}

/** 压力测试 */
export function runStressTest(req: StressTestRequest) {
  return apiPost<StressTestResult[]>('/api/risk/simulate', req);
}

/** 凯利公式 */
export function calcKelly(input: KellyInput) {
  return apiPost<KellyResult>('/api/risk/kelly', input);
}

/** 处置效应状态 */
export function fetchDisposition(symbol: string) {
  return apiGet<DispositionState>(`/api/position/disposition/${symbol}`);
}
