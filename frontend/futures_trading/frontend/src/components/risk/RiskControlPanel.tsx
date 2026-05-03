/**
 * 风控面板组件（使用 zustand store）
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useEffect } from 'react'
import { Card, Tag, Collapse, Statistic, Row, Col, Button, Space, Spin, Empty, Tooltip } from 'antd'
import {
  SafetyOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useRiskStore } from '../../store/useRiskStore'
import type { RiskRuleStatus, RiskLayerKey } from '../../types/risk'
import './RiskControlPanel.css'

const LAYER_CONFIG: Record<RiskLayerKey, { label: string; color: string; desc: string }> = {
  1: { label: 'Layer 1 · 基础风控', color: '#1890ff', desc: '宏观熔断 · 波动率 · 流动性' },
  2: { label: 'Layer 2 · 进阶风控', color: '#722ed1', desc: '亏损限制 · 连续亏损 · 处置效应' },
  3: { label: 'Layer 3 · 仓位风控', color: '#13c2c2', desc: '持仓 · 保证金 · 集中度' },
}

const SEVERITY_TAG: Record<string, { color: string; text: string }> = {
  PASS: { color: 'success', text: '通过' },
  WARN: { color: 'warning', text: '警告' },
  BLOCK: { color: 'error', text: '阻断' },
}

const RiskControlPanel: React.FC = () => {
  const { status, loadStatus, startPolling, stopPolling, statusLoading } = useRiskStore()

  useEffect(() => {
    loadStatus()
    startPolling(10000)
    return () => stopPolling()
  }, [])

  const overallStatus = status?.overallStatus ?? 'PASS'
  const triggeredCount = status?.triggeredCount ?? 0
  const totalCount = status?.rules?.length ?? 0
  const circuitBreaker = status?.circuitBreaker ?? false

  const getLayerRules = (layer: RiskLayerKey): RiskRuleStatus[] =>
    status?.rules?.filter((r: RiskRuleStatus) => r.layer === layer) ?? []

  const renderLayerPanel = (layer: RiskLayerKey) => {
    const cfg = LAYER_CONFIG[layer]
    const rules = getLayerRules(layer)
    const blockedCount = rules.filter((r) => r.severity === 'BLOCK').length

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ color: cfg.color, fontWeight: 600, fontSize: 14 }}>{cfg.label}</span>
        <span style={{ color: '#8c8c8c', fontSize: 12 }}>{cfg.desc}</span>
        {blockedCount > 0 && <Tag color="error">{blockedCount} 条触发</Tag>}
        <Tag color={rules.every((r) => r.severity === 'PASS') ? 'success' : 'warning'}>
          {rules.length} 条规则
        </Tag>
      </div>
    )
  }

  return (
    <div className="risk-control-panel">
      {/* 总体状态卡片 */}
      <Card
        className="rcp-header-card"
        title={
          <Space>
            <SafetyOutlined />
            <span>风控状态总览</span>
            <Tag color={SEVERITY_TAG[overallStatus]?.color}>
              {SEVERITY_TAG[overallStatus]?.text}
            </Tag>
            {circuitBreaker && <Tag color="error">已熔断</Tag>}
          </Space>
        }
        extra={
          <Tooltip title="刷新风控状态">
            <Button
              size="small"
              icon={<ReloadOutlined spin={statusLoading} />}
              onClick={loadStatus}
            >
              刷新
            </Button>
          </Tooltip>
        }
        size="small"
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} md={6}>
            <Statistic title="规则总数" value={totalCount} suffix="条" />
          </Col>
          <Col xs={12} md={6}>
            <Statistic
              title="触发规则"
              value={triggeredCount}
              suffix="条"
              valueStyle={{ color: triggeredCount > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Col>
          <Col xs={12} md={6}>
            <Statistic
              title="通过率"
              value={totalCount > 0 ? ((totalCount - triggeredCount) / totalCount * 100).toFixed(1) : 100}
              suffix="%"
              valueStyle={{ color: triggeredCount === 0 ? '#52c41a' : '#faad14' }}
            />
          </Col>
          <Col xs={12} md={6}>
            <Statistic
              title="熔断状态"
              value={circuitBreaker ? '已触发' : '正常'}
              valueStyle={{ color: circuitBreaker ? '#ff4d4f' : '#52c41a' }}
            />
          </Col>
        </Row>
      </Card>

      {/* 按层级展示规则 */}
      {statusLoading && !status ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="加载风控数据..." />
        </div>
      ) : !status ? (
        <Empty description="风控数据未加载" />
      ) : (
        <div className="rcp-layers" style={{ marginTop: 16 }}>
          <Collapse defaultActiveKey={[1, 2, 3]} ghost>
            {([1, 2, 3] as RiskLayerKey[]).map((layer) => (
              <Collapse.Panel header={renderLayerPanel(layer)} key={layer}>
                {getLayerRules(layer).map((rule) => (
                  <div
                    key={rule.ruleId}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '8px 24px',
                      borderBottom: '1px solid #f0f0f0',
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, fontSize: 13 }}>{rule.ruleName}</div>
                      <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                        当前: {rule.currentValue.toFixed(2)} / 阈值: {rule.threshold.toFixed(2)}
                        {rule.message ? ` · ${rule.message}` : ''}
                      </div>
                    </div>
                    <Tag color={SEVERITY_TAG[rule.severity]?.color}>
                      {SEVERITY_TAG[rule.severity]?.text}
                    </Tag>
                  </div>
                ))}
              </Collapse.Panel>
            ))}
          </Collapse>
        </div>
      )}
    </div>
  )
}

export default RiskControlPanel
