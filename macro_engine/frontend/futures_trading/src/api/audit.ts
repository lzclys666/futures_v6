/**
 * 审计日志 API
 * 对应后端路由: routes/audit.py
 *
 * 端点：
 *   GET  /api/audit/log       — 查询审计日志（分页）
 *   GET  /api/audit/summary   — 审计统计摘要
 *
 * 注意：后端尚未实现（Phase 5），当前使用 Mock 数据
 */
import { apiGet } from './client';
import type { ApiResponse } from '../types';
import type { AuditLogQuery, AuditLogResponse, AuditSummary } from '../types/audit';

/**
 * 查询审计日志（分页）
 * @param query - page, pageSize, action, level, startDate, endDate
 */
export function fetchAuditLog(query: AuditLogQuery = {}): ApiResponse<AuditLogResponse> {
  return apiGet<AuditLogResponse>('/api/audit/log', query);
}

/**
 * 审计统计摘要
 * 返回 info/warn/error 计数和近24h数量
 */
export function fetchAuditSummary(): ApiResponse<AuditSummary> {
  return apiGet<AuditSummary>('/api/audit/summary');
}
