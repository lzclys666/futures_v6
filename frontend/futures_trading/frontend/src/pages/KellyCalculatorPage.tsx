/**
 * 凯利公式计算器（纯前端版）
 * 公式：f* = (bp - q) / b
 *   b = 赔率（盈亏比），p = 胜率，q = 1 - p
 * @author Lucy
 * @date 2026-05-06
 */

import React, { useState, useCallback } from 'react'
import {
  Card,
  Form,
  InputNumber,
  Button,
  Statistic,
  Row,
  Col,
  Typography,
  Alert,
  Slider,
  Divider,
} from 'antd'
import { CalculatorOutlined, WarningOutlined, BulbOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

/** 计算结果 */
interface KellyResult {
  /** 凯利最优比例 f* */
  fStar: number
  /** 半凯利（安全仓位） */
  halfKelly: number
  /** 建议仓位金额 */
  suggestedAmount: number
  /** 建议手数（基于每手保证金） */
  suggestedLots: number
  /** 是否风险过高 */
  highRisk: boolean
}

/**
 * 凯利公式计算
 * f* = (b * p - q) / b
 * b = 赔率（盈亏比），p = 胜率，q = 1 - p
 */
function calcKelly(
  winRatePct: number,
  odds: number,
  fraction: number,
  capital: number,
  marginPerLot: number,
): KellyResult {
  const p = winRatePct / 100
  const q = 1 - p
  const b = odds

  // f* = (bp - q) / b
  const rawKelly = (b * p - q) / b

  // 限制在 [0, 1] 范围内
  const fStar = Math.max(0, Math.min(1, rawKelly))

  // 半凯利（fraction * f*）
  const halfKelly = fStar * fraction

  // 建议仓位金额
  const suggestedAmount = capital * halfKelly

  // 建议手数
  const suggestedLots = marginPerLot > 0 ? Math.floor(suggestedAmount / marginPerLot) : 0

  return {
    fStar,
    halfKelly,
    suggestedAmount,
    suggestedLots,
    highRisk: fStar > 0.2,
  }
}

const KellyCalculatorPage: React.FC = () => {
  const [form] = Form.useForm()
  const [result, setResult] = useState<KellyResult | null>(null)

  const handleCalculate = useCallback(() => {
    form.validateFields().then((values) => {
      const { winRate, odds, fraction = 0.5, capital, marginPerLot } = values
      const r = calcKelly(winRate, odds, fraction, capital, marginPerLot)
      setResult(r)
    })
  }, [form])

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <CalculatorOutlined style={{ marginRight: 8 }} />
        凯利公式计算器
      </Title>

      <Row gutter={[16, 16]}>
        {/* 左侧：参数输入 */}
        <Col xs={24} md={12}>
          <Card title="参数输入" size="small">
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                winRate: 50,
                odds: 2,
                fraction: 0.5,
                capital: 100000,
                marginPerLot: 10000,
              }}
            >
              <Form.Item
                name="winRate"
                label="胜率 (%)"
                rules={[
                  { required: true, message: '请输入胜率' },
                  {
                    validator: (_, v) =>
                      v >= 0 && v <= 100
                        ? Promise.resolve()
                        : Promise.reject('胜率必须在 0~100 之间'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={100}
                  step={1}
                  precision={1}
                  addonAfter="%"
                />
              </Form.Item>

              <Form.Item
                name="odds"
                label="赔率（盈亏比 b）"
                tooltip="平均盈利 / 平均亏损，如 2 表示盈亏比 2:1"
                rules={[
                  { required: true, message: '请输入赔率' },
                  {
                    validator: (_, v) =>
                      v > 0 ? Promise.resolve() : Promise.reject('赔率必须大于 0'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.01}
                  step={0.1}
                  precision={2}
                  placeholder="如 2 表示盈亏比 2:1"
                />
              </Form.Item>

              <Form.Item
                name="fraction"
                label="凯利系数"
                tooltip="0 = 不下注，0.5 = 半凯利（推荐），1 = 全凯利"
              >
                <Row gutter={12}>
                  <Col flex="auto">
                    <Slider
                      min={0}
                      max={1}
                      step={0.05}
                      marks={{
                        0: '0',
                        0.25: '0.25',
                        0.5: '0.5',
                        0.75: '0.75',
                        1: '1',
                      }}
                    />
                  </Col>
                  <Col>
                    <Form.Item name="fraction" noStyle>
                      <InputNumber
                        min={0}
                        max={1}
                        step={0.05}
                        precision={2}
                        style={{ width: 70 }}
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Form.Item>

              <Form.Item
                name="capital"
                label="账户总资金 (元)"
                rules={[
                  { required: true, message: '请输入总资金' },
                  {
                    validator: (_, v) =>
                      v > 0 ? Promise.resolve() : Promise.reject('总资金必须大于 0'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={1000}
                  precision={0}
                  formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(v) => Number(v?.replace(/,/g, '') ?? 0) as unknown as 0}
                />
              </Form.Item>

              <Form.Item
                name="marginPerLot"
                label="每手保证金 (元)"
                tooltip="用于计算建议手数"
                rules={[
                  { required: true, message: '请输入每手保证金' },
                  {
                    validator: (_, v) =>
                      v > 0 ? Promise.resolve() : Promise.reject('每手保证金必须大于 0'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={1000}
                  precision={0}
                  formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(v) => Number(v?.replace(/,/g, '') ?? 0) as unknown as 0}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  icon={<CalculatorOutlined />}
                  onClick={handleCalculate}
                  block
                >
                  计算
                </Button>
              </Form.Item>
            </Form>

            {/* 公式说明 */}
            <Divider dashed />
            <Text type="secondary" style={{ fontSize: 12 }}>
              公式：f* = (b × p − q) / b，其中 b=赔率，p=胜率，q=1−p
            </Text>
          </Card>
        </Col>

        {/* 右侧：计算结果 */}
        <Col xs={24} md={12}>
          {result ? (
            <>
              {/* 风险提示 */}
              {result.highRisk && (
                <Alert
                  message="风险过高"
                  description={
                    <span>
                      f* = <Text code>{(result.fStar * 100).toFixed(2)}%</Text>，超过 20%，
                      建议使用半凯利或更低系数控制风险。
                    </span>
                  }
                  type="warning"
                  icon={<WarningOutlined />}
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              {/* 推荐操作卡片 */}
              <Card
                size="small"
                style={{
                  background: result.highRisk ? '#fffbe6' : '#f6ffed',
                  border: `1px solid ${result.highRisk ? '#ffe58f' : '#b7eb8f'}`,
                  marginBottom: 16,
                }}
              >
                <Row align="middle" gutter={8}>
                  <Col>
                    <BulbOutlined
                      style={{ color: result.highRisk ? '#faad14' : '#52c41a', fontSize: 20 }}
                    />
                  </Col>
                  <Col flex="auto">
                    <Text strong style={{ color: result.highRisk ? '#d48806' : '#389e0d' }}>
                      推荐操作
                    </Text>
                    <div style={{ marginTop: 4 }}>
                      最优仓位{' '}
                      <Text code>{(result.fStar * 100).toFixed(2)}%</Text>
                      {' → '}
                      建议使用{' '}
                      <Text code>{(result.halfKelly * 100).toFixed(2)}%</Text>
                      {' '}资金，约{' '}
                      <Text code>{result.suggestedLots}</Text> 手
                    </div>
                  </Col>
                </Row>
              </Card>

              {/* 数值指标 */}
              <Card title="计算结果" size="small">
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Statistic
                      title="f*（最优比例）"
                      value={result.fStar * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: '#1890ff', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="安全仓位（半凯利）"
                      value={result.halfKelly * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: '#52c41a', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="建议金额"
                      value={result.suggestedAmount}
                      precision={0}
                      prefix="¥"
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="建议手数"
                      value={result.suggestedLots}
                      precision={0}
                      suffix="手"
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                </Row>

                {/* 仓位可视化条 */}
                <div style={{ marginTop: 20 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>仓位分布</Text>
                  <div
                    style={{
                      marginTop: 8,
                      position: 'relative',
                      height: 32,
                      background: '#f0f0f0',
                      borderRadius: 4,
                    }}
                  >
                    {/* 刻度 */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '0 4px',
                        height: '100%',
                        alignItems: 'center',
                      }}
                    >
                      {[0, 25, 50, 75, 100].map((pct) => (
                        <span key={pct} style={{ fontSize: 10, color: '#999' }}>{pct}%</span>
                      ))}
                    </div>

                    {/* f* 指针 */}
                    {(() => {
                      const pct = Math.min(result.fStar * 100, 100)
                      return (
                        <div
                          style={{
                            position: 'absolute',
                            left: `${pct}%`,
                            top: -8,
                            bottom: -8,
                            width: 3,
                            background: '#52c41a',
                            borderRadius: 2,
                            zIndex: 2,
                          }}
                        >
                          <span
                            style={{
                              position: 'absolute',
                              top: -16,
                              left: '50%',
                              transform: 'translateX(-50%)',
                              fontSize: 10,
                              color: '#52c41a',
                              whiteSpace: 'nowrap',
                              fontWeight: 600,
                            }}
                          >
                            f* {pct.toFixed(1)}%
                          </span>
                        </div>
                      )
                    })()}

                    {/* 安全仓位指针 */}
                    {(() => {
                      const pct = Math.min(result.halfKelly * 100, 100)
                      return (
                        <div
                          style={{
                            position: 'absolute',
                            left: `${pct}%`,
                            top: -8,
                            bottom: -8,
                            width: 3,
                            background: '#1890ff',
                            borderRadius: 2,
                            zIndex: 2,
                          }}
                        >
                          <span
                            style={{
                              position: 'absolute',
                              bottom: -16,
                              left: '50%',
                              transform: 'translateX(-50%)',
                              fontSize: 10,
                              color: '#1890ff',
                              whiteSpace: 'nowrap',
                              fontWeight: 600,
                            }}
                          >
                            安全 {pct.toFixed(1)}%
                          </span>
                        </div>
                      )
                    })()}
                  </div>
                  <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
                    <Text style={{ fontSize: 11, color: '#52c41a' }}>■ f* 最优比例</Text>
                    <Text style={{ fontSize: 11, color: '#1890ff' }}>■ 安全仓位</Text>
                  </div>
                </div>
              </Card>
            </>
          ) : (
            <Card size="small">
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <CalculatorOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                <div style={{ marginTop: 16 }}>
                  <Text type="secondary">输入参数并点击「计算」查看结果</Text>
                </div>
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default KellyCalculatorPage
