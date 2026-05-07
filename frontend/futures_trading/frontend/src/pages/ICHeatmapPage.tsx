/**
 * IC 热力图页面
 * 品种 × 因子 IC 矩阵，ECharts heatmap 渲染
 * 支持按 IC 绝对值排序、参数调整
 * @author Lucy
 * @date 2026-05-06
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Card, Typography, Row, Col, Select, Spin, Empty, Button, InputNumber, Space, Tag, Tooltip, Switch } from 'antd'
import { HeatMapOutlined, ReloadOutlined, SortAscendingOutlined, InfoCircleOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { fetchICHeatmap, MOCK_IC_HEATMAP } from '../api/macro'
import type { ICHeatmapData } from '../api/macro'

const { Title, Text } = Typography

const USE_MOCK = false // 切换为 true 使用 mock 数据

/** 默认品种列表 */
const DEFAULT_SYMBOLS = 'JM,RU,RB,ZN,NI'

/** 因子中文名映射 */
const FACTOR_LABELS: Record<string, string> = {
  basis: '基差',
  spread: '价差',
  hold_volume: '持仓量',
  basis_volatility: '基差波动率',
  import: '进口量',
}

/** 格式化因子名 */
function formatFactorName(f: string): string {
  return FACTOR_LABELS[f] ?? f
}

const ICHeatmapPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ICHeatmapData | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 参数
  const [symbols, setSymbols] = useState(DEFAULT_SYMBOLS)
  const [lookback, setLookback] = useState(60)
  const [holdPeriod, setHoldPeriod] = useState(5)

  // 排序
  const [sortByAbsIC, setSortByAbsIC] = useState(false)
  // 数值标签
  const [showLabels, setShowLabels] = useState(true)

  /** 加载数据 */
  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (USE_MOCK) {
        await new Promise((r) => setTimeout(r, 300))
        setData(MOCK_IC_HEATMAP)
      } else {
        const res = await fetchICHeatmap({ symbols, lookback, hold_period: holdPeriod })
        setData(res)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      // 降级到 mock
      setData(MOCK_IC_HEATMAP)
    } finally {
      setLoading(false)
    }
  }, [symbols, lookback, holdPeriod])

  useEffect(() => {
    void loadData()
  }, [loadData])

  /** 排序后的数据 */
  const sortedData = useMemo(() => {
    if (!data) return null
    if (!sortByAbsIC) return data

    // 按因子 IC 绝对值均值降序排列行（因子）
    const factorAvgIC = data.factors.map((f, fi) => {
      const row = data.icMatrix[fi] ?? []
      const avg = row.reduce((s, v) => s + Math.abs(v), 0) / Math.max(row.length, 1)
      return { factor: f, avg, idx: fi }
    })
    factorAvgIC.sort((a, b) => b.avg - a.avg)

    const newFactors = factorAvgIC.map((f) => f.factor)
    const newMatrix = factorAvgIC.map((f) => data.icMatrix[f.idx] ?? [])

    // 按品种 IC 绝对值均值降序排列列
    const symbolAvgIC = data.symbols.map((s, si) => {
      const col = newMatrix.map((row) => Math.abs(row[si] ?? 0))
      const avg = col.reduce((a, b) => a + b, 0) / Math.max(col.length, 1)
      return { symbol: s, avg, idx: si }
    })
    symbolAvgIC.sort((a, b) => b.avg - a.avg)

    const newSymbols = symbolAvgIC.map((s) => s.symbol)
    const finalMatrix = newMatrix.map((row) => symbolAvgIC.map((s) => row[s.idx] ?? 0))

    return {
      ...data,
      factors: newFactors,
      symbols: newSymbols,
      icMatrix: finalMatrix,
    }
  }, [data, sortByAbsIC])

  /** ECharts 配置 */
  const chartOption = useMemo((): EChartsOption => {
    if (!sortedData) return {}

    const { factors, symbols: syms, icMatrix } = sortedData

    // 构建 heatmap 数据 [x, y, value]
    const heatData: [number, number, number][] = []
    let minVal = 0
    let maxVal = 0

    for (let fi = 0; fi < factors.length; fi++) {
      for (let si = 0; si < syms.length; si++) {
        const v = icMatrix[fi]?.[si] ?? 0
        heatData.push([si, fi, parseFloat(v.toFixed(4))])
        if (v < minVal) minVal = v
        if (v > maxVal) maxVal = v
      }
    }

    // 对称色域
    const absMax = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.01)

    return {
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as { data: [number, number, number] }
          const [si, fi, val] = p.data
          const factorName = formatFactorName(factors[fi] ?? '')
          const symbolName = syms[si] ?? ''
          const color = val > 0 ? '#52c41a' : val < 0 ? '#ff4d4f' : '#8c8c8c'
          return `
            <div style="font-size:13px">
              <b>${symbolName}</b> × <b>${factorName}</b><br/>
              IC: <span style="color:${color};font-weight:600">${val > 0 ? '+' : ''}${val.toFixed(4)}</span>
            </div>
          `
        },
      },
      grid: {
        top: 40,
        bottom: 80,
        left: 120,
        right: 60,
      },
      xAxis: {
        type: 'category',
        data: syms,
        axisLabel: { fontSize: 13, fontWeight: 500 },
        splitArea: { show: true },
      },
      yAxis: {
        type: 'category',
        data: factors.map(formatFactorName),
        axisLabel: { fontSize: 13 },
        splitArea: { show: true },
      },
      visualMap: {
        min: -absMax,
        max: absMax,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 10,
        inRange: {
          color: ['#ff4d4f', '#ff7875', '#ffa39e', '#fff1f0', '#ffffff', '#f6ffed', '#b7eb8f', '#73d13d', '#52c41a'],
        },
        textStyle: { fontSize: 12 },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: ((val: any) => {
          const n = typeof val === 'number' ? val : 0
          return n.toFixed(3)
        }) as any,
      },
      series: [
        {
          type: 'heatmap',
          data: heatData,
          label: {
            show: showLabels,
            fontSize: 11,
            formatter: (params: unknown) => {
              const p = params as { data: [number, number, number] }
              const v = p.data[2]
              return `${v > 0 ? '+' : ''}${v.toFixed(3)}`
            },
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    }
  }, [sortedData, showLabels])

  /** 统计卡片 */
  const stats = useMemo(() => {
    if (!data) return null
    const all = data.icMatrix.flat()
    const absAll = all.map(Math.abs)
    return {
      count: all.length,
      mean: all.reduce((s, v) => s + v, 0) / Math.max(all.length, 1),
      maxAbs: Math.max(...absAll),
      positive: all.filter((v) => v > 0.02).length,
      negative: all.filter((v) => v < -0.02).length,
    }
  }, [data])

  return (
    <div>
      {/* 标题栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <HeatMapOutlined style={{ marginRight: 8 }} />
          IC 热力图
          <Tooltip title="Spearman Rank IC：因子值与未来 N 日收益的秩相关系数">
            <InfoCircleOutlined style={{ marginLeft: 8, color: '#8c8c8c', fontSize: 14 }} />
          </Tooltip>
        </Title>
        <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
          刷新
        </Button>
      </div>

      {/* 参数面板 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>品种</Text>
            <Select
              mode="tags"
              value={symbols.split(',')}
              onChange={(v) => setSymbols(v.join(','))}
              style={{ width: 260, display: 'block', marginTop: 4 }}
              placeholder="输入品种代码"
              tokenSeparators={[',']}
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>回看天数</Text>
            <InputNumber
              value={lookback}
              onChange={(v) => v && setLookback(v)}
              min={10}
              max={250}
              style={{ width: 100, display: 'block', marginTop: 4 }}
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>持有期</Text>
            <InputNumber
              value={holdPeriod}
              onChange={(v) => v && setHoldPeriod(v)}
              min={1}
              max={20}
              style={{ width: 100, display: 'block', marginTop: 4 }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>排序</Text>
            <Switch
              checked={sortByAbsIC}
              onChange={setSortByAbsIC}
              checkedChildren={<SortAscendingOutlined />}
              unCheckedChildren={<SortAscendingOutlined />}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>数值标签</Text>
            <Switch checked={showLabels} onChange={setShowLabels} />
          </div>
        </Space>
      </Card>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} md={4}>
            <Card size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>数据点</Text>
              <div style={{ fontSize: 24, fontWeight: 600, color: '#1890ff' }}>{stats.count}</div>
            </Card>
          </Col>
          <Col xs={12} md={5}>
            <Card size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>IC 均值</Text>
              <div style={{ fontSize: 24, fontWeight: 600, color: stats.mean >= 0 ? '#52c41a' : '#ff4d4f' }}>
                {stats.mean >= 0 ? '+' : ''}{stats.mean.toFixed(4)}
              </div>
            </Card>
          </Col>
          <Col xs={12} md={5}>
            <Card size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>|IC| 最大值</Text>
              <div style={{ fontSize: 24, fontWeight: 600, color: '#faad14' }}>{stats.maxAbs.toFixed(4)}</div>
            </Card>
          </Col>
          <Col xs={12} md={5}>
            <Card size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>显著正 IC</Text>
              <div style={{ fontSize: 24, fontWeight: 600, color: '#52c41a' }}>{stats.positive}</div>
              <Tag color="green" style={{ fontSize: 10 }}>IC &gt; 0.02</Tag>
            </Card>
          </Col>
          <Col xs={12} md={5}>
            <Card size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>显著负 IC</Text>
              <div style={{ fontSize: 24, fontWeight: 600, color: '#ff4d4f' }}>{stats.negative}</div>
              <Tag color="red" style={{ fontSize: 10 }}>IC &lt; -0.02</Tag>
            </Card>
          </Col>
        </Row>
      )}

      {/* 热力图 */}
      <Card
        size="small"
        title={
          <span>
            <HeatMapOutlined style={{ marginRight: 6 }} />
            品种 × 因子 IC 矩阵
            {data && (
              <Text type="secondary" style={{ fontSize: 12, marginLeft: 12 }}>
                回看 {data.lookbackPeriod} 天 · 持有 {data.holdPeriod} 天 · 更新 {data.updatedAt.slice(0, 16).replace('T', ' ')}
              </Text>
            )}
          </span>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Empty description={<span style={{ color: '#ff4d4f' }}>{error}（已降级为 mock 数据）</span>} />
          </div>
        ) : sortedData && sortedData.factors.length > 0 ? (
          <ReactECharts
            option={chartOption}
            style={{ height: Math.max(300, sortedData.factors.length * 60 + 120), width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        ) : (
          <Empty description="暂无 IC 数据" />
        )}
      </Card>
    </div>
  )
}

export default ICHeatmapPage
