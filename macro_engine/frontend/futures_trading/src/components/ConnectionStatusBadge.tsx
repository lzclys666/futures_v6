import React from 'react';
import { Badge, Space, Tooltip, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useWebSocketState } from '../hooks/useWebSocket';
import { useVnpyStore } from '../store/vnpyStore';

const { Text } = Typography;

/**
 * 连接状态徽章 — 顶栏展示 WebSocket + API 双通道状态
 * - WebSocket: ws://localhost:8000/ws/vnpy
 * - REST API: http://localhost:8000/api/*
 * - backendHealth='mock' 时显示黄色警告，提示用户当前为模拟数据
 */
const ConnectionStatusBadge: React.FC = () => {
  const { connectionState, connected: wsConnected } = useWebSocketState();
  const backendHealth = useVnpyStore((s) => s.backendHealth);

  const apiOk = backendHealth === 'reachable';
  const isMock = backendHealth === 'mock';

  return (
    <Space size={12}>
      <Tooltip
        title={
          connectionState === 'connected'
            ? 'WebSocket 已连接（实时推送）'
            : connectionState === 'connecting'
              ? 'WebSocket 连接中…'
              : connectionState === 'reconnecting'
                ? 'WebSocket 重连中…'
                : 'WebSocket 未连接（使用轮询）'
        }
      >
        <Space size={4}>
          <Badge
            status={wsConnected ? 'success' : connectionState === 'connecting' || connectionState === 'reconnecting' ? 'processing' : 'default'}
          />
          <Text style={{ fontSize: 12 }}>
            {wsConnected ? (
              <><CheckCircleOutlined style={{ color: '#52c41a' }} /> 实时</>
            ) : connectionState === 'connecting' || connectionState === 'reconnecting' ? (
              <><SyncOutlined spin style={{ color: '#faad14' }} /> 连接中</>
            ) : (
              <><CloseCircleOutlined style={{ color: '#8c8c8c' }} /> 轮询</>
            )}
          </Text>
        </Space>
      </Tooltip>

      <Tooltip
        title={
          apiOk
            ? 'API 可达（真实数据）'
            : isMock
              ? 'CTP 未连接，当前显示 Mock 模拟数据'
              : backendHealth === 'unknown'
                ? 'API 待检测'
                : 'API 不可达'
        }
      >
        <Space size={4}>
          <Badge
            status={apiOk ? 'success' : isMock ? 'warning' : backendHealth === 'unknown' ? 'processing' : 'error'}
          />
          <Text style={{ fontSize: 12, color: apiOk ? '#52c41a' : isMock ? '#faad14' : backendHealth === 'unknown' ? '#faad14' : '#ff4d4f' }}>
            {apiOk ? 'API' : isMock ? 'Mock' : '离线'}
          </Text>
        </Space>
      </Tooltip>
    </Space>
  );
};

export default ConnectionStatusBadge;
