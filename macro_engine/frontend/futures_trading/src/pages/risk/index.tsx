import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Table, Tag, Progress, Button, Space, Alert, Statistic, Badge, Tabs } from 'antd';
import { useRiskStore } from '../../store/riskStore';
import type { RiskRuleConfig } from '../../types/risk';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

/**
 * 风控面板页面
 * 展示 11 条风控规则状态、触发记录、风险等级
 */
const RiskPanel: React.FC = () => {
  const { status, rules, fetchStatus, fetchRules } = useRiskStore();
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchStatus();
    fetchRules();
    
    // 10s 轮询
    const timer = setInterval(() => {
      fetchStatus();
    }, 10000);
    
    return () => clearInterval(timer);
  }, [fetchStatus, fetchRules]);

  // 风险等级颜色
  const levelColors: Record<string, string> = {
    LOW: '#52c41a',
    MEDIUM: '#faad14',
    HIGH: '#ff4d4f',
    CRITICAL: '#ff4d4f',
  };

  // 规则表格列
  const ruleColumns = [
    {
      title: '规则ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
    },
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean) => (
        <Tag color={enabled ? '#52c41a' : '#8c8c8c'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      width: 120,
      render: (threshold: number, record: RiskRuleConfig) => (
        <Text>{threshold}{record.unit}</Text>
      ),
    },
    {
      title: '当前值',
      dataIndex: 'currentValue',
      key: 'currentValue',
      width: 120,
      render: (value: number, record: RiskRuleConfig) => (
        <Text style={{ color: value > record.threshold ? '#ff4d4f' : '#52c41a' }}>
          {value}{record.unit}
        </Text>
      ),
    },
    {
      title: '利用率',
      key: 'utilization',
      width: 150,
      render: (_: any, record: RiskRuleConfig) => {
        const pct = Math.min(100, (record.currentValue / record.threshold) * 100);
        return (
          <Progress 
            percent={Math.round(pct)} 
            size="small" 
            status={pct > 90 ? 'exception' : pct > 70 ? 'active' : 'success'}
          />
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: RiskRuleConfig) => (
        <Button type="link" size="small" href={`/risk/config?rule=${record.id}`}>
          配置
        </Button>
      ),
    },
  ];

  // 触发记录列
  const triggerColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
    },
    {
      title: '规则',
      dataIndex: 'ruleName',
      key: 'ruleName',
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: string) => (
        <Tag color={action === 'BLOCK' ? '#ff4d4f' : '#faad14'}>
          {action === 'BLOCK' ? '阻断' : '警告'}
        </Tag>
      ),
    },
    {
      title: '详情',
      dataIndex: 'detail',
      key: 'detail',
    },
  ];

  // Mock 触发记录
  const triggerRecords = [
    { timestamp: '2026-04-27 09:15:32', ruleName: '单日最大亏损', action: 'WARN', detail: '当前亏损 8.5%，接近阈值 10%' },
    { timestamp: '2026-04-27 10:23:18', ruleName: '单品种最大持仓', action: 'BLOCK', detail: 'RB 持仓 15 手，超过阈值 10 手' },
    { timestamp: '2026-04-26 14:45:05', ruleName: '资金使用率', action: 'WARN', detail: '资金使用率 78%，接近阈值 80%' },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>风控面板</Title>
        <Text type="secondary">实时监控 11 条风控规则状态</Text>
      </div>

      {/* 风险概览卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="风险等级"
              value={status?.overall || 'PASS'}
              valueStyle={{ color: levelColors[status?.overall || 'PASS'] }}
              prefix={<Badge status={status?.overall === 'PASS' ? 'success' : status?.overall === 'MEDIUM' || status?.overall === 'LOW' ? 'warning' : 'error'} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="通过规则"
              value={status?.passCount ?? 0}
              suffix={`/ ${rules.length}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="警告规则"
              value={status?.warnCount ?? 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="阻断规则"
              value={status?.blockCount ?? 0}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 标签页 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="规则状态" key="overview">
          <Card size="small">
            <Table
              dataSource={rules}
              columns={ruleColumns}
              rowKey="id"
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </TabPane>
        
        <TabPane tab="触发记录" key="triggers">
          <Card size="small">
            <Table
              dataSource={triggerRecords}
              columns={triggerColumns}
              rowKey="timestamp"
              pagination={false}
              size="small"
            />
          </Card>
        </TabPane>
        
        <TabPane tab="风险分布" key="distribution">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card size="small" title="Layer 1 - 交易前检查">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {rules.filter(r => r.layer === 1).map(rule => (
                    <div key={rule.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text>{rule.name}</Text>
                      <Tag color={rule.enabled ? '#52c41a' : '#8c8c8c'}>{rule.enabled ? '启用' : '禁用'}</Tag>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="Layer 2 - 持仓中检查">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {rules.filter(r => r.layer === 2).map(rule => (
                    <div key={rule.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text>{rule.name}</Text>
                      <Tag color={rule.enabled ? '#52c41a' : '#8c8c8c'}>{rule.enabled ? '启用' : '禁用'}</Tag>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Card size="small" title="Layer 3 - 日终检查">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {rules.filter(r => r.layer === 3).map(rule => (
                    <div key={rule.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text>{rule.name}</Text>
                      <Tag color={rule.enabled ? '#52c41a' : '#8c8c8c'}>{rule.enabled ? '启用' : '禁用'}</Tag>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default RiskPanel;