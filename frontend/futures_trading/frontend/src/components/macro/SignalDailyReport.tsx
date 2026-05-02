/**
 * SignalDailyReport · AG 每日信号汇总面板
 * @author Lucy (UI Designer)
 * @date 2026-04-22
 *
 * 定位：与 MacroDashboard 并列的 AG 专属信号日报 Tab
 * 数据源：/api/macro/signal/AG（主）+ CSV 历史存档（参考）
 *
 * confidence 推导规则（YIYI 确认）：
 *   compositeScore ≥ 0.3  → 高
 *   0.1 ≤ compositeScore < 0.3 → 中
 *   compositeScore < 0.1  → 低
 *
 * 金银比因子来源：factors 数组中 factorCode = "AU_AG_ratio_diff" 的 rawValue
 *   （对应 CSV 字段 AG_MACRO_GOLD_SILVER_RATIO）
 */

import React, { useEffect } from 'react'
import { Card, Tag, Spin, Tooltip } from 'antd'
import { useMacroStore } from '../../store/macroStore'
import { ComponentErrorBoundary, ApiErrorAlert } from '../common/ErrorBoundary'
import FactorCard from './FactorCard'
import './SignalDailyReport.css'

// ---------- 常量配置 ----------

const DIRECTION_CONFIG = {
  LONG:   { color: '#52c41a', label: '做多', zh: '多头信号' },
  SHORT:  { color: '#ff4d4f', label: '做空', zh: '空头信号' },
  NEUTRAL:{ color: '#faad14', label: '中性', zh: '中性信号' },
} as const

type Direction = 'LONG' | 'SHORT' | 'NEUTRAL'

const CONFIDENCE_CONFIG = {
  高:   { color: '#52c41a', dotClass: 'signal-daily__confidence-dot--high' },
  中:   { color: '#faad14', dotClass: 'signal-daily__confidence-dot--medium' },
  低:   { color: '#ff4d4f', dotClass: 'signal-daily__confidence-dot--low' },
} as const

/** 置信度等级 */
export type ConfidenceLevel = '高' | '中' | '低'

/**
 * 根据 compositeScore 推导置信度等级
 * YIYI 确认规则：≥0.3 高 / 0.1~0.3 中 / <0.1 低
 */
export function scoreToConfidence(score: number): ConfidenceLevel {
  const abs = Math.abs(score)
  if (abs >= 0.3) return '高'
  if (abs >= 0.1) return '中'
  return '低'
}

/**
 * 金银比因子数据（从 factors 数组中提取）
 * factorCode = "AU_AG_ratio_diff" 的 rawValue 即为金银比原始值
 */
export interface GoldSilverRatioData {
  /** 金银比原始值（来自因子 rawValue） */
  rawValue: number
  /** 标准化得分 */
  normalizedScore: number
  /** 因子权重 */
  weight: number
  /** 因子贡献 */
  contribution: number
  /** 因子 IC */
  factorIc: number | null
}

export interface SignalDailyReportProps {
  /** 默认品种，默认 AG */
  defaultSymbol?: string
}

// ---------- 子组件 ----------

/** 置信度标签 */
const ConfidenceBadge: React.FC<{ level: ConfidenceLevel }> = ({ level }) => {
  const cfg = CONFIDENCE_CONFIG[level]
  return (
    <span className="signal-daily__confidence">
      <span className={`signal-daily__confidence-dot ${cfg.dotClass}`} />
      置信度：{level}
    </span>
  )
}

/** 主信号卡片 */
const MainSignalCard: React.FC<{
  score: number
  direction: Direction
  confidence: ConfidenceLevel
  updatedAt: string
  loading: boolean
}> = ({ score, direction, confidence, updatedAt, loading }) => {
  const cfg = DIRECTION_CONFIG[direction]

  return (
    <Card className="signal-daily__main-card" bordered={false}>
      <Spin spinning={loading} tip="加载信号...">
        {/* 综合打分 + 方向标签 */}
        <div className="signal-daily__main-score">
          <span
            className="signal-daily__main-score-value"
            style={{ color: cfg.color }}
          >
            {score >= 0 ? '+' : ''}{score.toFixed(3)}
          </span>
          <Tag color={cfg.color} style={{ fontSize: 13 }}>
            {cfg.zh}
          </Tag>
        </div>

        {/* 置信度 */}
        <ConfidenceBadge level={confidence} />

        {/* 元信息 */}
        <div className="signal-daily__meta-row">
          <div className="signal-daily__meta-item">
            <span className="signal-daily__meta-label">品种</span>
            <span>AG 沪银</span>
          </div>
          <div className="signal-daily__meta-item">
            <span className="signal-daily__meta-label">更新</span>
            <span>
              {updatedAt
                ? new Date(updatedAt).toLocaleString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : '-'}
            </span>
          </div>
          <div className="signal-daily__meta-item">
            <span className="signal-daily__meta-label">风控</span>
            <span style={{ color: '#52c41a' }}>运行中</span>
          </div>
        </div>
      </Spin>
    </Card>
  )
}

/** 金银比因子卡片 */
const GoldSilverRatioCard: React.FC<{
  data: GoldSilverRatioData | null
  loading: boolean
}> = ({ data, loading }) => {
  return (
    <Card className="signal-daily__ratio-card" bordered={false}>
      <Spin spinning={loading} tip="加载因子...">
        <div className="signal-daily__ratio-header">
          <span className="signal-daily__ratio-label">金银比因子</span>
          <Tooltip title="因子代码 AU_AG_ratio_diff，对应 CSV 字段 AG_MACRO_GOLD_SILVER_RATIO">
            <Tag color="purple" style={{ fontSize: 11 }}>AG_MACRO_GOLD_SILVER_RATIO</Tag>
          </Tooltip>
        </div>

        <div className="signal-daily__ratio-value">
          {data ? data.rawValue.toFixed(4) : '-.----'}
        </div>

        <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4 }}>
          标准化得分 {data ? (data.normalizedScore >= 0 ? '+' : '') + data.normalizedScore.toFixed(3) : '-'}
        </div>

        {/* 因子得分进度条（-1~1 映射到 0%~100%） */}
        <div className="signal-daily__ratio-bar">
          {(() => {
            const ns = data?.normalizedScore
            return (
              <div
                className="signal-daily__ratio-bar-fill"
                style={{
                  width: ns != null
                    ? `${Math.round((ns + 1) / 2 * 100)}%`
                    : '50%',
                  background: ns != null && ns >= 0 ? '#52c41a' : '#ff4d4f',
                }}
              />
            )
          })()}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 11, color: '#8c8c8c' }}>
          <span>权重 {(data?.weight ?? 0 * 100).toFixed(0)}%</span>
          <span>
            IC {data?.factorIc != null ? (
              <span style={{ color: data.factorIc > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
                {data.factorIc > 0 ? '+' : ''}{data.factorIc.toFixed(4)}
              </span>
            ) : '-'}
          </span>
        </div>
      </Spin>
    </Card>
  )
}

/** IC 指标卡片 */
const ICCard: React.FC<{
  ic: number | null
  ir: number | null
  tStat: number | null
  loading: boolean
}> = ({ ic, ir, tStat, loading }) => {
  const icColor = ic == null ? '' : ic > 0 ? '#52c41a' : '#ff4d4f'
  const irColor = ir == null ? '' : ir > 0 ? '#52c41a' : '#ff4d4f'
  const tColor = tStat == null ? '' : Math.abs(tStat) > 2 ? '#52c41a' : '#faad14'

  return (
    <Card className="signal-daily__ic-card" bordered={false}>
      <Spin spinning={loading} tip="加载IC...">
        <div className="signal-daily__ic-title">AG 因子 IC 指标</div>
        <div className="signal-daily__ic-grid">
          <div className="signal-daily__ic-item">
            <span className="signal-daily__ic-item-label">IC 均值</span>
            <span
              className="signal-daily__ic-item-value"
              style={{ color: icColor || undefined }}
            >
              {ic != null ? (ic > 0 ? '+' : '') + ic.toFixed(4) : '-'}
            </span>
          </div>
          <div className="signal-daily__ic-item">
            <span className="signal-daily__ic-item-label">IC IR</span>
            <span
              className="signal-daily__ic-item-value"
              style={{ color: irColor || undefined }}
            >
              {ir != null ? (ir > 0 ? '+' : '') + ir.toFixed(3) : '-'}
            </span>
          </div>
          <div className="signal-daily__ic-item">
            <span className="signal-daily__ic-item-label">t 统计量</span>
            <span
              className="signal-daily__ic-item-value"
              style={{ color: tColor || undefined }}
            >
              {tStat != null ? (tStat > 0 ? '+' : '') + tStat.toFixed(2) : '-'}
            </span>
          </div>
          <div className="signal-daily__ic-item">
            <span className="signal-daily__ic-item-label">IC 显著性</span>
            <span
              className="signal-daily__ic-item-value"
              style={{ color: tColor || undefined }}
            >
              {tStat != null ? (Math.abs(tStat) > 2 ? '✅ 显著' : '⚠️ 不显著') : '-'}
            </span>
          </div>
        </div>
      </Spin>
    </Card>
  )
}

/** 因子明细卡片（复用现有 FactorCard 网格） */
const FactorDetailsCard: React.FC<{
  factors: import('../../types/macro').FactorDetail[]
  loading: boolean
}> = ({ factors, loading }) => {
  return (
    <Card title="因子明细" size="small" bordered={false} bodyStyle={{ padding: 12 }}>
      <Spin spinning={loading} tip="加载因子...">
        <div className="macro-dashboard__factor-grid">
          {factors.map(f => (
            <FactorCard key={f.factorCode} factor={f} />
          ))}
        </div>
      </Spin>
    </Card>
  )
}

/** 持仓状态卡片（Paper Trading 数据） */
const PositionCard: React.FC<{
  compositeScore: number
  direction: Direction
  confidence: ConfidenceLevel
}> = ({ compositeScore, direction, confidence }) => {
  // Paper Trading 模拟数据（实盘数据需对接 /api/paper/positions）
  const positionAmount = Math.abs(compositeScore) >= 0.1 ? Math.round(Math.abs(compositeScore) * 100) : 0
  const positionDirection = compositeScore >= 0.1 ? '多头' : compositeScore <= -0.1 ? '空头' : '空仓'
  const estimatedDD = -0.05 // 模拟当前回撤

  return (
    <Card className="signal-daily__position-card" bordered={false}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#262626', marginBottom: 8 }}>
        Paper Trading 持仓状态
      </div>
      <div className="signal-daily__position-row">
        <span className="signal-daily__position-label">方向</span>
        <Tag color={DIRECTION_CONFIG[direction].color}>
          {positionDirection}
        </Tag>
      </div>
      <div className="signal-daily__position-row">
        <span className="signal-daily__position-label">仓位</span>
        <span className="signal-daily__position-value">{positionAmount}%</span>
      </div>
      <div className="signal-daily__position-row">
        <span className="signal-daily__position-label">初始资金</span>
        <span className="signal-daily__position-value">¥1,000,000</span>
      </div>
      <div className="signal-daily__position-row">
        <span className="signal-daily__position-label">当前回撤</span>
        <span
          className="signal-daily__position-value"
          style={{ color: estimatedDD < -0.15 ? '#ff4d4f' : estimatedDD < -0.1 ? '#faad14' : '#52c41a' }}
        >
          {(estimatedDD * 100).toFixed(2)}%
        </span>
      </div>
      <div className="signal-daily__position-row">
        <span className="signal-daily__position-label">置信度</span>
        <Tag color={CONFIDENCE_CONFIG[confidence].color}>{confidence}</Tag>
      </div>
    </Card>
  )
}

/** 风控状态卡片 */
const RiskControlCard: React.FC = () => {
  // 五层风控状态（模拟数据，实盘需对接风控 API）
  const levels = [
    { label: 'L1 仓位限制（≤30%）', status: 'ok' as const, value: '当前 18%' },
    { label: 'L2 信号阈值（|z|≥0.5）', status: 'ok' as const, value: '通过' },
    { label: 'L3 日度回撤监控（-15%）', status: 'ok' as const, value: '-5.2%' },
    { label: 'L4 IC 熔断（IC≥0.05）', status: 'ok' as const, value: 'IC=0.1486' },
    { label: 'L5 流动性风险（≤20%单笔）', status: 'ok' as const, value: '当前 8%' },
  ]

  const statusLabel: Record<'ok' | 'warn' | 'danger', string> = {
    ok: '正常',
    warn: '告警',
    danger: '触发',
  }

  return (
    <Card className="signal-daily__risk-card" bordered={false}>
      <div className="signal-daily__risk-title">五层风控状态</div>
      <div className="signal-daily__risk-list">
        {levels.map(l => (
          <div key={l.label} className="signal-daily__risk-item">
            <Tooltip title={l.label}>
              <span className="signal-daily__risk-item-label">
                {l.label.split(' ')[0]} {l.label.split('（')[1]?.replace('）', '')}
              </span>
            </Tooltip>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: '#8c8c8c' }}>{l.value}</span>
              <span className={`signal-daily__risk-item-status signal-daily__risk-item-status--${l.status}`}>
                {statusLabel[l.status]}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ---------- 主组件 ----------

const SignalDailyReport: React.FC<SignalDailyReportProps> = ({
  defaultSymbol = 'AG',
}) => {
  const {
    selectedSymbol,
    setSelectedSymbol,
    currentSignal,
    currentSignalLoading,
    factorDetails,
    factorDetailsLoading,
    loadAllSignals,
    loadSignal,
    loadFactorDetails,
    loadScoreHistory,
    error,
    clearError,
  } = useMacroStore()

  useEffect(() => {
    setSelectedSymbol(defaultSymbol)
  }, [defaultSymbol])

  // 从 factors 数组中提取 AU_AG_ratio_diff 因子
  const goldSilverFactor = React.useMemo<GoldSilverRatioData | null>(() => {
    if (!factorDetails.length) return null
    const f = factorDetails.find(f => f.factorCode === 'AU_AG_ratio_diff')
    if (!f) return null
    return {
      rawValue: f.rawValue,
      normalizedScore: f.normalizedScore,
      weight: f.weight,
      contribution: f.contribution,
      factorIc: null, // TODO: 对接 IC API 后填充
    }
  }, [factorDetails])

  // 计算置信度
  const confidence = React.useMemo<ConfidenceLevel>(() => {
    return scoreToConfidence(currentSignal?.compositeScore ?? 0)
  }, [currentSignal?.compositeScore])

  const direction: Direction = currentSignal?.direction ?? 'NEUTRAL'

  // IC 相关数据（来自 YIYI 文档，AG IC = +0.1486，IR=1.494，t=55.72）
  const IC_DATA = {
    ic: 0.1486,
    ir: 1.494,
    tStat: 55.72,
  }

  return (
    <div className="signal-daily">
      {/* 顶部工具栏 */}
      <div className="signal-daily__toolbar">
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
          <span className="signal-daily__title">AG 信号日报</span>
          <span className="signal-daily__subtitle">
            沪银 · Paper Trading · {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })}
          </span>
        </div>
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

      {/* 第一行：主信号卡片 + 金银比卡片 + IC 卡片 */}
      <div className="signal-daily__summary-row">
        <ComponentErrorBoundary fallback={<ApiErrorAlert error="主信号加载失败" />}>
          <MainSignalCard
            score={currentSignal?.compositeScore ?? 0}
            direction={direction}
            confidence={confidence}
            updatedAt={currentSignal?.updatedAt ?? ''}
            loading={currentSignalLoading}
          />
        </ComponentErrorBoundary>
        <ComponentErrorBoundary fallback={<ApiErrorAlert error="金银比因子加载失败" />}>
          <GoldSilverRatioCard
            data={goldSilverFactor}
            loading={factorDetailsLoading}
          />
        </ComponentErrorBoundary>
        <ComponentErrorBoundary fallback={<ApiErrorAlert error="IC 指标加载失败" />}>
          <ICCard
            ic={IC_DATA.ic}
            ir={IC_DATA.ir}
            tStat={IC_DATA.tStat}
            loading={factorDetailsLoading}
          />
        </ComponentErrorBoundary>
      </div>

      {/* 第二行：因子明细（全量因子） */}
      <div className="signal-daily__factors-section">
        <ComponentErrorBoundary fallback={<ApiErrorAlert error="因子明细加载失败" />}>
          <FactorDetailsCard
            factors={factorDetails}
            loading={factorDetailsLoading}
          />
        </ComponentErrorBoundary>
      </div>

      {/* 第三行：持仓状态 + 风控状态 */}
      <div className="signal-daily__bottom-row">
        <ComponentErrorBoundary fallback={<ApiErrorAlert error="持仓状态加载失败" />}>
          <PositionCard
            compositeScore={currentSignal?.compositeScore ?? 0}
            direction={direction}
            confidence={confidence}
          />
        </ComponentErrorBoundary>
        <ComponentErrorBoundary fallback={<ApiErrorAlert error="风控状态加载失败" />}>
          <RiskControlCard />
        </ComponentErrorBoundary>
      </div>
    </div>
  )
}

export default SignalDailyReport
