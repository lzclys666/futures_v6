import React, { useMemo } from 'react';
import { Card, Empty, Typography } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

const { Text } = Typography;

interface FactorCorrelation {
  factor1: string;
  factor2: string;
  ic: number; // information coefficient, -1 to 1
}

interface Props {
  data?: FactorCorrelation[];
  height?: number;
}

const MOCK_FACTORS = [
  '库存变化', '基差率', '现货升贴水', '开工率',
  '钢厂利润', '港口库存', '铁水产量', '成交量',
  '情绪指数', '资金流向', '波动率', '趋势强度',
];

/** 生成 Mock IC 矩阵 */
function generateMockData(): FactorCorrelation[] {
  const result: FactorCorrelation[] = [];
  for (let i = 0; i < MOCK_FACTORS.length; i++) {
    for (let j = i; j < MOCK_FACTORS.length; j++) {
      if (i === j) {
        result.push({ factor1: MOCK_FACTORS[i], factor2: MOCK_FACTORS[j], ic: 1 });
      } else {
        // 随机 IC，偏向 0 附近
        const ic = parseFloat((Math.random() * 0.6 - 0.3).toFixed(2));
        result.push({ factor1: MOCK_FACTORS[i], factor2: MOCK_FACTORS[j], ic });
      }
    }
  }
  return result;
}

/**
 * IC 热力图 — 因子间信息系数矩阵可视化
 * Phase 3 对接 YIYI IC API，当前为 Mock 数据
 */
const ICHeatmap: React.FC<Props> = ({ data, height = 480 }) => {
  const rawData = data ?? useMemo(() => generateMockData(), []);

  const option: EChartsOption = useMemo(() => {
    const factors = MOCK_FACTORS;
    const gridData = factors.map((f1, i) =>
      factors.map((_, j) => {
        if (i === j) return [i, j, 1];
        const corr = rawData.find(d =>
          (d.factor1 === f1 && d.factor2 === factors[j]) ||
          (d.factor1 === factors[j] && d.factor2 === f1)
        );
        return [i, j, corr?.ic ?? 0];
      })
    ).flat();

    return {
      tooltip: {
        position: 'top',
        formatter: (params: any) => {
          const [x, y, v] = params.value;
          return `${factors[x]} ↔ ${factors[y]}<br/>IC: <b>${v.toFixed(3)}</b>`;
        },
      },
      grid: { left: 100, right: 40, top: 20, bottom: 80 },
      xAxis: {
        type: 'category',
        data: factors,
        splitArea: { show: true },
        axisLabel: { rotate: 45, fontSize: 10 },
      },
      yAxis: {
        type: 'category',
        data: factors,
        splitArea: { show: true },
        axisLabel: { fontSize: 10 },
      },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: ['#313695', '#4575b4', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027'],
        },
        text: ['正相关', '负相关'],
      },
      series: [{
        type: 'heatmap',
        data: gridData,
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
        label: { show: false },
      }],
    };
  }, [rawData]);

  return (
    <Card
      title="因子 IC 热力图"
      extra={<Text type="secondary" style={{ fontSize: 12 }}>YIYI 因子引擎 · 信息系数矩阵</Text>}
    >
      {rawData.length === 0 ? (
        <Empty description="暂无 IC 数据 — 等待 YIYI API 对接" />
      ) : (
        <ReactECharts option={option} style={{ height }} />
      )}
    </Card>
  );
};

export default ICHeatmap;
