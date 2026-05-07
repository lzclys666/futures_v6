/**
 * 熔断器面板组件
 * @author YIYI
 * @date 2026-04-30
 */

import React, { useEffect, useState, useRef } from 'react'
import { Card, Tag, Button, Space, Spin, Empty, Modal, Input, List, Tooltip, Progress, Alert, message } from 'antd'
import {
  SafetyOutlined,
  StopOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  WarningOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import {
  fetchCircuitBreaker,
  confirmPause,
  dismiss,
  resume,
} from '../../api/circuitBreaker'
import type { CircuitBreakerResponse, CircuitBreakerStatus } from '../../types/risk'
import './CircuitBreakerPanel.css'

const STATUS_CONFIG: Record<CircuitBreakerStatus, { color: string; text: string; icon: React.ReactNode; cardClass: string }> = {
  RUNNING: { color: '#52c41a', text: '正常运行', icon: <CheckCircleOutlined />, cardClass: 'cb-status-running' },
  PENDING_CONFIRM: { color: '#faad14', text: '待确认', icon: <ClockCircleOutlined />, cardClass: 'cb-status-pending' },
  PAUSED: { color: '#ff4d4f', text: '已暂停', icon: <StopOutlined />, cardClass: 'cb-status-paused' },
  RECOVERING: { color: '#1890ff', text: '恢复中', icon: <ReloadOutlined spin />, cardClass: 'cb-status-recovering' },
}

const ACTION_CONFIG: Record<string, { color: string; text: string }> = {
  PAUSE_CONFIRMED: { color: 'error', text: '确认暂停' },
  PAUSE_AUTO: { color: 'error', text: '自动暂停' },
  DISMISS: { color: 'success', text: '忽略警报' },
  RESUME: { color: 'processing', text: '恢复交易' },
  RECOVER_AUTO: { color: 'processing', text: '自动恢复' },
}

const CircuitBreakerPanel: React.FC = () => {
  const [status, setStatus] = useState<CircuitBreakerResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [confirmModal, setConfirmModal] = useState<'pause' | 'dismiss' | 'resume' | null>(null)
  const [notes, setNotes] = useState('')
  const [reason, setReason] = useState('')
  const [countdown, setCountdown] = useState<number | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const totalConfirmSeconds = 30 * 60 // 30分钟确认窗口

  // 加载状态
  const loadStatus = async () => {
    setLoading(true)
    try {
      const data = await fetchCircuitBreaker()
      setStatus(data)
    } catch (err) {
      console.error('Failed to fetch circuit breaker status:', err)
      message.error('获取熔断器状态失败')
    } finally {
      setLoading(false)
    }
  }

  // 启动轮询（5秒间隔）
  useEffect(() => {
    loadStatus()
    pollingRef.current = setInterval(loadStatus, 5000)
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      if (countdownRef.current) {
        clearInterval(countdownRef.current)
        countdownRef.current = null
      }
    }
  }, [])

  // 倒计时逻辑
  useEffect(() => {
    if (status?.status === 'PENDING_CONFIRM' && status.confirmDeadline) {
      const deadline = new Date(status.confirmDeadline).getTime()
      
      const updateCountdown = () => {
        const remaining = Math.max(0, Math.floor((deadline - Date.now()) / 1000))
        setCountdown(remaining)
        if (remaining <= 0) {
          if (countdownRef.current) clearInterval(countdownRef.current)
        }
      }
      
      updateCountdown()
      countdownRef.current = setInterval(updateCountdown, 1000)
      
      return () => {
        if (countdownRef.current) {
          clearInterval(countdownRef.current)
          countdownRef.current = null
        }
      }
    } else {
      setCountdown(null)
    }
  }, [status?.status, status?.confirmDeadline])

  // 确认暂停
  const handleConfirmPause = async () => {
    if (!notes.trim()) {
      message.warning('请填写备注')
      return
    }
    try {
      const data = await confirmPause({ confirmed_by: 'user', notes })
      setStatus(data)
      setConfirmModal(null)
      setNotes('')
      message.success('已确认暂停交易')
    } catch (err) {
      message.error('操作失败：' + String(err))
    }
  }

  // 忽略警报
  const handleDismiss = async () => {
    if (!reason.trim()) {
      message.warning('请填写忽略原因')
      return
    }
    if (reason.trim().length < 10) {
      message.warning('忽略原因至少需要10个字符')
      return
    }
    try {
      const data = await dismiss({ confirmed_by: 'user', reason })
      setStatus(data)
      setConfirmModal(null)
      setReason('')
      message.success('已忽略警报')
    } catch (err) {
      message.error('操作失败：' + String(err))
    }
  }

  // 恢复交易
  const handleResume = async () => {
    try {
      const data = await resume({ confirmed_by: 'user' })
      setStatus(data)
      setConfirmModal(null)
      message.success('已恢复交易')
    } catch (err) {
      message.error('操作失败：' + String(err))
    }
  }

  const cfg = status ? STATUS_CONFIG[status.status] : STATUS_CONFIG.RUNNING

  return (
    <div className="circuit-breaker-panel">
      {/* 状态卡片 */}
      <Card
        className={`cbp-header-card ${cfg.cardClass}`}
        title={
          <Space>
            <SafetyOutlined />
            <span>熔断器状态</span>
            <Tag color={cfg.color} style={{ fontSize: 14, padding: '4px 12px' }}>
              {cfg.icon} {cfg.text}
            </Tag>
          </Space>
        }
        extra={
          <Tooltip title="刷新状态">
            <Button size="small" icon={<ReloadOutlined spin={loading} />} onClick={loadStatus}>
              刷新
            </Button>
          </Tooltip>
        }
      >
      {loading && !status ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin /><div style={{ marginTop: 8, color: '#8c8c8c' }}>加载中...</div>
          </div>
        ) : !status ? (
          <Empty description="状态未加载" />
        ) : (
          <>
            {/* 警报信息 */}
            {status.status === 'PENDING_CONFIRM' && (
              <Alert
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                message={`检测到 ${status.triggerCondition || '市场异常'}`}
                description={`同向极端：${(status.sameDirectionPct != null ? status.sameDirectionPct * 100 : 0).toFixed(0)}% 品种同向`}
                style={{ marginBottom: 16 }}
              />
            )}

            {/* 倒计时 */}
            {countdown !== null && countdown > 0 && (
              <div style={{ marginBottom: 16 }}>
                <Progress
                  percent={Math.min(100, (countdown / totalConfirmSeconds) * 100)}
                  status="active"
                  strokeColor="#faad14"
                  format={() => `确认截止：${Math.floor(countdown / 60)}:${(countdown % 60).toString().padStart(2, '0')}`}
                />
              </div>
            )}

            {/* 数据展示 */}
            <div className="cbp-stats" style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>同向比例</div>
                <div style={{ fontSize: 24, fontWeight: 600 }}>
                  {(status.sameDirectionPct != null ? status.sameDirectionPct * 100 : 0).toFixed(0)}%
                </div>
              </div>
              {status.sameDirectionData && (
                <>
                  <div>
                    <div style={{ fontSize: 12, color: '#52c41a' }}>做多品种</div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>
                      {status.sameDirectionData.longSymbols?.join(', ') || '-'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#ff4d4f' }}>做空品种</div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>
                      {status.sameDirectionData.shortSymbols?.slice(0, 5).join(', ')}
                      {status.sameDirectionData.shortSymbols?.length > 5 && '...'}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* 操作按钮 */}
            <Space wrap>
              {status.status === 'PENDING_CONFIRM' && (
                <>
                  <Button type="primary" danger icon={<StopOutlined />} onClick={() => setConfirmModal('pause')}>
                    确认暂停交易
                  </Button>
                  <Button icon={<CheckCircleOutlined />} onClick={() => setConfirmModal('dismiss')}>
                    忽略警报
                  </Button>
                </>
              )}
              {status.status === 'PAUSED' && (
                <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => setConfirmModal('resume')}>
                  恢复交易
                </Button>
              )}
            </Space>
          </>
        )}
      </Card>

      {/* 操作历史 */}
      {status?.history && status.history.length > 0 && (
        <Card
          className="cbp-history-card"
          title="操作历史（最近5条）"
          size="small"
          style={{ marginTop: 16 }}
        >
          <List
            dataSource={status.history.slice(0, 5)}
            renderItem={(item) => {
              const actionCfg = ACTION_CONFIG[item.action] || { color: 'default', text: item.action }
              return (
                <List.Item>
                  <Space>
                    <Tag color={actionCfg.color}>{actionCfg.text}</Tag>
                    <span style={{ color: '#8c8c8c', fontSize: 12 }}>
                      {new Date(item.timestamp).toLocaleString('zh-CN')}
                    </span>
                    {item.notes && <span style={{ fontSize: 12 }}>{item.notes}</span>}
                    {item.operator && <Tag>{item.operator}</Tag>}
                  </Space>
                </List.Item>
              )
            }}
          />
        </Card>
      )}

      {/* 确认暂停弹窗 */}
      <Modal
        title="确认暂停交易"
        open={confirmModal === 'pause'}
        onOk={handleConfirmPause}
        onCancel={() => { setConfirmModal(null); setNotes('') }}
        okText="确认暂停"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <p>您确定要暂停交易吗？暂停后仅允许平仓，禁止开新仓。</p>
        <Input.TextArea
          placeholder="请填写备注（必填）"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </Modal>

      {/* 忽略警报弹窗 */}
      <Modal
        title="忽略警报"
        open={confirmModal === 'dismiss'}
        onOk={handleDismiss}
        onCancel={() => { setConfirmModal(null); setReason('') }}
        okText="确认忽略"
        cancelText="取消"
      >
        <Alert
          type="warning"
          message="风险提示"
          description="忽略警报后交易将继续，您将自行承担所有风险。"
          style={{ marginBottom: 16 }}
        />
        <Input.TextArea
          placeholder="请填写忽略原因（必填，至少10字）"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
        />
      </Modal>

      {/* 恢复交易弹窗 */}
      <Modal
        title="恢复交易"
        open={confirmModal === 'resume'}
        onOk={handleResume}
        onCancel={() => setConfirmModal(null)}
        okText="确认恢复"
        cancelText="取消"
      >
        <p>确认恢复交易吗？恢复后系统将正常下单。</p>
      </Modal>
    </div>
  )
}

export default CircuitBreakerPanel