/**
 * 用户 API 封装
 * @author Lucy
 * @date 2026-04-27
 */

import { createClient } from './client'
import type { UserProfile, UserPreferences, RiskProfile } from '../types/user'

const client = createClient('/api/user')

/** GET /api/user/profile → 用户信息 */
export async function fetchUserProfile(): Promise<UserProfile> {
  const res = await client.get<UserProfile>('/profile')
  return res.data
}

/** PUT /api/user/preferences → 更新偏好设置 */
export async function updatePreferences(prefs: Partial<UserPreferences>): Promise<UserPreferences> {
  const res = await client.put<UserPreferences>('/preferences', prefs)
  return res.data
}

/** PUT /api/user/risk-profile → 更新风控画像 */
export async function updateRiskProfile(profile: Partial<RiskProfile>): Promise<RiskProfile> {
  const res = await client.put<RiskProfile>('/risk-profile', profile)
  return res.data
}

/** GET /api/user/performance → 交易绩效 */
export async function fetchPerformance(days?: number): Promise<{
  dates: string[]
  returns: number[]
  pnl: number[]
  benchmarkReturns: number[]
}> {
  const res = await client.get('/performance', { params: { days } })
  return res.data
}
