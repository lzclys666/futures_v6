import React, { useState, useMemo } from 'react';
import {
  Card, Table, DatePicker, Select, Button, Tag, Typography,
  Space, Row, Col, Statistic,
} from 'antd';
import {
  FileTextOutlined, FilterOutlined, ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface AuditRecord {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  target: string;
  details: string;
  severity: 'INFO' | 'WARN' | 'ERROR';
}

/** Mock 审计日志数据 */
function getMockAuditLogs(): AuditRecord[] {
  const actions = ['UPDATE_RISK_RULE', 'PLACE_ORDER', 'CANCEL_ORDER', 'LOGIN', 'UPDATE_PROFILE', 'RUN_STRESS_TEST'];
  const users = ['trader_001', 'admin', 'system'];
  const logs: AuditRecord[] = [];
  const now = Date.now();

  for (let i = 0; i < 60; i++) {
    const ts = new Date(now - i * 15 * 60 * 1000); // 每15分钟一条
    const action = actions[Math.floor(Math.random() * actions.length)];
    const severity = action.startsWith('UPDATE_RISK') || action === 'PLACE_ORDER' ? 'WARN'
      : action === 'CANCEL_ORDER' ? 'ERROR' : 'INFO';
    logs.push({
      id: `log_${i}`,
      timestamp: ts.toISOString(),
      user: users[Math.floor(Math.random() * users.length)],
      action,
      target: action === 'UPDATE_RISK_RULE' ? 'R2_DAILY_LOSS'
        : action === 'PLACE_ORDER' ? 'RB2505'
        : action === 'CANCEL_ORDER' ? 'HC2505'
        : '-',
      details: action === 'UPDATE_RISK_RULE' ? '阈值从 50000 调整为 80000'
        : action === 'PLACE_ORDER' ? '开多 RB2505 x3 @3715'
        : action === 'CANCEL_ORDER' ? '撤销委托 RB2505 x2'
        : action === 'LOGIN' ? '登录成功'
        : action === 'UPDATE_PROFILE' ? '更新风险画像：保守型 → 稳健型'
        : '压力测试场景：闪崩',
      severity,
    });
  }
  return logs;
}

/** 动作类型中文映射 */
const ACTION_LABELS: Record<string, string> = {
  UPDATE_RISK_RULE: '风控规则变更',
  PLACE_ORDER: '下单',
  CANCEL_ORDER: '撤单',
  LOGIN: '登录',
  LOGOUT: '登出',
  UPDATE_PROFILE: '更新画像',
  RUN_STRESS_TEST: '压力测试',
};

const SEVERITY_COLORS: Record<string, string> = {
  INFO: 'blue',
  WARN: 'orange',
  ERROR: 'red',
};

/**
 * 系统管理 — 审计日志页面（Phase 4）
 * 记录所有关键操作，含筛选 + 重置功能
 */
const AdminPage: React.FC = () => {
  const [allLogs] = useState<AuditRecord[]>(() => getMockAuditLogs());
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [actionType, setActionType] = useState<string>('ALL');
  const [keyword, setKeyword] = useState<string>('');

  /** 重置全部筛选条件 */
  const handleReset = () => {
    setDateRange(null);
    setActionType('ALL');
    setKeyword('');
  };

  /** 根据筛选条件过滤 */
  const filteredLogs = useMemo(() => {
    return allLogs.filter(log => {
      if (actionType !== 'ALL' && log.action !== actionType) return false;
      if (dateRange) {
        const ts = new Date(log.timestamp).getTime();
        const [start, end] = dateRange;
        if (ts < new Date(start).getTime() || ts > new Date(end).getTime()) return false;
      }
      if (keyword && !log.details.includes(keyword) && !log.user.includes(keyword) && !log.target.includes(keyword)) {
        return false;
      }
      return true;
    });
  }, [allLogs, dateRange, actionType, keyword]);

  const columns: ColumnsType<AuditRecord> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 170,
      render: (ts: string) => new Date(ts).toLocaleString('zh-CN'),
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: '用户',
      dataIndex: 'user',
      key: 'user',
      width: 100,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (a: string) => ACTION_LABELS[a] ?? a,
    },
    {
      title: '对象',
      dataIndex: 'target',
      key: 'target',
      width: 120,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
    },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (s: string) => <Tag color={SEVERITY_COLORS[s]}>{s}</Tag>,
      filters: [
        { text: '信息', value: 'INFO' },
        { text: '警告', value: 'WARN' },
        { text: '错误', value: 'ERROR' },
      ],
      onFilter: (value, record) => record.severity === value,
    },
  ];

  const hasFilters = dateRange !== null || actionType !== 'ALL' || keyword !== '';

  return (
    <div style={{ padding: 16, maxWidth: 1400, margin: '0 auto' }}>
      <Title level={4}><FileTextOutlined /> 审计日志</Title>
      <Text type="secondary">系统关键操作记录 · 仅保留最近 30 天</Text>

      {/* 筛选栏 */}
      <Card size="small" style={{ marginTop: 16, marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Space>
              <FilterOutlined />
              <Text>筛选：</Text>
            </Space>
          </Col>
          <Col>
            <RangePicker
              onChange={(dates, dateStrings) => {
                if (dates && dateStrings[0] && dateStrings[1]) {
                  setDateRange([dateStrings[0], dateStrings[1]]);
                } else {
                  setDateRange(null);
                }
              }}
              placeholder={['开始日期', '结束日期']}
              style={{ width: 260 }}
            />
          </Col>
          <Col>
            <Select
              value={actionType}
              onChange={setActionType}
              style={{ width: 140 }}
            >
              <Option value="ALL">全部操作</Option>
              {Object.entries(ACTION_LABELS).map(([k, v]) => (
                <Option key={k} value={k}>{v}</Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Select
              value={keyword || undefined}
              onChange={v => setKeyword(v ?? '')}
              allowClear
              placeholder="搜索用户/详情/对象"
              style={{ width: 160 }}
              showSearch
              filterOption={(input, option) =>
                (option?.children as any)?.props?.children?.props?.children?.props?.children
                  ?.toLowerCase().includes(input.toLowerCase()) ?? false
              }
            >
              {allLogs.slice(0, 20).map(log => (
                <Option key={log.id} value={log.user}>{log.user}</Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              disabled={!hasFilters}
            >
              重置
            </Button>
          </Col>
          <Col push={1}>
            <Text type="secondary">共 {filteredLogs.length} 条记录</Text>
          </Col>
        </Row>
      </Card>

      {/* 统计摘要 */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="总记录数" value={filteredLogs.length} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="警告"
              value={filteredLogs.filter(l => l.severity === 'WARN').length}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="错误"
              value={filteredLogs.filter(l => l.severity === 'ERROR').length}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 日志表格 */}
      <Card size="small" title="操作记录">
        <Table
          dataSource={filteredLogs}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  );
};

export default AdminPage;
