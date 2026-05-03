/**
 * 用户偏好与画像管理
 * @author Lucy
 * @date 2026-04-27
 */

import { create } from 'zustand'
import type { UserProfile, UserPreferences, RiskProfile } from '../types/user'
import { fetchUserProfile, updatePreferences, updateRiskProfile } from '../api/user'

interface UserState {
  /** 用户信息 */
  profile: UserProfile | null
  profileLoading: boolean

  /** 绩效数据 */
  performance: { dates: string[]; returns: number[]; pnl: number[]; benchmarkReturns: number[] } | null
  performanceLoading: boolean

  /** 是否跟随操作系统深色模式（自动主题） */
  darkAlgorithm: boolean

  // ---- 动作 ----
  loadProfile: () => Promise<void>
  /** 更新偏好（本地 + 远程） */
  savePreferences: (prefs: Partial<UserPreferences>) => Promise<void>
  /** 更新风控画像 */
  saveRiskProfile: (profile: Partial<RiskProfile>) => Promise<void>
  /** 切换主题 */
  toggleTheme: () => void

  error: string | null
  clearError: () => void
}

// 监听 OS 深色模式变化
function getSystemDarkMode(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

let _darkModeListener: MediaQueryList | null = null

function setupDarkModeListener(set: (state: Partial<UserState>) => void) {
  if (typeof window === 'undefined') return
  _darkModeListener = window.matchMedia('(prefers-color-scheme: dark)')
  _darkModeListener.addEventListener('change', (e) => {
    set({ darkAlgorithm: e.matches })
  })
}

export const useUserStore = create<UserState>((set, get) => {
  setupDarkModeListener(set)
  return {
    profile: null,
    profileLoading: false,
    performance: null,
    performanceLoading: false,
    darkAlgorithm: getSystemDarkMode(),
    error: null,

  loadProfile: async () => {
    set({ profileLoading: true })
    try {
      const profile = await fetchUserProfile()
      set({ profile, profileLoading: false, error: null })
    } catch {
      // API 失败则用 mock 数据兜底
      set({
        profile: {
          userId: 'mock-user-001',
          username: 'trader01',
          displayName: '演示交易员',
          email: 'trader01@futures.local',
          role: 'trader',
          createdAt: '2025-01-15 09:00:00',
          lastLoginAt: new Date().toLocaleString('zh-CN'),
          preferences: {
            defaultSymbol: 'AU',
            theme: 'light',
            language: 'zh-CN',
            refreshInterval: 5,
            notifications: {
              riskAlert: true,
              tradeFilled: true,
              circuitBreaker: true,
              dailyReport: false,
              channels: ['web'],
            },
          },
          riskProfile: {
            riskTolerance: 'moderate',
            maxDrawdown: 10,
            maxDailyLoss: 50000,
            maxSingleSymbolPct: 30,
            maxTotalPositionPct: 60,
            maxLeverage: 3,
          },
          totalTradingDays: 128,
          cumulativeReturn: 23.5,
          winRate: 62.3,
          sharpeRatio: 1.85,
          maxHistoricalDrawdown: 8.2,
        },
        profileLoading: false,
        error: null,
      })
    }
  },

  savePreferences: async (prefs) => {
    try {
      const updated = await updatePreferences(prefs)
      const p = get().profile
      if (p) {
        set({ profile: { ...p, preferences: updated } })
      }
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  saveRiskProfile: async (rp) => {
    try {
      const updated = await updateRiskProfile(rp)
      const p = get().profile
      if (p) {
        set({ profile: { ...p, riskProfile: updated } })
      }
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  toggleTheme: () => {
    const p = get().profile
    if (!p) return
    const newTheme = p.preferences.theme === 'dark' ? 'light' : 'dark'
    set({ profile: { ...p, preferences: { ...p.preferences, theme: newTheme } } })
  },

  clearError: () => set({ error: null }),
  }}
))
