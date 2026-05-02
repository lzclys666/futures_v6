/**
 * MacroDashboard · 宏观打分主面板
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import React, { useEffect } from 'react'
import { Row, Col, Card, Statistic, Select, Tag, Spin } from 'antd'
import { useMacroStore } from '../../store/macroStore'
import { ComponentErrorBoundary, ApiErrorAlert } from '../common/ErrorBoundary'
import FactorCard from './FactorCard'
import SignalChart from './SignalChart'
import WeightTable from './WeightTable'
import './MacroDashboard.css'

const SIGNAL_CONFIG = {
  LONG:    { color: '#52c41a', label: '多头', zh: '做多信号' },
  SHORT:   { color: '#ff4d4f', label: '空头', zh: '做空信号' },
  NEUTRAL: { color: '#faad14', label: '中性', zh: '中性信号' },
}

const SYMBOL_OPTIONS = [
  { value: 'RU', label: '橡胶 (RU)' },
  { value: 'CU', label: '铜 (CU)' },
  { value: 'AU', label: '黄金 (AU)' },
  { value: 'AG', label: '白银 (AG)' },
]

const MacroDashboard: React.FC = () => {
  const {
    selectedSymbol,
    setSelectedSymbol,
    currentSignal,
    currentSignalLoading,
    allSignals,
    allSignalsLoading,
    factorDetails,
    factorDetailsLoading,
    scoreHistory,
    scoreHistoryLoading,
    loadAllSignals,
    loadSignal,
    loadFactorDetails,
    loadScoreHistory,
    error,
    clearError,
  } = useMacroStore()

  // 初始化加载
  useEffect(() => {
    loadAllSignals()
    loadSignal(selectedSymbol)
    loadFactorDetails(selectedSymbol)
    loadScoreHistory(selectedSymbol)
  }, [])

  const handleSymbolChange = (symbol: string) => {
    clearError()
    setSelectedSymbol(symbol)
  }

  const cfg = currentSignal ? SIGNAL_CONFIG[currentSignal.direction] : null

  return (
    <div className="macro-dashboard">
      {/* 顶部导航栏 */}
      <div className="macro-dashboard__toolbar">
        <span className="macro-dashboard__title">宏观基本面打分</span>
        <Select
          value={selectedSymbol}
          onChange={handleSymbolChange}
          options={SYMBOL_OPTIONS}
          style={{ width: 160 }}
        />
      </div>

      {/* 错误提示 */}
      {error && (
        <ApiErrorAlert
          error={error}
          onRetry={() => {
            clearError()
            loadAllSignals()
            loadSignal(selectedSymbol)
            loadFactorDetails(selectedSymbol)
            loadScoreHistory(selectedSymbol)
          }}
        />
      )}

      {/* 综合打分卡片 */}
      <ComponentErrorBoundary>
        <Card className="macro-dashboard__score-card" bordered={false}>
          <Row gutter={24} align="middle">
            <Col flex="160px">
              <Statistic
                title="综合打分"
                value={currentSignal?.compositeScore ?? 0}
                precision={3}
                valueStyle={{
                  fontFamily: 'Courier New, monospace',
                  fontSize: 28,
                  fontWeight: 700,
                  color: cfg ? cfg.color : '#262626',
                }}
                suffix={
                  cfg ? (
                    <Tag color={cfg.color} style={{ fontSize: 12, marginLeft: 8 }}>
                      {cfg.zh}
                    </Tag>
                  ) : null
                }
              />
            </Col>
            <Col flex="auto">
              <Spin spinning={currentSignalLoading} tip="加载信号...">
                <div className="macro-dashboard__meta">
                  <span>品种：<b>{selectedSymbol}</b></span>
                  <span>更新时间：{currentSignal?.updatedAt ? new Date(currentSignal.updatedAt).toLocaleString('zh-CN') : '-'}</span>
                </div>
              </Spin>
            </Col>
            <Col flex="200px">
              <Spin spinning={allSignalsLoading} tip="加载全品种...">
                <div className="macro-dashboard__all-signals">
                  <span className="macro-dashboard__all-label">其他品种：</span>
                  {allSignals.slice(0, 5).map(s => {
                    const sc = SIGNAL_CONFIG[s.direction]
                    return (
                      <Tag key={s.symbol} color={sc.color} style={{ marginBottom: 4 }}>
                        {s.symbol} {s.compositeScore >= 0 ? '+' : ''}{s.compositeScore.toFixed(2)}
                      </Tag>
                    )
                  })}
                </div>
              </Spin>
            </Col>
          </Row>
        </Card>
      </ComponentErrorBoundary>

      {/* 主体内容：因子卡片 + 历史走势图 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        {/* 左列：因子卡片 */}
        <Col span={10}>
          <Card title="因子明细" size="small" bordered={false}>
            <ComponentErrorBoundary fallback={<ApiErrorAlert error="因子明细加载失败" />}>
              <Spin spinning={factorDetailsLoading} tip="加载因子...">
                <div className="macro-dashboard__factor-grid">
                  {factorDetails.map(f => (
                    <FactorCard key={f.factorCode} factor={f} />
                  ))}
                </div>
              </Spin>
            </ComponentErrorBoundary>
          </Card>
        </Col>

        {/* 右列：历史走势图 */}
        <Col span={14}>
          <Card size="small" bordered={false} bodyStyle={{ padding: 0 }}>
            <ComponentErrorBoundary fallback={<ApiErrorAlert error="图表加载失败" />}>
              <SignalChart
                symbol={selectedSymbol}
                history={scoreHistory}
                loading={scoreHistoryLoading}
              />
            </ComponentErrorBoundary>
          </Card>

          {/* 权重表 */}
          <Card title="因子权重与贡献" size="small" bordered={false} style={{ marginTop: 16 }}>
            <ComponentErrorBoundary fallback={<ApiErrorAlert error="权重表加载失败" />}>
              <Spin spinning={factorDetailsLoading} tip="加载权重...">
                <WeightTable factors={factorDetails} />
              </Spin>
            </ComponentErrorBoundary>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default MacroDashboard
