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
  SameDirectionData,
} from '../types/risk'

const client = createClient('/api/risk')

/**
 * 后端 → 前端字段适配
 *
 * 后端返回 snake_case: trigger_condition, same_direction_pct, confirm_deadline, trigger_detail
 * 前端使用 camelCase: triggerCondition, sameDirectionPct, confirmDeadline, sameDirectionData
 */
function _adaptCircuitBreaker(o: Record<string, unknown>): CircuitBreakerResponse {
  // trigger_detail → sameDirectionData
  const td = o.trigger_detail as Record<string, unknown> | undefined
  let sameDirectionData: SameDirectionData | null = null
  if (td) {
    sameDirectionData = {
      longSymbols: (td.long_symbols ?? td.longSymbols ?? []) as string[],
      shortSymbols: (td.short_symbols ?? td.shortSymbols ?? []) as string[],
      pct: (td.pct ?? o.same_direction_pct ?? o.sameDirectionPct ?? 0) as number,
    }
  }

  return {
    status: o.status as CircuitBreakerResponse['status'],
    triggerCondition: (o.trigger_condition ?? o.triggerCondition ?? null) as string | null,
    sameDirectionPct: (o.same_direction_pct ?? o.sameDirectionPct ?? 0) as number,
    sameDirectionData,
    confirmDeadline: (o.confirm_deadline ?? o.confirmDeadline ?? null) as string | null,
    updatedAt: (o.updated_at ?? o.updatedAt ?? new Date().toISOString()) as string,
    history: (o.history ?? []) as CircuitBreakerResponse['history'],
  }
}

/** GET /api/risk/circuit_breaker → 查询熔断器状态 */
export async function fetchCircuitBreaker(): Promise<CircuitBreakerResponse> {
  const res = await client.get<unknown>('/circuit_breaker')
  return _adaptCircuitBreaker(res.data as Record<string, unknown>)
}

/** POST /api/risk/circuit_breaker/confirm_pause → 确认暂停交易 */
export async function confirmPause(params: ConfirmPauseParams): Promise<CircuitBreakerResponse> {
  const res = await client.post<unknown>('/circuit_breaker/confirm_pause', params)
  return _adaptCircuitBreaker(res.data as Record<string, unknown>)
}

/** POST /api/risk/circuit_breaker/dismiss → 忽略警报 */
export async function dismiss(params: DismissParams): Promise<CircuitBreakerResponse> {
  const res = await client.post<unknown>('/circuit_breaker/dismiss', params)
  return _adaptCircuitBreaker(res.data as Record<string, unknown>)
}

/** POST /api/risk/circuit_breaker/resume → 恢复交易 */
export async function resume(params: ResumeParams): Promise<CircuitBreakerResponse> {
  const res = await client.post<unknown>('/circuit_breaker/resume', params)
  return _adaptCircuitBreaker(res.data as Record<string, unknown>)
}