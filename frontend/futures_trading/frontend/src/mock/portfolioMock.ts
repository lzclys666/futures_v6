/**
 * 持仓看板 Mock 数据
 * @author Lucy
 * @date 2026-05-06
 * 
 * 包含 5 个品种的持仓数据 + 账户总览数据
 * 后端就绪后通过 api/vnpy.ts 的 USE_MOCK 开关切换
 */

import type { VnpyPosition, VnpyAccount } from '../types/vnpy'

/** Mock 账户数据 — 总权益 100 万，可用 60 万 */
export const MOCK_ACCOUNT: VnpyAccount = {
  accountId: 'SIM-001',
  balance: 1000000,
  available: 600000,
  frozen: 150000,
  unrealizedPnl: 52800,
  realizedPnl: 18500,
  totalPnl: 71300,
  returnRate: 0.0713,
  marginRatio: 0.25,
  updatedAt: new Date().toISOString(),
}

/** Mock 持仓数据 — 5 个品种，多空混合 */
export const MOCK_POSITIONS: VnpyPosition[] = [
  {
    symbol: 'RU2509',
    direction: 'LONG',
    volume: 8,
    ydVolume: 5,
    tdVolume: 3,
    available: 8,
    avgPrice: 14320,
    lastPrice: 14650,
    unrealizedPnl: 13200,
    margin: 57280,
    pnlRate: 0.0231,
    updatedAt: new Date().toISOString(),
  },
  {
    symbol: 'AG2509',
    direction: 'SHORT',
    volume: 5,
    ydVolume: 5,
    tdVolume: 0,
    available: 5,
    avgPrice: 8150,
    lastPrice: 7980,
    unrealizedPnl: 8500,
    margin: 40750,
    pnlRate: 0.0209,
    updatedAt: new Date().toISOString(),
  },
  {
    symbol: 'AU2509',
    direction: 'LONG',
    volume: 3,
    ydVolume: 3,
    tdVolume: 0,
    available: 3,
    avgPrice: 580,
    lastPrice: 592,
    unrealizedPnl: 18000,
    margin: 17400,
    pnlRate: 0.0207,
    updatedAt: new Date().toISOString(),
  },
  {
    symbol: 'CU2507',
    direction: 'LONG',
    volume: 2,
    ydVolume: 0,
    tdVolume: 2,
    available: 2,
    avgPrice: 78500,
    lastPrice: 79200,
    unrealizedPnl: 7000,
    margin: 78500,
    pnlRate: 0.0089,
    updatedAt: new Date().toISOString(),
  },
  {
    symbol: 'RB2510',
    direction: 'SHORT',
    volume: 10,
    ydVolume: 10,
    tdVolume: 0,
    available: 10,
    avgPrice: 3620,
    lastPrice: 3585,
    unrealizedPnl: 3500,
    margin: 36200,
    pnlRate: 0.0097,
    updatedAt: new Date().toISOString(),
  },
]
