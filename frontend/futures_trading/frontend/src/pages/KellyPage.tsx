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

const KellyPage: React.FC = () => {
  const [form] = Form.useForm()
  const { kellyResult, runKelly, kellyLoading } = useRiskStore()

  const handleCalculate = async () => {
    const values = await form.validateFields()
    await runKelly(values)
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <CalculatorOutlined style={{ marginRight: 8 }} />
        凯利公式计算器
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="参数输入" size="small">
            <Form form={form} layout="vertical">
              <Form.Item name="symbol" label="品种" rules={[{ required: true, message: '请输入品种代码' }]}>
                <Input style={{ width: '100%' }} placeholder="如: RU, AG, AU" />
              </Form.Item>
              <Form.Item name="winRate" label="胜率 (0-1)" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} max={1} step={0.01} precision={2} />
              </Form.Item>
              <Form.Item name="avgWin" label="平均盈利 (元)" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
              <Form.Item name="avgLoss" label="平均亏损 (元)" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
              <Form.Item name="capital" label="总资金 (元)" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
              <Form.Item name="fraction" label="凯利系数 (0-1, 默认0.5)">
                <InputNumber style={{ width: '100%' }} min={0} max={1} step={0.1} defaultValue={0.5} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" icon={<CalculatorOutlined />} loading={kellyLoading} onClick={handleCalculate}>
                  计算
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          {kellyResult ? (
            <Card title="计算结果" size="small">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Statistic title="f* (最优比例)" value={kellyResult.fStar} precision={4} suffix="%" valueStyle={{ color: '#1890ff' }} />
                </Col>
                <Col span={12}>
                  <Statistic title="建议仓位" value={kellyResult.suggestedPosition} precision={2} suffix="元" valueStyle={{ color: '#52c41a' }} />
                </Col>
                <Col span={12}>
                  <Statistic title="建议手数" value={kellyResult.suggestedLots} precision={1} suffix="手" />
                </Col>
                <Col span={12}>
                  <Statistic title="凯利系数" value={kellyResult.kellyFraction} precision={2} />
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
