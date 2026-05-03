import React, { useState, useEffect, useCallback } from 'react'
import {
  Card, Form, Select, InputNumber, Button, Table, Tag, Space,
  Row, Col, message, Empty, Statistic, Badge, Divider
} from 'antd'
import {
  SendOutlined, CloseOutlined, ReloadOutlined,
  RiseOutlined, FallOutlined, ThunderboltOutlined, CheckCircleOutlined,
  InboxOutlined, SwapOutlined, SafetyOutlined
} from '@ant-design/icons'
import RiskControlPanel from '../risk/RiskControlPanel'
import { useRiskStore } from '../../store/useRiskStore'
import './TradingPanel.css'

// ==================== Types ====================

interface OrderRequest {
  vt_symbol: string
  direction: 'LONG' | 'SHORT'
  offset: 'OPEN' | 'CLOSE' | 'CLOSETODAY' | 'CLOSEYESTERDAY'
  volume: number
  price: number
  order_type: 'LIMIT' | 'MARKET'
}

interface ActiveOrder {
  vt_orderid: string
  symbol: string
  direction: string
  offset: string
  price: number
  volume: number
  traded: number
  status: string
  order_time: string
}

interface TradeRecord {
  trade_id: string
  symbol: string
  direction: string
  offset: string
  price: number
  volume: number
  trade_time: string
}

interface Position {
  symbol: string
  direction: string
  volume: number
  price: number
  pnl: number
}

// ==================== Constants ====================

const SYMBOLS = [
  { value: 'RU2505.SHFE', label: 'RU 橡胶2505' },
  { value: 'ZN2505.SHFE', label: 'ZN 锌2505' },
  { value: 'RB2510.SHFE', label: 'RB 螺纹2510' },
  { value: 'NI2505.SHFE', label: 'NI 镍2505' },
  { value: 'AG2506.SHFE', label: 'AG 白银2506' },
  { value: 'AU2506.SHFE', label: 'AU 黄金2506' },
  { value: 'SC2506.SHFE', label: 'SC 原油2506' },
  { value: 'FG2509.SHFE', label: 'FG 玻璃2509' },
]

// ==================== Helpers ====================

/** 从 ApiResponse 中提取 data 字段 */
async function fetchApiData<T>(url: string): Promise<T> {
  const res = await fetch(url)
  const json = await res.json()
  // 格式1: { code: 0, data: ... }
  if (json.code === 0 && json.data !== undefined) return json.data as T
  // 格式2: 纯数组
  if (Array.isArray(json)) return json as T
  // 格式3: { status: 'success', data: ... }（有 data 字段则解包）
  if (json.data) return json.data as T
  // 格式4: { status: 'success', orders: [...], trades: [...], positions: [...] } 等
  //         无 data 字段，整体返回（组件自行提取子字段）
  return json as T
}

// ==================== Component ====================

const TradingPanel: React.FC = () => {
  const [form] = Form.useForm<OrderRequest>()
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [orders, setOrders] = useState<ActiveOrder[]>([])
  const [trades, setTrades] = useState<TradeRecord[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [engineStatus, setEngineStatus] = useState<'unknown' | 'running' | 'stopped'>('unknown')
  const [selectedSymbol, setSelectedSymbol] = useState('RU2505.SHFE')
  void selectedSymbol

  // ─── Risk Store ───
  const { precheckOrder, precheckResult, precheckLoading } = useRiskStore()

  // ─── Fetch Functions ───

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [ordersData, tradesData, posData, statusData] = await Promise.allSettled([
        fetchApiData<any[]>('/api/trading/orders'),
        fetchApiData<any[]>('/api/trading/trades'),
        fetchApiData<any>('/api/trading/positions'),
        fetchApiData<any>('/api/vnpy/status'),
      ])

      if (ordersData.status === 'fulfilled') {
        const raw = (ordersData.value as any)?.orders ?? ((Array.isArray(ordersData.value) ? ordersData.value : []) || [])
        setOrders(raw.map((o: any, i: number) => ({
          vt_orderid: o.vt_orderid || o.order_id || `order-${i}`,
          symbol: (o.vt_symbol || o.symbol || '').split('.')[0],
          direction: o.direction || '-',
          offset: o.offset || '-',
          price: o.price || 0,
          volume: o.volume || 0,
          traded: o.traded || o.traded_volume || 0,
          status: o.status || 'unknown',
          order_time: o.order_time || o.datetime || '-',
        })))
      }

      if (tradesData.status === 'fulfilled') {
        const raw = (tradesData.value as any)?.trades ?? ((Array.isArray(tradesData.value) ? tradesData.value : []) || [])
        setTrades(raw.map((t: any, i: number) => ({
          trade_id: t.trade_id || t.vt_tradeid || `trade-${i}`,
          symbol: (t.vt_symbol || t.symbol || '').split('.')[0],
          direction: t.direction || '-',
          offset: t.offset || '-',
          price: t.price || 0,
          volume: t.volume || 0,
          trade_time: t.trade_time || t.datetime || '-',
        })))
      }

      if (posData.status === 'fulfilled') {
        const data = posData.value
        if (data && data.positions) {
          setPositions(data.positions.map((p: any) => ({
            symbol: p.symbol || '-',
            direction: p.direction || '-',
            volume: p.lots || p.volume || 0,
            price: p.entry_price || p.price || 0,
            pnl: p.unrealized_pnl || p.pnl || 0,
          })))
        } else {
          setPositions([])
        }
      }

      // 从状态数据推断引擎状态
      if (statusData.status === 'fulfilled' && statusData.value) {
        setEngineStatus(statusData.value.status === 'running' ? 'running' : 'stopped')
      } else {
        setEngineStatus('stopped')
      }
    } catch (e) {
      message.error('获取交易数据失败')
      setEngineStatus('stopped')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const timer = setInterval(fetchAll, 5000)
    return () => clearInterval(timer)
  }, [fetchAll])

  // ─── Submit Order ───

  /** 提取品种代码（去掉交易所后缀，如 RU2505.SHFE → RU2505） */
  const extractSymbol = (vtSymbol: string) =>
    vtSymbol.replace(/\.(SHFE|DCE|CZCE|CFFEX|MFEX)$/, '')

  const handleSubmit = async (values: OrderRequest) => {
    // Step 1：风控预检
    const symbol = extractSymbol(values.vt_symbol)
    const passed = await precheckOrder({
      symbol,
      direction: values.direction,
      price: values.price,
      volume: values.volume,
    })
    if (!passed) {
      const violations = precheckResult?.violations ?? []
      if (violations.length > 0) {
        const msgs = violations.map((v) => v.message).join('；')
        message.error({ content: `⛔ 风控拦截：${msgs}`, duration: 5 })
      } else {
        message.error('⛔ 风控预检未通过，订单被拦截')
      }
      return
    }

    // Step 2：实际下单
    setSubmitting(true)
    try {
      const res = await fetch('/api/trading/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vt_symbol: values.vt_symbol,
          direction: values.direction,
          offset: values.offset,
          price: values.price,
          volume: values.volume,
        }),
      })
      const json = await res.json()
      if (json.code === 0 && json.data?.vt_orderid) {
        message.success(`✅ 下单成功: ${json.data.vt_orderid}`)
        form.resetFields()
        fetchAll()
      } else {
        message.error(json.message || '下单失败')
      }
    } catch (e) {
      message.error('下单请求失败')
    } finally {
      setSubmitting(false)
    }
  }

  // ─── Cancel Order ───

  const handleCancel = async (vtOrderId: string) => {
    try {
      const res = await fetch(`/api/trading/order/${vtOrderId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const json = await res.json()
      if (json.success || json.code === 0) {
        message.success('撤单成功')
        fetchAll()
      } else {
        message.error(json.message || '撤单失败')
      }
    } catch (e) {
      message.error('撤单请求失败')
    }
  }

  // ─── Columns ───

  const orderColumns = [
    { title: '订单号', dataIndex: 'vt_orderid', key: 'vt_orderid', width: 180 },
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 80 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (v: string) => (
        <Tag color={v === 'LONG' ? 'red' : v === 'SHORT' ? 'green' : 'default'}>
          {v === 'LONG' ? '多' : v === 'SHORT' ? '空' : v}
        </Tag>
      ),
    },
    { title: '开平', dataIndex: 'offset', key: 'offset', width: 80 },
    { title: '价格', dataIndex: 'price', key: 'price', width: 100 },
    { title: '数量', dataIndex: 'volume', key: 'volume', width: 80 },
    { title: '成交', dataIndex: 'traded', key: 'traded', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => {
        const color = v === '全部成交' ? 'success' : v === '未成交' ? 'processing' : v === '已撤单' ? 'default' : 'warning'
        return <Tag color={color}>{v}</Tag>
      },
    },
    { title: '时间', dataIndex: 'order_time', key: 'order_time', width: 160 },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: any, record: ActiveOrder) => (
        <Button
          size="small"
          danger
          icon={<CloseOutlined />}
          onClick={() => handleCancel(record.vt_orderid)}
          disabled={record.status === '已撤单' || record.status === '全部成交'}
        >
          撤
        </Button>
      ),
    },
  ]

  const tradeColumns = [
    { title: '成交号', dataIndex: 'trade_id', key: 'trade_id', width: 180 },
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 80 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (v: string) => (
        <Tag color={v === 'LONG' ? 'red' : v === 'SHORT' ? 'green' : 'default'}>
          {v === 'LONG' ? '多' : v === 'SHORT' ? '空' : v}
        </Tag>
      ),
    },
    { title: '开平', dataIndex: 'offset', key: 'offset', width: 80 },
    { title: '价格', dataIndex: 'price', key: 'price', width: 100 },
    { title: '数量', dataIndex: 'volume', key: 'volume', width: 80 },
    { title: '时间', dataIndex: 'trade_time', key: 'trade_time', width: 160 },
  ]

  const posColumns = [
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 100 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (v: string) => (
        <Tag color={v === 'LONG' ? 'red' : v === 'SHORT' ? 'green' : 'default'}>
          {v === 'LONG' ? '多' : v === 'SHORT' ? '空' : v}
        </Tag>
      ),
    },
    { title: '手数', dataIndex: 'volume', key: 'volume', width: 80 },
    { title: '均价', dataIndex: 'price', key: 'price', width: 100 },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 120,
      render: (v: number) => (
        <span style={{ color: (v || 0) >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {v >= 0 ? '+' : ''}{v?.toFixed(2)}
        </span>
      ),
    },
  ]

  // ─── Render ───

  return (
    <div className="trading-panel">
      {/* Header */}
      <div className="trading-header">
        <div className="trading-title">
          <SwapOutlined className="trading-title-icon" />
          <span>交易下单</span>
          <Badge
            status={engineStatus === 'running' ? 'success' : engineStatus === 'stopped' ? 'error' : 'default'}
            text={engineStatus === 'running' ? '引擎运行中' : engineStatus === 'stopped' ? '引擎未连接' : '状态未知'}
          />
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAll} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      <Row gutter={16}>
        {/* Order Form */}
        <Col span={8}>
          <Card title={<><SendOutlined /> 下单</>} className="trading-form-card">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{
                vt_symbol: 'RU2505.SHFE',
                direction: 'LONG',
                offset: 'OPEN',
                volume: 1,
                price: 0,
                order_type: 'LIMIT',
              }}
            >
              <Form.Item
                name="vt_symbol"
                label="品种"
                rules={[{ required: true }]}
              >
                <Select
                  options={SYMBOLS}
                  onChange={setSelectedSymbol}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>

              <Form.Item
                name="direction"
                label="方向"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { value: 'LONG', label: <><RiseOutlined /> 做多</> },
                    { value: 'SHORT', label: <><FallOutlined /> 做空</> },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name="offset"
                label="开平"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { value: 'OPEN', label: '开仓' },
                    { value: 'CLOSE', label: '平仓' },
                    { value: 'CLOSETODAY', label: '平今' },
                    { value: 'CLOSEYESTERDAY', label: '平昨' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name="volume"
                label="手数"
                rules={[{ required: true, type: 'number', min: 1, message: '手数须为≥1的整数' }]}
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="price"
                label="价格"
                rules={[{ required: true, type: 'number', message: '请输入有效价格' }]}
              >
                <InputNumber
                  min={0}
                  step={1}
                  style={{ width: '100%' }}
                  placeholder="限价单价格"
                />
              </Form.Item>

              <Form.Item
                name="order_type"
                label="类型"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { value: 'LIMIT', label: '限价单' },
                    { value: 'MARKET', label: '市价单' },
                  ]}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SendOutlined />}
                  loading={submitting || precheckLoading}
                  block
                  size="large"
                >
                  下单
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        {/* 风控状态面板 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <SafetyOutlined style={{ marginRight: 6, color: '#1890ff' }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>风控状态</span>
        </div>
        <RiskControlPanel />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Data Panels */}
        <Col span={16}>
          <Row gutter={[0, 16]}>
            {/* Positions */}
            <Col span={24}>
              <Card
                title={<><InboxOutlined /> 持仓 ({positions.length})</>}
                className="trading-data-card"
                extra={
                  <Space>
                    <Statistic
                      value={positions.reduce((s, p) => s + (p.pnl || 0), 0)}
                      precision={2}
                      prefix="总盈亏:"
                      valueStyle={{
                        fontSize: 14,
                        color: positions.reduce((s, p) => s + (p.pnl || 0), 0) >= 0 ? '#52c41a' : '#ff4d4f',
                      }}
                    />
                  </Space>
                }
              >
                {positions.length > 0 ? (
                  <Table
                    dataSource={positions}
                    columns={posColumns}
                    rowKey="symbol"
                    size="small"
                    pagination={false}
                    scroll={{ x: 500 }}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无持仓" />
                )}
              </Card>
            </Col>

            {/* Active Orders */}
            <Col span={24}>
              <Card
                title={<><ThunderboltOutlined /> 活动订单 ({orders.filter(o => o.status !== '已撤单' && o.status !== '全部成交').length})</>}
                className="trading-data-card"
              >
                {orders.length > 0 ? (
                  <Table
                    dataSource={orders}
                    columns={orderColumns}
                    rowKey="vt_orderid"
                    size="small"
                    pagination={{ pageSize: 5, size: 'small' }}
                    scroll={{ x: 900 }}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无订单" />
                )}
              </Card>
            </Col>

            {/* Trades */}
            <Col span={24}>
              <Card
                title={<><CheckCircleOutlined /> 今日成交 ({trades.length})</>}
                className="trading-data-card"
              >
                {trades.length > 0 ? (
                  <Table
                    dataSource={trades}
                    columns={tradeColumns}
                    rowKey="trade_id"
                    size="small"
                    pagination={{ pageSize: 5, size: 'small' }}
                    scroll={{ x: 700 }}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无成交" />
                )}
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>
    </div>
  )
}

export default TradingPanel
