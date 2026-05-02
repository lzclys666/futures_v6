import React, { useState, useEffect } from 'react';
import {
  Card, Table, Tag, Typography, Space, DatePicker, Select, Empty, Button,
  Statistic, Row, Col,
} from 'antd';
import { AuditOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Text } = Typography;

interface AuditRecord {
  id: string;
  timestamp: string;
  action: string;
  symbol: string;
  details: string;
  user: string;
  level: 'info' | 'warning' | 'error';
}

/** Mock 审计日志数据 */
function generateMockAuditLog(): AuditRecord[] {
  const actions = ['下单', '撤单', '平仓', '修改风控规则', '切换风险画像', '登录', '压力测试', '规则模拟'];
  const levels: AuditRecord['level'][] = ['info', 'info', 'info', 'warning', 'error'];
  const records: AuditRecord[] = [];
  for (let i = 0; i < 200; i++) {
    const d = dayjs().subtract(Math.floor(Math.random() * 30), 'day');
    records.push({
      id: `AUDIT-${10000 + i}`,
      timestamp: d.format('YYYY-MM-DD HH:mm:ss'),
      action: actions[Math.floor(Math.random() * actions.length)],
      symbol: ['RB', 'JM', 'NI', 'RU', 'ZN', '—'][Math.floor(Math.random() * 6)],
      details: `操作详情 #${i + 1}`,
      user: ['trader_001', 'admin', 'system'][Math.floor(Math.random() * 3)],
      level: levels[Math.floor(Math.random() * levels.length)],
    });
  }
  return records.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

/**
 * 审计日志 — Phase 5
 * 200 条 Mock 数据，支持虚拟滚动
 */
const AuditLog: React.FC = () => {
  const [records] = useState<AuditRecord[]>(() => generateMockAuditLog());
  const [filterAction, setFilterAction] = useState<string>('all');
  const [filterLevel, setFilterLevel] = useState<string>('all');

  /** 重置全部筛选条件 */
  const handleReset = () => {
    setFilterAction('all');
    setFilterLevel('all');
  };

  const filtered = records.filter(r => {
    if (filterAction !== 'all' && r.action !== filterAction) return false;
    if (filterLevel !== 'all' && r.level !== filterLevel) return false;
    return true;
  });

  const columns: ColumnsType<AuditRecord> = [
    { title: '时间', dataIndex: 'timestamp', key: 'timestamp', width: 170 },
    { title: '用户', dataIndex: 'user', key: 'user', width: 100 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 120 },
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 80,
      render: (v: string) => v === '—' ? <Text type="secondary">—</Text> : <Tag>{v}</Tag> },
    { title: '详情', dataIndex: 'details', key: 'details', ellipsis: true },
    {
      title: '级别', dataIndex: 'level', key: 'level', width: 80,
      render: (v: string) => {
        const colors: Record<string, string> = { info: 'default', warning: 'warning', error: 'error' };
        const labels: Record<string, string> = { info: '信息', warning: '警告', error: '错误' };
        return <Tag color={colors[v]}>{labels[v]}</Tag>;
      },
    },
  ];

  const levelCount = filtered.filter(r => r.level === 'error').length;
  const warnCount = filtered.filter(r => r.level === 'warning').length;

  return (
    <div style={{ padding: 16, maxWidth: 1400, margin: '0 auto' }}>
      <Typography.Title level={4}><AuditOutlined /> 审计日志</Typography.Title>
      <Text type="secondary">记录所有交易操作、风控变更和系统事件</Text>

      {/* 统计摘要 */}
      <Row gutter={12} style={{ marginTop: 16, marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="总记录数" value={filtered.length} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="警告" value={warnCount} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="错误" value={levelCount} valueStyle={{ color: '#ff4d4f' }} />
          </Card>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Text strong><SearchOutlined /> 筛选：</Text>
          <Select value={filterAction} onChange={setFilterAction} style={{ width: 140 }}>
            <Select.Option value="all">全部操作</Select.Option>
            {['下单', '撤单', '平仓', '修改风控规则', '切换风险画像', '登录', '压力测试', '规则模拟'].map(a => (
              <Select.Option key={a} value={a}>{a}</Select.Option>
            ))}
          </Select>
          <Select value={filterLevel} onChange={setFilterLevel} style={{ width: 120 }}>
            <Select.Option value="all">全部级别</Select.Option>
            <Select.Option value="info">信息</Select.Option>
            <Select.Option value="warning">警告</Select.Option>
            <Select.Option value="error">错误</Select.Option>
          </Select>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReset}
            disabled={filterAction === 'all' && filterLevel === 'all'}
          >
            重置
          </Button>
          <Text type="secondary">共 {filtered.length} 条记录</Text>
        </Space>
      </Card>

      {/* 日志表格 — 虚拟滚动 */}
      <Card size="small" title="操作记录">
        <Table
          dataSource={filtered}
          columns={columns}
          rowKey="id"
          size="small"
          virtual                          // ← Phase 5: 虚拟滚动
          scroll={{ x: 900, y: 500 }}
          pagination={{ pageSize: 50, size: 'small' }}
          locale={{ emptyText: <Empty description="无记录" /> }}
        />
      </Card>
    </div>
  );
};

export default AuditLog;
