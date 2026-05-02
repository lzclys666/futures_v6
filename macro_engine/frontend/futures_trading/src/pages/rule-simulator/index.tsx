
import {
  Card, Button, Select, InputNumber, Row, Col, Statistic, Typography,
  Space, Tag, Divider, Table, Empty, message, Alert,
} from 'antd';
import {
  ExperimentOutlined, CalculatorOutlined,
  CheckCircleOutlined, WarningOutlined, CloseCircleOutlined,
  PlusOutlined, MinusOutlined, UndoOutlined,
} from '@ant-design/icons';
import type { SymbolCode } from '../../types';
import { SYMBOL_LIST } from '../../types';

const { Text, Title } = Typography;

type SimAction = 'add_long' | 'add_short' | 'reduce';

interface SimRuleResult {
  ruleId: string;
  name: string;
  before: 'PASS' | 'WARN' | 'BLOCK';
  after: 'PASS' | 'WARN' | 'BLOCK';
  beforeValue: number;
  afterValue: number;
  threshold: number;
  changed: boolean;
}

const MOCK_RULES: SimRuleResult[] = [
  { ruleId: 'R1_SINGLE_SYMBOL', name: '单品种仓位', before: 'PASS', after: 'PASS', beforeValue: 22, afterValue: 22, threshold: 30, changed: false },
  { ruleId: 'R2_DAILY_LOSS', name: '单日亏损', before: 'PASS', after: 'PASS', beforeValue: 8500, afterValue: 8500, threshold: 50000, changed: false },
  { ruleId: 'R4_TOTAL_MARGIN', name: '总保证金', before: 'WARN', after: 'WARN', beforeValue: 42, afterValue: 42, threshold: 50, changed: false },
  { ruleId: 'R5_VOLATILITY', name: '波动率', before: 'PASS', after: 'PASS', beforeValue: 1.5, afterValue: 1.5, threshold: 3, changed: false },
  { ruleId: 'R6_LIQUIDITY', name: '流动性', before: 'PASS', after: 'PASS', beforeValue: 0.8, afterValue: 0.8, threshold: 1, changed: false },
  { ruleId: 'R9_CAPITAL_SUFFICIENCY', name: '资金充足', before: 'PASS', after: 'PASS', beforeValue: 185000, afterValue: 185000, threshold: 50000, changed: false },
];

const ACTION_OPTIONS: { value: SimAction; label: string; icon: React.ReactNode }[] = [
  { value: 'add_long', label: '加仓做多', icon: <PlusOutlined style={{ color: '#52c41a' }} /> },
  { value: 'add_short', label: '加仓做空', icon: <PlusOutlined style={{ color: '#ff4d4f' }} /> },
  { value: 'reduce', label: '减持平仓', icon: <MinusOutlined style={{ color: '#faad14' }} /> },
];

/**
 * Rule Simulator — 模拟交易对风控规则的影响
 * "如果我加仓 2 手螺纹钢..."
 * P4-1: 添加重置按钮 + Enter 键盘快捷键
 */
const RuleSimulator: React.FC = () => {
  const [symbol, setSymbol] = useState<SymbolCode>('RB');
  const [action, setAction] = useState<SimAction>('add_long');
  const [volume, setVolume] = useState(2);
  const [price, setPrice] = useState<number | null>(3750);
  const [results, setResults] = useState<SimRuleResult[] | null>(null);

  // Enter 键盘快捷键触发模拟


  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
        const active = document.activeElement;
        // 仅在 volume/price input 内按 Enter 才触发
        if (active && (active.id === 'sim-volume' || active.id === 'sim-price')) {
          handleSimulate();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [symbol, action, volume, price]);

  /** 重置：清空结果 + 恢复默认值 */
  const handleReset = () => {
    setSymbol('RB');
    setAction('add_long');
    setVolume(2);
    setPrice(3750);
    setResults(null);
  };

  const handleSimulate = () => {
    if (!price) { message.warning('请输入价格'); return; }
    if (volume <= 0) { message.warning('请输入有效手数'); return; }

    const simulated = MOCK_RULES.map(rule => {
      let newValue = rule.beforeValue;
      let newSeverity: 'PASS' | 'WARN' | 'BLOCK' = rule.before;

      switch (rule.ruleId) {
        case 'R1_SINGLE_SYMBOL':
          newValue = action !== 'reduce'
            ? Math.min(rule.beforeValue + volume * 4, 100)
            : Math.max(rule.beforeValue - volume * 4, 0);
          break;
        case 'R4_TOTAL_MARGIN':
          newValue = action !== 'reduce'
            ? Math.min(rule.beforeValue + volume * 2.5, 100)
            : Math.max(rule.beforeValue - volume * 2.5, 0);
          break;
        case 'R9_CAPITAL_SUFFICIENCY':
          newValue = action !== 'reduce'
            ? Math.max(rule.beforeValue - volume * price * 0.15, 0)
            : Math.min(rule.beforeValue + volume * price * 0.1, 500000);
          break;
      }

      if (rule.ruleId === 'R9_CAPITAL_SUFFICIENCY') {
        newSeverity = newValue < 100000 ? 'BLOCK' : newValue < 200000 ? 'WARN' : 'PASS';
      } else {
        const ratio = newValue / rule.threshold;
        newSeverity = ratio >= 1 ? 'BLOCK' : ratio >= 0.8 ? 'WARN' : 'PASS';
      }

      return {
        ...rule,
        after: newSeverity,
        afterValue: parseFloat(newValue.toFixed(2)),
        changed: newSeverity !== rule.before || Math.abs(newValue - rule.beforeValue) > 0.01,
      };
    });

    setResults(simulated);
  };

  const changedCount = results?.filter(r => r.changed).length ?? 0;
  const blockCount = results?.filter(r => r.after === 'BLOCK').length ?? 0;
  const warnCount = results?.filter(r => r.after === 'WARN').length ?? 0;

  const columns = [
    { title: '规则', dataIndex: 'ruleId', key: 'ruleId', width: 150, render: (id: string) => <Text code>{id}</Text> },
    { title: '名称', dataIndex: 'name', key: 'name', width: 100 },
    {
      title: '操作前', key: 'before', width: 130,
      render: (_: unknown, r: SimRuleResult) => (
        <Space>
          <Tag color={r.before === 'PASS' ? 'success' : r.before === 'WARN' ? 'warning' : 'error'}>
            {r.before === 'PASS' ? '通过' : r.before === 'WARN' ? '警告' : '阻断'}
          </Tag>
          <Text type="secondary">{r.beforeValue}</Text>
        </Space>
      ),
    },
    {
      title: '操作后', key: 'after', width: 130,
      render: (_: unknown, r: SimRuleResult) => (
        <Space>
          <Tag color={r.after === 'PASS' ? 'success' : r.after === 'WARN' ? 'warning' : 'error'}>
            {r.after === 'PASS' ? '通过' : r.after === 'WARN' ? '警告' : '阻断'}
          </Tag>
          <Text style={{ color: r.changed ? '#ff4d4f' : undefined, fontWeight: r.changed ? 'bold' : undefined }}>
            {r.afterValue}
          </Text>
        </Space>
      ),
    },
    { title: '阈值', dataIndex: 'threshold', key: 'threshold', width: 80 },
    {
      title: '变化', key: 'changed', width: 80,
      render: (_: unknown, r: SimRuleResult) => r.changed
        ? <Tag color="error">⚠ 变化</Tag>
        : <Tag>—</Tag>,
    },
  ];

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4}><ExperimentOutlined /> Rule Simulator</Title>
      <Text type="secondary">模拟交易对风控规则的影响 — "如果我加仓 2 手螺纹钢..."</Text>
      <Divider />
      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <Card
            size="small"
            title="模拟操作"
            extra={
              <Button
                icon={<UndoOutlined />}
                onClick={handleReset}
                size="small"
              >
                重置
              </Button>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>品种</Text>
                <Select value={symbol} onChange={setSymbol} style={{ width: '100%' }}>
                  {SYMBOL_LIST.map(s => (
                    <Select.Option key={s.code} value={s.code}>{s.name} ({s.code})</Select.Option>
                  ))}
                </Select>
              </div>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>操作</Text>
                <Select value={action} onChange={setAction} style={{ width: '100%' }}>
                  {ACTION_OPTIONS.map(o => (
                    <Select.Option key={o.value} value={o.value}>
                      <Space>{o.icon} {o.label}</Space>
                    </Select.Option>
                  ))}
                </Select>
              </div>
              <Row gutter={12}>
                <Col span={12}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>价格 (¥)</Text>
                  <InputNumber
                    id="sim-price"
                    ref={(el) => (priceInputRef.current = el)}
                    style={{ width: '100%' }}
                    value={price}
                    onChange={setPrice}
                    min={0}
                    step={1}
                    prefix="¥"
                  />
                </Col>
                <Col span={12}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>手数</Text>
                  <InputNumber
                    id="sim-volume"
                    style={{ width: '100%' }}
                    value={volume}
                    onChange={v => setVolume(v ?? 1)}
                    min={1}
                    max={100}
                    step={1}
                  />
                </Col>
              </Row>
              <Button
                type="primary"
                size="large"
                block
                icon={<CalculatorOutlined />}
                onClick={handleSimulate}
              >
                运行模拟（Enter 触发）
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          {results ? (
            <>
              <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={32}>
                  <Col><Statistic
                    title="阻断规则"
                    value={blockCount}
                    valueStyle={{ color: blockCount > 0 ? '#ff4d4f' : '#52c41a' }}
                    prefix={blockCount > 0 ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
                  /></Col>
                  <Col><Statistic
                    title="警告规则"
                    value={warnCount}
                    valueStyle={{ color: warnCount > 0 ? '#faad14' : '#52c41a' }}
                    prefix={<WarningOutlined />}
                  /></Col>
                  <Col><Statistic
                    title="状态变化"
                    value={changedCount}
                    valueStyle={{ color: changedCount > 0 ? '#ff4d4f' : '#52c41a' }}
                    prefix={changedCount > 0 ? <WarningOutlined /> : <CheckCircleOutlined />}
                  /></Col>
                  <Col>
                    <Tag
                      color={blockCount > 0 ? 'error' : warnCount > 0 ? 'warning' : 'success'}
                      style={{ fontSize: 14, padding: '4px 16px', marginTop: 4 }}
                    >
                      {blockCount > 0 ? '❌ 操作被阻断' : warnCount > 0 ? '⚠️ 存在风险' : '✅ 操作可执行'}
                    </Tag>
                  </Col>
                </Row>
              </Card>

              {blockCount > 0 && (
                <Alert
                  type="error"
                  message="风控阻断 — 当前模拟操作会导致以下规则触发阻断"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              <Card size="small" title="逐规则对比">
                <Table
                  dataSource={results}
                  columns={columns}
                  rowKey="ruleId"
                  size="small"
                  pagination={false}
                />
              </Card>
            </>
          ) : (
            <Card><Empty description="选择操作参数并点击「运行模拟」查看风控影响" /></Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default RuleSimulator;
