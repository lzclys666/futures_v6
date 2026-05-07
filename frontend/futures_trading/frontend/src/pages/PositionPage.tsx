/**
 * 持仓看板 v2 — 账户总览 + 持仓列表 + 按品种分组
 * @author Lucy
 * @date 2026-05-06
 * 
 * 数据来源：useVnpyStore → api/vnpy.ts（USE_MOCK 开关控制）
 * 后端就绪后只需将 api/vnpy.ts 的 USE_MOCK 改为 false
 */

import React, { useEffect, useMemo, useState, useCallback } from 'react'
import { Card, Table, Tag, Button, Statistic, Row, Col, Typography, Empty, Progress, Space, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  TableOutlined,
  CloseCircleOutlined,
  WalletOutlined,
  RiseOutlined,
  FallOutlined,
  SafetyOutlined,
  FundOutlined,
  PercentageOutlined,
} from '@ant-design/icons'
import { useVnpyStore } from '../store/useVnpyStore'
import type { VnpyPosition } from '../types/vnpy'
import { assessAllPositions } from '../utils/dispositionEffect'
import type { PositionRiskAssessment } from '../utils/dispositionEffect'
import DispositionAlert from '../components/DispositionAlert'

const { Title, Text } = Typography

/** 品种中文名映射 */
const SYMBOL_NAMES: Record<string, string> = {
  RU: '橡胶',
  AG: '白银',
  AU: '黄金',
  CU: '铜',
  RB: '螺纹钢',
  AL: '铝',
  ZN: '锌',
  NI: '镍',
  I: '铁矿石',
  J: '焦炭',
  JM: '焦煤',
  TA: 'PTA',
  MA: '甲醇',
  SC: '原油',
  FU: '燃油',
}

/** 从合约代码提取品种名（去掉数字） */
function getSymbolName(symbol: string): string {
  const base = symbol.replace(/\d+$/, '')
  return SYMBOL_NAMES[base] || base
}

/** 格式化金额 */
function formatMoney(v: number): string {
  if (Math.abs(v) >= 10000) {
    return `${(v / 10000).toFixed(2)}万`
  }
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

/** 盈亏颜色 — 红涨绿跌（A 股惯例） */
function pnlColor(v: number | null | undefined): string {
  if (v == null) return '#999'
  return v > 0 ? '#ff4d4f' : v < 0 ? '#52c41a' : '#999'
}

const PositionPage: React.FC = () => {
  const { positions, account, loadPositions, loadAccount, startPolling, stopPolling } = useVnpyStore()

  // ---- 处置效应检测 ----
  const [alertOpen, setAlertOpen] = useState(false)
  const [currentAssessment, setCurrentAssessment] = useState<PositionRiskAssessment | null>(null)
  const [dismissedSymbols, setDismissedSymbols] = useState<Set<string>>(new Set())

  /** 检测所有持仓的处置效应风险 */
  const riskAlerts = useMemo(() => {
    return assessAllPositions(positions).filter((a) => !dismissedSymbols.has(a.symbol))
  }, [positions, dismissedSymbols])

  /** 当有新的高风险告警时自动弹窗（取优先级最高的一条） */
  useEffect(() => {
    if (riskAlerts.length > 0 && !alertOpen) {
      setCurrentAssessment(riskAlerts[0])
      setAlertOpen(true)
    }
  }, [riskAlerts])

  const handleFollowAction = useCallback((assessment: PositionRiskAssessment) => {
    setAlertOpen(false)
    // TODO: 接入平仓 API，调用 suggestedAction
    console.log('处置效应建议操作:', assessment.symbol, assessment.suggestedAction)
  }, [])

  const handleDismiss = useCallback(() => {
    setAlertOpen(false)
  }, [])

  const handleNeverRemind = useCallback((symbol: string) => {
    setDismissedSymbols((prev) => new Set(prev).add(symbol))
    setAlertOpen(false)
  }, [])

  useEffect(() => {
    loadPositions()
    loadAccount()
    startPolling(5000)
    return () => stopPolling()
  }, [])

  // ---- 聚合计算 ----
  const totalPnl = useMemo(
    () => positions.reduce((s, p) => s + (p.unrealizedPnl ?? 0), 0),
    [positions],
  )
  const totalMargin = useMemo(
    () => positions.reduce((s, p) => s + (p.margin ?? 0), 0),
    [positions],
  )
  const longPositions = useMemo(() => positions.filter((p) => p.direction === 'LONG'), [positions])
  const shortPositions = useMemo(() => positions.filter((p) => p.direction === 'SHORT'), [positions])
  const riskRatio = account && account.balance > 0
    ? ((totalMargin / account.balance) * 100)
    : 0

  // ---- 表格列定义 ----
  const columns: ColumnsType<VnpyPosition> = [
    {
      title: '品种',
      dataIndex: 'symbol',
      key: 'symbol',
      fixed: 'left',
      width: 120,
      render: (v: string) => (
        <Space>
          <Text strong>{v}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{getSymbolName(v)}</Text>
        </Space>
      ),
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 70,
      filters: [
        { text: '多头', value: 'LONG' },
        { text: '空头', value: 'SHORT' },
      ],
      onFilter: (value, record) => record.direction === value,
      render: (v: string) => (
        <Tag color={v === 'LONG' ? '#ff4d4f' : '#52c41a'} style={{ fontWeight: 600 }}>
          {v === 'LONG' ? '多' : '空'}
        </Tag>
      ),
    },
    {
      title: '数量',
      key: 'volume',
      align: 'right',
      width: 130,
      render: (_, r) => (
        <Tooltip title={`昨仓 ${r.ydVolume} / 今仓 ${r.tdVolume}`}>
          <Text>{r.volume}手</Text>
        </Tooltip>
      ),
    },
    {
      title: '成本价',
      dataIndex: 'avgPrice',
      key: 'avgPrice',
      align: 'right',
      width: 100,
      render: (v: number) => v?.toFixed(2) ?? '--',
    },
    {
      title: '现价',
      dataIndex: 'lastPrice',
      key: 'lastPrice',
      align: 'right',
      width: 100,
      render: (v: number, r) => {
        const diff = r.lastPrice - r.avgPrice
        const color = r.direction === 'LONG'
          ? (diff >= 0 ? '#ff4d4f' : '#52c41a')
          : (diff <= 0 ? '#ff4d4f' : '#52c41a')
        return <Text style={{ color }}>{v?.toFixed(2) ?? '--'}</Text>
      },
    },
    {
      title: '浮动盈亏',
      dataIndex: 'unrealizedPnl',
      key: 'unrealizedPnl',
      align: 'right',
      width: 110,
      sorter: (a, b) => (a.unrealizedPnl ?? 0) - (b.unrealizedPnl ?? 0),
      render: (v: number) => (
        <Text strong style={{ color: pnlColor(v) }}>
          {v != null ? `${v > 0 ? '+' : ''}${v.toLocaleString('zh-CN')}` : '--'}
        </Text>
      ),
    },
    {
      title: '盈亏率',
      dataIndex: 'pnlRate',
      key: 'pnlRate',
      align: 'right',
      width: 90,
      sorter: (a, b) => (a.pnlRate ?? 0) - (b.pnlRate ?? 0),
      render: (v: number) => (
        <Text style={{ color: pnlColor(v) }}>
          {v != null ? `${(v * 100).toFixed(2)}%` : '--'}
        </Text>
      ),
    },
    {
      title: '保证金',
      dataIndex: 'margin',
      key: 'margin',
      align: 'right',
      width: 110,
      render: (v: number) => v?.toLocaleString('zh-CN') ?? '--',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 80,
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
      {/* 处置效应告警弹窗 */}
      <DispositionAlert
        open={alertOpen}
        assessment={currentAssessment}
        onFollowAction={handleFollowAction}
        onDismiss={handleDismiss}
        onNeverRemind={handleNeverRemind}
      />
      <Title level={4} style={{ marginBottom: 16 }}>
        <TableOutlined style={{ marginRight: 8 }} />
        持仓看板
      </Title>

      {/* ── 账户总览 ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" hoverable>
            <Statistic
              title="总权益"
              value={account?.balance ?? 0}
              precision={0}
              prefix={<FundOutlined />}
              suffix="元"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" hoverable>
            <Statistic
              title="可用资金"
              value={account?.available ?? 0}
              precision={0}
              prefix={<WalletOutlined />}
              suffix="元"
              valueStyle={{ fontSize: 18, color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" hoverable>
            <Statistic
              title="持仓盈亏"
              value={totalPnl}
              precision={0}
              prefix={totalPnl >= 0 ? <RiseOutlined /> : <FallOutlined />}
              suffix="元"
              valueStyle={{ fontSize: 18, color: pnlColor(totalPnl) }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" hoverable>
            <Statistic
              title="保证金占用"
              value={totalMargin}
              precision={0}
              prefix={<SafetyOutlined />}
              suffix="元"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" hoverable>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 13 }}>
                <PercentageOutlined style={{ marginRight: 4 }} />
                风险度
              </Text>
            </div>
            <Progress
              percent={Number(riskRatio.toFixed(1))}
              size="small"
              status={riskRatio > 80 ? 'exception' : riskRatio > 60 ? 'active' : 'normal'}
              strokeColor={riskRatio > 80 ? '#ff4d4f' : riskRatio > 60 ? '#faad14' : '#1890ff'}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {formatMoney(totalMargin)} / {formatMoney(account?.balance ?? 0)}
            </Text>
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" hoverable>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 13 }}>持仓分布</Text>
            </div>
            <Space>
              <Tag color="#ff4d4f">多 {longPositions.length}</Tag>
              <Tag color="#52c41a">空 {shortPositions.length}</Tag>
            </Space>
            <div style={{ marginTop: 4 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                共 {positions.length} 个品种
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* ── 持仓列表 ── */}
      <Card>
        <Table
          columns={columns}
          dataSource={positions}
          rowKey={(r) => `${r.symbol}-${r.direction}`}
          pagination={false}
          scroll={{ x: 960 }}
          size="middle"
          locale={{ emptyText: <Empty description="暂无持仓" /> }}
          rowClassName={(r) =>
            r.unrealizedPnl != null && r.unrealizedPnl < 0 ? 'row-loss' : ''
          }
          summary={() =>
            positions.length > 0 ? (
              <Table.Summary fixed>
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={5}>
                    <Text strong>合计</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1} align="right">
                    <Text strong style={{ color: pnlColor(totalPnl) }}>
                      {totalPnl > 0 ? '+' : ''}{totalPnl.toLocaleString('zh-CN')}
                    </Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={2} />
                  <Table.Summary.Cell index={3} align="right">
                    <Text strong>{totalMargin.toLocaleString('zh-CN')}</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4} />
                </Table.Summary.Row>
              </Table.Summary>
            ) : null
          }
        />
      </Card>
    </div>
  )
}

export default PositionPage
