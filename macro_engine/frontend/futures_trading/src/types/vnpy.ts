/**
 * VNPy 交易网关相关类型定义
 * 对应后端 API: http://localhost:8000
 */

/** 后端健康状态：mock=CTP未连接但Mock模式可用 */
export type BackendHealth = 'reachable' | 'unreachable' | 'unknown' | 'mock';

/** VNPy 网关状态（会话信息） */
export interface VnpyGatewayStatus {
  gatewayStatus: 'connected' | 'disconnected' | 'connecting';
  tradingDay: string;
  marketSession: 'open' | 'closed';
  sessionEndTime: string;
}

/** VNPy 运行状态 */
export interface VnpyStatus {
  status: 'running' | 'stopped' | 'error';
  engineType: string;
  startTime?: string;
  uptime?: number;
  version: string;
}

/** 账户信息 */
export interface AccountInfo {
  accountId: string;
  balance: number;
  available: number;
  frozen: number;
  margin: number;
  commission: number;
  profit: number;
  riskRatio: number;
  positionPnl?: number;
  closePnl?: number;
}

/** VNPy 原始持仓（后端格式，未经前端映射） */
export interface VnpyPosition {
  symbol: string;
  exchange: string;
  direction: 'long' | 'short';
  volume: number;
  price: number;
  profit: number;
  margin: number;
  openTime: string;
}

/** VNPy 原始订单（后端格式） */
export interface VnpyOrder {
  vtOrderId: string;
  symbol: string;
  exchange: string;
  direction: 'long' | 'short';
  offset: 'open' | 'close' | 'close_today' | 'close_yesterday';
  price: number;
  volume: number;
  traded: number;
  status: 'submitting' | 'submitted' | 'partial' | 'filled' | 'canceled' | 'rejected';
  orderTime: string;
  reference?: string;
}

/** 风控状态（VNpy 层级） */
export interface VnpyRiskStatus {
  active: boolean;
  ruleCount: number;
  triggeredCount: number;
  lastTriggerTime?: string;
  overallLevel: 'PASS' | 'HIGH' | 'MEDIUM' | 'LOW';
}

/** 风控规则（VNpy 层级） */
export interface VnpyRiskRule {
  ruleId: string;
  name: string;
  description: string;
  enabled: boolean;
  severity: 'PASS' | 'HIGH' | 'MEDIUM' | 'LOW';
  threshold: number;
  currentValue: number;
  triggered: boolean;
  lastTriggered?: string;
}

/** 策略 */
export interface Strategy {
  name: string;
  className: string;
  vtSymbol: string;
  status: 'initializing' | 'running' | 'stopped' | 'error';
  parameters: Record<string, any>;
  variables: Record<string, any>;
  profit: number;
  tradeCount: number;
}
