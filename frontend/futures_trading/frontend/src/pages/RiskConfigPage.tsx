/**
 * 风控规则配置页面 v2
 * 功能：规则列表 + 规则详情展开 + 模拟测试 + 风控状态 + 预检
 * @author Lucy
 * @date 2026-05-06
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Switch,
  InputNumber,
  Slider,
  Tooltip,
  Badge,
  Typography,
  message,
  Row,
  Col,
  Statistic,
  Select,
  Input,
  Form,
  Space,
  Descriptions,
  Alert,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  SettingOutlined,
  SaveOutlined,
  LoadingOutlined,
  SafetyOutlined,
  ExperimentOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { useRiskStore } from '../store/useRiskStore'
import { useRiskWebSocket } from '../hooks/useRiskWebSocket'
import type { RiskRule, RiskLayerKey, RiskStatusResponse } from '../types/risk'
import type { SimulateResult } from '../api/risk'

const { Title, Text } = Typography
const { Option } = Select

// ---------- 常量 ----------

const LAYER_CONFIG: Record<RiskLayerKey, { label: string; color: string; desc: string }> = {
  1: { label: 'Layer 1 · 基础风控', color: '#1890ff', desc: '宏观熔断 · 波动率 · 流动性' },
  2: { label: 'Layer 2 · 进阶风控', color: '#722ed1', desc: '亏损限制 · 连续亏损 · 处置效应' },
  3: { label: 'Layer 3 · 仓位风控', color: '#13c2c2', desc: '持仓 · 保证金 · 集中度' },
}

const SEVERITY_TAG: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
  PASS: { color: 'success', text: '通过', icon: <CheckCircleOutlined /> },
  WARN: { color: 'warning', text: '警告', icon: <WarningOutlined /> },
  BLOCK: { color: 'error', text: '阻断', icon: <CloseCircleOutlined /> },
}

const DIRECTION_OPTIONS = [
  { value: 'LONG', label: '做多' },
  { value: 'SHORT', label: '做空' },
]

// ---------- 辅助函数 ----------

function getSliderRange(threshold: number): [number, number] {
  if (threshold < 0) return [threshold * 2, 0]
  if (threshold <= 1) return [0, 1]
  return [threshold * 0.5, threshold * 1.5]
}

function getSliderStep(threshold: number): number {
  return threshold <= 1 ? 0.01 : 1
}

/** 规则 ID 对应的详细描述（展开行用） */
const RULE_DETAIL: Record<string, { trigger: string; example: string; unit: string }> = {
  R1_SINGLE_SYMBOL: { trigger: '单一品种持仓占总权益比例超过阈值', example: '总权益100万，阈值30%→单品种最多30万', unit: '比例' },
  R2_DAILY_LOSS: { trigger: '当日累计亏损超过总权益阈值比例', example: '总权益100万，阈值5%→当日最大亏损5万', unit: '比例' },
  R3_PRICE_LIMIT: { trigger: '总持仓保证金占总权益比例超过阈值', example: '总权益100万，阈值80%→最多占用80万保证金', unit: '比例' },
  R4_TOTAL_MARGIN: { trigger: '保证金占用率实时超过阈值', example: '阈值90%→保证金占用率超90%时阻断', unit: '比例' },
  R5_VOLATILITY: { trigger: 'ATR波动率超过阈值时禁止开仓', example: 'ATR=0.03，阈值0.05→通过', unit: '比例' },
  R6_LIQUIDITY: { trigger: '日均成交量低于阈值时禁止开仓', example: '日均5000手，阈值1000手→通过', unit: '手' },
  R7_CONSECUTIVE_LOSS: { trigger: '连续亏损笔数达到阈值时暂停交易', example: '连续3笔亏损→暂停', unit: '笔' },
  R8_TRADING_HOURS: { trigger: '最大回撤超过阈值时减仓', example: '回撤5%，阈值15%→通过', unit: '比例' },
  R9_CAPITAL_SUFFICIENCY: { trigger: '单一板块持仓集中度超过阈值', example: '有色板块占比30%，阈值50%→通过', unit: '比例' },
  R10_MACRO_CIRCUIT_BREAKER: { trigger: '宏观打分低于阈值时禁止开仓', example: '宏观打分0.45，阈值-0.5→通过', unit: '分' },
  R11_DISPOSITION_EFFECT: { trigger: '盈利单平均持仓时间低于阈值（小时）', example: '平均持仓48h，阈值24h→通过', unit: '小时' },
  R12_CANCEL_LIMIT: { trigger: '撤单次数达到阈值时限制交易', example: '当日撤单0次，阈值10次→通过', unit: '次' },
}

// ---------- 子组件 ----------

/** 风控状态总览卡片 */
interface StatusOverviewProps {
  wsData: ReturnType<typeof useRiskWebSocket>['riskStatus']
  wsConnected: boolean
  wsError: string | null
}

const StatusOverview: React.FC<StatusOverviewProps> = ({ wsData, wsConnected, wsError }) => {
  const { status, loadStatus, statusLoading } = useRiskStore()

  useEffect(() => {
    // WebSocket 未连接时 fallback 到 REST 轮询
    if (!wsConnected) {
      loadStatus()
    }
  }, [wsConnected, loadStatus])

  // 优先使用 WebSocket 实时数据，fallback 到 REST API 数据
  const mergedStatus: RiskStatusResponse | null = useMemo(() => {
    if (wsData) {
      // WS 推送的数据缺少 date/triggeredCount/circuitBreaker，需补充
      const rules = wsData.rules ?? []
      const triggeredCount = rules.filter((r) => r.severity !== 'PASS').length
      return {
        date: new Date().toISOString().slice(0, 10),
        overallStatus: wsData.overallStatus,
        rules,
        triggeredCount,
        circuitBreaker: wsData.overallStatus === 'BLOCK',
        updatedAt: wsData.updatedAt,
      }
    }
    return status
  }, [wsData, status])

  const overallStatus = mergedStatus?.overallStatus ?? 'PASS'
  const triggeredCount = mergedStatus?.triggeredCount ?? 0
  const totalCount = mergedStatus?.rules?.length ?? 0
  const circuitBreaker = mergedStatus?.circuitBreaker ?? false

  return (
    <Card
      size="small"
      title={
        <Space>
          <SafetyOutlined />
          <span>风控状态总览</span>
          <Tag color={SEVERITY_TAG[overallStatus]?.color} icon={SEVERITY_TAG[overallStatus]?.icon}>
            {SEVERITY_TAG[overallStatus]?.text}
          </Tag>
          {circuitBreaker && <Tag color="error">已熔断</Tag>}
        </Space>
      }
      extra={
        <Space>
          {/* WebSocket 连接状态指示器 */}
          <Tooltip title={wsConnected ? 'WebSocket 已连接（实时）' : wsError ? `WebSocket 错误: ${wsError}` : 'WebSocket 未连接（REST 轮询）'}>
            <Badge
              status={wsConnected ? 'success' : 'error'}
              text={<Text type="secondary" style={{ fontSize: 11 }}>{wsConnected ? '实时' : '离线'}</Text>}
            />
          </Tooltip>
          <Button size="small" icon={<ReloadOutlined spin={statusLoading} />} onClick={loadStatus}>
            刷新
          </Button>
        </Space>
      }
    >
      <Row gutter={[16, 12]}>
        <Col xs={12} sm={6}>
          <Statistic title="规则总数" value={totalCount} suffix="条" />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="触发规则"
            value={triggeredCount}
            suffix="条"
            valueStyle={{ color: triggeredCount > 0 ? '#ff4d4f' : '#52c41a' }}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="通过率"
            value={totalCount > 0 ? ((totalCount - triggeredCount) / totalCount * 100).toFixed(1) : 100}
            suffix="%"
            valueStyle={{ color: triggeredCount === 0 ? '#52c41a' : '#faad14' }}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="熔断状态"
            value={circuitBreaker ? '已触发' : '正常'}
            valueStyle={{ color: circuitBreaker ? '#ff4d4f' : '#52c41a' }}
          />
        </Col>
      </Row>

      {/* 各层级状态摘要 */}
      {mergedStatus?.rules && (
        <Row gutter={8} style={{ marginTop: 12 }}>
          {([1, 2, 3] as RiskLayerKey[]).map((layer) => {
            const layerRules = mergedStatus.rules.filter((r) => r.layer === layer)
            const blocked = layerRules.filter((r) => r.severity !== 'PASS').length
            const cfg = LAYER_CONFIG[layer]
            return (
              <Col xs={24} sm={8} key={layer}>
                <div
                  style={{
                    padding: '6px 10px',
                    borderRadius: 6,
                    border: `1px solid ${blocked > 0 ? '#ffccc7' : '#d9d9d9'}`,
                    background: blocked > 0 ? '#fff2f0' : '#f6ffed',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Text style={{ fontSize: 12, color: cfg.color, fontWeight: 600 }}>{cfg.label}</Text>
                  <Space size={4}>
                    <Text type="secondary" style={{ fontSize: 11 }}>{layerRules.length}条</Text>
                    {blocked > 0 && <Tag color="error" style={{ fontSize: 11, lineHeight: '16px', padding: '0 4px' }}>{blocked}触发</Tag>}
                  </Space>
                </div>
              </Col>
            )
          })}
        </Row>
      )}
    </Card>
  )
}

/** 模拟测试面板 */
const SimulatePanel: React.FC = () => {
  const { simulateResult, simulateLoading, precheckResult, precheckLoading, runSimulate, precheckOrder } = useRiskStore()
  const [form] = Form.useForm()
  const [mode, setMode] = useState<'simulate' | 'precheck'>('simulate')

  const handleRun = useCallback(async () => {
    try {
      const values = await form.validateFields()
      if (mode === 'simulate') {
        await runSimulate(values)
      } else {
        await precheckOrder(values)
      }
    } catch {
      // validation error
    }
  }, [form, mode, runSimulate, precheckOrder])

  const result = mode === 'simulate' ? simulateResult : precheckResult
  const loading = mode === 'simulate' ? simulateLoading : precheckLoading

  const renderResult = (r: SimulateResult | null) => {
    if (!r) return null
    const hasViolations = r.violations.length > 0
    return (
      <div style={{ marginTop: 12 }}>
        <Alert
          type={r.pass ? 'success' : 'error'}
          showIcon
          icon={r.pass ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          message={r.pass ? '风控检查通过' : '风控检查未通过'}
          description={
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                检查 {r.checkedRules} 条规则 · {new Date(r.timestamp).toLocaleTimeString()}
              </Text>
            </div>
          }
        />
        {hasViolations && (
          <div style={{ marginTop: 8 }}>
            {r.violations.map((v, i) => (
              <Alert
                key={i}
                type={v.severity === 'BLOCK' ? 'error' : 'warning'}
                style={{ marginTop: 4 }}
                message={
                  <Space>
                    <Tag color={v.severity === 'BLOCK' ? 'error' : 'warning'} style={{ margin: 0 }}>
                      {v.ruleId}
                    </Tag>
                    <Text>{v.ruleName}</Text>
                  </Space>
                }
                description={v.message}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <ExperimentOutlined />
          <span>风控模拟测试</span>
        </Space>
      }
    >
      <Form form={form} layout="inline" initialValues={{ symbol: 'IF', direction: 'LONG', price: 4000, volume: 10 }}>
        <Row gutter={[8, 8]} style={{ width: '100%' }}>
          <Col xs={12} sm={6}>
            <Form.Item name="symbol" label="品种" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
              <Input placeholder="如 IF" style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col xs={12} sm={6}>
            <Form.Item name="direction" label="方向" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
              <Select style={{ width: '100%' }}>
                {DIRECTION_OPTIONS.map((o) => (
                  <Option key={o.value} value={o.value}>{o.label}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={12} sm={4}>
            <Form.Item name="price" label="价格" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
              <InputNumber style={{ width: '100%' }} min={0} precision={2} />
            </Form.Item>
          </Col>
          <Col xs={12} sm={4}>
            <Form.Item name="volume" label="数量" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
              <InputNumber style={{ width: '100%' }} min={1} precision={0} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={4}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Select value={mode} onChange={setMode} size="small" style={{ width: 80 }}>
                <Option value="simulate">模拟</Option>
                <Option value="precheck">预检</Option>
              </Select>
              <Button type="primary" icon={<ExperimentOutlined />} loading={loading} onClick={handleRun}>
                运行
              </Button>
            </Space>
          </Col>
        </Row>
      </Form>
      {renderResult(result)}
    </Card>
  )
}

// ---------- 主页面 ----------

const RiskConfigPage: React.FC = () => {
  const { rules, rulesLoading, loadRules, updateRiskRule } = useRiskStore()
  const { riskStatus: wsData, connected: wsConnected, error: wsError } = useRiskWebSocket()
  const [editing, setEditing] = useState<Partial<Record<RiskRule['ruleId'], Partial<RiskRule>>>>({})
  const [savingMap, setSavingMap] = useState<Record<string, boolean>>({})
  const [sliderMode, setSliderMode] = useState<Record<string, boolean>>({})
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([])

  useEffect(() => {
    loadRules()
  }, [loadRules])

  const editingRef = useRef(editing)
  editingRef.current = editing

  const handleChange = useCallback(
    (ruleId: RiskRule['ruleId'], field: string, value: unknown) => {
      setEditing((prev) => ({
        ...prev,
        [ruleId]: { ...prev[ruleId], [field]: value },
      }))
    },
    [],
  )

  const handleSave = useCallback(
    async (ruleId: RiskRule['ruleId']) => {
      const changes = editingRef.current[ruleId]
      if (!changes) return
      setSavingMap((prev) => ({ ...prev, [ruleId]: true }))
      try {
        await updateRiskRule({ ruleId, ...changes })
        message.success('规则已更新')
        setEditing((prev) => {
          const next = { ...prev }
          delete next[ruleId]
          return next
        })
      } catch {
        message.error('更新失败')
      } finally {
        setSavingMap((prev) => {
          const next = { ...prev }
          delete next[ruleId]
          return next
        })
      }
    },
    [updateRiskRule],
  )

  const isDirty = useCallback(
    (record: RiskRule): boolean => {
      const changes = editingRef.current[record.ruleId]
      if (!changes) return false
      return (
        (changes.enabled !== undefined && changes.enabled !== record.enabled) ||
        (changes.threshold !== undefined && changes.threshold !== record.threshold)
      )
    },
    [],
  )

  /** 展开行渲染：规则详情 */
  const expandedRowRender = useCallback((record: RiskRule) => {
    const detail = RULE_DETAIL[record.ruleId]
    const status = useRiskStore.getState().status?.rules?.find((r) => r.ruleId === record.ruleId)
    const severityInfo = status ? SEVERITY_TAG[status.severity] : null
    const layerInfo = LAYER_CONFIG[record.layer as RiskLayerKey]

    return (
      <div style={{ padding: '8px 0' }}>
        <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} bordered>
          <Descriptions.Item label="规则 ID">
            <Tag>{record.ruleId}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="层级">
            <Tag color={layerInfo?.color}>{layerInfo?.label ?? `Layer ${record.layer}`}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="启用状态">
            <Tag color={record.enabled ? 'success' : 'default'}>{record.enabled ? '已启用' : '已禁用'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="阈值" span={1}>
            <Text strong>{record.threshold}</Text>
            {detail?.unit && <Text type="secondary"> ({detail.unit})</Text>}
          </Descriptions.Item>
          {record.warnThreshold !== undefined && (
            <Descriptions.Item label="告警阈值">
              <Text type="warning">{record.warnThreshold}</Text>
            </Descriptions.Item>
          )}
          {status && (
            <>
              <Descriptions.Item label="当前值">
                <Text>{status.currentValue}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="运行状态">
                <Tag color={severityInfo?.color} icon={severityInfo?.icon}>
                  {severityInfo?.text}
                </Tag>
              </Descriptions.Item>
            </>
          )}
          <Descriptions.Item label="触发条件" span={2}>
            {detail?.trigger ?? record.description}
          </Descriptions.Item>
          <Descriptions.Item label="示例" span={1}>
            <Text type="secondary">{detail?.example ?? '-'}</Text>
          </Descriptions.Item>
        </Descriptions>
      </div>
    )
  }, [])

  const columns: ColumnsType<RiskRule> = useMemo(
    () => [
      {
        title: '',
        key: 'dirty',
        width: 32,
        render: (_, record) =>
          isDirty(record) ? <Badge color="#faad14" /> : <Badge color="transparent" />,
      },
      { title: '规则 ID', dataIndex: 'ruleId', key: 'id', width: 160 },
      { title: '规则名称', dataIndex: 'ruleName', key: 'name', width: 160 },
      {
        title: '层级',
        dataIndex: 'layer',
        key: 'layer',
        width: 120,
        render: (v: number) => {
          const info = LAYER_CONFIG[v as RiskLayerKey]
          return info ? <Tag color={info.color}>{info.label}</Tag> : <Tag>Layer {v}</Tag>
        },
      },
      {
        title: '启用',
        dataIndex: 'enabled',
        key: 'enabled',
        width: 80,
        render: (v, record) => (
          <Switch
            checked={editing[record.ruleId]?.enabled ?? v}
            onChange={(checked) => handleChange(record.ruleId, 'enabled', checked)}
          />
        ),
      },
      {
        title: '阈值',
        dataIndex: 'threshold',
        key: 'threshold',
        width: 260,
        render: (v, record) => {
          const currentValue = editing[record.ruleId]?.threshold ?? v
          const useSlider = sliderMode[record.ruleId]
          const [min, max] = getSliderRange(v)
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {useSlider ? (
                <Slider
                  style={{ flex: 1, margin: 0 }}
                  min={min}
                  max={max}
                  step={getSliderStep(v)}
                  value={currentValue}
                  onChange={(val) => handleChange(record.ruleId, 'threshold', val)}
                />
              ) : (
                <InputNumber
                  value={currentValue}
                  onChange={(val) => handleChange(record.ruleId, 'threshold', val)}
                  style={{ width: 100 }}
                  precision={2}
                />
              )}
              <Switch
                size="small"
                checked={useSlider}
                checkedChildren="滑"
                unCheckedChildren="数"
                onChange={(on) => setSliderMode((prev) => ({ ...prev, [record.ruleId]: on }))}
              />
            </div>
          )
        },
      },
      {
        title: '描述',
        dataIndex: 'description',
        key: 'desc',
        ellipsis: true,
        render: (v: string) => (
          <Tooltip title={v}>
            <span>{v}</span>
          </Tooltip>
        ),
      },
      {
        title: '操作',
        key: 'action',
        width: 100,
        render: (_, record) => {
          const saving = savingMap[record.ruleId]
          const dirty = isDirty(record)
          return (
            <Button
              type="primary"
              size="small"
              icon={saving ? <LoadingOutlined /> : <SaveOutlined />}
              disabled={!dirty}
              loading={saving}
              onClick={() => handleSave(record.ruleId)}
            >
              保存
            </Button>
          )
        },
      },
    ],
    [editing, savingMap, sliderMode, isDirty, handleChange, handleSave],
  )

  return (
    <div style={{ padding: '0 4px' }}>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        风控规则配置
      </Title>

      {/* 上半部分：状态总览 + 模拟测试 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <StatusOverview wsData={wsData} wsConnected={wsConnected} wsError={wsError} />
        </Col>
        <Col xs={24} lg={12}>
          <SimulatePanel />
        </Col>
      </Row>

      {/* WebSocket 断开连接横幅 */}
      {!wsConnected && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="实时连接已断开，当前使用 REST 轮询（10 秒刷新）"
          style={{ marginBottom: 16 }}
          banner
        />
      )}

      {/* 下半部分：规则列表 */}
      <Card
        size="small"
        title={
          <Space>
            <InfoCircleOutlined />
            <span>规则列表（R1-R12）</span>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
              点击行展开详情
            </Text>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="ruleId"
          loading={rulesLoading}
          pagination={false}
          scroll={{ x: 1100 }}
          expandable={{
            expandedRowRender,
            expandedRowKeys,
            onExpandedRowsChange: (keys) => setExpandedRowKeys(keys as React.Key[]),
            rowExpandable: (record) => !!RULE_DETAIL[record.ruleId],
          }}
          size="small"
        />
      </Card>
    </div>
  )
}

export default RiskConfigPage
