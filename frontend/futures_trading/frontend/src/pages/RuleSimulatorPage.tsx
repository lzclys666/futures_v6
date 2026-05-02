/**
 * 风控规则模拟器
 * 模拟不同参数组合下风控规则的表现
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useState } from 'react'
import { Card, Typography, Row, Col, Form, InputNumber, Button, Table, Tag, Alert } from 'antd'
import { ExperimentOutlined, SafetyOutlined, ThunderboltOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

/** 模拟结果 */
interface SimResult {
  ruleId: string
  ruleName: string
  triggered: boolean
  currentValue: number
  threshold: number
  marginUsed: number
  message: string
}

/** 风控规则模板 */
const RULE_TEMPLATES: Array<{ ruleId: string; name: string; unit: string; defaultThreshold: number }> = [
  { ruleId: 'R1_SINGLE_SYMBOL', name: '单品种仓位上限', unit: '%', defaultThreshold: 30 },
  { ruleId: 'R2_DAILY_LOSS', name: '日内最大亏损', unit: '元', defaultThreshold: 50000 },
  { ruleId: 'R3_TOTAL_POSITION', name: '总仓位上限', unit: '%', defaultThreshold: 80 },
  { ruleId: 'R4_MARGIN_RATIO', name: '保证金比例上限', unit: '%', defaultThreshold: 30 },
  { ruleId: 'R5_VOLATILITY', name: '波动率阈值', unit: '%', defaultThreshold: 5 },
  { ruleId: 'R6_LEVERAGE', name: '杠杆倍数上限', unit: 'x', defaultThreshold: 5 },
  { ruleId: 'R7_CORRELATION', name: '品种相关性上限', unit: '', defaultThreshold: 0.8 },
  { ruleId: 'R8_CONCENTRATION', name: '集中度上限', unit: '%', defaultThreshold: 50 },
  { ruleId: 'R9_LIQUIDITY', name: '流动性阈值', unit: '万元', defaultThreshold: 100 },
  { ruleId: 'R10_DRAWDOWN', name: '最大回撤', unit: '%', defaultThreshold: 15 },
  { ruleId: 'R11_MACRO_REGIME', name: '宏观 Regime 切换', unit: '', defaultThreshold: 1 },
]

const RuleSimulatorPage: React.FC = () => {
  const [form] = Form.useForm()
  const [results, setResults] = useState<SimResult[]>([])
  const [loading, setLoading] = useState(false)
  const [_enableAll, _setEnableAll] = useState(true)

  /** 持仓参数 */
  const [positionParams, setPositionParams] = useState({
    totalMargin: 150000,
    totalCapital: 1000000,
    dailyPnl: -32000,
    leverage: 3.5,
    volatility: 0.038,
  })

  const handleSimulate = async () => {
    setLoading(true)
    await new Promise((r) => setTimeout(r, 600))

    const simResults: SimResult[] = RULE_TEMPLATES.map((tmpl) => {
      let triggered = false
      let currentValue = 0
      let message = ''

      switch (tmpl.ruleId) {
        case 'R1_SINGLE_SYMBOL':
          currentValue = 32.5
          triggered = currentValue > positionParams.totalMargin / positionParams.totalCapital * 100 * 0.3
          message = triggered ? `单品种橡胶仓位 32.5% 超过阈值 30%` : `单品种仓位正常`
          break
        case 'R2_DAILY_LOSS':
          currentValue = Math.abs(positionParams.dailyPnl)
          triggered = currentValue > 50000
          message = triggered ? `日内亏损 ¥${currentValue.toLocaleString()} 触发熔断` : `日内亏损在容忍范围内`
          break
        case 'R3_TOTAL_POSITION':
          currentValue = (positionParams.totalMargin / positionParams.totalCapital) * 100
          triggered = currentValue > 80
          message = triggered ? `总仓位 ${currentValue.toFixed(1)}% 超过上限 80%` : `总仓位 ${currentValue.toFixed(1)}% 正常`
          break
        case 'R4_MARGIN_RATIO':
          currentValue = (positionParams.totalMargin / positionParams.totalCapital) * 100
          triggered = currentValue > 30
          message = triggered ? `保证金比例 ${currentValue.toFixed(1)}% 超过上限 30%` : `保证金比例正常`
          break
        case 'R5_VOLATILITY':
          currentValue = positionParams.volatility * 100
          triggered = currentValue > 5
          message = triggered ? `波动率 ${currentValue.toFixed(2)}% 接近阈值 5%` : `波动率正常`
          break
        case 'R6_LEVERAGE':
          currentValue = positionParams.leverage
          triggered = currentValue > 5
          message = triggered ? `杠杆 ${currentValue.toFixed(1)}x 超过上限 5x` : `杠杆正常`
          break
        case 'R7_CORRELATION':
          currentValue = 0.72
          triggered = currentValue > 0.8
          message = triggered ? `品种相关性 0.72 在安全范围内` : `品种相关性正常`
          break
        case 'R8_CONCENTRATION':
          currentValue = 48
          triggered = currentValue > 50
          message = triggered ? `集中度 48% 低于上限 50%` : `集中度正常`
          break
        case 'R9_LIQUIDITY':
          currentValue = 85
          triggered = currentValue < 100
          message = triggered ? `流动性 85 万低于阈值 100 万` : `流动性正常`
          break
        case 'R10_DRAWDOWN':
          currentValue = 12.5
          triggered = currentValue > 15
          message = triggered ? `最大回撤 12.5% 在容忍范围 15% 内` : `回撤正常`
          break
        case 'R11_MACRO_REGIME':
          currentValue = 0
          triggered = false
          message = `当前 Regime: 宽松，顺势策略正常`
          break
      }

      return {
        ruleId: tmpl.ruleId,
        ruleName: tmpl.name,
        triggered,
        currentValue,
        threshold: tmpl.defaultThreshold,
        marginUsed: (currentValue / tmpl.defaultThreshold) * 100,
        message,
      }
    })

    setResults(simResults)
    setLoading(false)
  }

  const columns = [
    {
      title: '规则',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 180,
    },
    {
      title: '状态',
      dataIndex: 'triggered',
      key: 'triggered',
      width: 90,
      render: (v: boolean) => (
        <Tag color={v ? 'error' : 'success'}>{v ? '触发' : '通过'}</Tag>
      ),
    },
    {
      title: '当前值',
      dataIndex: 'currentValue',
      key: 'currentValue',
      width: 110,
      render: (v: number, row: SimResult) => {
        const template = RULE_TEMPLATES.find((t) => t.ruleId === row.ruleId)
        const unit = template?.unit || ''
        const prefix = typeof v === 'number' && v < 0 ? '' : ''
        return (
          <span style={{ color: row.triggered ? '#ff4d4f' : '#52c41a', fontWeight: 500 }}>
            {prefix}{typeof v === 'number' ? v.toFixed(2) : v}{unit}
          </span>
        )
      },
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      width: 90,
      render: (v: number, row: SimResult) => {
        const template = RULE_TEMPLATES.find((t) => t.ruleId === row.ruleId)
        const unit = template?.unit || ''
        return <span style={{ color: '#8c8c8c' }}>{v}{unit}</span>
      },
    },
    {
      title: '使用率',
      dataIndex: 'marginUsed',
      key: 'marginUsed',
      width: 160,
      render: (v: number) => {
        const color = v > 100 ? '#ff4d4f' : v > 80 ? '#faad14' : '#52c41a'
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3 }}>
              <div style={{ width: `${Math.min(v, 100)}%`, height: '100%', background: color, borderRadius: 3 }} />
            </div>
            <span style={{ fontSize: 12, color, minWidth: 40 }}>{v.toFixed(0)}%</span>
          </div>
        )
      },
    },
    {
      title: '说明',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
  ]

  const triggeredCount = results.filter((r) => r.triggered).length

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <ExperimentOutlined style={{ marginRight: 8 }} />
        风控规则模拟器
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card title="模拟参数" size="small">
            <Form form={form} layout="vertical">
              <Form.Item label="总保证金 (元)">
                <InputNumber
                  style={{ width: '100%' }}
                  value={positionParams.totalMargin}
                  onChange={(v) => setPositionParams({ ...positionParams, totalMargin: v || 0 })}
                  min={0}
                  step={10000}
                />
              </Form.Item>
              <Form.Item label="总资金 (元)">
                <InputNumber
                  style={{ width: '100%' }}
                  value={positionParams.totalCapital}
                  onChange={(v) => setPositionParams({ ...positionParams, totalCapital: v || 0 })}
                  min={0}
                  step={100000}
                />
              </Form.Item>
              <Form.Item label="日内盈亏 (元)">
                <InputNumber
                  style={{ width: '100%' }}
                  value={positionParams.dailyPnl}
                  onChange={(v) => setPositionParams({ ...positionParams, dailyPnl: v || 0 })}
                  step={1000}
                />
              </Form.Item>
              <Form.Item label="杠杆倍数">
                <InputNumber
                  style={{ width: '100%' }}
                  value={positionParams.leverage}
                  onChange={(v) => setPositionParams({ ...positionParams, leverage: v || 0 })}
                  min={0}
                  max={10}
                  step={0.5}
                />
              </Form.Item>
              <Form.Item label="波动率 (%)">
                <InputNumber
                  style={{ width: '100%' }}
                  value={parseFloat((positionParams.volatility * 100).toFixed(2))}
                  onChange={(v) => setPositionParams({ ...positionParams, volatility: (v || 0) / 100 })}
                  min={0}
                  max={20}
                  step={0.1}
                />
              </Form.Item>
              <Form.Item>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  loading={loading}
                  onClick={handleSimulate}
                  block
                >
                  执行模拟
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} md={16}>
          {results.length > 0 && (
            <Card
              size="small"
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <SafetyOutlined />
                  <span>模拟结果</span>
                  <Tag color={triggeredCount === 0 ? 'success' : triggeredCount < 3 ? 'warning' : 'error'}>
                    {triggeredCount === 0 ? '全部通过' : `${triggeredCount} 条触发`}
                  </Tag>
                </div>
              }
            >
              {triggeredCount > 0 && (
                <Alert
                  message="风控预警"
                  description={`当前参数下有 ${triggeredCount} 条规则触发风控，请调整参数后重试。`}
                  type="warning"
                  showIcon
                  style={{ marginBottom: 12 }}
                />
              )}
              <Table
                columns={columns}
                dataSource={results}
                rowKey="ruleId"
                size="small"
                pagination={false}
              />
            </Card>
          )}

          {results.length === 0 && (
            <Card size="small" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text type="secondary">填写参数后点击「执行模拟」查看结果</Text>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default RuleSimulatorPage
