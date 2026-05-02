import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AccountInfo, VnpyGatewayStatus, BackendHealth } from '../types/vnpy';
import type { Position, Order } from '../types/trading';
import * as vnpyApi from '../api/vnpy';
import { IS_MOCK_MODE } from '../api/client';

interface VnpyState {
  gateway: VnpyGatewayStatus | null;
  account: AccountInfo | null;
  positions: Position[];
  orders: Order[];
  connected: boolean;
  loading: boolean;
  error: string | null;
  backendHealth: BackendHealth;
  
  fetchGatewayStatus: () => Promise<void>;
  fetchAccount: () => Promise<void>;
  fetchPositions: () => Promise<void>;
  fetchOrders: () => Promise<void>;
  placeOrder: (order: { symbol: string; direction: string; volume: number; price: number; orderType?: string }) => Promise<{ success: boolean; data?: { vt_orderid: string }; message?: string }>;
  cancelOrder: (vtOrderId: string) => Promise<void>;
  updateFromWs: (gateway: Partial<VnpyGatewayStatus>, account: Partial<AccountInfo>) => void;
}

/**
 * VNpy 网关 Store — 网关状态持久化 + WebSocket 实时更新
 * Mock 模式：始终 connected=true，数据由 client.ts mock 层提供
 */
export const useVnpyStore = create<VnpyState>()(
  persist(
    (set, get) => ({
      gateway: null,
      account: null,
      positions: [],
      orders: [],
      connected: false,
      loading: false,
      error: null,
      backendHealth: 'unknown' as BackendHealth,

      fetchGatewayStatus: async () => {
        set({ loading: true, error: null });
        try {
          const res = await vnpyApi.fetchVnpyStatus();
          if (res.success) {
            set({ gateway: res.data, backendHealth: 'reachable', connected: true });
          }
        } catch {
          if (IS_MOCK_MODE) {
            // Mock 模式：网关不可达时仍展示 Mock 数据，不阻断用户操作
            set({
              gateway: {
                gatewayStatus: 'connected',
                tradingDay: new Date().toISOString().slice(0, 10),
                marketSession: isTradingSession() ? 'open' : 'closed',
                sessionEndTime: '15:00:00',
              } as VnpyGatewayStatus,
              backendHealth: 'mock',
              connected: true,
            });
          } else {
            set({
              gateway: { gatewayStatus: 'disconnected', tradingDay: '', marketSession: 'closed', sessionEndTime: '' } as VnpyGatewayStatus,
              backendHealth: 'unreachable',
              connected: false,
            });
          }
        } finally {
          set({ loading: false });
        }
      },

      fetchAccount: async () => {
        try {
          const res = await vnpyApi.fetchAccount();
          if (res.success) set({ account: res.data });
        } catch (e) {
          console.error('[vnpyStore] fetchAccount:', e);
        }
      },

      fetchPositions: async () => {
        try {
          const res = await vnpyApi.fetchPositions();
          if (res.success) set({ positions: res.data });
        } catch (e) {
          console.error('[vnpyStore] fetchPositions:', e);
        }
      },

      fetchOrders: async () => {
        try {
          const res = await vnpyApi.fetchOrders();
          if (res.success) set({ orders: res.data });
        } catch (e) {
          console.error('[vnpyStore] fetchOrders:', e);
        }
      },

      placeOrder: async (order) => {
        try {
          const res = await vnpyApi.placeOrder({
            symbol: order.symbol,
            direction: order.direction,
            volume: order.volume,
            price: order.price,
            orderType: order.orderType || 'LIMIT',
          });
          if (res.success) {
            get().fetchOrders();
            return { success: true, data: res.data };
          }
          return { success: false, message: res.message };
        } catch (e) {
          return { success: false, message: String(e) };
        }
      },

      cancelOrder: async (vtOrderId) => {
        try {
          await vnpyApi.cancelOrder(vtOrderId);
          get().fetchOrders();
        } catch (e) {
          console.error('[vnpyStore] cancelOrder:', e);
        }
      },

      /** WebSocket 实时更新（不触发 loading） */
      updateFromWs: (gateway, account) => {
        set((state) => ({
          gateway: gateway ? { ...state.gateway, ...gateway } as VnpyGatewayStatus : state.gateway,
          account: account ? { ...state.account, ...account } as AccountInfo : state.account,
        }));
      },
    }),
    {
      name: 'futures-vnpy-store',
      partialize: (state) => ({
        gateway: state.gateway,
        account: state.account,
        backendHealth: state.backendHealth,
        connected: state.connected,
      }),
    }
  )
);

/** 判断当前是否处于交易时段（9:00-15:00 / 21:00-23:00） */
function isTradingSession(): boolean {
  const now = new Date();
  const h = now.getHours();
  const mi = now.getMinutes();
  const minute = h * 60 + mi;
  // 日盘：09:00-15:00
  const dayOpen = 9 * 60;
  const dayClose = 15 * 60;
  // 夜盘：21:00-23:00（周一至周四）
  const nightOpen = 21 * 60;
  const nightClose = 23 * 60;
  const dow = now.getDay(); // 0=周日，6=周六

  if (dow === 0 || dow === 6) return false;
  if (minute >= dayOpen && minute < dayClose) return true;
  if (minute >= nightOpen && minute < nightClose) return true;
  return false;
}
