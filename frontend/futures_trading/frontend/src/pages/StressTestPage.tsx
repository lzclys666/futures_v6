/**
 * 压力测试报告页面
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useState } from 'react'
import { Card, Select, Button, Table, Tag, Statistic, Row, Col, Typography, Empty } from 'antd'
import { ThunderboltOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useRiskStore } from '../store/useRiskStore'

const { Title, Text } = Typography

const StressTestPage: React.FC = () => {
  const [symbol, setSymbol] = useState('AU')
  const { stressReport, runStressTest, stressLoading } = useRiskStore()

  const handleRun = () => {
    runStressTest({ symbol })
  }

  const columns = [
    { title: '场景', dataIndex: 'scenarioName', key: 'name' },
    { title: '预计盈亏', dataIndex: 'estimatedPnl', key: 'pnl', align: 'right' as const, render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v?.toFixed(0)}</Text> },
    { title: '盈亏率', dataIndex: 'estimatedPnlPct', key: 'pnlPct', align: 'right' as const, render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{(v * 100)?.toFixed(2)}%</Text> },
    { title: '风控触发', dataIndex: 'riskTriggered', key: 'risk', render: (v: boolean) => <Tag color={v ? 'error' : 'success'}>{v ? '是' : '否'}</Tag> },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <ThunderboltOutlined style={{ marginRight: 8 }} />
        压力测试报告
      </Title>

      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <Select value={symbol} onChange={setSymbol} style={{ width: 160 }} options={[{ value: 'AU', label: 'AU (黄金)' }, { value: 'AG', label: 'AG (白银)' }, { value: 'CU', label: 'CU (铜)' }, { value: 'ZN', label: 'ZN (锌)' }]} />
          <Button type="primary" icon={<PlayCircleOutlined />} loading={stressLoading} onClick={handleRun}>
            运行测试
          </Button>
        </div>
      </Card>

      {stressReport ? (
        <div>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} md={6}>
              <Card size="small"><Statistic title="当前盈亏" value={stressReport.currentPnl} precision={0} suffix="元" /></Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small"><Statistic title="最坏场景" value={stressReport.worstCase?.scenarioName || '--'} /></Card>
            </Col>
          </Row>
          <Card title="场景结果" size="small">
            <Table columns={columns} dataSource={stressReport.scenarios} rowKey="scenarioId" pagination={false} />
          </Card>
          {stressReport.recommendations.length > 0 && (
            <Card title="建议" size="small" style={{ marginTop: 16 }}>
              {stressReport.recommendations.map((r: string, i: number) => (
                <div key={i} style={{ padding: '4px 0' }}>• {r}</div>
              ))}
            </Card>
          )}
        </div>
      ) : (
        <Empty description="选择品种并点击「运行测试」" />
      )}
    </div>
  )
}

export default StressTestPage
