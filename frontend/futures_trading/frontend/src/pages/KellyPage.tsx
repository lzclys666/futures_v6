/**
 * 凯利公式计算器
 * @author Lucy
 * @date 2026-04-27
 */

import React from 'react'
import { Card, Form, Input, InputNumber, Button, Statistic, Row, Col, Typography, Alert } from 'antd'
import { CalculatorOutlined, BulbOutlined } from '@ant-design/icons'
import { useRiskStore } from '../store/useRiskStore'

const { Title, Text } = Typography

interface KellyFormValues {
  symbol: string
  winRate: number
  avgWin: number
  avgLoss: number
  capital: number
  fraction?: number
}

const KellyPage: React.FC = () => {
  const [form] = Form.useForm<KellyFormValues>()
  const { kellyResult, runKelly, kellyLoading } = useRiskStore()

  const handleCalculate = async () => {
    const values = await form.validateFields()
    await runKelly(values as Parameters<typeof runKelly>[0])
  }

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
            <Form form={form} layout="vertical">
              <Form.Item name="symbol" label="品种" rules={[{ required: true, message: '请输入品种代码' }]}>
                <Input style={{ width: '100%' }} placeholder="如: RU, AG, AU" />
              </Form.Item>

              <Form.Item
                name="winRate"
                label="胜率 (0-1)"
                rules={[
                  { required: true, message: '请输入胜率' },
                  {
                    validator: (_, value) =>
                      value >= 0 && value <= 1 ? Promise.resolve() : Promise.reject('胜率必须在 0~1 之间'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={1}
                  step={0.01}
                  precision={4}
                  placeholder="0.5"
                />
              </Form.Item>

              <Form.Item
                name="avgWin"
                label="平均盈利 (元)"
                rules={[
                  { required: true, message: '请输入平均盈利' },
                  {
                    validator: (_, value) =>
                      value > 0 ? Promise.resolve() : Promise.reject('平均盈利必须大于 0'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={0.01}
                  precision={2}
                />
              </Form.Item>

              <Form.Item
                name="avgLoss"
                label="平均亏损 (元)"
                rules={[
                  { required: true, message: '请输入平均亏损' },
                  {
                    validator: (_, value) =>
                      value > 0 ? Promise.resolve() : Promise.reject('平均亏损必须大于 0'),
                  },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      const avgWin = getFieldValue('avgWin')
                      if (avgWin != null && value != null && avgWin <= value) {
                        return Promise.reject(new Error('平均盈利必须大于平均亏损'))
                      }
                      return Promise.resolve()
                    },
                  }),
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={0.01}
                  precision={2}
                />
              </Form.Item>

              <Form.Item
                name="capital"
                label="总资金 (元)"
                rules={[
                  { required: true, message: '请输入总资金' },
                  {
                    validator: (_, value) =>
                      value > 0 ? Promise.resolve() : Promise.reject('总资金必须大于 0'),
                  },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={100}
                  precision={2}
                />
              </Form.Item>

              <Form.Item name="fraction" label="凯利系数 (0-1, 默认0.5)">
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={1}
                  step={0.1}
                  precision={3}
                  placeholder="0.5"
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  icon={<CalculatorOutlined />}
                  loading={kellyLoading}
                  onClick={handleCalculate}
                >
                  计算
                </Button>
              </Form.Item>
            </Form>

            {/* 迷你柱状图：Kelly 可视化 */}
            {kellyResult && (
              <div style={{ marginTop: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  仓位分布图
                </Text>
                <div
                  style={{
                    marginTop: 8,
                    position: 'relative',
                    height: 32,
                    background: '#f0f0f0',
                    borderRadius: 4,
                    overflow: 'visible',
                  }}
                >
                  {/* 背景刻度 */}
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
                      <span key={pct} style={{ fontSize: 10, color: '#999', position: 'relative' }}>
                        {pct}%
                      </span>
                    ))}
                  </div>

                  {/* fStar 位置（绿色竖线） */}
                  {(() => {
                    const fStarPct = Math.min(kellyResult.fStar * 100, 100)
                    return (
                      <div
                        title={`f* = ${(kellyResult.fStar * 100).toFixed(2)}%`}
                        style={{
                          position: 'absolute',
                          left: `${fStarPct}%`,
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
                          f* {fStarPct.toFixed(1)}%
                        </span>
                      </div>
                    )
                  })()}

                  {/* 安全仓位 fStar*0.5（蓝色竖线） */}
                  {(() => {
                    const safePct = Math.min(kellyResult.fStar * 50, 100)
                    return (
                      <div
                        title={`安全仓位 = ${safePct.toFixed(2)}%`}
                        style={{
                          position: 'absolute',
                          left: `${safePct}%`,
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
                          安全 {safePct.toFixed(1)}%
                        </span>
                      </div>
                    )
                  })()}
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
                  <Text style={{ fontSize: 11, color: '#52c41a' }}>■ f* 最优比例</Text>
                  <Text style={{ fontSize: 11, color: '#1890ff' }}>■ 安全仓位 (50%f*)</Text>
                </div>
              </div>
            )}
          </Card>
        </Col>

        {/* 右侧：计算结果 */}
        <Col xs={24} md={12}>
          {kellyLoading ? (
            <Card title="计算结果" size="small">
              <div
                style={{
                  height: 200,
                  borderRadius: 4,
                  animation: 'skeleton-pulse 1.5s ease-in-out infinite',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <style>{`
                  @keyframes skeleton-pulse {
                    0% { background: #f5f5f5; }
                    50% { background: #e8e8e8; }
                    100% { background: #f5f5f5; }
                  }
                `}</style>
              </div>
            </Card>
          ) : kellyResult ? (
            <>
              {/* 推荐操作卡片（绿色背景） */}
              <Card
                size="small"
                style={{ background: '#f6ffed', border: '1px solid #b7eb8f', marginBottom: 16 }}
              >
                <Row align="middle" gutter={8}>
                  <Col>
                    <BulbOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                  </Col>
                  <Col>
                    <Text strong style={{ color: '#389e0d', fontSize: 14 }}>
                      推荐操作
                    </Text>
                    <div style={{ marginTop: 4 }}>
                      f* = <Text code>{(kellyResult.fStar * 100).toFixed(2)}%</Text>
                      {' '}建议仓位{' '}
                      <Text code>{(kellyResult.suggestedPosition * 100).toFixed(2)}%</Text>
                      {' '}({kellyResult.suggestedLots}手)
                    </div>
                  </Col>
                </Row>
              </Card>

              {/* 结果卡片 */}
              <Card title="计算结果" size="small">
                <Row gutter={[16, 16]}>
                  <Col xs={12} md={12}>
                    <Statistic
                      title="f* (最优比例)"
                      value={kellyResult.fStar * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: '#1890ff', fontSize: 20 }}
                    />
                  </Col>
                  <Col xs={12} md={12}>
                    <Statistic
                      title="建议仓位"
                      value={kellyResult.suggestedPosition * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: '#52c41a', fontSize: 20 }}
                    />
                  </Col>
                  <Col xs={12} md={12}>
                    <Statistic
                      title="建议手数"
                      value={kellyResult.suggestedLots}
                      precision={1}
                      suffix="手"
                      valueStyle={{ fontSize: 20 }}
                    />
                  </Col>
                  <Col xs={12} md={12}>
                    <Statistic
                      title="凯利系数"
                      value={kellyResult.kellyFraction}
                      precision={3}
                      valueStyle={{ fontSize: 20 }}
                    />
                  </Col>
                </Row>

                <Alert
                  message="解读"
                  description={kellyResult.interpretation}
                  type="info"
                  icon={<BulbOutlined />}
                  style={{ marginTop: 16 }}
                />
              </Card>
            </>
          ) : (
            <Card size="small">
              <Text type="secondary">输入参数并点击「计算」查看结果</Text>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default KellyPage
