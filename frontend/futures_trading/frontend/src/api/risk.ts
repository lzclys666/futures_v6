/**
 * 风控 API 封装
 * @author Lucy
 * @date 2026-04-27
 */

import { createClient } from './client'
import type {
  RiskRule,
  RiskRuleId,
  RiskSeverity,
  RiskStatusResponse,
  KellyRequest,
  KellyResponse,
  StressTestReport,
} from '../types/risk'

const USE_MOCK = false // 后端 6 个端点已全部实现，2026-04-29 切换真实 API

// ---------- Mock 数据 ----------

const MOCK_RISK_STATUS: RiskStatusResponse = {
  date: new Date().toISOString().slice(0, 10),
  overallStatus: 'PASS',
  rules: [
    { ruleId: 'R1_SINGLE_SYMBOL', ruleName: '单品种持仓限制', severity: 'PASS', currentValue: 0.18, threshold: 0.3, triggered: false, message: '', layer: 3, updatedAt: new Date().toISOString() },
    { ruleId: 'R2_DAILY_LOSS', ruleName: '单日亏损限制', severity: 'PASS', currentValue: 0.02, threshold: 0.05, triggered: false, message: '', layer: 2, updatedAt: new Date().toISOString() },
    { ruleId: 'R3_PRICE_LIMIT', ruleName: '总持仓限制', severity: 'PASS', currentValue: 0.45, threshold: 0.8, triggered: false, message: '', layer: 3, updatedAt: new Date().toISOString() },
    { ruleId: 'R4_TOTAL_MARGIN', ruleName: '总保证金上限', severity: 'PASS', currentValue: 0.55, threshold: 0.9, triggered: false, message: '', layer: 3, updatedAt: new Date().toISOString() },
    { ruleId: 'R5_VOLATILITY', ruleName: '波动率熔断', severity: 'PASS', currentValue: 0.03, threshold: 0.05, triggered: false, message: '', layer: 1, updatedAt: new Date().toISOString() },
    { ruleId: 'R6_LIQUIDITY', ruleName: '流动性检查', severity: 'PASS', currentValue: 5000, threshold: 1000, triggered: false, message: '', layer: 1, updatedAt: new Date().toISOString() },
    { ruleId: 'R7_CONSECUTIVE_LOSS', ruleName: '连续亏损限制', severity: 'PASS', currentValue: 0, threshold: 3, triggered: false, message: '', layer: 2, updatedAt: new Date().toISOString() },
    { ruleId: 'R8_TRADING_HOURS', ruleName: '回撤监控', severity: 'PASS', currentValue: 0.05, threshold: 0.15, triggered: false, message: '', layer: 2, updatedAt: new Date().toISOString() },
    { ruleId: 'R9_CAPITAL_SUFFICIENCY', ruleName: '集中度限制', severity: 'PASS', currentValue: 0.3, threshold: 0.5, triggered: false, message: '', layer: 3, updatedAt: new Date().toISOString() },
    { ruleId: 'R10_MACRO_CIRCUIT_BREAKER', ruleName: '宏观熔断', severity: 'PASS', currentValue: 0.45, threshold: -0.5, triggered: false, message: '', layer: 1, updatedAt: new Date().toISOString() },
    { ruleId: 'R11_DISPOSITION_EFFECT', ruleName: '处置效应监控', severity: 'PASS', currentValue: 48, threshold: 24, triggered: false, message: '', layer: 2, updatedAt: new Date().toISOString() },
    { ruleId: 'R12_CANCEL_LIMIT', ruleName: '撤单频率限制', severity: 'PASS', currentValue: 0, threshold: 10, triggered: false, message: '', layer: 2, updatedAt: new Date().toISOString() },
  ],
  triggeredCount: 0,
  circuitBreaker: false,
  updatedAt: new Date().toISOString(),
}

const MOCK_RULES: RiskRule[] = [
  { ruleId: 'R1_SINGLE_SYMBOL', ruleName: '单品种持仓限制', enabled: true, threshold: 0.3, layer: 3, description: '单一品种持仓不超过总权益30%' },
  { ruleId: 'R2_DAILY_LOSS', ruleName: '单日亏损限制', enabled: true, threshold: 0.05, layer: 2, description: '单日亏损不超过总权益5%' },
  { ruleId: 'R3_PRICE_LIMIT', ruleName: '总持仓限制', enabled: true, threshold: 0.8, layer: 3, description: '总持仓保证金不超过总权益80%' },
  { ruleId: 'R4_TOTAL_MARGIN', ruleName: '总保证金上限', enabled: true, threshold: 0.9, layer: 3, description: '保证金占用率实时监控' },
  { ruleId: 'R5_VOLATILITY', ruleName: '波动率熔断', enabled: true, threshold: 0.05, layer: 1, description: 'ATR波动率超过阈值禁止开仓' },
  { ruleId: 'R6_LIQUIDITY', ruleName: '流动性检查', enabled: true, threshold: 1000, layer: 1, description: '日均成交量低于阈值禁止开仓' },
  { ruleId: 'R7_CONSECUTIVE_LOSS', ruleName: '连续亏损限制', enabled: true, threshold: 3, layer: 2, description: '连续3笔亏损暂停交易' },
  { ruleId: 'R8_TRADING_HOURS', ruleName: '回撤监控', enabled: true, threshold: 0.15, layer: 2, description: '最大回撤超过15%减仓' },
  { ruleId: 'R9_CAPITAL_SUFFICIENCY', ruleName: '集中度限制', enabled: true, threshold: 0.5, layer: 3, description: '单一板块持仓不超过50%' },
  { ruleId: 'R10_MACRO_CIRCUIT_BREAKER', ruleName: '宏观熔断', enabled: true, threshold: -0.5, layer: 1, description: '宏观打分低于-0.5禁止开仓' },
  { ruleId: 'R11_DISPOSITION_EFFECT', ruleName: '处置效应监控', enabled: true, threshold: 24, layer: 2, description: '盈利单持仓时间过短警告' },
  { ruleId: 'R12_CANCEL_LIMIT', ruleName: '撤单频率限制', enabled: true, threshold: 10, layer: 2, description: '撤单频率过高限制交易' },
]

const MOCK_KELLY: KellyResponse = {
  fStar: 0.25,
  suggestedPosition: 0.2,
  suggestedLots: 5,
  kellyFraction: 0.25,
  interpretation: '建议仓位20%，风险可控',
}

const MOCK_STRESS: StressTestReport = {
  date: new Date().toISOString().slice(0, 10),
  symbol: 'RU',
  currentPnl: 25000,
  scenarios: [
    { scenarioId: 's1', scenarioName: '黑天鹅事件', estimatedPnl: -50000, estimatedPnlPct: -0.05, marginChange: -10000, riskTriggered: true, triggeredRules: ['R10_MACRO_CIRCUIT_BREAKER'] },
    { scenarioId: 's2', scenarioName: '极端波动', estimatedPnl: -30000, estimatedPnlPct: -0.03, marginChange: -5000, riskTriggered: true, triggeredRules: ['R5_VOLATILITY'] },
    { scenarioId: 's3', scenarioName: '流动性枯竭', estimatedPnl: -20000, estimatedPnlPct: -0.02, marginChange: -3000, riskTriggered: false, triggeredRules: [] },
    { scenarioId: 's4', scenarioName: '连续亏损', estimatedPnl: -15000, estimatedPnlPct: -0.015, marginChange: -2000, riskTriggered: false, triggeredRules: [] },
  ],
  worstCase: { scenarioId: 's1', scenarioName: '黑天鹅事件', estimatedPnl: -50000, estimatedPnlPct: -0.05, marginChange: -10000, riskTriggered: true, triggeredRules: ['R10_MACRO_CIRCUIT_BREAKER'] },
  recommendations: ['建议降低仓位至20%', '启用对冲策略', '密切关注宏观因子变化'],
}

// ---------- API ----------

const client = createClient('/api/risk')

/** GET /api/risk/status → 风控状态总览（11 条规则） */
export async function fetchRiskStatus(): Promise<RiskStatusResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return MOCK_RISK_STATUS
  }
  const res = await client.get<RiskStatusResponse>('/status')
  return res.data
}

/** GET /api/risk/rules → 风控规则配置列表 */
export async function fetchRiskRules(): Promise<RiskRule[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 150))
    return MOCK_RULES
  }
  const res = await client.get<RiskRule[]>('/rules')
  return res.data
}

/** PUT /api/risk/rules → 更新风控规则配置 */
export async function updateRiskRule(rule: Partial<RiskRule> & { ruleId: string }): Promise<RiskRule> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300))
    const existing = MOCK_RULES.find((r) => r.ruleId === rule.ruleId)
    if (!existing) throw new Error('规则不存在')
    return { ...existing, ...rule }
  }
  const res = await client.put<RiskRule>(`/rules/${rule.ruleId}`, rule)
  return res.data
}

/** 模拟结果类型 */
export interface SimulateResult {
  pass: boolean
  violations: Array<{ ruleId: RiskRuleId; ruleName: string; message: string; severity: RiskSeverity }>
  checkedRules: number
  timestamp: string
}

/** POST /api/risk/simulate → 风控模拟测试 */
export async function simulateRisk(params: {
  symbol: string
  direction: 'LONG' | 'SHORT'
  price: number
  volume: number
}): Promise<SimulateResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300))
    // 模拟：大单量触发违规
    const violations: SimulateResult['violations'] = []
    if (params.volume > 50) {
      violations.push({
        ruleId: 'R1_SINGLE_SYMBOL',
        ruleName: '单品种持仓限制',
        message: `${params.symbol} 持仓量 ${params.volume} 超过单品种限制`,
        severity: 'BLOCK',
      })
    }
    if (params.volume > 30 && params.direction === 'LONG') {
      violations.push({
        ruleId: 'R4_TOTAL_MARGIN',
        ruleName: '总保证金上限',
        message: '预计保证金占用率将超过90%',
        severity: 'WARN',
      })
    }
    return {
      pass: violations.filter((v) => v.severity === 'BLOCK').length === 0,
      violations,
      checkedRules: 12,
      timestamp: new Date().toISOString(),
    }
  }
  const res = await client.post<SimulateResult>('/simulate', params)
  return res.data
}

/** POST /api/risk/precheck → 下单前风控预检 */
export async function precheckRisk(params: {
  symbol: string
  direction: 'LONG' | 'SHORT'
  price: number
  volume: number
}): Promise<SimulateResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    // 预检比模拟更严格
    const violations: SimulateResult['violations'] = []
    if (params.volume > 20) {
      violations.push({
        ruleId: 'R1_SINGLE_SYMBOL',
        ruleName: '单品种持仓限制',
        message: `预检：${params.symbol} 下单量 ${params.volume} 接近单品种限制`,
        severity: 'WARN',
      })
    }
    if (params.volume > 80) {
      violations.push({
        ruleId: 'R4_TOTAL_MARGIN',
        ruleName: '总保证金上限',
        message: '预检：预计保证金占用率将超过上限',
        severity: 'BLOCK',
      })
    }
    return {
      pass: violations.filter((v) => v.severity === 'BLOCK').length === 0,
      violations,
      checkedRules: 12,
      timestamp: new Date().toISOString(),
    }
  }
  const res = await client.post<SimulateResult>('/precheck', params)
  return res.data
}

/** POST /api/risk/kelly → 凯利公式计算 */
export async function calculateKelly(params: KellyRequest): Promise<KellyResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250))
    return { ...MOCK_KELLY, fStar: MOCK_KELLY.fStar, interpretation: `凯利计算: ${params.symbol}` }
  }
  const res = await client.post<KellyResponse>('/kelly', params)
  return res.data
}

/** POST /api/risk/stress-test → 压力测试 */
export async function runStressTest(params: {
  symbol: string
  scenarios?: string[]
}): Promise<StressTestReport> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300))
    return { ...MOCK_STRESS, symbol: params.symbol }
  }
  const res = await client.post<StressTestReport>('/stress-test', params)
  return res.data
}
