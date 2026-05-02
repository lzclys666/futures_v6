import React, { useEffect } from 'react';
import { Card, Empty, Tag, Progress, Row, Col, Typography, Spin, Select } from 'antd';
import { useMacroStore } from '../store/macroStore';
import type { SignalStrength } from '../types/macro';

const { Text } = Typography;
const { Option } = Select;

const SYMBOL_OPTIONS = [
  { value: 'RB', label: '螺纹钢 (RB)' },
  { value: 'JM', label: '焦煤 (JM)' },
  { value: 'NI', label: '镍 (NI)' },
  { value: 'RU', label: '橡胶 (RU)' },
  { value: 'ZN', label: '锌 (ZN)' },
];

/**
 * 信号系统卡片 — P2-3 修复版
 * P2-3: 添加品种选择器，支持切换品种查看信号
 *
 * 品种变化 → setSymbol 更新 currentSymbol → useEffect 重新拉取数据
 */
const SignalSystemCardBase: React.FC = () => {
  const {
    signalSystem,
    batchSignals,
    currentSymbol,
    fetchSignalSystem,
    fetchBatchSignals,
  } = useMacroStore();

  // currentSymbol 变化时重新拉取信号系统数据（仅信号系统相关，不影响主信号）
  useEffect(() => {
    fetchSignalSystem(currentSymbol);
    fetchBatchSignals([currentSymbol]);
  }, [currentSymbol, fetchSignalSystem, fetchBatchSignals]);

  // 品种切换：更新 store currentSymbol（触发主信号 MacroBoard 共用状态）
  const handleSymbolChange = (symbol: string) => {
    useMacroStore.getState().setSymbol(symbol as any);
  };

  // displaySignal：优先 signalSystem（YIYI Week 4），fallback batchSignals[0]
  const displaySignal = signalSystem ?? batchSignals[0] ?? null;

  if (!displaySignal) {
    return (
      <Card size="small" title="信号系统">
        <Spin size="small" style={{ display: 'block', margin: '20px auto', textAlign: 'center' }} />
        <Empty description="暂无信号数据" style={{ marginTop: 16 }} />
        <p style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center', marginTop: 8, marginBottom: 0 }}>
          非交易时段 — 数据来自 Mock 快照
        </p>
      </Card>
    );
  }

  const compositeScore = 'compositeScore' in displaySignal
    ? (displaySignal as any).compositeScore
    : (displaySignal as any).score ?? 0;
  const signalStrength = 'signalStrength' in displaySignal
    ? (displaySignal as any).signalStrength
    : (displaySignal as any).signal ?? undefined;
  const confidence = 'confidence' in displaySignal
    ? (displaySignal as any).confidence
    : (displaySignal as any).strength === 'STRONG' ? 85
      : (displaySignal as any).strength === 'MODERATE' ? 55 : 25;
  const regime = 'regime' in displaySignal ? (displaySignal as any).regime : undefined;
  const factorBreakdown = 'factorBreakdown' in displaySignal
    ? (displaySignal as any).factorBreakdown
    : 'factorDetails' in displaySignal ? (displaySignal as any).factorDetails : [];

  const signalColor = (s: SignalStrength | string | undefined): string => {
    switch (s) {
      case 'STRONG_BUY': case 'BUY': return '#52c41a';
      case 'SELL': case 'STRONG_SELL': return '#ff4d4f';
      case 'NEUTRAL': return '#faad14';
      default: return '#8c8c8c';
    }
  };

  const signalLabel = (s: SignalStrength | string | undefined): string => {
    switch (s) {
      case 'STRONG_BUY': return '强烈做多';
      case 'BUY': return '做多';
      case 'SELL': return '做空';
      case 'STRONG_SELL': return '强烈做空';
      case 'NEUTRAL': return '中性';
      default: return '未知';
    }
  };

  return (
    <Card
      size="small"
      title={`信号系统 — ${displaySignal.symbol}`}
      extra={
        <Select
          value={currentSymbol}
          onChange={handleSymbolChange}
          style={{ width: 140 }}
          size="small"
        >
          {SYMBOL_OPTIONS.map(opt => (
            <Option key={opt.value} value={opt.value}>{opt.label}</Option>
          ))}
        </Select>
      }
    >
      <div style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Typography.Text type="secondary">综合评分</Typography.Text>
            <div style={{
              fontSize: 32, fontWeight: 'bold',
              color: compositeScore > 60 ? '#52c41a' : compositeScore < 40 ? '#ff4d4f' : '#faad14'
            }}>
              {typeof compositeScore === 'number' ? compositeScore.toFixed(1) : '--'}
            </div>
          </Col>
          <Col span={12}>
            <Typography.Text type="secondary">信号强度</Typography.Text>
            <div>
              <Tag color={signalColor(signalStrength)} style={{ fontSize: 16, padding: '4px 12px' }}>
                {signalLabel(signalStrength)}
              </Tag>
            </div>
          </Col>
        </Row>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Typography.Text type="secondary">置信度</Typography.Text>
        <Progress
          percent={typeof confidence === 'number' ? confidence : 0}
          status="active"
          strokeColor={confidence > 70 ? '#52c41a' : confidence > 40 ? '#faad14' : '#ff4d4f'}
        />
      </div>

      {regime && (
        <div style={{ marginBottom: 16 }}>
          <Typography.Text type="secondary">市场状态</Typography.Text>
          <div>
            <Tag color={regime === 'TRENDING' ? '#52c41a' : regime === 'RANGING' ? '#faad14' : '#ff4d4f'}>
              {regime === 'TRENDING' ? '趋势' : regime === 'RANGING' ? '震荡' : '波动'}
            </Tag>
          </div>
        </div>
      )}

      {Array.isArray(factorBreakdown) && factorBreakdown.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text type="secondary">因子分解</Typography.Text>
          {factorBreakdown.map((factor: any) => (
            <div key={factor.factorName} style={{ marginTop: 8 }}>
              <Row justify="space-between">
                <Typography.Text>{factor.factorName}</Typography.Text>
                <Typography.Text style={{ color: factor.direction === 'positive' ? '#52c41a' : factor.direction === 'negative' ? '#ff4d4f' : '#8c8c8c' }}>
                  {factor.contribution > 0 ? '+' : ''}{factor.contribution?.toFixed(2) ?? '0.00'}
                </Typography.Text>
              </Row>
              <Progress
                percent={Math.min(Math.abs(factor.contribution ?? 0) * 5, 100)}
                size="small"
                strokeColor={factor.direction === 'positive' ? '#52c41a' : factor.direction === 'negative' ? '#ff4d4f' : '#8c8c8c'}
                showInfo={false}
              />
            </div>
          ))}
        </div>
      )}

      <p style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center', marginTop: 12, marginBottom: 0 }}>
        非交易时段 — 数据来自 Mock 快照 · Phase 3 对接 YIYI 信号 API 后实时更新
      </p>
    </Card>
  );
};

const SignalSystemCard = React.memo(SignalSystemCardBase);
export default SignalSystemCard;
