import React, { useState, useMemo, useEffect } from 'react';
import { useMacroStore } from '../../store/macroStore';
import {
  Card, Row, Col, Statistic, Table, Tag, Typography, Select,
  Space, Divider, Empty, Spin,
} from 'antd';
import {
  FundViewOutlined, RiseOutlined, FallOutlined,
  TrophyOutlined, DashboardOutlined, LineChartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { SymbolCode } from '../../types';
import { SYMBOL_OPTIONS } from '../../constants/symbols';
import IcHeatmapCard from '../../components/IcHeatmapCard';

const { Text, Title } = Typography;

interface FactorScore {
  factorName: string;
  value: number;
  weight: number;
  contribution: number;
  direction: 'bullish' | 'bearish' | 'neutral';
}

interface DailyIC {
  date: string;
  ic: number;
  rankIc: number;
}

function generateMockSignals(symbol: SymbolCode): FactorScore[] {
  const factors = [
    '库存变化', '基差率', '现货升贴水', '开工率', '钢厂利润',
    '港口库存', '铁水产量', '成交量', '情绪指数', '资金流向',
  ];
  const baseSeed = Array.from(symbol).reduce((s, ch) => s + ch.charCodeAt(0), 0);
  return factors.map((name, i) => {
    const val = parseFloat((Math.sin(baseSeed * 0.7 + i * 1.3) * 1.5).toFixed(2));
    const weight = parseFloat((Math.abs(Math.cos(i * 0.8 + 1.1)) * 0.35).toFixed(2));
    const contrib = parseFloat((val * weight).toFixed(2));
    return {
      factorName: name,
      value: val,
      weight,
      contribution: contrib,
      direction: contrib > 0.1 ? 'bullish' : contrib < -0.1 ? 'bearish' : 'neutral',
    };
  });
}

function generateMockICSeries(symbol: SymbolCode): DailyIC[] {
  const seed = Array.from(symbol).reduce((s, ch) => s + ch.charCodeAt(0) * 7, 0);
  const dates: DailyIC[] = [];
  for (let i = 30; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push({
      date: d.toISOString().slice(0, 10),
      ic: parseFloat((Math.sin((seed + i) * 0.4) * 0.15 + (Math.random() - 0.5) * 0.1).toFixed(3)),
      rankIc: parseFloat((Math.cos((seed + i) * 0.35) * 0.12 + (Math.random() - 0.5) * 0.08).toFixed(3)),
    });
  }
  return dates;
}

const FactorDashboard: React.FC = () => {
  const [symbol, setSymbol] = useState<SymbolCode>('RB');

  // YIYI Signal System — 真实 API（端口 8002）
  const { signalSystem, batchSignals, fetchSignalSystem, fetchBatchSignals } = useMacroStore();

  // 品种切换时重新拉取 YIYI 信号
  useEffect(() => {
    fetchSignalSystem(symbol);
    fetchBatchSignals([symbol]);
  }, [symbol, fetchSignalSystem, fetchBatchSignals]);

  // 当前品种的 YIYI 信号（降级：batchSignals 兜底）
  const yiyiData = batchSignals.find(s => s.symbol === symbol) ?? signalSystem;

  // 因子贡献 — 优先用 YIYI factorDetails（5/15 后填充），暂无则降级到 MacroBoard store 数据
  const { signal: macroSignal } = useMacroStore();
  const factorDetails = yiyiData?.factorDetails?.length
    ? yiyiData.factorDetails.map(f => ({
        factorName: f.factorName,
        value: f.rawScore ?? 0,
        weight: f.weight ?? 0,
        contribution: f.contribution,
        direction: (f.factorDirection === 'LONG' ? 'bullish' : f.factorDirection === 'SHORT' ? 'bearish' : 'neutral') as 'bullish' | 'bearish' | 'neutral',
      }))
    : macroSignal?.factorDetails?.map(f => ({
        factorName: f.factorName,
        value: f.rawScore ?? 0,
        weight: f.weight ?? 0,
        contribution: f.contribution,
        direction: (f.direction === 'positive' ? 'bullish' : f.direction === 'negative' ? 'bearish' : 'neutral') as 'bullish' | 'bearish' | 'neutral',
      })) ?? generateMockSignals(symbol);

  // IC 时序 — 仍为 Mock（YIYI IC 时序 API 尚未提供）
  const icSeries = useMemo(() => generateMockICSeries(symbol), [symbol]);

  // 综合评分 — 来自 YIYI compositeScore
  const compositeScore = yiyiData?.compositeScore ?? macroSignal?.score ?? 0;
  const bullishCount = factorDetails.filter(f => f.direction === 'bullish').length;
  const bearishCount = factorDetails.filter(f => f.direction === 'bearish').length;
  const avgAbsIC = useMemo(
    () => parseFloat((icSeries.reduce((s, d) => s + Math.abs(d.ic), 0) / icSeries.length).toFixed(3)),
    [icSeries]
  );

  const icChartOption: EChartsOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['IC', 'Rank IC'], top: 0 },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: icSeries.map(d => d.date.slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', min: -0.3, max: 0.3, axisLabel: { fontSize: 10 } },
    series: [
      { name: 'IC', type: 'line', data: icSeries.map(d => d.ic), smooth: true, lineStyle: { color: '#1890ff', width: 2 }, itemStyle: { color: '#1890ff' }, markLine: { silent: true, data: [{ yAxis: 0, lineStyle: { color: '#d9d9d9', type: 'dashed' } }] } },
      { name: 'Rank IC', type: 'line', data: icSeries.map(d => d.rankIc), smooth: true, lineStyle: { color: '#52c41a', width: 2 }, itemStyle: { color: '#52c41a' } },
    ],
  }), [icSeries]);

  const contribOption: EChartsOption = useMemo(() => ({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 40, top: 10, bottom: 10 },
    xAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    yAxis: { type: 'category', data: factorDetails.map(s => s.factorName).reverse(), axisLabel: { fontSize: 10 }, inverse: true },
    series: [{
      type: 'bar',
      data: factorDetails.map(s => ({ value: s.contribution, itemStyle: { color: s.contribution >= 0 ? '#52c41a' : '#ff4d4f' } })).reverse(),
      barMaxWidth: 20,
    }],
  }), [factorDetails]);

  const columns = [
    { title: '因子', dataIndex: 'factorName', key: 'factorName', width: 100 },
    { title: 'Z-Score', dataIndex: 'value', key: 'value', width: 80, render: (v: number) => <Text>{v?.toFixed(2) ?? '-'}</Text> },
    { title: '权重', dataIndex: 'weight', key: 'weight', width: 80, render: (v: number) => <Tag>{v != null ? `${(v * 100).toFixed(0)}%` : '-'}</Tag> },
    { title: '贡献', dataIndex: 'contribution', key: 'contribution', width: 80, render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2) ?? '-'}</Text> },
    { title: '方向', dataIndex: 'direction', key: 'direction', width: 80, render: (d: string) => d === 'bullish' ? <Tag color="green"><RiseOutlined /> 看多</Tag> : d === 'bearish' ? <Tag color="red"><FallOutlined /> 看空</Tag> : <Tag>中性</Tag> },
  ];

  return (
    <div style={{ padding: 16, maxWidth: 1400, margin: '0 auto' }}>
      <Title level={4}><DashboardOutlined /> 因子仪表盘</Title>
      <Text type="secondary">因子战绩 + IC 走势 · YIYI 因子引擎</Text>
      <Divider />
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card size="small">
            <Row align="middle" gutter={16}>
              <Col>
                <Text strong>品种：</Text>
                <Select value={symbol} onChange={setSymbol} style={{ width: 140 }}>
                  {SYMBOL_OPTIONS.map(opt => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}
                </Select>
              </Col>
              <Col flex="auto">
                <Row gutter={32}>
                  <Col><Statistic
                    title="复合评分"
                    value={compositeScore}
                    valueStyle={{ color: compositeScore >= 55 ? '#52c41a' : compositeScore <= 45 ? '#ff4d4f' : '#faad14', fontSize: 24 }}
                    prefix={compositeScore >= 55 ? <RiseOutlined /> : compositeScore <= 45 ? <FallOutlined /> : undefined}
                  /></Col>
                  <Col><Statistic title="看多因子" value={bullishCount} valueStyle={{ color: '#52c41a' }} suffix={`/ ${factorDetails.length}`} /></Col>
                  <Col><Statistic title="看空因子" value={bearishCount} valueStyle={{ color: '#ff4d4f' }} suffix={`/ ${factorDetails.length}`} /></Col>
                  <Col><Statistic title="均 |IC|" value={avgAbsIC} valueStyle={{ color: '#1890ff' }} /></Col>
                </Row>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={10}>
          <Card size="small" title="因子贡献分解" extra={<Text type="secondary" style={{ fontSize: 11 }}>多空分解</Text>}>
            <ReactECharts option={contribOption} style={{ height: 320 }} />
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card size="small" title={<><LineChartOutlined /> IC 时序走势</>} extra={<Text type="secondary" style={{ fontSize: 11 }}>近30日</Text>}>
            <ReactECharts option={icChartOption} style={{ height: 320 }} />
          </Card>
        </Col>
      </Row>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card size="small" title="因子明细" extra={<Text type="secondary" style={{ fontSize: 11 }}>按贡献排序</Text>}>
            <Table dataSource={scores.sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))} columns={columns} rowKey="factorName" size="small" pagination={false} />
          </Card>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={24}>
          <IcHeatmapCard />
        </Col>
      </Row>
      <Divider />
      <Text type="secondary" style={{ fontSize: 12 }}>IC 热力图数据来源：YIYI 因子分析服务（端口 8002）· 因子战绩及 IC 时序为 Mock 数据（Phase 3 对接真实 API）</Text>
    </div>
  );
};

export default FactorDashboard;
