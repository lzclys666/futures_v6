/**
 * 风控模块 · TypeScript 类型定义
 * @author Lucy
 * @date 2026-04-27
 */

// ---------- 熔断器枚举 ----------

/** 熔断器状态 */
export type CircuitBreakerStatus = 'RUNNING' | 'PENDING_CONFIRM' | 'PAUSED' | 'RECOVERING'

/** 操作动作类型 */
export type CircuitAction = 'PAUSE_CONFIRMED' | 'PAUSE_AUTO' | 'DISMISS' | 'RESUME' | 'RECOVER_AUTO'

// ---------- 熔断器类型 ----------

/** 同向持仓数据 */
export interface SameDirectionData {
  longSymbols: string[]
  shortSymbols: string[]
  pct: number
}

/** 操作历史记录 */
export interface CircuitHistoryEntry {
  action: CircuitAction
  operator: string
  notes: string
  timestamp: string
}

/** 熔断器响应 */
export interface CircuitBreakerResponse {
  status: CircuitBreakerStatus
  /** 触发条件描述 */
  triggerCondition: string | null
  /** 同方向极端仓位比例（0-1） */
  sameDirectionPct: number
  /** 同方向数据详情 */
  sameDirectionData: SameDirectionData | null
  /** 确认截止时间 */
  confirmDeadline: string | null
  /** 最后更新时间 */
  updatedAt: string
  /** 操作历史（最近5条） */
  history: CircuitHistoryEntry[]
}

/** 确认暂停请求参数 */
export interface ConfirmPauseParams {
  confirmed_by: string
  notes: string
}

/** 忽略警报请求参数 */
export interface DismissParams {
  confirmed_by: string
  reason: string
}

/** 恢复交易请求参数 */
export interface ResumeParams {
  confirmed_by: string
}

/** 风控规则 ID（大写，与后端对齐） */
export type RiskRuleId =
  | 'R1_SINGLE_SYMBOL'
  | 'R2_DAILY_LOSS'
  | 'R3_TOTAL_POSITION'
  | 'R4_MARGIN_RATIO'
  | 'R5_VOLATILITY'
  | 'R6_LIQUIDITY'
  | 'R7_CONSECUTIVE_LOSS'
  | 'R8_DRAWDOWN'
  | 'R9_CONCENTRATION'
  | 'R10_CIRCUIT_BREAKER'
  | 'R11_DISPOSITION'

/** 风控严重级别 */
export type RiskSeverity = 'PASS' | 'LOW' | 'MEDIUM' | 'HIGH'

/** 风控层级分组 */
export type RiskLayerKey = 'layer1' | 'layer2' | 'layer3'

/** 单条风控规则状态 */
export interface RiskRuleStatus {
  ruleId: RiskRuleId
  ruleName: string
  severity: RiskSeverity
  /** 当前值 */
  currentValue: number
  /** 阈值 */
  threshold: number
  /** 是否触发 */
  triggered: boolean
  /** 描述信息 */
  message: string
  /** 所属层级 */
  layer: RiskLayerKey
  /** 更新时间 */
  updatedAt: string
}

/** 风控规则配置项 */
export interface RiskRule {
  ruleId: RiskRuleId
  ruleName: string
  enabled: boolean
  threshold: number
  /** 告警阈值（低于 threshold） */
  warnThreshold?: number
  /** 所属层级 */
  layer: RiskLayerKey
  /** 规则描述 */
  description: string
  /** 策略参数（可调） */
  params?: Record<string, number | string>
}

/** 风控状态总览（API 响应） */
export interface RiskStatusResponse {
  date: string
  overallStatus: RiskSeverity
  rules: RiskRuleStatus[]
  /** 触发规则数 */
  triggeredCount: number
  /** 熔断状态 */
  circuitBreaker: boolean
  updatedAt: string
}

/** 凯利公式请求 */
export interface KellyRequest {
  symbol: string
  winRate: number
  avgWin: number
  avgLoss: number
  capital: number
  /** 凯利系数（0-1，默认 0.5） */
  fraction?: number
}

/** 凯利公式响应 */
export interface KellyResponse {
  fStar: number
  suggestedPosition: number
  suggestedLots: number
  kellyFraction: number
  interpretation: string
}

/** 压力测试场景 */
export interface StressTestScenario {
  id: string
  name: string
  description: string
  /** 价格变动百分比 */
  priceChangePct: number
  /** 波动率变动倍数 */
  volMultiplier: number
  /** 流动性变动百分比 */
  liquidityChangePct: number
}

/** 单场景压力测试结果 */
export interface StressTestResult {
  scenarioId: string
  scenarioName: string
  /** 预计 PnL */
  estimatedPnl: number
  /** 预计 PnL 百分比 */
  estimatedPnlPct: number
  /** 预计保证金变化 */
  marginChange: number
  /** 是否触发风控 */
  riskTriggered: boolean
  /** 触发规则列表 */
  triggeredRules: RiskRuleId[]
}

/** 压力测试报告 */
export interface StressTestReport {
  date: string
  symbol: string
  currentPnl: number
  scenarios: StressTestResult[]
  /** 最坏情况 */
  worstCase: StressTestResult
  /** 建议 */
  recommendations: string[]
}

// Re-export circuit breaker types for consumers
export type { CircuitBreakerStatus, CircuitBreakerResponse, CircuitHistoryEntry, SameDirectionData, ConfirmPauseParams, DismissParams, ResumeParams }
