/**
 * 交易模块 · API 封装
 * @date 2026-04-24
 */

import { createClient } from './client'
import type { PortfolioData } from '../types/macro'
import type { PositionItem } from '../types/macro'
import { fetchRiskStatus } from './risk'

const USE_MOCK = false // 后端 /api/trading/* 就绪后改为 false

// ---------- Mock 数据（对应 types/macro.ts 的 snake_case 字段） ----------

const MOCK_PORTFOLIO: PortfolioData = {
  date: new Date().toISOString().slice(0, 10),
  totalEquity: 1000000,
  availableCash: 850000,
  positions: [
    {
      symbol: 'RU2501',
      name: '橡胶',
      direction: 'LONG',
      positionPct: 18.2,
      lots: 5,
      entryPrice: 14500,
      currentPrice: 14620,
      unrealizedPnl: 6000,
    },
    {
      symbol: 'AG2502',
      name: '白银',
      direction: 'SHORT',
      positionPct: 8.7,
      lots: 3,
      entryPrice: 5800,
      currentPrice: 5750,
      unrealizedPnl: 1500,
    },
    {
      symbol: 'AU2506',
      name: '黄金',
      direction: 'LONG',
      positionPct: 12.4,
      lots: 2,
      entryPrice: 620,
      currentPrice: 625,
      unrealizedPnl: 10000,
    },
  ],
  totalPositionPct: 39.3,
  dailyPnl: 17500,
  dailyReturn: 0.0175,
  currentDrawdown: 0.02,
  maxDrawdown: 0.05,
}

// ---------- Axios 实例（复用 client.ts 统一拦截器） ----------

const http = createClient('/api/trading')

/**
 * GET /api/trading/portfolio → 聚合组合数据（账户统计 + 持仓列表）
 * 后端返回 snake_case，前端需要 camelCase
 */
export async function fetchPortfolio(): Promise<PortfolioData> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200))
    return MOCK_PORTFOLIO
  }
  const res = await http.get<unknown>('/portfolio')
  // res.data 是后端返回的 portfolio 对象（已由 client.ts 解包）
  const p = (res.data as Record<string, unknown>)?.portfolio as Record<string, unknown> | undefined
  if (!p) throw new Error('组合数据格式错误')
  // 转换 snake_case → camelCase
  return {
    date: (p.date as string) || '',
    totalEquity: (p.total_equity as number) ?? 0,
    availableCash: (p.available_cash as number) ?? 0,
    dailyPnl: (p.daily_pnl as number) ?? 0,
    dailyReturn: (p.daily_return as number) ?? 0,
    totalPositionPct: (p.total_position_pct as number) ?? 0,
    currentDrawdown: 0,
    maxDrawdown: 0,
    positions: (p.positions as Array<Record<string, unknown>> || []).map((pos): PositionItem => ({
      symbol: (pos.symbol as string) || '',
      direction: (pos.direction as PositionItem['direction']) || 'NEUTRAL',
      lots: (pos.volume as number) || 0,
      entryPrice: (pos.price as number) ?? null,
      currentPrice: (pos.price as number) ?? null,
      unrealizedPnl: (pos.pnl as number) ?? null,
      positionPct: 0,
    })),
  }
}

/**
 * GET /api/risk/status — 风控状态（委托自 @/api/risk）
 */
export { fetchRiskStatus } from './risk'
