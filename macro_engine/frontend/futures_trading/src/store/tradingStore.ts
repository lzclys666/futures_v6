import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Position, Order, PrecheckRequest, PrecheckResult } from '../types/trading';
import * as vnpyApi from '../api/vnpy';
import { checkOrderWithRules } from './riskStore';
import { useRiskStore } from './riskStore';

interface TradingState {
  positions: Position[];
  orders: Order[];
  positionsLoading: boolean;
  precheckResult: PrecheckResult | null;
  prechecking: boolean;
  placingOrder: boolean;
  orderError: string | null;

  fetchPositions: () => Promise<void>;
  fetchOrders: () => Promise<void>;
  fetchAccount: () => Promise<void>;
  placeOrder: (req: Omit<PrecheckRequest, 'direction'> & { direction: 'long' | 'short' }) => Promise<{ vtOrderId: string } | null>;
  cancelOrder: (orderId: string) => Promise<void>;
  /** 风控预检 — 调用 riskStore 本地规则校验（Phase 3 切后端 API） */
  runPrecheck: (req: PrecheckRequest) => Promise<PrecheckResult>;
  clearPrecheck: () => void;
  /** WebSocket 实时更新 */
  updatePositionsFromWs: (positions: Position[]) => void;
  updateOrdersFromWs: (orders: Order[]) => void;
}

/**
 * 交易 Store — 持仓/订单持久化 + WebSocket 实时更新 + 真实下单/撤单
 */
export const useTradingStore = create<TradingState>()(
  persist(
    (set, get) => ({
      positions: [],
      orders: [],
      positionsLoading: false,
      precheckResult: null,
      prechecking: false,
      placingOrder: false,
      orderError: null,

      fetchPositions: async () => {
        set({ positionsLoading: true });
        try {
          const res = await vnpyApi.fetchPositions();
          if (res.success) set({ positions: res.data });
        } catch (e) {
          console.error('[tradingStore] fetchPositions:', e);
        } finally {
          set({ positionsLoading: false });
        }
      },

      fetchOrders: async () => {
        try {
          const res = await vnpyApi.fetchOrders();
          if (res.success) set({ orders: res.data });
        } catch (e) {
          console.error('[tradingStore] fetchOrders:', e);
        }
      },

      fetchAccount: async () => {
        try {
          await vnpyApi.fetchAccount();
        } catch (e) {
          console.error('[tradingStore] fetchAccount:', e);
        }
      },

      /** 真实下单 — 调用 POST /api/trading/order */
      placeOrder: async (req) => {
        set({ placingOrder: true, orderError: null });
        try {
          const res = await vnpyApi.placeOrder({
            symbol: req.symbol,
            direction: req.direction === 'long' ? 'LONG' : 'SHORT',
            price: req.price,
            volume: req.volume,
          });
          if (res.success) {
            get().fetchOrders();
            // 兼容 vtOrderId（新）和 vt_orderid（旧）
            const vtOrderId = res.data?.vtOrderId ?? res.data?.vt_orderid;
            return vtOrderId ? { vtOrderId } : null;
          }
          set({ orderError: res.error ?? '下单失败' });
          return null;
        } catch (e) {
          const msg = e instanceof Error ? e.message : '网络错误';
          set({ orderError: msg });
          return null;
        } finally {
          set({ placingOrder: false });
        }
      },

      /** 撤单 — 调用 DELETE /api/trading/order/{vtOrderId} */
      cancelOrder: async (vtOrderId) => {
        try {
          await vnpyApi.cancelOrder(vtOrderId);
          get().fetchOrders();
        } catch (e) {
          console.error('[tradingStore] cancelOrder:', e);
        }
      },

      /** 风控预检 — Phase 3 替换为后端 /api/risk/precheck */
      runPrecheck: async (req) => {
        set({ prechecking: true, precheckResult: null });
        try {
          // 从 riskStore 获取当前规则（Zustand get() 在 action 中可用）
          const { rules } = useRiskStore.getState();
          const check = checkOrderWithRules(rules, {
            symbol: req.symbol,
            direction: req.direction,
            volume: req.volume,
            price: req.price,
          });
          const result: PrecheckResult = {
            passed: check.pass,
            blockedRules: check.pass ? [] : [check.message ?? ''],
            warnings: [],
          };
          set({ precheckResult: result });
          return result;
        } finally {
          set({ prechecking: false });
        }
      },

      clearPrecheck: () => set({ precheckResult: null }),

      updatePositionsFromWs: (positions) => set({ positions }),
      updateOrdersFromWs: (orders) => set({ orders }),
    }),
    {
      name: 'futures-trading-store',
      partialize: (state) => ({
        positions: state.positions,
        orders: state.orders,
      }),
    }
  )
);
