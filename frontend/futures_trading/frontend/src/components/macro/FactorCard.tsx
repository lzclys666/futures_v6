/**
 * FactorCard · 因子卡片
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import React, { useMemo } from 'react'
import { Card, Progress, Tag, Tooltip, Collapse } from 'antd'
import type { FactorCardProps } from '../../types/macro'
import type { RiskSeverity } from '../../types/risk'
import './FactorCard.css'

const DIRECTION_COLOR: Record<string, string> = {
  positive: '#52c41a',
  negative: '#ff4d4f',
  neutral:  '#999999',
}

const DIRECTION_LABEL: Record<string, string> = {
  positive: '正贡献',
  negative: '负贡献',
  neutral:  '中性',
}

// 风险字段 → 显示标签映射
const RISK_FIELDS: { key: string; label: string }[] = [
  { key: 'r1_single_position',    label: 'R1 单品种仓位' },
  { key: 'r2_continuous_profit',  label: 'R2 连续盈利' },
  { key: 'r3_price_limit',        label: 'R3 涨跌停' },
  { key: 'r4_total_position',     label: 'R4 总仓位' },
  { key: 'r5_stop_loss',          label: 'R5 止损' },
  { key: 'r6_max_drawdown',       label: 'R6 最大回撤' },
  { key: 'r7_trading_frequency',  label: 'R7 交易频率' },
  { key: 'r8_trading_hours',      label: 'R8 交易时段' },
  { key: 'r9_frozen_capital',     label: 'R9 冻结资金' },
  { key: 'r10_circuit_breaker',   label: 'R10 熔断' },
  { key: 'r11_disposition_effect',label: 'R11 处置效应' },
  { key: 'r12_cancel_limit',      label: 'R12 撤单限制' },
]

const RISK_COLOR: Record<RiskSeverity, string> = {
  PASS: '#52c41a',
  WARN: '#faad14',
  BLOCK: '#ff4d4f',
}

const RISK_LABEL: Record<RiskSeverity, string> = {
  PASS: '✓',
  WARN: '!',
  BLOCK: '✕',
}

const FactorCard: React.FC<FactorCardProps> = ({ factor }) => {
  const scorePercent = Math.round((factor.normalizedScore + 1) / 2 * 100)

  // 提取非 PASS 风险项
  const riskAlerts = useMemo(() => {
    return RISK_FIELDS.filter(({ key }) => {
      const val = (factor as unknown as Record<string, unknown>)[key] as RiskSeverity | undefined
      return val && val !== 'PASS'
    }).map(({ key, label }) => ({
      key,
      label,
      severity: (factor as unknown as Record<string, unknown>)[key] as RiskSeverity,
    }))
  }, [factor])

  const hasAlerts = riskAlerts.length > 0

  return (
    <Card
      size="small"
      className={`factor-card${hasAlerts ? ' factor-card--has-risk' : ''}`}
      bordered={false}
    >
      <div className="factor-card__header">
        <Tooltip title={factor.factorCode}>
          <span className="factor-card__name">{factor.factorName}</span>
        </Tooltip>
        <Tag color={DIRECTION_COLOR[factor.direction]}>
          {DIRECTION_LABEL[factor.direction]}
        </Tag>
      </div>

      <div className="factor-card__score">
        <span className="factor-card__score-value">
          {factor.normalizedScore >= 0 ? '+' : ''}
          {factor.normalizedScore.toFixed(3)}
        </span>
        <span className="factor-card__weight">
          权重 {(factor.weight * 100).toFixed(0)}%
        </span>
      </div>

      <Progress
        percent={scorePercent}
        showInfo={false}
        strokeColor={DIRECTION_COLOR[factor.direction]}
        trailColor="#f0f0f0"
        className="factor-card__progress"
      />

      <div className="factor-card__footer">
        <span>贡献值</span>
        <span className="factor-card__contribution">
          {factor.contribution >= 0 ? '+' : ''}
          {factor.contribution.toFixed(4)}
        </span>
      </div>

      {/* 风险状态区域：仅在存在 WARN/BLOCK 时显示 */}
      {hasAlerts && (
        <Collapse
          size="small"
          className="factor-card__risk-collapse"
          defaultActiveKey={['risk']}
          items={[
            {
              key: 'risk',
              label: (
                <span className="factor-card__risk-title">
                  ⚠ 风险告警 ({riskAlerts.length})
                </span>
              ),
              children: (
                <div className="factor-card__risk-list">
                  {riskAlerts.map(({ key, label, severity }) => (
                    <Tooltip key={key} title={`${label}: ${severity}`}>
                      <span
                        className="factor-card__risk-dot"
                        style={{ backgroundColor: RISK_COLOR[severity] }}
                      >
                        {RISK_LABEL[severity]}
                      </span>
                    </Tooltip>
                  ))}
                </div>
              ),
            },
          ]}
        />
      )}

      {/* 全部 PASS 时显示一个绿色小点作为安全指示 */}
      {!hasAlerts && (
        <div className="factor-card__risk-safe">
          <span className="factor-card__risk-dot" style={{ backgroundColor: RISK_COLOR.PASS }}>
            {RISK_LABEL.PASS}
          </span>
          <span className="factor-card__risk-safe-text">风控全通过</span>
        </div>
      )}
    </Card>
  )
}

export default FactorCard
