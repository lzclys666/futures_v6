/**
 * 下单面板
 * @date 2026-04-24
 */

import React, { useState } from 'react'
import { Card, Form, Select, InputNumber, Radio, Button, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import type { OrderDirection, PriceType } from '../../types/macro'
import { placeOrder } from '../../api/trading'

const SYMBOL_OPTIONS = [
  { value: 'RU', label: '橡胶 (RU)' },
  { value: 'CU', label: '铜 (CU)' },
  { value: 'AU', label: '黄金 (AU)' },
  { value: 'AG', label: '白银 (AG)' },
  { value: 'RB', label: '螺纹钢 (RB)' },
  { value: 'TA', label: 'PTA (TA)' },
]

interface OrderFormValues {
  symbol: string
  direction: OrderDirection
  lots: number
  price_type: PriceType
  price?: number | null
}

const OrderPanel: React.FC = () => {
  const [form] = Form.useForm<OrderFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const [priceType, setPriceType] = useState<PriceType>('market')

  const handleSubmit = async (values: OrderFormValues) => {
    setSubmitting(true)
    try {
      const req = {
        symbol: values.symbol,
        direction: values.direction,
        lots: values.lots,
        price_type: values.price_type,
        price: values.price_type === 'market' ? null : values.price ?? null,
      }
      await placeOrder(req)
      message.success('下单成功')
      form.resetFields(['lots', 'price'])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '下单失败'
      message.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card title="下单" size="small" style={{ marginBottom: 16 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          symbol: 'RU',
          direction: 'BUY',
          lots: 1,
          price_type: 'market',
        }}
      >
        <Form.Item
          name="symbol"
          label="品种"
          rules={[{ required: true, message: '请选择品种' }]}
        >
          <Select options={SYMBOL_OPTIONS} />
        </Form.Item>

        <Form.Item
          name="direction"
          label="方向"
          rules={[{ required: true }]}
        >
          <Radio.Group>
            <Radio.Button value="BUY">买入</Radio.Button>
            <Radio.Button value="SELL">卖出</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          name="lots"
          label="手数"
          rules={[{ required: true, min: 1, type: 'number', message: '手数至少为1' }]}
        >
          <InputNumber min={1} max={9999} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="price_type"
          label="价格类型"
          rules={[{ required: true }]}
        >
          <Radio.Group onChange={(e) => setPriceType(e.target.value)}>
            <Radio.Button value="market">市价</Radio.Button>
            <Radio.Button value="limit">限价</Radio.Button>
            <Radio.Button value="stop">止损</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {priceType === 'limit' && (
          <Form.Item
            name="price"
            label="委托价格"
            rules={[{ required: true, message: '请输入委托价格' }]}
          >
            <InputNumber min={0} step={1} style={{ width: '100%' }} />
          </Form.Item>
        )}

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            icon={<SendOutlined />}
            loading={submitting}
            block
          >
            提交订单
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}

export default OrderPanel
