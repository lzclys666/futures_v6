/**
 * 月度报告导出页面
 * 生成并导出交易月度报告（PDF / CSV）
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useState } from 'react'
import { Card, Typography, Row, Col, Form, Select, Button, Table, Tag, Space, Statistic, message } from 'antd'
import { FilePdfOutlined, FileExcelOutlined, CalendarOutlined, RiseOutlined } from '@ant-design/icons'

const { Title } = Typography

interface TradeRecord {
  date: string
  symbol: string
  direction: 'LONG' | 'SHORT'
  volume: number
  pnl: number
  cumulative: number
}

interface DailySummary {
  date: string
  trades: number
  pnl: number
  winRate: number
  positions: number
}

const mockTradeRecords: TradeRecord[] = [
  { date: '2026-04-01', symbol: 'RU2501', direction: 'LONG', volume: 2, pnl: 3200, cumulative: 3200 },
  { date: '2026-04-03', symbol: 'AG2502', direction: 'SHORT', volume: 3, pnl: -1500, cumulative: 1700 },
  { date: '2026-04-07', symbol: 'AU2506', direction: 'LONG', volume: 1, pnl: 5800, cumulative: 7500 },
  { date: '2026-04-10', symbol: 'RB2501', direction: 'SHORT', volume: 5, pnl: 2100, cumulative: 9600 },
  { date: '2026-04-14', symbol: 'RU2501', direction: 'SHORT', volume: 2, pnl: -800, cumulative: 8800 },
  { date: '2026-04-17', symbol: 'AG2502', direction: 'LONG', volume: 3, pnl: 4200, cumulative: 13000 },
  { date: '2026-04-21', symbol: 'AU2506', direction: 'LONG', volume: 2, pnl: -2200, cumulative: 10800 },
  { date: '2026-04-24', symbol: 'RB2501', direction: 'SHORT', volume: 4, pnl: 3600, cumulative: 14400 },
]

const mockDailySummary: DailySummary[] = [
  { date: '2026-04-01', trades: 1, pnl: 3200, winRate: 100, positions: 1 },
  { date: '2026-04-03', trades: 1, pnl: -1500, winRate: 0, positions: 1 },
  { date: '2026-04-07', trades: 1, pnl: 5800, winRate: 100, positions: 2 },
  { date: '2026-04-10', trades: 1, pnl: 2100, winRate: 100, positions: 1 },
  { date: '2026-04-14', trades: 1, pnl: -800, winRate: 0, positions: 1 },
  { date: '2026-04-17', trades: 1, pnl: 4200, winRate: 100, positions: 2 },
  { date: '2026-04-21', trades: 1, pnl: -2200, winRate: 0, positions: 1 },
  { date: '2026-04-24', trades: 1, pnl: 3600, winRate: 100, positions: 2 },
]

const ReportPage: React.FC = () => {
  const [form] = Form.useForm()
  const [exporting, setExporting] = useState(false)
  const [_month] = useState('2026-04')

  const totalPnl = mockTradeRecords.reduce((sum, t) => sum + t.pnl, 0)
  const winTrades = mockTradeRecords.filter((t) => t.pnl > 0).length
  const totalTrades = mockTradeRecords.length
  const winRate = (winTrades / totalTrades) * 100

  const tradeColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '品种',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 100,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (v: string) => <Tag color={v === 'LONG' ? 'success' : 'error'}>{v === 'LONG' ? '多' : '空'}</Tag>,
    },
    { title: '手数', dataIndex: 'volume', key: 'volume', width: 70 },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 100,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v >= 0 ? '+' : ''}{v.toLocaleString()}
        </span>
      ),
    },
    {
      title: '累计收益',
      dataIndex: 'cumulative',
      key: 'cumulative',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v >= 0 ? '+' : ''}{v.toLocaleString()}
        </span>
      ),
    },
  ]

  const dailyColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '交易次数', dataIndex: 'trades', key: 'trades', width: 90 },
    {
      title: '日盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 120,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v >= 0 ? '+' : ''}{v.toLocaleString()}
        </span>
      ),
    },
    {
      title: '胜率',
      dataIndex: 'winRate',
      key: 'winRate',
      width: 90,
      render: (v: number) => <span style={{ color: v >= 50 ? '#52c41a' : '#ff4d4f' }}>{v}%</span>,
    },
    { title: '持仓数', dataIndex: 'positions', key: 'positions', width: 80 },
  ]

  const handleExportPdf = async () => {
    setExporting(true)
    await new Promise((r) => setTimeout(r, 1500))
    message.success('PDF 报告已生成并下载')
    setExporting(false)
  }

  const handleExportCsv = async () => {
    setExporting(true)
    await new Promise((r) => setTimeout(r, 800))
    message.success('CSV 数据已导出')
    setExporting(false)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <CalendarOutlined style={{ marginRight: 8 }} />
          月度报告导出
        </Title>
        <Space>
          <Button
            icon={<FilePdfOutlined />}
            onClick={handleExportPdf}
            loading={exporting}
          >
            导出 PDF
          </Button>
          <Button
            icon={<FileExcelOutlined />}
            onClick={handleExportCsv}
            loading={exporting}
          >
            导出 CSV
          </Button>
        </Space>
      </div>

      <Form
        form={form}
        layout="inline"
        initialValues={{ month: '2026-04', symbol: '全部' }}
        style={{ marginBottom: 16 }}
      >
        <Form.Item name="month" label="报告月份">
          <Select style={{ width: 140 }} options={[
            { value: '2026-04', label: '2026年4月' },
            { value: '2026-03', label: '2026年3月' },
            { value: '2026-02', label: '2026年2月' },
          ]} />
        </Form.Item>
        <Form.Item name="symbol" label="品种">
          <Select style={{ width: 120 }} options={[
            { value: '全部', label: '全部品种' },
            { value: 'RU', label: '橡胶 RU' },
            { value: 'AG', label: '白银 AG' },
            { value: 'AU', label: '黄金 AU' },
            { value: 'RB', label: '螺纹钢 RB' },
          ]} />
        </Form.Item>
      </Form>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic
              title="月度收益"
              value={totalPnl}
              precision={0}
              suffix="元"
              prefix={<RiseOutlined />}
              valueStyle={{ color: totalPnl >= 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic
              title="总交易次数"
              value={totalTrades}
              suffix="次"
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic
              title="胜率"
              value={winRate}
              precision={1}
              suffix="%"
              valueStyle={{ color: winRate >= 50 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic
              title="盈利交易"
              value={winTrades}
              suffix={`/ ${totalTrades}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="交易明细">
            <Table
              columns={tradeColumns}
              dataSource={mockTradeRecords}
              rowKey="date"
              size="small"
              pagination={false}
              scroll={{ x: 600 }}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="每日汇总">
            <Table
              columns={dailyColumns}
              dataSource={mockDailySummary}
              rowKey="date"
              size="small"
              pagination={false}
              scroll={{ x: 500 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ReportPage
