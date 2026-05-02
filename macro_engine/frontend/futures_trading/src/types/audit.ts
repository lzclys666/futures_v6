/**
 * 审计日志类型定义
 * 对应后端路由: routes/audit.py
 */

/** 审计日志操作级别 */
export type AuditLevel = 'info' | 'warning' | 'error';

/** 审计日志操作类型 */
export type AuditAction =
  | '下单'
  | '撤单'
  | '开仓'
  | '平仓'
  | '修改风控规则'
  | '切换风险画像'
  | '登录'
  | '登出'
  | '压力测试'
  | '规则模拟'
  | '系统配置变更';

/** 单条审计日志记录 */
export interface AuditRecord {
  id: string;
  timestamp: string;           // ISO 8601: '2026-04-28T14:30:00'
  action: AuditAction;
  symbol?: string;             // 品种代码，操作涉及品种时填写
  details: string;            // 操作详情描述
  user: string;               // 用户名
  level: AuditLevel;
  ip?: string;                 // 操作 IP 地址
  result?: 'success' | 'fail' | 'blocked';
}

/** 审计日志查询参数 */
export interface AuditLogQuery {
  page?: number;
  pageSize?: number;
  action?: AuditAction | 'all';
  level?: AuditLevel | 'all';
  startDate?: string;         // 'YYYY-MM-DD'
  endDate?: string;           // 'YYYY-MM-DD'
  user?: string;
  symbol?: string;
}

/** 审计日志分页响应 */
export interface AuditLogResponse {
  records: AuditRecord[];
  total: number;
  page: number;
  pageSize: number;
}

/** 审计统计摘要 */
export interface AuditSummary {
  totalCount: number;
  infoCount: number;
  warnCount: number;
  errorCount: number;
  last24hCount: number;
}
