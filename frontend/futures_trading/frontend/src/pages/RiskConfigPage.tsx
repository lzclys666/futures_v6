/**
 * 风控规则配置页面
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useEffect, useState } from 'react'
import { Card, Table, Tag, Button, Switch, InputNumber, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { SettingOutlined, SaveOutlined } from '@ant-design/icons'
import { useRiskStore } from '../store/useRiskStore'
import type { RiskRule } from '../types/risk'

const { Title } = Typography

const RiskConfigPage: React.FC = () => {
  const { rules, loadRules, updateRiskRule } = useRiskStore()
  const [editing, setEditing] = useState<Partial<Record<RiskRule['ruleId'], Partial<RiskRule>>>>({})

  useEffect(() => {
    loadRules()
  }, [])

  const handleChange = (ruleId: RiskRule['ruleId'], field: string, value: unknown) => {
    setEditing((prev) => ({
      ...prev,
      [ruleId]: { ...prev[ruleId], [field]: value },
    }))
  }

  const handleSave = async (ruleId: RiskRule['ruleId']) => {
    const changes = editing[ruleId]
    if (!changes) return
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
    }
  }

  const columns: ColumnsType<RiskRule> = [
    { title: '规则 ID', dataIndex: 'ruleId', key: 'id', width: 160 },
    { title: '规则名称', dataIndex: 'ruleName', key: 'name', width: 180 },
    { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true },
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
      width: 120,
      render: (v, record) => (
        <InputNumber
          value={editing[record.ruleId]?.threshold ?? v}
          onChange={(val) => handleChange(record.ruleId, 'threshold', val)}
          style={{ width: 100 }}
          precision={2}
        />
      ),
    },
    {
      title: '层级',
      dataIndex: 'layer',
      key: 'layer',
      width: 120,
      render: (v) => (
        <Tag color={v === 'layer1' ? 'green' : v === 'layer2' ? 'orange' : 'red'}>
          {v === 'layer1' ? 'Layer 1' : v === 'layer2' ? 'Layer 2' : 'Layer 3'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<SaveOutlined />}
          disabled={!editing[record.ruleId]}
          onClick={() => handleSave(record.ruleId)}
        >
          保存
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        风控规则配置
      </Title>
      <Card>
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="ruleId"
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  )
}

export default RiskConfigPage
