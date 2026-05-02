import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserProfile, PerformanceSummary, EquityPoint } from '../types/user';
import * as userApi from '../api/user';

interface UserState {
  profile: UserProfile | null;
  performance: PerformanceSummary | null;
  equityCurve: EquityPoint[];
  loading: boolean;
  fetchProfile: () => Promise<void>;
  fetchPerformance: (period?: string) => Promise<void>;
  fetchEquityCurve: (days?: number) => Promise<void>;
  setProfile: (profile: UserProfile) => void;
}

/**
 * 用户 Store — profile 和偏好持久化到 localStorage
 */
export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      profile: null,
      performance: null,
      equityCurve: [],
      loading: false,

      fetchProfile: async () => {
        set({ loading: true });
        try {
          const res = await userApi.fetchUserProfile();
          if (res.success) set({ profile: res.data });
        } catch {
          set({
            profile: { username: '交易员', riskProfile: 'moderate', accountId: 'mock-001' },
          });
        } finally {
          set({ loading: false });
        }
      },

      fetchPerformance: async (period = 'monthly') => {
        try {
          const res = await userApi.fetchPerformance(period);
          if (res.success) set({ performance: res.data });
        } catch (e) {
          console.error('[userStore] fetchPerformance:', e);
        }
      },

      fetchEquityCurve: async (days = 90) => {
        try {
          const res = await userApi.fetchEquityCurve(days);
          if (res.success) set({ equityCurve: res.data });
        } catch (e) {
          console.error('[userStore] fetchEquityCurve:', e);
        }
      },

      setProfile: (profile) => {
        set({ profile });
      },
    }),
    {
      name: 'futures-user-store',
      partialize: (state) => ({
        profile: state.profile,
      }),
    }
  )
);
