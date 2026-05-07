/**
 * FactorDashboardPage · 因子仪表盘（Phase 3）
 *
 * 布局：
 *   顶部 - 品种选择器
 *   左侧 - 信号概览（方向、得分、置信度）
 *   右侧 - 因子明细表（因子名、IC 值、得分、权重）
 *   底部 - 得分趋势图（折线）
 *
 * @author Lucy
 * @date 2026-05-06
 */

import React, { useEffect } from 'react'
import { Row, Col, Card, Select, Tag, Spin, Empty, Table, Statistic } from 'antd'
import { BarChartOutlined, FundOutlined, ExperimentOutlined } from '@ant-design/icons'
import { useMacroStore } from '../store/macroStore'
import SignalChart from '../components/macro/SignalChart'
import type { FactorDetail, SignalDirection } from '../types/macro'

const SIGNAL_CONFIG: Record<SignalDirection, { color: string; zh: string }> = {
  LONG:    { color: '#52c41a', zh: '做多信号' },
  SHORT:   { color: '#ff4d4f', zh: '做空信号' },
  NEUTRAL: { color: '#faad14', zh: '中性信号' },
}

const SYMBOL_OPTIONS = [
  { value: 'RU', label: '橡胶 (RU)' },
  { value: 'CU', label: '铜 (CU)' },
  { value: 'AU', label: '黄金 (AU)' },
  { value: 'AG', label: '白银 (AG)' },
  { value: 'RB', label: '螺纹 (RB)' },
  { value: 'ZN', label: '锌 (ZN)' },
  { value: 'NI', label: '镍 (NI)' },
]

const CONFIDENCE_MAP: Record<string, { color: string; label: string }> = {
  high:   { color: '#52c41a', label: '高' },
  medium: { color: '#faad14', label: '中' },
  low:    { color: '#ff4d4f', label: '低' },
}

const FactorDashboardPage: React.FC = () => {
  const {
    selectedSymbol,
    setSelectedSymbol,
    currentSignal,
    currentSignalLoading,
    factorDetails,
    factorDetailsLoading,
    scoreHistory,
    scoreHistoryLoading,
    loadSignal,
    loadFactorDetails,
    loadScoreHistory,
  } = useMacroStore()

  useEffect(() => {
    loadSignal(selectedSymbol)
    loadFactorDetails(selectedSymbol)
    loadScoreHistory(selectedSymbol)
  }, [selectedSymbol, loadSignal, loadFactorDetails, loadScoreHistory])

  const handleSymbolChange = (symbol: string) => {
    setSelectedSymbol(symbol)
  }

  const signalCfg = currentSignal ? SIGNAL_CONFIG[currentSignal.direction] : null
  const confCfg = currentSignal?.confidence ? CONFIDENCE_MAP[currentSignal.confidence] : null

  // 因子明细表列定义
  const factorColumns = [
    {
      title: '因子',
      dataIndex: 'factorName',
      key: 'factorName',
      width: 120,
      render: (v: string, row: FactorDetail) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>{v}</span>
          <Tag
            color={row.direction === 'positive' ? 'green' : row.direction === 'negative' ? 'red' : 'default'}
            style={{ fontSize: 10, padding: '0 4px', margin: 0 }}
          >
            {row.direction === 'positive' ? '多' : row.direction === 'negative' ? '空' : '中'}
          </Tag>
        </div>
      ),
    },
    {
      title: 'IC 值',
      dataIndex: 'factorIc',
      key: 'factorIc',
      width: 80,
      render: (v: number | undefined) => (
        <span style={{ color: v != null ? (v > 0 ? '#52c41a' : '#ff4d4f') : '#bfbfbf' }}>
          {v != null ? v.toFixed(3) : '-'}
        </span>
      ),
    },
    {
      title: '得分',
      dataIndex: 'normalizedScore',
      key: 'normalizedScore',
      width: 80,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v > 0 ? '+' : ''}{v.toFixed(3)}
        </span>
      ),
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      width: 100,
      render: (v: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3 }}>
            <div style={{ width: `${v * 100}%`, height: '100%', background: '#1890ff', borderRadius: 3 }} />
          </div>
          <span style={{ fontSize: 12, minWidth: 36 }}>{(v * 100).toFixed(1)}%</span>
        </div>
      ),
    },
    {
      title: '贡献',
      dataIndex: 'contribution',
      key: 'contribution',
      width: 80,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v > 0 ? '+' : ''}{(v * 100).toFixed(1)}%
        </span>
      ),
    },
  ]

  return (
    <div>
      {/* 顶部：标题 + 品种选择器 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h4 style={{ margin: 0 }}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          因子仪表盘
        </h4>
        <Select
          value={selectedSymbol}
          onChange={handleSymbolChange}
          options={SYMBOL_OPTIONS}
          style={{ width: 160 }}
        />
      </div>

      <Row gutter={[16, 16]}>
        {/* 左侧：信号概览 */}
        <Col xs={24} md={8}>
          <Card size="small" title={<span><FundOutlined style={{ marginRight: 6 }} />信号概览</span>}>
            <Spin spinning={currentSignalLoading}>
              {currentSignal ? (
                <div>
                  <Statistic
                    title="综合得分"
                    value={currentSignal.compositeScore}
                    precision={3}
                    valueStyle={{
                      fontSize: 32,
                      fontWeight: 700,
                      color: signalCfg?.color ?? '#262626',
                    }}
                  />
                  <div style={{ marginTop: 16 }}>
                    <div style={{ marginBottom: 8 }}>
                      <span style={{ color: '#8c8c8c', marginRight: 8 }}>方向：</span>
                      <Tag color={signalCfg?.color}>{signalCfg?.zh}</Tag>
                    </div>
                    <div style={{ marginBottom: 8 }}>
                      <span style={{ color: '#8c8c8c', marginRight: 8 }}>置信度：</span>
                      <Tag color={confCfg?.color ?? '#d9d9d9'}>{confCfg?.label ?? '-'}</Tag>
                    </div>
                    <div>
                      <span style={{ color: '#8c8c8c', marginRight: 8 }}>更新时间：</span>
                      <span>{currentSignal.updatedAt ? new Date(currentSignal.updatedAt).toLocaleString('zh-CN') : '-'}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <Empty description="暂无信号数据" />
              )}
            </Spin>
          </Card>
        </Col>

        {/* 右侧：因子明细表 */}
        <Col xs={24} md={16}>
          <Card size="small" title={<span><ExperimentOutlined style={{ marginRight: 6 }} />因子明细</span>}>
            <Spin spinning={factorDetailsLoading}>
              {factorDetails.length > 0 ? (
                <Table
                  columns={factorColumns}
                  dataSource={factorDetails}
                  rowKey="factorCode"
                  size="small"
                  pagination={false}
                  scroll={{ x: 500 }}
                />
              ) : (
                <Empty description="暂无因子数据" />
              )}
            </Spin>
          </Card>
        </Col>
      </Row>

      {/* 底部：得分趋势图 */}
      <Card
        size="small"
        title={<span><BarChartOutlined style={{ marginRight: 6 }} />得分趋势</span>}
        style={{ marginTop: 16 }}
      >
        <SignalChart
          symbol={selectedSymbol}
          history={scoreHistory}
          loading={scoreHistoryLoading}
        />
      </Card>
    </div>
  )
}

export default FactorDashboardPage
