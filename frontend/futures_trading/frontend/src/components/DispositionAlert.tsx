/**
 * 处置效应告警弹窗组件
 * @author Lucy
 * @date 2026-05-06
 *
 * 当持仓触发处置效应检测条件时弹出提醒：
 *   - 盈利 > 10% 且持仓 < 3天 → 建议继续持有
 *   - 亏损 > 15% 且持仓 > 30天 → 建议止损
 *
 * 三个按钮：「按建议操作」「忽略」「不再提醒」
 */

import React, { useMemo } from 'react'
import { Modal, Typography, Space, Tag, Button, Descriptions, Alert } from 'antd'
import {
  WarningOutlined,
  AlertOutlined,
  RiseOutlined,
  FallOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import type { PositionRiskAssessment, DispositionAction } from '../utils/dispositionEffect'

const { Text, Paragraph } = Typography

/** 按钮文案映射 */
const ACTION_LABELS: Record<DispositionAction, string> = {
  TAKE_PROFIT: '止盈平仓',
  STOP_LOSS: '止损平仓',
  HOLD: '继续持有',
}

/** 风险等级配色 */
const RISK_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  HIGH: { color: '#ff4d4f', icon: <AlertOutlined />, label: '高风险' },
  WARN: { color: '#faad14', icon: <WarningOutlined />, label: '警告' },
}

interface DispositionAlertProps {
  /** 是否显示弹窗 */
  open: boolean
  /** 当前评估结果 */
  assessment: PositionRiskAssessment | null
  /** 按建议操作回调 */
  onFollowAction: (assessment: PositionRiskAssessment) => void
  /** 忽略回调 */
  onDismiss: () => void
  /** 不再提醒回调 */
  onNeverRemind: (symbol: string) => void
}

const DispositionAlert: React.FC<DispositionAlertProps> = ({
  open,
  assessment,
  onFollowAction,
  onDismiss,
  onNeverRemind,
}) => {
  const config = useMemo(() => {
    if (!assessment) return RISK_CONFIG.WARN
    return RISK_CONFIG[assessment.riskLevel] ?? RISK_CONFIG.WARN
  }, [assessment])

  if (!assessment) return null

  const isProfit = assessment.alertType === 'EARLY_PROFIT'
  const pnlPct = (assessment.pnlRate * 100).toFixed(2)

  return (
    <Modal
      title={
        <Space>
          {config.icon}
          <span style={{ color: config.color }}>
            处置效应提醒 — {assessment.symbol}
          </span>
          <Tag color={config.color}>{config.label}</Tag>
        </Space>
      }
      open={open}
      width={480}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            type="link"
            danger
            size="small"
            onClick={() => onNeverRemind(assessment.symbol)}
          >
            不再提醒
          </Button>
          <Space>
            <Button onClick={onDismiss}>忽略</Button>
            <Button
              type="primary"
              danger={assessment.suggestedAction === 'STOP_LOSS'}
              icon={isProfit ? <RiseOutlined /> : <FallOutlined />}
              onClick={() => onFollowAction(assessment)}
            >
              {ACTION_LABELS[assessment.suggestedAction]}
            </Button>
          </Space>
        </div>
      }
      maskClosable={false}
      destroyOnClose
    >
      <Alert
        message={isProfit ? '过早止盈倾向' : '过久持有亏损'}
        description={assessment.reason}
        type={isProfit ? 'warning' : 'error'}
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Descriptions column={2} size="small" bordered>
        <Descriptions.Item label="品种方向">
          <Tag color={assessment.direction === 'LONG' ? '#ff4d4f' : '#52c41a'}>
            {assessment.direction === 'LONG' ? '多头' : '空头'}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="浮动盈亏率">
          <Text strong style={{ color: isProfit ? '#ff4d4f' : '#52c41a' }}>
            {isProfit ? '+' : ''}{pnlPct}%
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="持仓天数">
          <Space>
            <ClockCircleOutlined />
            <Text>{assessment.holdDays} 天</Text>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="建议操作">
          <Tag icon={<CheckCircleOutlined />} color="processing">
            {ACTION_LABELS[assessment.suggestedAction]}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      <Paragraph type="secondary" style={{ marginTop: 12, fontSize: 12, marginBottom: 0 }}>
        处置效应是行为金融学中的常见偏误：投资者倾向于过早卖出盈利头寸、过久持有亏损头寸。
        系统基于您的持仓数据自动检测，仅供参考，不构成投资建议。
      </Paragraph>
    </Modal>
  )
}

export default DispositionAlert
