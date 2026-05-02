import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { RiskStatus, RiskRuleConfig } from '../types/risk';
import * as riskApi from '../api/risk';

interface RiskState {
  status: RiskStatus | null;
  rules: RiskRuleConfig[];
  loading: boolean;

  fetchStatus: () => Promise<void>;
  fetchRules: () => Promise<void>;
  updateRules: (rules: RiskRuleConfig[]) => Promise<void>;
  /** 风控预检 — 调用本地规则校验 */
  checkOrder: (order: { symbol: string; direction: string; volume: number; price: number }) => Promise<{ pass: boolean; message?: string }>;
}

/**
 * 风控 Store — 规则配置持久化到 localStorage
 * 用户自定义的风险阈值在刷新后保留
 *
 * 规则 ID 规范来源：pages/risk/config.tsx 的 RULE_META
 * Layer 分组：L1=市场风险 / L2=账户风险 / L3=交易执行
 */
export const useRiskStore = create<RiskState>()(
  persist(
    (set, get) => ({
      status: null,
      rules: [],
      loading: false,

      fetchStatus: async () => {
        set({ loading: true });
        try {
          const res = await riskApi.fetchRiskStatus();
          if (res.success) set({ status: res.data });
        } catch (e) {
          console.error('[riskStore] fetchStatus:', e);
        } finally {
          set({ loading: false });
        }
      },

      fetchRules: async () => {
        try {
          const res = await riskApi.fetchRiskRules();
          if (res.success) {
            set({ rules: res.data });
          } else {
            set({ rules: getFallbackRules() });
          }
        } catch (e) {
          console.error('[riskStore] fetchRules:', e);
          set({ rules: getFallbackRules() });
        }
      },

      updateRules: async (rules) => {
        set({ rules });
        try {
          await riskApi.updateRiskRules(rules);
        } catch (e) {
          console.error('[riskStore] updateRules:', e);
        }
      },

      /** 风控预检 — 本地规则校验（实际使用 store 中的 rules 状态） */
      checkOrder: async (order) => {
        return checkOrderWithRules(get().rules, order);
      },
    }),
    {
      name: 'futures-risk-store',
      partialize: (state) => ({ rules: state.rules }),
    }
  )
);

/** 风控预检详细结果（含触发规则列表） */
export interface RiskCheckDetail {
  pass: boolean;
  /** 所有未通过的规则 */
  failedRules: Array<{
    ruleId: string;
    name: string;
    currentValue: number;
    threshold: number;
    unit: string;
    message: string;
  }>;
  /** 汇总消息（同原 message 字段） */
  message: string;
}

/**
 * 纯函数：给定规则列表 + 订单，进行本地风控预检
 * 可被 tradingStore.runPrecheck 直接调用（避免在 Zustand action 中使用 hook）
 */
export function checkOrderWithRules(
  rules: RiskRuleConfig[],
  order: { symbol: string; direction: string; volume: number; price: number }
): RiskCheckDetail {
  const activeRules = rules.filter(r => r.enabled);
  const failedRules: RiskCheckDetail['failedRules'] = [];

  // 检查单品种最大持仓
  const positionLimit = activeRules.find(r => r.ruleId === 'R1_SINGLE_SYMBOL');
  if (positionLimit && order.volume > (positionLimit.threshold || 10)) {
    failedRules.push({
      ruleId: positionLimit.ruleId,
      name: positionLimit.name,
      currentValue: order.volume,
      threshold: positionLimit.threshold,
      unit: positionLimit.unit || '手',
      message: `当前手数 ${order.volume} 超过限制 ${positionLimit.threshold}手`,
    });
  }

  // 检查单日亏损
  const dailyLoss = activeRules.find(r => r.ruleId === 'R2_DAILY_LOSS');
  if (dailyLoss && dailyLoss.currentValue >= dailyLoss.threshold) {
    failedRules.push({
      ruleId: dailyLoss.ruleId,
      name: dailyLoss.name,
      currentValue: dailyLoss.currentValue,
      threshold: dailyLoss.threshold,
      unit: dailyLoss.unit || '¥',
      message: `当日已亏损 ${dailyLoss.currentValue.toLocaleString()}，超过阈值 ${dailyLoss.threshold.toLocaleString()}`,
    });
  }

  // 检查总保证金占比
  const totalMargin = activeRules.find(r => r.ruleId === 'R4_TOTAL_MARGIN');
  if (totalMargin && totalMargin.currentValue >= totalMargin.threshold) {
    failedRules.push({
      ruleId: totalMargin.ruleId,
      name: totalMargin.name,
      currentValue: totalMargin.currentValue,
      threshold: totalMargin.threshold,
      unit: '%',
      message: `保证金占比 ${totalMargin.currentValue}% 已达上限 ${totalMargin.threshold}%`,
    });
  }

  // 检查资金充足性
  const capital = activeRules.find(r => r.ruleId === 'R9_CAPITAL_SUFFICIENCY');
  if (capital && capital.currentValue < capital.threshold) {
    failedRules.push({
      ruleId: capital.ruleId,
      name: capital.name,
      currentValue: capital.currentValue,
      threshold: capital.threshold,
      unit: '倍',
      message: `可用资金倍数 ${capital.currentValue} 低于要求 ${capital.threshold}倍`,
    });
  }

  // 检查交易时间
  const now = new Date();
  const hour = now.getHours();
  const minute = now.getMinutes();
  const isTradingHours = (hour === 9 && minute >= 30) || (hour >= 10 && hour <= 11) ||
    (hour === 13 && minute >= 30) || (hour >= 14 && hour <= 15) ||
    (hour >= 21 && hour <= 23);
  if (!isTradingHours) {
    failedRules.push({
      ruleId: 'R8_TRADING_HOURS',
      name: '交易时间',
      currentValue: 0,
      threshold: 1,
      unit: '',
      message: '当前非交易时段（支持 09:30-11:30 / 13:30-15:00 / 21:00-23:00）',
    });
  }

  if (failedRules.length > 0) {
    return { pass: false, failedRules, message: `${failedRules.length} 条规则未通过` };
  }
  return { pass: true, failedRules: [], message: '风控检查通过' };
}

/** Fallback 规则（与 config.tsx 的 RULE_META 保持一致） */
function getFallbackRules(): RiskRuleConfig[] {
  return [
    // Layer 1 — 市场风险
    { id: 'R1', ruleId: 'R1_SINGLE_SYMBOL', name: '单品种仓位', enabled: true, layer: 1, threshold: 30, currentValue: 20, unit: '%' },
    { id: 'R2', ruleId: 'R2_DAILY_LOSS', name: '单日亏损', enabled: true, layer: 1, threshold: 50000, currentValue: 35000, unit: '¥' },
    { id: 'R3', ruleId: 'R3_PRICE_LIMIT', name: '涨跌停', enabled: true, layer: 1, threshold: 1, currentValue: 0, unit: '' },
    // Layer 2 — 账户风险
    { id: 'R4', ruleId: 'R4_TOTAL_MARGIN', name: '总保证金', enabled: true, layer: 2, threshold: 50, currentValue: 35, unit: '%' },
    { id: 'R5', ruleId: 'R5_VOLATILITY', name: '波动率', enabled: true, layer: 2, threshold: 0.03, currentValue: 0.015, unit: '' },
    { id: 'R6', ruleId: 'R6_LIQUIDITY', name: '流动性', enabled: true, layer: 2, threshold: 1.0, currentValue: 1.5, unit: '' },
    // Layer 3 — 交易执行
    { id: 'R7', ruleId: 'R7_CONSECUTIVE_LOSS', name: '连续亏损', enabled: true, layer: 3, threshold: 3, currentValue: 1, unit: '笔' },
    { id: 'R8', ruleId: 'R8_TRADING_HOURS', name: '交易时间', enabled: true, layer: 3, threshold: 1, currentValue: 1, unit: '' },
    { id: 'R9', ruleId: 'R9_CAPITAL_SUFFICIENCY', name: '资金充足', enabled: true, layer: 3, threshold: 1.5, currentValue: 2.0, unit: '倍' },
    { id: 'R10', ruleId: 'R10_MACRO_CIRCUIT_BREAKER', name: '宏观熔断', enabled: true, layer: 1, threshold: 0.5, currentValue: 0.72, unit: '' },
    { id: 'R11', ruleId: 'R11_DISPOSITION_EFFECT', name: '处置效应', enabled: true, layer: 3, threshold: 10, currentValue: 5, unit: '天' },
  ];
}
