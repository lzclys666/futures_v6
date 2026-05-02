/**
 * 持仓看板页面
 * 整合 VNpy 持仓数据 + 一键平仓
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useEffect } from 'react'
import { Card, Table, Tag, Button, Statistic, Row, Col, Typography, Empty } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { TableOutlined, CloseCircleOutlined, WalletOutlined } from '@ant-design/icons'
import { useVnpyStore } from '../store/useVnpyStore'
import type { VnpyPosition } from '../types/vnpy'

const { Title, Text } = Typography

const PositionPage: React.FC = () => {
  const { positions, account, loadPositions, loadAccount, startPolling, stopPolling } = useVnpyStore()

  useEffect(() => {
    loadPositions()
    loadAccount()
    startPolling(5000)
    return () => stopPolling()
  }, [])

  const totalPnl = positions.reduce((sum: number, p: VnpyPosition) => sum + (p.unrealizedPnl ?? 0), 0)
  const longCount = positions.filter((p: VnpyPosition) => p.direction === 'LONG').length
  const shortCount = positions.filter((p: VnpyPosition) => p.direction === 'SHORT').length

  const columns: ColumnsType<VnpyPosition> = [
    { title: '品种', dataIndex: 'symbol', key: 'symbol', fixed: 'left' },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      render: (v: string) => (
        <Tag color={v === 'LONG' ? 'green' : 'red'}>{v === 'LONG' ? '多' : '空'}</Tag>
      ),
    },
    { title: '总持仓', dataIndex: 'volume', key: 'volume', align: 'right' },
    { title: '昨仓', dataIndex: 'ydVolume', key: 'ydVolume', align: 'right' },
    { title: '今仓', dataIndex: 'tdVolume', key: 'tdVolume', align: 'right' },
    { title: '可平', dataIndex: 'available', key: 'available', align: 'right' },
    {
      title: '开仓均价',
      dataIndex: 'avgPrice',
      key: 'avgPrice',
      align: 'right',
      render: (v: number) => v?.toFixed(2),
    },
    {
      title: '当前价',
      dataIndex: 'lastPrice',
      key: 'lastPrice',
      align: 'right',
      render: (v: number) => v?.toFixed(2),
    },
    {
      title: '浮动盈亏',
      dataIndex: 'unrealizedPnl',
      key: 'unrealizedPnl',
      align: 'right',
      render: (v: number) => (
        <Text style={{ color: (v ?? 0) >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {v != null ? `${v > 0 ? '+' : ''}${v.toFixed(0)}` : '--'}
        </Text>
      ),
    },
    {
      title: '盈亏率',
      dataIndex: 'pnlRate',
      key: 'pnlRate',
      align: 'right',
      render: (v: number) => (
        <Text style={{ color: (v ?? 0) >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {v != null ? `${(v * 100).toFixed(2)}%` : '--'}
        </Text>
      ),
    },
    {
      title: '保证金',
      dataIndex: 'margin',
      key: 'margin',
      align: 'right',
      render: (v: number) => v?.toFixed(0),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      render: (_, record) => (
        <Button
          size="small"
          danger
          icon={<CloseCircleOutlined />}
          onClick={() => {
            // TODO: 调用平仓 API
            console.log('平仓', record.symbol, record.direction)
          }}
        >
          平仓
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <TableOutlined style={{ marginRight: 8 }} />
        持仓看板
      </Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="总浮动盈亏" value={totalPnl} precision={0} prefix={<WalletOutlined />} suffix="元" valueStyle={{ color: totalPnl >= 0 ? '#52c41a' : '#ff4d4f' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="多头持仓" value={longCount} suffix="品种" valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="空头持仓" value={shortCount} suffix="品种" valueStyle={{ color: '#ff4d4f' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="可用资金" value={account?.available ?? 0} precision={2} suffix="元" valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
      </Row>

      {/* 持仓表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={positions}
          rowKey={(r) => `${r.symbol}-${r.direction}`}
          pagination={false}
          scroll={{ x: 1200 }}
          locale={{ emptyText: <Empty description="暂无持仓" /> }}
        />
      </Card>
    </div>
  )
}

export default PositionPage
