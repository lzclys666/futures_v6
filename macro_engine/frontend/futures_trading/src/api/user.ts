/**
 * 用户 / 个人中心 API
 * 对应后端路由: routes/user.py
 *
 * 端点：
 *   GET  /api/user/profile              — 用户信息
 *   GET  /api/user/equity-history     — 资金曲线
 *   GET  /api/user/notification-prefs — 通知偏好（GET）
 *   POST /api/user/notification-prefs — 更新通知偏好
 *   POST /api/user/avatar             — 头像上传
 *
 * 注意：后端尚未完全实现，当前使用 Mock 数据
 */
import { apiGet, apiPost } from './client';
import type { ApiResponse } from '../types';
import type { UserProfile, PerformanceSummary, EquityPoint, NotificationPrefs, AvatarUploadResponse } from '../types/user';

/** 获取用户信息 */
export function fetchUserProfile(): ApiResponse<UserProfile> {
  return apiGet<UserProfile>('/api/user/profile');
}

/** 获取绩效摘要 */
export function fetchPerformance(period = 'monthly'): ApiResponse<PerformanceSummary> {
  return apiGet<PerformanceSummary>('/api/user/performance', { period });
}

/** 获取资金曲线历史 */
export function fetchEquityHistory(days = 90): ApiResponse<EquityPoint[]> {
  return apiGet<EquityPoint[]>('/api/user/equity-history', { days });
}

/** fetchEquityCurve — alias for fetchEquityHistory (used by userStore) */
export const fetchEquityCurve = fetchEquityHistory;

/** 获取通知偏好设置 */
export function fetchNotificationPrefs(): ApiResponse<NotificationPrefs> {
  return apiGet<NotificationPrefs>('/api/user/notification-prefs');
}

/** 更新通知偏好设置 */
export function updateNotificationPrefs(prefs: NotificationPrefs): ApiResponse<NotificationPrefs> {
  return apiPost<NotificationPrefs>('/api/user/notification-prefs', prefs);
}

/** 上传头像（FormData） */
export function uploadAvatar(file: File): ApiResponse<AvatarUploadResponse> {
  const formData = new FormData();
  formData.append('avatar', file);
  return apiPost<AvatarUploadResponse>('/api/user/avatar', formData);
}
