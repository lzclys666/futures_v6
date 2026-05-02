/**
 * 用户模块 · TypeScript 类型定义
 * @author Lucy
 * @date 2026-04-27
 */

/** 通知设置 */
export interface NotificationSettings {
  /** 风控告警 */
  riskAlert: boolean
  /** 交易成交 */
  tradeFilled: boolean
  /** 熔断通知 */
  circuitBreaker: boolean
  /** 每日报告 */
  dailyReport: boolean
  /** 通知渠道：email / wechat / web */
  channels: string[]
}

/** 用户画像（风控偏好） */
export interface RiskProfile {
  /** 风险偏好：conservative / moderate / aggressive */
  riskTolerance: 'conservative' | 'moderate' | 'aggressive'
  /** 最大回撤容忍度（%） */
  maxDrawdown: number
  /** 日内最大亏损（元） */
  maxDailyLoss: number
  /** 单品种最大仓位比例 */
  maxSingleSymbolPct: number
  /** 总仓位上限比例 */
  maxTotalPositionPct: number
  /** 杠杆倍数上限 */
  maxLeverage: number
}

/** 用户偏好设置 */
export interface UserPreferences {
  /** 默认品种 */
  defaultSymbol: string
  /** 主题：light / dark */
  theme: 'light' | 'dark'
  /** 语言 */
  language: 'zh-CN' | 'en-US'
  /** 数据刷新间隔（秒） */
  refreshInterval: number
  /** 通知设置 */
  notifications: NotificationSettings
}

/** 用户完整信息 */
export interface UserProfile {
  userId: string
  username: string
  displayName: string
  email: string
  role: 'admin' | 'trader' | 'viewer'
  /** 账户创建时间 */
  createdAt: string
  /** 最近登录时间 */
  lastLoginAt: string
  /** 偏好设置 */
  preferences: UserPreferences
  /** 风控画像 */
  riskProfile: RiskProfile
  /** 累计交易天数 */
  totalTradingDays: number
  /** 累计收益率 */
  cumulativeReturn: number
  /** 胜率 */
  winRate: number
  /** 夏普比率 */
  sharpeRatio?: number
  /** 最大回撤 */
  maxHistoricalDrawdown?: number
}
