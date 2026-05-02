/**
 * SignalChart · 信号历史走势图（ECharts）
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import React, { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { SignalChartProps } from '../../types/macro'
import { Spin } from 'antd'

const SignalChart: React.FC<SignalChartProps> = ({ symbol, history, loading }) => {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current) return
    instanceRef.current = echarts.init(chartRef.current)

    // 【修复】添加 window resize 监听，自动调整图表尺寸
    const handleResize = () => instanceRef.current?.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      instanceRef.current?.dispose()
    }
  }, [])

  useEffect(() => {
    const chart = instanceRef.current
    if (!chart || loading || !history.length) return

    const dates = history.map(p => p.date)
    const scores = history.map(p => p.score)

    const option: echarts.EChartsOption = {
      backgroundColor: '#ffffff',
      title: {
        text: `${symbol} 宏观综合打分走势`,
        left: 16,
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 600, color: '#262626' },
      },
      tooltip: {
        trigger: 'axis',
        // 【修复】使用正确的 ECharts tooltip formatter 参数类型
        formatter: (params: unknown) => {
          const p = Array.isArray(params) ? params[0] : params
          const raw = (p as { value?: unknown }).value
          const score = typeof raw === 'number' ? raw.toFixed(3) : String(raw)
          return `${(p as { axisValue?: string }).axisValue}<br/>打分: <b>${score}</b>`
        },
      },
      grid: { left: 48, right: 16, top: 44, bottom: 32 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: 10, color: '#8c8c8c' },
        axisLine: { lineStyle: { color: '#e8e8e8' } },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        min: -1,
        max: 1,
        splitNumber: 4,
        axisLabel: { fontSize: 10, color: '#8c8c8c' },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      },
      series: [
        {
          type: 'line',
          data: scores,
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { width: 2 },
          itemStyle: { color: '#597ef7' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(89,126,247,0.2)' },
              { offset: 1, color: 'rgba(89,126,247,0)' },
            ]),
          },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', color: '#d9d9d9' },
            data: [
              { yAxis: 0.15, label: { formatter: '多头线 {c}', fontSize: 10, color: '#52c41a' }, lineStyle: { color: '#52c41a' } },
              { yAxis: -0.15, label: { formatter: '空头线 {c}', fontSize: 10, color: '#ff4d4f' }, lineStyle: { color: '#ff4d4f' } },
              { yAxis: 0, label: { formatter: '0', fontSize: 10, color: '#bfbfbf' } },
            ],
          },
        },
      ],
    }

    chart.setOption(option, true)
  }, [symbol, history, loading])

  if (loading) {
    return (
      <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin tip="加载历史走势..." />
      </div>
    )
  }

  return <div ref={chartRef} style={{ width: '100%', height: 320 }} />
}

export default SignalChart
