/**
 * 持仓看板组件
 * @date 2026-04-24
 */
import React, { useEffect, useRef } from 'react'
import { Table, Tag, Statistic, Row, Col, Card, Space, Badge, Tooltip, Spin } from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  SafetyCertificateOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useTradingStore } from '../../store/tradingStore'
import type { PositionItem } from '../../types/macro'
import type { RiskRuleStatus } from '../../types/risk'
import './PositionBoard.css'

/** 方向 → Tag 颜色 */
const DIR_COLOR: Record<string, string> = {
  LONG: 'green',
  SHORT: 'red',
  NEUTRAL: 'default',
}

/** 方向 → 中文 */
const DIR_LABEL: Record<string, string> = {
  LONG: '多',
  SHORT: '空',
  NEUTRAL: '平',
}

/** 风控状态 → Badge 状态 */
const RISK_STATUS_MAP: Record<string, 'success' | 'warning' | 'error'> = {
  'PASS': 'success',
  'WARN': 'warning',
  'BLOCK': 'error',
}

const PositionBoard: React.FC = () => {
  const {
    portfolio, portfolioLoading, loadPortfolio,
    riskStatus, riskLoading, loadRiskStatus,
    refreshInterval,
  } = useTradingStore()

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 初始加载 + 自动刷新
  useEffect(() => {
    loadPortfolio()
    loadRiskStatus()
    if (refreshInterval > 0) {
      timerRef.current = setInterval(() => {
        loadPortfolio()
        loadRiskStatus()
      }, refreshInterval)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [refreshInterval])

  // --- 持仓表格列 ---
  const positionColumns: ColumnsType<PositionItem> = [
    {
      title: '品种',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 80,
      render: (v: string) => <span style={{ fontWeight: 600 }}>{v}</span>,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 70,
      render: (v: string) => <Tag color={DIR_COLOR[v]}>{DIR_LABEL[v] || v}</Tag>,
    },
    {
      title: '手数',
      dataIndex: 'lots',
      key: 'lots',
      width: 70,
      align: 'right',
    },
    {
      title: '开仓价',
      dataIndex: 'entry_price',
      key: 'entry_price',
      width: 100,
      align: 'right',
      render: (v: number | null) => v != null ? v.toLocaleString() : '-',
    },
    {
      title: '当前价',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 100,
      align: 'right',
      render: (v: number | null) => v != null ? v.toLocaleString() : '-',
    },
    {
      title: '浮动盈亏',
      dataIndex: 'unrealized_pnl',
      key: 'unrealized_pnl',
      width: 120,
      align: 'right',
      render: (v: number | null) => {
        if (v == null) return '-'
        const color = v > 0 ? '#52c41a' : v < 0 ? '#ff4d4f' : '#999'
        const icon = v > 0 ? <ArrowUpOutlined /> : v < 0 ? <ArrowDownOutlined /> : null
        return (
          <span style={{ color, fontWeight: 600 }}>
            {icon} {v > 0 ? '+' : ''}{v.toLocaleString()}
          </span>
        )
      },
    },
    {
      title: '持仓占比',
      dataIndex: 'position_pct',
      key: 'position_pct',
      width: 90,
      align: 'right',
      render: (v: number) => `${v.toFixed(1)}%`,
    },
  ]

  // --- 风控表格列 ---
  const riskColumns: ColumnsType<RiskRuleStatus> = [
    { title: '层级', dataIndex: 'layer', key: 'layer', width: 60 },
    { title: '规则', dataIndex: 'ruleName', key: 'ruleName', width: 140 },
    {
      title: '状态',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (v: string) => <Badge status={RISK_STATUS_MAP[v]} text={v} />,
    },
    { title: '当前值', dataIndex: 'currentValue', key: 'currentValue', width: 100, align: 'right' },
    { title: '阈值', dataIndex: 'threshold', key: 'threshold', width: 100, align: 'right' },
  ]

  return (
    <div className="position-board">
      {/* 顶部汇总 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={4}>
          <Card size="small">
            <Statistic
              title="总资金"
              value={portfolio?.totalEquity ?? 0}
              precision={0}
              prefix="¥"
            />
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small">
            <Statistic
              title="可用资金"
              value={portfolio?.availableFunds ?? 0}
              precision={0}
              prefix="¥"
              valueStyle={{
                color:
                  (portfolio?.availableFunds ?? 0) <= 0
                    ? '#ff4d4f'
                    : (portfolio?.availableFunds ?? 0) < (portfolio?.totalEquity ?? 1) * 0.1
                      ? '#faad14'
                      : '#52c41a',
              }}
            />
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small">
            <Statistic
              title="冻结保证金"
              value={portfolio?.usedMargin ?? 0}
              precision={0}
              prefix="¥"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small">
            <Statistic
              title="当日盈亏"
              value={portfolio?.dailyPnl ?? 0}
              precision={0}
              valueStyle={{
                color: (portfolio?.dailyPnl ?? 0) >= 0 ? '#52c41a' : '#ff4d4f',
              }}
              prefix={(portfolio?.dailyPnl ?? 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small">
            <Statistic
              title="当日收益率"
              value={(portfolio?.dailyReturn ?? 0) * 100}
              precision={2}
              suffix="%"
              valueStyle={{
                color: (portfolio?.dailyReturn ?? 0) >= 0 ? '#52c41a' : '#ff4d4f',
              }}
            />
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small">
            <Statistic
              title="持仓占比"
              value={portfolio?.totalPositionPct ?? 0}
              precision={1}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 持仓明细 */}
      <Card
        title="持仓明细"
        size="small"
        extra={
          <Tooltip title="刷新">
            <ReloadOutlined
              onClick={() => { loadPortfolio(); loadRiskStatus() }}
              spin={portfolioLoading}
              style={{ cursor: 'pointer' }}
            />
          </Tooltip>
        }
        style={{ marginBottom: 16 }}
      >
        <Spin spinning={portfolioLoading}>
          <Table<PositionItem>
            columns={positionColumns}
            dataSource={portfolio?.positions ?? []}
            rowKey="symbol"
            size="small"
            pagination={false}
            locale={{ emptyText: '暂无持仓' }}
          />
        </Spin>
      </Card>

      {/* 风控状态 */}
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>风控状态</span>
            {riskStatus && (
              <Badge
                status={RISK_STATUS_MAP[riskStatus.overallStatus]}
                text={riskStatus.overallStatus}
              />
            )}
          </Space>
        }
        size="small"
      >
        <Spin spinning={riskLoading}>
          <Table<RiskRuleStatus>
            columns={riskColumns}
            dataSource={riskStatus?.rules ?? []}
            rowKey="ruleId"
            size="small"
            pagination={false}
            locale={{ emptyText: '暂无风控数据' }}
          />
        </Spin>
      </Card>
    </div>
  )
}

export default PositionBoard
