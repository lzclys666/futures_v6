/**
 * 因子仪表盘
 * 展示所有品种的因子 IC 热力图、因子权重、因子贡献
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useState } from 'react'
import { Card, Typography, Row, Col, Select, Spin, Empty, Table, Tag, Tooltip } from 'antd'
import { BarChartOutlined, HeatMapOutlined, ProjectOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

/** IC 热力图数据类型 */
interface ICHeatmapRow {
  factorName: string
  icMean: number
  icStd: number
  icir: number
  rankIcMean: number
  rankIcir: number
  weight: number
  contribution: number
  direction: 'positive' | 'negative' | 'neutral'
}

/** Mock IC 热力图数据 */
const MOCK_IC_HEATMAP: Record<string, ICHeatmapRow[]> = {
  RU: [
    { factorName: '铜', icMean: 0.053, icStd: 0.089, icir: 0.595, rankIcMean: 0.061, rankIcir: 0.68, weight: 0.18, contribution: 0.32, direction: 'positive' },
    { factorName: '金', icMean: 0.041, icStd: 0.078, icir: 0.526, rankIcMean: 0.048, rankIcir: 0.59, weight: 0.15, contribution: 0.25, direction: 'positive' },
    { factorName: '原油', icMean: -0.032, icStd: 0.095, icir: -0.337, rankIcMean: -0.028, rankIcir: -0.29, weight: 0.14, contribution: -0.18, direction: 'negative' },
    { factorName: '美债', icMean: 0.029, icStd: 0.082, icir: 0.354, rankIcMean: 0.033, rankIcir: 0.41, weight: 0.12, contribution: 0.15, direction: 'positive' },
    { factorName: '标普', icMean: -0.021, icStd: 0.071, icir: -0.296, rankIcMean: -0.019, rankIcir: -0.25, weight: 0.10, contribution: -0.08, direction: 'negative' },
    { factorName: '黄金', icMean: 0.055, icStd: 0.091, icir: 0.604, rankIcMean: 0.064, rankIcir: 0.71, weight: 0.16, contribution: 0.38, direction: 'positive' },
    { factorName: '工业', icMean: -0.018, icStd: 0.066, icir: -0.273, rankIcMean: -0.015, rankIcir: -0.22, weight: 0.08, contribution: -0.06, direction: 'negative' },
    { factorName: '农产品', icMean: 0.009, icStd: 0.058, icir: 0.155, rankIcMean: 0.011, rankIcir: 0.18, weight: 0.07, contribution: 0.03, direction: 'neutral' },
  ],
  AG: [
    { factorName: '铜', icMean: 0.038, icStd: 0.085, icir: 0.447, rankIcMean: 0.044, rankIcir: 0.52, weight: 0.16, contribution: 0.22, direction: 'positive' },
    { factorName: '金', icMean: 0.062, icStd: 0.097, icir: 0.639, rankIcMean: 0.071, rankIcir: 0.74, weight: 0.22, contribution: 0.48, direction: 'positive' },
    { factorName: '原油', icMean: -0.025, icStd: 0.088, icir: -0.284, rankIcMean: -0.022, rankIcir: -0.24, weight: 0.13, contribution: -0.12, direction: 'negative' },
    { factorName: '美债', icMean: 0.021, icStd: 0.074, icir: 0.284, rankIcMean: 0.025, rankIcir: 0.33, weight: 0.11, contribution: 0.09, direction: 'positive' },
    { factorName: '标普', icMean: -0.015, icStd: 0.068, icir: -0.221, rankIcMean: -0.013, rankIcir: -0.18, weight: 0.09, contribution: -0.05, direction: 'negative' },
    { factorName: '黄金', icMean: 0.058, icStd: 0.094, icir: 0.617, rankIcMean: 0.067, rankIcir: 0.72, weight: 0.20, contribution: 0.44, direction: 'positive' },
    { factorName: '工业', icMean: -0.012, icStd: 0.061, icir: -0.197, rankIcMean: -0.010, rankIcir: -0.16, weight: 0.06, contribution: -0.03, direction: 'neutral' },
    { factorName: '农产品', icMean: 0.007, icStd: 0.052, icir: 0.135, rankIcMean: 0.009, rankIcir: 0.16, weight: 0.03, contribution: 0.01, direction: 'neutral' },
  ],
  AU: [
    { factorName: '铜', icMean: 0.028, icStd: 0.072, icir: 0.389, rankIcMean: 0.033, rankIcir: 0.45, weight: 0.14, contribution: 0.15, direction: 'positive' },
    { factorName: '金', icMean: 0.071, icStd: 0.103, icir: 0.689, rankIcMean: 0.082, rankIcir: 0.79, weight: 0.25, contribution: 0.55, direction: 'positive' },
    { factorName: '原油', icMean: -0.019, icStd: 0.081, icir: -0.235, rankIcMean: -0.017, rankIcir: -0.20, weight: 0.12, contribution: -0.08, direction: 'negative' },
    { factorName: '美债', icMean: 0.034, icStd: 0.079, icir: 0.430, rankIcMean: 0.039, rankIcir: 0.50, weight: 0.13, contribution: 0.18, direction: 'positive' },
    { factorName: '标普', icMean: -0.011, icStd: 0.065, icir: -0.169, rankIcMean: -0.009, rankIcir: -0.14, weight: 0.08, contribution: -0.03, direction: 'neutral' },
    { factorName: '黄金', icMean: 0.068, icStd: 0.101, icir: 0.673, rankIcMean: 0.079, rankIcir: 0.77, weight: 0.23, contribution: 0.51, direction: 'positive' },
    { factorName: '工业', icMean: -0.008, icStd: 0.055, icir: -0.145, rankIcMean: -0.007, rankIcir: -0.12, weight: 0.03, contribution: -0.01, direction: 'neutral' },
    { factorName: '农产品', icMean: 0.004, icStd: 0.048, icir: 0.083, rankIcMean: 0.005, rankIcir: 0.10, weight: 0.02, contribution: 0.01, direction: 'neutral' },
  ],
  RB: [
    { factorName: '铜', icMean: 0.048, icStd: 0.092, icir: 0.522, rankIcMean: 0.056, rankIcir: 0.61, weight: 0.19, contribution: 0.35, direction: 'positive' },
    { factorName: '金', icMean: 0.032, icStd: 0.081, icir: 0.395, rankIcMean: 0.038, rankIcir: 0.46, weight: 0.14, contribution: 0.20, direction: 'positive' },
    { factorName: '原油', icMean: -0.044, icStd: 0.098, icir: -0.449, rankIcMean: -0.039, rankIcir: -0.38, weight: 0.17, contribution: -0.28, direction: 'negative' },
    { factorName: '美债', icMean: 0.022, icStd: 0.076, icir: 0.289, rankIcMean: 0.026, rankIcir: 0.34, weight: 0.11, contribution: 0.11, direction: 'positive' },
    { factorName: '标普', icMean: -0.017, icStd: 0.069, icir: -0.246, rankIcMean: -0.015, rankIcir: -0.20, weight: 0.09, contribution: -0.06, direction: 'negative' },
    { factorName: '黄金', icMean: 0.036, icStd: 0.086, icir: 0.419, rankIcMean: 0.042, rankIcir: 0.49, weight: 0.16, contribution: 0.24, direction: 'positive' },
    { factorName: '工业', icMean: -0.028, icStd: 0.073, icir: -0.384, rankIcMean: -0.024, rankIcir: -0.32, weight: 0.10, contribution: -0.14, direction: 'negative' },
    { factorName: '农产品', icMean: 0.006, icStd: 0.051, icir: 0.118, rankIcMean: 0.007, rankIcir: 0.14, weight: 0.04, contribution: 0.02, direction: 'neutral' },
  ],
}

const SYMBOLS = ['RU', 'AG', 'AU', 'RB']

const FactorDashboardPage: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('RU')
  const [loading] = useState(false)

  const data = MOCK_IC_HEATMAP[selectedSymbol] || []

  const columns = [
    {
      title: '因子',
      dataIndex: 'factorName',
      key: 'factorName',
      width: 100,
      render: (v: string, row: ICHeatmapRow) => (
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
      title: 'IC 均值',
      dataIndex: 'icMean',
      key: 'icMean',
      width: 90,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v > 0 ? '+' : ''}{v.toFixed(3)}
        </span>
      ),
    },
    {
      title: 'IC 标准差',
      dataIndex: 'icStd',
      key: 'icStd',
      width: 90,
      render: (v: number) => <span style={{ color: '#8c8c8c' }}>{v.toFixed(3)}</span>,
    },
    {
      title: 'ICIR',
      dataIndex: 'icir',
      key: 'icir',
      width: 80,
      render: (v: number) => (
        <span style={{ color: v > 0.3 ? '#52c41a' : v > 0 ? '#faad14' : '#ff4d4f', fontWeight: 500 }}>
          {v.toFixed(3)}
        </span>
      ),
    },
    {
      title: 'Rank ICIR',
      dataIndex: 'rankIcir',
      key: 'rankIcir',
      width: 90,
      render: (v: number) => (
        <span style={{ color: v > 0.3 ? '#52c41a' : v > 0 ? '#faad14' : '#ff4d4f', fontWeight: 500 }}>
          {v.toFixed(3)}
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
      title: '因子贡献',
      dataIndex: 'contribution',
      key: 'contribution',
      width: 100,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
          {v > 0 ? '+' : ''}{(v * 100).toFixed(1)}%
        </span>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          因子仪表盘
        </Title>
        <Select
          value={selectedSymbol}
          onChange={setSelectedSymbol}
          options={SYMBOLS.map((s) => ({ value: s, label: s }))}
          style={{ width: 120 }}
        />
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={6}>
          <Card size="small">
            <Text type="secondary" style={{ fontSize: 12 }}>因子数量</Text>
            <div style={{ fontSize: 28, fontWeight: 600, color: '#1890ff' }}>{data.length}</div>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card size="small">
            <Text type="secondary" style={{ fontSize: 12 }}>正向因子</Text>
            <div style={{ fontSize: 28, fontWeight: 600, color: '#52c41a' }}>
              {data.filter((d) => d.direction === 'positive').length}
            </div>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card size="small">
            <Text type="secondary" style={{ fontSize: 12 }}>负向因子</Text>
            <div style={{ fontSize: 28, fontWeight: 600, color: '#ff4d4f' }}>
              {data.filter((d) => d.direction === 'negative').length}
            </div>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card size="small">
            <Text type="secondary" style={{ fontSize: 12 }}>平均 ICIR</Text>
            <div style={{ fontSize: 28, fontWeight: 600, color: '#faad14' }}>
              {(data.reduce((sum, d) => sum + d.icir, 0) / Math.max(data.length, 1)).toFixed(3)}
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        size="small"
        title={
          <span>
            <HeatMapOutlined style={{ marginRight: 6 }} />
            IC 热力图 &amp; 因子权重
          </span>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : data.length === 0 ? (
          <Empty description="暂无缘何数据" />
        ) : (
          <Table
            columns={columns}
            dataSource={data}
            rowKey="factorName"
            size="small"
            pagination={false}
            scroll={{ x: 700 }}
          />
        )}
      </Card>

      <Card
        size="small"
        title={
          <span>
            <ProjectOutlined style={{ marginRight: 6 }} />
            因子贡献分布
          </span>
        }
        style={{ marginTop: 16 }}
      >
        <Row gutter={[8, 8]}>
          {data
            .slice()
            .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
            .map((row) => (
              <Col span={12} key={row.factorName}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid #f5f5f5' }}>
                  <div style={{ width: 80, fontSize: 13 }}>{row.factorName}</div>
                  <div style={{ flex: 1, height: 20, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                    <Tooltip title={`贡献: ${(row.contribution * 100).toFixed(1)}%`}>
                      <div
                        style={{
                          position: 'absolute',
                          left: row.contribution >= 0 ? '50%' : 'auto',
                          right: row.contribution < 0 ? '50%' : 'auto',
                          width: `${Math.abs(row.contribution) * 300}%`,
                          maxWidth: '100%',
                          height: '100%',
                          background: row.contribution >= 0 ? '#52c41a' : '#ff4d4f',
                          borderRadius: 4,
                          transition: 'width 0.3s',
                        }}
                      />
                    </Tooltip>
                  </div>
                  <div style={{ width: 50, textAlign: 'right', fontSize: 12, color: row.contribution >= 0 ? '#52c41a' : '#ff4d4f' }}>
                    {row.contribution >= 0 ? '+' : ''}{(row.contribution * 100).toFixed(1)}%
                  </div>
                </div>
              </Col>
            ))}
        </Row>
      </Card>
    </div>
  )
}

export default FactorDashboardPage
