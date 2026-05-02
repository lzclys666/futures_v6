/** 品种代码 */
export type SymbolCode = 'RB' | 'HC' | 'I' | 'J' | 'JM' | 'AU' | 'AG' | 'CU' | 'AL';

/** 订单方向 */
export type OrderDirection = 'long' | 'short';

/** 订单类型 */
export type OrderType = 'market' | 'limit' | 'stop';

/** 订单状态 */
export type OrderStatus = 'pending' | 'filled' | 'partial' | 'cancelled' | 'rejected';

/** 持仓 */
export interface Position {
  symbol: SymbolCode;
  symbolName: string;
  direction: OrderDirection;
  volume: number;
  avgPrice: number;
  lastPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
  margin: number;
  openTime: string;
}

/** 订单 */
export interface Order {
  orderId: string;
  symbol: SymbolCode;
  direction: OrderDirection;
  price: number;
  volume: number;
  filledVolume: number;
  orderType: OrderType;
  status: OrderStatus;
  createdAt: string;
  updatedAt: string;
}

/** 风控预检请求 */
export interface PrecheckRequest {
  symbol: SymbolCode;
  direction: OrderDirection;
  volume: number;
  price: number;
}

/** 风控预检结果 */
export interface PrecheckResult {
  passed: boolean;
  blockedRules: string[];
  warnings: string[];
}
