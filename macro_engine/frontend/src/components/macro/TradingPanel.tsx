/**
 * 交易面板组件
 * 展示：订单列表、成交记录、风控状态、下单表单
 * @date 2026-04-24
 */
import React, { useEffect, useState } from 'react'
import {
  Card, Table, Tag,
  Statistic, Row, Col, Alert, Badge, Tabs, Descriptions
} from 'antd'
import {
  ShoppingCartOutlined,
  HistoryOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useTradingStore } from '../../store/tradingStore'
import { fetchOrders, fetchTrades } from '../../api/trading'
import type { Order, Trade } from '../../types/macro'
import OrderPanel from '../trading/OrderPanel'

/** 订单状态 → 颜色 */
const ORDER_STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  submitted: 'processing',
  partial_filled: 'warning',
  filled: 'success',
  cancelled: 'default',
  rejected: 'error',
}

/** 方向 → 颜色 */
const DIR_COLOR: Record<string, string> = {
  BUY: 'green',
  SELL: 'red',
}

const TradingPanel: React.FC = () => {
  const { riskStatus, loadPortfolio, loadRiskStatus } = useTradingStore()
  const [orders, setOrders] = useState<Order[]>([])
  const [trades, setTrades] = useState<Trade[]>([])

  // 加载订单和成交
  const loadOrders = async () => {
    try {
      const data = await fetchOrders()
      setOrders(data)
    } catch (e) {
      console.error('加载订单失败:', e)
    }
  }

  const loadTrades = async () => {
    try {
      const data = await fetchTrades()
      setTrades(data)
    } catch (e) {
      console.error('加载成交失败:', e)
    }
  }

  useEffect(() => {
    loadOrders()
    loadTrades()
    const timer = setInterval(() => {
      loadOrders()
      loadTrades()
      loadPortfolio()
      loadRiskStatus()
    }, 10000)
    return () => clearInterval(timer)
  }, [])

  // 订单列定义
  const orderColumns: ColumnsType<Order> = [
    { title: '订单ID', dataIndex: 'id', key: 'id', width: 120 },
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 80 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (v: string) => (
        <Tag color={DIR_COLOR[v]}>{v === 'BUY' ? '买入' : '卖出'}</Tag>
      ),
    },
    { title: '手数', dataIndex: 'lots', key: 'lots', width: 70 },
    {
      title: '价格',
      key: 'price',
      width: 100,
      render: (_, r) => (r.price ? r.price.toFixed(2) : '市价'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => (
        <Badge status={ORDER_STATUS_COLOR[v] as any} text={v} />
      ),
    },
    { title: '成交', dataIndex: 'filled_lots', key: 'filled_lots', width: 70 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
  ]

  // 成交列定义
  const tradeColumns: ColumnsType<Trade> = [
    { title: '成交ID', dataIndex: 'id', key: 'id', width: 120 },
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 80 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (v: string) => (
        <Tag color={DIR_COLOR[v]}>{v === 'BUY' ? '买入' : '卖出'}</Tag>
      ),
    },
    { title: '手数', dataIndex: 'lots', key: 'lots', width: 70 },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (v: number) => v.toFixed(2),
    },
    { title: '时间', dataIndex: 'trade_time', key: 'trade_time', width: 160 },
    {
      title: '手续费',
      dataIndex: 'commission',
      key: 'commission',
      width: 100,
      render: (v: number) => v.toFixed(2),
    },
  ]

  const tabItems = [
    {
      key: 'orders',
      label: (
        <span>
          <ShoppingCartOutlined /> 订单 ({orders.length})
        </span>
      ),
      children: (
        <Table
          columns={orderColumns}
          dataSource={orders}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 800 }}
        />
      ),
    },
    {
      key: 'trades',
      label: (
        <span>
          <HistoryOutlined /> 成交 ({trades.length})
        </span>
      ),
      children: (
        <Table
          columns={tradeColumns}
          dataSource={trades}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 800 }}
        />
      ),
    },
    {
      key: 'risk',
      label: (
        <span>
          <SafetyCertificateOutlined /> 风控
        </span>
      ),
      children: riskStatus ? (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="总状态"
                  value={riskStatus.overall_status}
                  valueStyle={{
                    color: riskStatus.overall_status === '正常' ? '#3f8600' : '#cf1322',
                  }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="权益"
                  value={riskStatus.equity}
                  precision={2}
                  prefix="¥"
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="回撤"
                  value={riskStatus.drawdown * 100}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: riskStatus.drawdown < -0.1 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
          </Row>
          <Descriptions bordered size="small" column={2}>
            {riskStatus.levels.map((level) => (
              <Descriptions.Item
                key={level.level + level.name}
                label={
                  <Badge
                    status={level.status === '正常' ? 'success' : level.status === '告警' ? 'warning' : 'error'}
                    text={`${level.level} ${level.name}`}
                  />
                }
              >
                {level.value || '-'} / 阈值: {level.threshold || '-'}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </div>
      ) : (
        <Alert message="风控数据加载中..." type="info" />
      ),
    },
  ]

  return (
    <div>
      {/* 下单表单 */}
      <OrderPanel />

      {/* 标签页：订单/成交/风控 */}
      <Tabs items={tabItems} defaultActiveKey="orders" />
    </div>
  )
}

export default TradingPanel
