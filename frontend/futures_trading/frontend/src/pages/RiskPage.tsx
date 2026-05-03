/**
 * 风控面板页面
 * 11 条规则状态展示 + 层级分组
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useEffect } from 'react'
import { Card, Table, Tag, Progress, Typography, Row, Col, Statistic, Empty } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { SafetyCertificateOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useRiskStore } from '../store/useRiskStore'
import type { RiskRuleStatus, RiskLayerKey } from '../types/risk'

const { Title } = Typography

const severityConfig = {
  PASS: { color: '#52c41a', icon: <CheckCircleOutlined />, label: '通过' },
  WARN: { color: '#faad14', icon: <WarningOutlined />, label: '警告' },
  BLOCK: { color: '#ff4d4f', icon: <CloseCircleOutlined />, label: '阻断' },
}

const layerConfig: Record<RiskLayerKey, { title: string; color: string }> = {
  1: { title: 'Layer 1 · 基础风控', color: '#52c41a' },
  2: { title: 'Layer 2 · 进阶风控', color: '#faad14' },
  3: { title: 'Layer 3 · 熔断风控', color: '#ff4d4f' },
}

const RiskPage: React.FC = () => {
  const { status, loadStatus, startPolling, stopPolling } = useRiskStore()

  useEffect(() => {
    loadStatus()
    startPolling(10000)
    return () => stopPolling()
  }, [])

  const columns: ColumnsType<RiskRuleStatus> = [
    { title: '规则', dataIndex: 'ruleName', key: 'name', fixed: 'left', width: 180 },
    {
      title: '状态',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (v: string) => (
        <Tag color={severityConfig[v as keyof typeof severityConfig]?.color} icon={severityConfig[v as keyof typeof severityConfig]?.icon}>
          {severityConfig[v as keyof typeof severityConfig]?.label}
        </Tag>
      ),
    },
    {
      title: '当前值',
      dataIndex: 'currentValue',
      key: 'current',
      align: 'right',
      render: (v: number) => v?.toFixed(2),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      align: 'right',
      render: (v: number) => v?.toFixed(2),
    },
    {
      title: '使用率',
      key: 'usage',
      align: 'right',
      render: (_, r) => {
        const pct = r.threshold > 0 ? (r.currentValue / r.threshold) * 100 : 0
        return (
          <Progress
            percent={Math.min(pct, 100)}
            size="small"
            status={pct > 100 ? 'exception' : pct > 80 ? 'active' : 'success'}
            format={(p) => `${p?.toFixed(0)}%`}
          />
        )
      },
    },
    { title: '描述', dataIndex: 'message', key: 'message', ellipsis: true },
  ]

  const triggeredCount = status?.triggeredCount ?? 0
  const totalCount = status?.rules?.length ?? 0
  const passRate = totalCount > 0 ? ((totalCount - triggeredCount) / totalCount) * 100 : 100

  // 按层级分组
  const layerRules: Record<RiskLayerKey, RiskRuleStatus[]> = {
    1: status?.rules?.filter((r: RiskRuleStatus) => r.layer === 1) ?? [],
    2: status?.rules?.filter((r: RiskRuleStatus) => r.layer === 2) ?? [],
    3: status?.rules?.filter((r: RiskRuleStatus) => r.layer === 3) ?? [],
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SafetyCertificateOutlined style={{ marginRight: 8 }} />
        风控面板
      </Title>

      {/* 总览统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="规则总数" value={totalCount} suffix="条" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="触发规则" value={triggeredCount} suffix="条" valueStyle={{ color: triggeredCount > 0 ? '#ff4d4f' : '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="通过率" value={passRate} precision={1} suffix="%" valueStyle={{ color: passRate >= 90 ? '#52c41a' : passRate >= 70 ? '#faad14' : '#ff4d4f' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="熔断状态" value={status?.circuitBreaker ? '已触发' : '正常'} valueStyle={{ color: status?.circuitBreaker ? '#ff4d4f' : '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      {/* 各层级规则表 */}
      {([1, 2, 3] as RiskLayerKey[]).map((layer) => (
        <Card
          key={layer}
          size="small"
          title={
            <span style={{ color: layerConfig[layer].color }}>
              {layerConfig[layer].title}
            </span>
          }
          style={{ marginBottom: 16 }}
        >
          {layerRules[layer].length > 0 ? (
            <Table
              columns={columns}
              dataSource={layerRules[layer]}
              rowKey="ruleId"
              pagination={false}
              size="small"
              scroll={{ x: 800 }}
            />
          ) : (
            <Empty description="该层级暂无规则" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      ))}
    </div>
  )
}

export default RiskPage
