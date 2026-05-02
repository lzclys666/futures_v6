/**
 * FactorCard · 因子卡片
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import React from 'react'
import { Card, Progress, Tag, Tooltip } from 'antd'
import type { FactorCardProps } from '../../types/macro'
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

const FactorCard: React.FC<FactorCardProps> = ({ factor }) => {
  const scorePercent = Math.round((factor.normalizedScore + 1) / 2 * 100)

  return (
    <Card size="small" className="factor-card" bordered={false}>
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
    </Card>
  )
}

export default FactorCard
