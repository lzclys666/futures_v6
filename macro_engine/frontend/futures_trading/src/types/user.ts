import type { RiskProfile } from './risk';

/** 用户信息 */
export interface UserProfile {
  username: string;
  riskProfile: RiskProfile;
  accountId: string;
  email?: string;
  avatar?: string;           // 头像 URL
  createdAt?: string;         // 注册时间 ISO 8601
}

/** 绩效摘要 */
export interface PerformanceSummary {
  totalReturn: number;        // 总收益率 %
  sharpeRatio: number;        // 夏普比率
  maxDrawdown: number;         // 最大回撤 %
  winRate: number;             // 胜率 0-1
  avgWinLossRatio: number;     // 平均盈亏比
  totalTrades: number;         // 总交易次数
  period: string;              // 统计周期描述 e.g. '近90日'
}

/** 资金曲线点 */
export interface EquityPoint {
  date: string;                // 'YYYY-MM-DD'
  equity: number;              // 当日权益
  return: number;               // 当日收益率 %
}

/** 通知偏好设置 */
export interface NotificationPrefs {
  riskBlock: boolean;          // 风控阻断通知（任何 HIGH 规则触发时推送）
  dispositionEffect: boolean;   // 处置效应提醒（R11 触发时弹窗）
  dailyReport: boolean;        // 日度绩效报告（每日 18:00 推送）
  weeklyReport: boolean;       // 周度报告（每周一 09:00）
  extremeWeatherAlert: boolean; // 极端行情预警
}

/** 头像上传响应 */
export interface AvatarUploadResponse {
  avatarUrl: string;           // 上传后的头像 URL
}
