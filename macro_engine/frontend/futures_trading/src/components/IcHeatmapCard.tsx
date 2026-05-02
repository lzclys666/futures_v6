import React, { useEffect, useState } from 'react';
import { Card, Empty, Typography, Tooltip, Space, Spin } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useMacroStore } from '../store/macroStore';

/** YIYI 因子英文名 → 中文标签 */
const FACTOR_LABELS: Record<string, string> = {
  basis: '基差率',
  spread: '价差',
  hold_volume: '持仓量',
  basis_volatility: '基差波动率',
  import: '进口',
  momentum: '动量',
  carry: 'Carry',
  liquidity: '流动性',
  volatility: '波动率',
  trend: '趋势',
};

function toChinese(name: string): string {
  return FACTOR_LABELS[name] ?? name;
}

const HEIGHT = 240; // 固定像素高度，保证 grid 百分比计算正确

/**
 * IC 热力图卡片组件
 * 展示因子与品种之间的 IC 相关性
 * 数据来自 fetchIcHeatmap（端口 8002，YIYI 因子分析服务）
 * 非交易时段使用 store mock fallback
 */
const IcHeatmapCardBase: React.FC = () => {
  const { icHeatmap, fetchIcHeatmap, loading } = useMacroStore();
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    if (!fetched && !icHeatmap) {
      fetchIcHeatmap();
      setFetched(true);
    }
  }, [fetched, icHeatmap, fetchIcHeatmap]);

  if (!icHeatmap && loading) {
    return (
      <Card size="small" title="IC 热力图">
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
          <p style={{ fontSize: 12, color: '#8c8c8c', marginTop: 8, marginBottom: 0 }}>加载中...</p>
        </div>
      </Card>
    );
  }

  if (!icHeatmap) {
    return (
      <Card size="small" title="IC 热力图">
        <Empty description="暂无 IC 数据 — 等待 YIYI API 对接" />
        <p style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center', marginTop: 8, marginBottom: 0 }}>
          非交易时段 — Mock 数据
        </p>
      </Card>
    );
  }

  const { factors, symbols, icMatrix } = icHeatmap;

  const data: [number, number, number][] = [];
  icMatrix.forEach((row, i) => {
    row.forEach((value, j) => {
      data.push([j, i, value]);
    });
  });

  const gridHeight = Math.floor(HEIGHT * 0.6); // = 144px

  const option = {
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const factor = toChinese(factors[params.value[1]]);
        const symbol = symbols[params.value[0]];
        const value = params.value[2];
        return `${symbol} - ${factor}<br/>IC: ${value.toFixed(4)}`;
      },
    },
    grid: { height: gridHeight, top: '10%', left: '15%', right: '10%' },
    xAxis: { type: 'category', data: symbols.map(s => s), splitArea: { show: true }, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'category', data: factors.map(f => toChinese(f)), splitArea: { show: true }, axisLabel: { fontSize: 11 } },
    visualMap: {
      min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%',
      inRange: { color: ['#ff4d4f', '#ffffff', '#52c41a'] },
    },
    series: [{
      name: 'IC', type: 'heatmap', data,
      label: { show: true, formatter: (params: any) => params.value[2].toFixed(2), fontSize: 10 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
    }],
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>IC 热力图 (回看: {icHeatmap.lookbackPeriod}日, 持有: {icHeatmap.holdPeriod}日)</span>
          <Tooltip title="信息系数(IC)衡量因子对收益的预测能力，范围[-1,1]，|IC|>0.05为有效因子">
            <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
          </Tooltip>
        </Space>
      }
      extra={<Typography.Text type="secondary" style={{ fontSize: 12 }}>非交易时段 — Mock 数据</Typography.Text>}
    >
      {/* 颜色图例说明 */}
      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        <Text style={{ fontSize: 11, color: '#8c8c8c' }}>IC 值：</Text>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 16, height: 12, backgroundColor: '#ff4d4f', borderRadius: 2 }} />
          <Text style={{ fontSize: 10 }}>-1 负相关</Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 16, height: 12, backgroundColor: '#ffffff', border: '1px solid #d9d9d9', borderRadius: 2 }} />
          <Text style={{ fontSize: 10 }}>0 无相关</Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 16, height: 12, backgroundColor: '#52c41a', borderRadius: 2 }} />
          <Text style={{ fontSize: 10 }}>+1 正相关</Text>
        </div>
      </div>
      <ReactECharts option={option} style={{ height: HEIGHT }} />
    </Card>
  );
};

const IcHeatmapCard = React.memo(IcHeatmapCardBase);
export default IcHeatmapCard;
