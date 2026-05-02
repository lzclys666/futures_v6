/**
 * 熔断器 API 封装
 * @author Lucy
 * @date 2026-04-30
 */

import { createClient } from './client'
import type {
  CircuitBreakerResponse,
  ConfirmPauseParams,
  DismissParams,
  ResumeParams,
} from '../types/risk'

const client = createClient('/api/risk')

/** GET /api/risk/circuit_breaker → 查询熔断器状态 */
export async function fetchCircuitBreaker(): Promise<CircuitBreakerResponse> {
  const res = await client.get<CircuitBreakerResponse>('/circuit_breaker')
  return res.data
}

/** POST /api/risk/circuit_breaker/confirm_pause → 确认暂停交易 */
export async function confirmPause(params: ConfirmPauseParams): Promise<CircuitBreakerResponse> {
  const res = await client.post<CircuitBreakerResponse>('/circuit_breaker/confirm_pause', params)
  return res.data
}

/** POST /api/risk/circuit_breaker/dismiss → 忽略警报 */
export async function dismiss(params: DismissParams): Promise<CircuitBreakerResponse> {
  const res = await client.post<CircuitBreakerResponse>('/circuit_breaker/dismiss', params)
  return res.data
}

/** POST /api/risk/circuit_breaker/resume → 恢复交易 */
export async function resume(params: ResumeParams): Promise<CircuitBreakerResponse> {
  const res = await client.post<CircuitBreakerResponse>('/circuit_breaker/resume', params)
  return res.data
}