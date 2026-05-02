import React, { useState, useMemo } from 'react';
import {
  Card, Button, Select, Table, Statistic, Row, Col, Tag, Typography,
  Space, Divider, Empty, Alert, Slider,
} from 'antd';
import {
  ThunderboltOutlined, WarningOutlined, CheckCircleOutlined,
  ExperimentOutlined, FireOutlined, CloudOutlined,
} from '@ant-design/icons';
import type { StressTestRequest, StressTestResult } from '../../types/risk';

const { Text, Title } = Typography;

type Scenario = StressTestRequest['scenario'];
const SCENARIOS: { value: Scenario; label: string; icon: React.ReactNode; desc: string; defaultMagnitude: number }[] = [
  { value: 'flash_crash', label: '闪崩', icon: <FireOutlined />, desc: '市场价格瞬间暴跌', defaultMagnitude: 8 },
  { value: 'volatility_spike', label: '波动率飙升', icon: <ExperimentOutlined />, desc: '波动率翻倍', defaultMagnitude: 2 },
  { value: 'liquidity_dryup', label: '流动性枯竭', icon: <CloudOutlined />, desc: '对手盘消失', defaultMagnitude: 15 },
  { value: 'correlated_drawdown', label: '相关性回撤', icon: <WarningOutlined />, desc: '所有持仓品种同向不利波动', defaultMagnitude: 5 },
];

const SEVERITY_RATING: Record<string, { color: string; label: string }> = {
  PASS: { color: '#52c41a', label: '安全' },
  LOW: { color: '#1890ff', label: '低风险' },
  MEDIUM: { color: '#faad14', label: '中等风险' },
  HIGH: { color: '#ff4d4f', label: '高风险' },
};

/** Mock 持仓数据（非交易时段） */
function getMockPositions(): StressTestRequest['positions'] {
  return [
    { symbol: 'RB', exchange: 'SHFE', direction: 'long', volume: 5, avgPrice: 3700, positionType: 'open' },
    { symbol: 'JM', exchange: 'DCE', direction: 'long', volume: 3, avgPrice: 1850, positionType: 'open' },
    { symbol: 'NI', exchange: 'SHFE', direction: 'short', volume: 2, avgPrice: 118000, positionType: 'open' },
  ];
}

/** Mock 压力测试计算 */
function runMockStressTest(scenario: Scenario, positions: StressTestRequest['positions'], magnitude: number): StressTestResult[] {
  const totalExposure = positions.reduce((s, p) => s + p.avgPrice * p.volume * (p.direction === 'long' ? 1 : -0.5), 0);
  const base = Math.abs(totalExposure);
  const mag = magnitude / 100; // 转换为小数

  switch (scenario) {
    case 'flash_crash':
      return [{
        scenarioName: `闪崩 (${magnitude}%)`,
        totalPnl: base * -mag,
        remainingEquity: 500000 + base * -mag,
        drawdownPct: magnitude,
        survived: base * mag < 150000,
        rating: base * mag < 50000 ? 'PASS' : base * mag < 100000 ? 'MEDIUM' : 'HIGH',
      }];
    case 'volatility_spike':
      return [{
        scenarioName: `波动率飙升 (${magnitude}x)`,
        totalPnl: base * -mag * 0.7,
        remainingEquity: 500000 + base * -mag * 0.7,
        drawdownPct: magnitude * 0.7,
        survived: true,
        rating: 'MEDIUM',
      }];
    case 'liquidity_dryup':
      return [{
        scenarioName: `流动性枯竭 (${magnitude}%)`,
        totalPnl: base * -mag,
        remainingEquity: 500000 + base * -mag,
        drawdownPct: magnitude,
        survived: base * mag < 200000,
        rating: base * mag < 100000 ? 'MEDIUM' : 'HIGH',
      }];
    case 'correlated_drawdown':
      return [
        { scenarioName: `螺纹钢-${magnitude}%`, totalPnl: -18500 * (magnitude / 5), remainingEquity: 500000 - 18500 * (magnitude / 5), drawdownPct: magnitude * 0.74, survived: true, rating: magnitude < 8 ? 'LOW' : 'MEDIUM' },
        { scenarioName: `热卷-${magnitude}%`, totalPnl: -11490 * (magnitude / 5), remainingEquity: 500000 - 11490 * (magnitude / 5), drawdownPct: magnitude * 0.46, survived: true, rating: 'PASS' },
        { scenarioName: `焦炭+${magnitude}%`, totalPnl: -21805 * (magnitude / 5), remainingEquity: 500000 - 21805 * (magnitude / 5), drawdownPct: magnitude * 0.88, survived: true, rating: magnitude < 8 ? 'MEDIUM' : 'HIGH' },
        { scenarioName: `焦煤+${magnitude}%`, totalPnl: -29400 * (magnitude / 5), remainingEquity: 500000 - 29400 * (magnitude / 5), drawdownPct: magnitude * 1.18, survived: true, rating: magnitude < 8 ? 'MEDIUM' : 'HIGH' },
        { scenarioName: `全品种联动`, totalPnl: -81195 * (magnitude / 5), remainingEquity: 500000 - 81195 * (magnitude / 5), drawdownPct: magnitude * 3.24, survived: magnitude < 12, rating: magnitude < 8 ? 'MEDIUM' : 'HIGH' },
      ];
    default:
      return [];
  }
}

/**
 * 压力测试报告 — Phase 3
 * 4 种标准场景，基于当前持仓计算极端行情影响
 * 数据来源：持仓看板（Phase 2）；无持仓时使用 Mock 数据
 */
const StressTestReport: React.FC = () => {
  const [scenario, setScenario] = useState<Scenario>('flash_crash');
  const [magnitude, setMagnitude] = useState<number>(8); // 默认幅度
  const [results, setResults] = useState<StressTestResult[]>([]);
  const [running, setRunning] = useState(false);

  const positions = useMemo(() => getMockPositions(), []);

  // 场景变化时更新默认幅度
  const handleScenarioChange = (value: Scenario) => {
    setScenario(value);
    const scenarioConfig = SCENARIOS.find(s => s.value === value);
    setMagnitude(scenarioConfig?.defaultMagnitude || 8);
  };

  const handleRun = async () => {
    setRunning(true);
    await new Promise(r => setTimeout(r, 800));
    const res = runMockStressTest(scenario, positions, magnitude);
    setResults(res);
    setRunning(false);
  };

  const totalResult = results.length === 1 ? results[0] : null;
  const overallSurvived = results.every(r => r.survived);
  const worstRating = results.reduce<string>((worst, r) => {
    const order = { PASS: 0, LOW: 1, MEDIUM: 2, HIGH: 3 };
    return order[r.rating] > (order[worst] ?? 0) ? r.rating : worst;
  }, 'PASS');

  const positionColumns = [
    { title: '品种', dataIndex: 'symbol', key: 'symbol', width: 70 },
    { title: '交易所', dataIndex: 'exchange', key: 'exchange', width: 70 },
    {
      title: '方向', dataIndex: 'direction', key: 'direction', width: 60,
      render: (d: string) => <Tag color={d === 'long' ? 'green' : 'red'}>{d === 'long' ? '多' : '空'}</Tag>,
    },
    { title: '开平', dataIndex: 'positionType', key: 'positionType', width: 70,
      render: (t: string) => t === 'open' ? '开仓' : t === 'close' ? '平仓' : t === 'close_today' ? '平今' : t,
    },
    { title: '手数', dataIndex: 'volume', key: 'volume', width: 60, align: 'right' as const },
    {
      title: '均价', dataIndex: 'avgPrice', key: 'avgPrice', width: 90, align: 'right' as const,
      render: (v: number) => v?.toFixed(2) ?? '-',
    },
    {
      title: '合约价值', key: 'exposure', width: 100, align: 'right' as const,
      render: (_: any, record: any) => {
        const exposure = record.avgPrice * record.volume * (record.direction === 'long' ? 1 : -0.5);
        return <Text style={{ color: exposure >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {exposure >= 0 ? '+' : ''}{exposure.toFixed(0)}
        </Text>;
      },
    },
  ];

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4}><ThunderboltOutlined /> 压力测试报告</Title>
      <Text type="secondary">非交易时段 — 使用 Mock 数据模拟</Text>

      <Divider />

      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card size="small" title="测试场景">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select value={scenario} onChange={handleScenarioChange} style={{ width: '100%' }}>
                {SCENARIOS.map(s => (
                  <Select.Option key={s.value} value={s.value}>
                    <Space>{s.icon} {s.label} <Text type="secondary">— {s.desc}</Text></Space>
                  </Select.Option>
                ))}
              </Select>
              {/* 幅度滑块 */}
              <div>
                <Text style={{ fontSize: 12 }}>幅度调节：{magnitude}{scenario === 'volatility_spike' ? 'x' : '%'}</Text>
                <Slider
                  min={scenario === 'volatility_spike' ? 1 : 3}
                  max={scenario === 'volatility_spike' ? 5 : 30}
                  value={magnitude}
                  onChange={setMagnitude}
                  marks={scenario === 'volatility_spike' ? { 1: '1x', 2: '2x', 3: '3x', 4: '4x', 5: '5x' } : { 5: '5%', 10: '10%', 15: '15%', 20: '20%', 25: '25%', 30: '30%' }}
                />
              </div>
              <Button
                type="primary"
                size="large"
                block
                icon={<ThunderboltOutlined />}
                loading={running}
                onClick={handleRun}
              >
                运行压力测试
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card size="small" title="当前持仓（Mock）">
            {positions.length === 0 ? <Empty description="无持仓" /> : (
              <Table
                dataSource={positions}
                columns={positionColumns}
                rowKey="symbol"
                size="small"
                pagination={false}
                scroll={{ x: 'max-content' }}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Divider />

      {results.length > 0 && (
        <>
          {totalResult && (
            <Card size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16} align="middle">
                <Col flex="auto">
                  <Space>
                    {overallSurvived
                      ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 28 }} />
                      : <WarningOutlined style={{ color: '#ff4d4f', fontSize: 28 }} />}
                    <div>
                      <Title level={5} style={{ margin: 0 }}>
                        {totalResult.scenarioName} — {overallSurvived ? '✅ 存活' : '❌ 爆仓'}
                      </Title>
                      <Text type="secondary">综合评级：</Text>{' '}
                      <Tag color={SEVERITY_RATING[worstRating]?.color}>{SEVERITY_RATING[worstRating]?.label}</Tag>
                    </div>
                  </Space>
                </Col>
                <Col>
                  <Row gutter={32}>
                    <Col><Statistic title="总盈亏" value={`¥${totalResult.totalPnl.toLocaleString()}`} valueStyle={{ color: totalResult.totalPnl >= 0 ? '#52c41a' : '#ff4d4f' }} /></Col>
                    <Col><Statistic title="剩余权益" value={`¥${totalResult.remainingEquity.toLocaleString()}`} /></Col>
                  </Row>
                </Col>
              </Row>
            </Card>
          )}

          {results.length > 1 && (
            <Card size="small" title="逐品种测试结果" style={{ marginBottom: 16 }}>
              <Table
                dataSource={results}
                columns={[
                  { title: '场景', dataIndex: 'scenarioName', key: 'scenarioName' },
                  { title: '盈亏', dataIndex: 'totalPnl', key: 'totalPnl', render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>¥{v.toLocaleString()}</Text> },
                  { title: '剩余权益', dataIndex: 'remainingEquity', key: 'remainingEquity', render: (v: number) => `¥${v.toLocaleString()}` },
                  { title: '回撤%', dataIndex: 'drawdownPct', key: 'drawdownPct', render: (v: number) => `${v}%` },
                  { title: '存活', dataIndex: 'survived', key: 'survived', render: (v: boolean) => v ? <Tag color="success">存活</Tag> : <Tag color="error">爆仓</Tag> },
                  { title: '评级', dataIndex: 'rating', key: 'rating', render: (v: string) => <Tag color={SEVERITY_RATING[v]?.color}>{SEVERITY_RATING[v]?.label}</Tag> },
                ]}
                rowKey="scenarioName"
                size="small"
                pagination={false}
              />
            </Card>
          )}

          <Alert
            type={overallSurvived ? 'success' : 'error'}
            message={overallSurvived ? '压力测试通过 — 当前持仓组合在极端行情下可存活' : '压力测试未通过 — 建议调整持仓或增加保证金'}
            showIcon
          />
        </>
      )}

      {results.length === 0 && !running && (
        <Card><Empty description="选择场景并点击「运行压力测试」查看结果" /></Card>
      )}
    </div>
  );
};

export default StressTestReport;
