import React, { useEffect, useState, useMemo } from 'react';
import { Typography, Card, Row, Col, Select, Spin, Empty, Statistic } from 'antd';
import ReactECharts from 'echarts-for-react';
import { useMacroStore } from '../../store/macroStore';
import type { SymbolCode } from '../../types';
import { SYMBOL_OPTIONS } from '../../constants/symbols';

const { Title, Text } = Typography;
const { Option } = Select;

/**
 * 宏观看板页面
 * 展示单品种的宏观因子信号、历史走势、因子分解
 *
 * 数据来源（优先级）：
 * 1. fetchSignal() → /api/macro/signal/{symbol}（端口 8000）
 * 2. fetchScoreHistory() → /api/macro/score-history/{symbol}
 * 非交易时段：store mock fallback
 */
const MacroBoard: React.FC = () => {
  const {
    currentSymbol,
    signal,
    scoreHistory,
    loading,
    setSymbol,
    fetchSignal,
    fetchScoreHistory,
  } = useMacroStore();

  const [days, setDays] = useState(30);

  // 初始化 + 品种/天数变化时重新拉取（含 5s 轮询）
  useEffect(() => {
    fetchSignal();
    fetchScoreHistory(days);

    const id = setInterval(() => {
      fetchSignal();
      fetchScoreHistory(days);
    }, 5000);

    return () => clearInterval(id);
  }, [currentSymbol, days, fetchSignal, fetchScoreHistory]);

  // P2-4: ECharts option 用 useMemo 缓存避免每次渲染重建
  const historyOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: scoreHistory.map((d) => d.date),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}' },
    },
    series: [{
      name: '综合评分',
      type: 'line',
      data: scoreHistory.map((d) => d.score),
      smooth: true,
      lineStyle: { color: '#1890ff', width: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(24,144,255,0.3)' },
            { offset: 1, color: 'rgba(24,144,255,0.05)' },
          ],
        },
      },
    }],
  }), [scoreHistory]);

  const factorOption = useMemo(() => ({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      min: -50,
      max: 50,
      axisLabel: { formatter: '{value}' },
    },
    yAxis: {
      type: 'category',
      data: signal?.factorDetails?.map((f) => f.factorName).reverse() || [],
      axisLabel: { fontSize: 11 },
    },
    series: [{
      name: '贡献度',
      type: 'bar',
      data: signal?.factorDetails?.map((f) => ({
        value: f.contribution,
        itemStyle: {
          color: f.direction === 'positive' ? '#52c41a' : f.direction === 'negative' ? '#ff4d4f' : '#8c8c8c',
        },
      })).reverse() || [],
      barWidth: '60%',
      label: {
        show: true,
        position: 'right',
        formatter: (params: any) => params.value > 0 ? `+${params.value.toFixed(1)}` : params.value.toFixed(1),
      },
    }],
  }), [signal?.factorDetails]);

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>宏观看板</Title>
          <Text type="secondary">宏观因子信号与历史走势</Text>
        </div>
        <div>
          <Select value={currentSymbol} onChange={(v) => setSymbol(v as SymbolCode)} style={{ width: 150, marginRight: 8 }}>
            {SYMBOL_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
          <Select value={days} onChange={(v) => setDays(v)} style={{ width: 100 }}>
            <Option value={7}>7天</Option>
            <Option value={30}>30天</Option>
            <Option value={60}>60天</Option>
            <Option value={90}>90天</Option>
          </Select>
        </div>
      </div>

      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />
      ) : !signal ? (
        <Empty description="暂无信号数据" />
      ) : (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* 主区域：综合评分 + 信号 */}
            <Col span={16}>
              <Card size="small">
                <Row gutter={32}>
                  <Col span={12}>
                    <Statistic
                      title="综合评分"
                      value={signal.score}
                      precision={1}
                      valueStyle={{ color: signal.score > 60 ? '#52c41a' : signal.score < 40 ? '#ff4d4f' : '#faad14', fontSize: 32 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="信号方向"
                      value={signal.signal}
                      valueStyle={{ color: signal.signal === 'BUY' ? '#52c41a' : signal.signal === 'SELL' ? '#ff4d4f' : '#faad14', fontSize: 24 }}
                    />
                  </Col>
                </Row>
              </Card>
            </Col>
            {/* 次区域：强度 + 日期 */}
            <Col span={8}>
              <Card size="small">
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="强度"
                      value={signal.strength}
                      valueStyle={{ color: signal.strength === 'STRONG' ? '#52c41a' : signal.strength === 'WEAK' ? '#ff4d4f' : '#faad14' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic title="更新日期" value={signal.timestamp?.slice(0, 10) || ''} />
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          <Card size="small" title="历史走势" style={{ marginBottom: 16 }}>
            {scoreHistory.length > 0
              ? <ReactECharts option={historyOption} style={{ height: 300 }} />
              : <Empty description="暂无历史数据" />}
          </Card>

          <Card size="small" title="因子分解">
            {signal.factorDetails && signal.factorDetails.length > 0
              ? <ReactECharts option={factorOption} style={{ height: 400 }} />
              : <Empty description="暂无因子数据" />}
          </Card>
        </>
      )}

      <p style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center', marginTop: 12 }}>
        当前为非交易时段，数据来自 Mock 快照 · Phase 3 对接 YIYI 信号 API 后实时更新
      </p>
    </div>
  );
};

export default MacroBoard;
