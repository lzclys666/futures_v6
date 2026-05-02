/**
 * WeightTable · 因子权重表
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import React from 'react'
import { Table, Tag, Tooltip } from 'antd'
import type { WeightTableProps } from '../../types/macro'
import type { ColumnsType } from 'antd/es/table'
import type { FactorDetail } from '../../types/macro'

/**
 * 判断因子数据是否可用（未因网络封锁导致 rawValue 缺失）。
 * normalizedScore=0 且 rawValue 无效 → 数据积累中，需要降级显示。
 */
function isDataUnavailable(factor: FactorDetail): boolean {
  return factor.normalizedScore === 0 && !factor.rawValue && factor.rawValue !== 0
}

const WeightTable: React.FC<WeightTableProps> = ({ factors }) => {
  const columns: ColumnsType<FactorDetail> = [
    {
      title: '因子代码',
      dataIndex: 'factorCode',
      key: 'factorCode',
      width: 160,
      render: (code: string) => (
        <code style={{ fontSize: 11, background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
          {code}
        </code>
      ),
    },
    {
      title: '因子名称',
      dataIndex: 'factorName',
      key: 'factorName',
      width: 120,
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      width: 80,
      render: (w: number) => `${(w * 100).toFixed(1)}%`,
      sorter: (a, b) => a.weight - b.weight,
    },
    {
      title: '标准化得分',
      dataIndex: 'normalizedScore',
      key: 'normalizedScore',
      width: 110,
      render: (s: number, record: FactorDetail) => {
        if (isDataUnavailable(record)) {
          return (
            <Tooltip title="数据积累中" placement="top">
              <span style={{ fontFamily: 'Courier New, monospace', fontWeight: 600, color: '#8c8c8c', cursor: 'default' }}>
                —
              </span>
            </Tooltip>
          )
        }
        return (
          <span style={{ fontFamily: 'Courier New, monospace', fontWeight: 600 }}>
            {s >= 0 ? '+' : ''}{s.toFixed(3)}
          </span>
        )
      },
      sorter: (a, b) => a.normalizedScore - b.normalizedScore,
    },
    {
      title: '贡献值',
      dataIndex: 'contribution',
      key: 'contribution',
      width: 100,
      render: (c: number, record: FactorDetail) => {
        if (isDataUnavailable(record)) {
          return (
            <Tooltip title="数据积累中" placement="top">
              <span style={{ fontFamily: 'Courier New, monospace', color: '#8c8c8c', cursor: 'default' }}>
                —
              </span>
            </Tooltip>
          )
        }
        return (
          <span
            style={{
              fontFamily: 'Courier New, monospace',
              color: c > 0 ? '#52c41a' : c < 0 ? '#ff4d4f' : '#8c8c8c',
              fontWeight: 600,
            }}
          >
            {c >= 0 ? '+' : ''}{c.toFixed(4)}
          </span>
        )
      },
      sorter: (a, b) => a.contribution - b.contribution,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (d: string) => {
        const cfg: Record<string, { color: string; text: string }> = {
          positive: { color: '#f6ffed', text: '正' },
          negative: { color: '#fff2f0', text: '负' },
          neutral:  { color: '#f5f5f5', text: '中' },
        }
        const c = cfg[d] || cfg.neutral
        return (
          <Tag color={d === 'positive' ? 'green' : d === 'negative' ? 'red' : 'default'}>
            {c.text}贡献
          </Tag>
        )
      },
      filters: [
        { text: '正贡献', value: 'positive' },
        { text: '负贡献', value: 'negative' },
        { text: '中性', value: 'neutral' },
      ],
      onFilter: (value, record) => record.direction === value,
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={factors}
      rowKey="factorCode"
      size="small"
      pagination={false}
      scroll={{ y: 240 }}
      style={{ background: '#fff', borderRadius: 8 }}
    />
  )
}

export default WeightTable
