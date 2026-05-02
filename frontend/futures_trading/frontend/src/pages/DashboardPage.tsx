/**
 * 首页 Dashboard
 * 整合：账户快照 + 风控总览 + 信号摘要 + 持仓概览
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useEffect } from 'react'
import { Row, Col, Card, Statistic, Tag, Empty, Alert, Typography, Divider } from 'antd'
import {
  RiseOutlined,
  FallOutlined,
  WalletOutlined,
  DollarOutlined,
  SafetyCertificateOutlined,
  TableOutlined,
} from '@ant-design/icons'
import { useVnpyStore } from '../store/useVnpyStore'
import type { VnpyState } from '../store/useVnpyStore'
import { useRiskStore } from '../store/useRiskStore'
import { useMacroStore } from '../store/macroStore'
import CircuitBreakerPanel from '../components/risk/CircuitBreakerPanel'

const { Title, Text } = Typography

/** 颜色映射 */
const severityColor: Record<string, string> = {
  PASS: '#52c41a',
  LOW: '#1677ff',
  MEDIUM: '#faad14',
  HIGH: '#ff4d4f',
}

const DashboardPage: React.FC = () => {
  const { account, positions, loadAccount, loadPositions, startPolling, stopPolling } = useVnpyStore()
  const { status: riskStatus, loadStatus: loadRisk, startPolling: startRiskPolling, stopPolling: stopRiskPolling } = useRiskStore()
  const { allSignals, loadAllSignals } = useMacroStore()

  useEffect(() => {
    loadAccount()
    loadPositions()
    loadRisk()
    loadAllSignals()
    startPolling(5000)
    startRiskPolling(10000)
    return () => { stopPolling(); stopRiskPolling() }
  }, [])

  const isConnected = useVnpyStore((s: VnpyState) => s.status?.state === 'connected')
  const triggeredRules = riskStatus?.rules?.filter((r: { triggered: boolean }) => r.triggered) ?? []
  const overallOk = riskStatus?.overallStatus === 'PASS'

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        📊 交易仪表盘
      </Title>

      {!isConnected && (
        <Alert
          message="VNpy 未连接"
          description="交易网关未启动，数据为 Mock 模式。请启动 VNpy 以获取实时数据。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 第一行：账户概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="总资产"
              value={account?.balance ?? 0}
              precision={2}
              prefix={<WalletOutlined />}
              suffix="元"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="可用资金"
              value={account?.available ?? 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="浮动盈亏"
              value={account?.unrealizedPnl ?? 0}
              precision={2}
              prefix={(account?.unrealizedPnl ?? 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
              suffix="元"
              valueStyle={{ color: (account?.unrealizedPnl ?? 0) >= 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="保证金率"
              value={account?.marginRatio ?? 0}
              precision={1}
              suffix="%"
              valueStyle={{
                color: (account?.marginRatio ?? 0) > 80 ? '#ff4d4f'
                  : (account?.marginRatio ?? 0) > 60 ? '#faad14'
                  : '#52c41a',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 熔断器面板 */}
      <CircuitBreakerPanel />

      <Divider style={{ margin: '16px 0' }} />

      {/* 第二行：风控 + 信号 + 持仓 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card
            size="small"
            title={<span><SafetyCertificateOutlined style={{ marginRight: 8 }} />风控状态</span>}
            extra={
              <Tag color={overallOk ? 'success' : triggeredRules.length > 2 ? 'error' : 'warning'}>
                {overallOk ? '全部 PASS' : `${triggeredRules.length} 条触发`}
              </Tag>
            }
          >
            {riskStatus ? (
              <div>
                {riskStatus.rules.slice(0, 6).map((r: { ruleId: string; ruleName: string; severity: string }) => (
                  <div key={r.ruleId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <Text style={{ fontSize: 13 }}>{r.ruleName}</Text>
                    <Tag color={severityColor[r.severity]} style={{ margin: 0 }}>{r.severity}</Tag>
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="风控数据未加载" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Card
            size="small"
            title={<span><RiseOutlined style={{ marginRight: 8 }} />因子信号</span>}
          >
            {allSignals.length > 0 ? (
              <div>
                {allSignals.map((s: { symbol: string; compositeScore: number; direction: string }) => (
                  <div key={s.symbol} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <Text strong style={{ fontSize: 14 }}>{s.symbol}</Text>
                    <div>
                      <Text style={{ fontSize: 14, marginRight: 8 }}>{s.compositeScore.toFixed(3)}</Text>
                      <Tag color={s.direction === 'LONG' ? 'success' : s.direction === 'SHORT' ? 'error' : 'default'}>
                        {s.direction === 'LONG' ? '做多' : s.direction === 'SHORT' ? '做空' : '中性'}
                      </Tag>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="信号数据未加载" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Card
            size="small"
            title={<span><TableOutlined style={{ marginRight: 8 }} />持仓概览</span>}
            extra={<Text type="secondary">{positions.length} 个品种</Text>}
          >
            {positions.length > 0 ? (
              <div>
                {positions.slice(0, 5).map((p: { symbol: string; direction: string; volume: number; unrealizedPnl?: number }) => (
                  <div key={p.symbol} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <div>
                      <Text style={{ fontSize: 13 }}>{p.symbol}</Text>
                      <Tag color={p.direction === 'LONG' ? 'green' : 'red'} style={{ marginLeft: 8, fontSize: 11 }}>
                        {p.direction === 'LONG' ? '多' : '空'} {p.volume}手
                      </Tag>
                    </div>
                    <Text style={{ fontSize: 13, color: (p.unrealizedPnl ?? 0) >= 0 ? '#52c41a' : '#ff4d4f' }}>
                      {p.unrealizedPnl != null ? `${p.unrealizedPnl > 0 ? '+' : ''}${p.unrealizedPnl.toFixed(0)}` : '--'}
                    </Text>
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无持仓" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage
