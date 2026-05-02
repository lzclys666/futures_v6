import React, { useEffect, useState } from 'react';
import {
  Card, Switch, Slider, InputNumber, Button, Tabs, Typography,
  Row, Col, Space, message, Tag, Descriptions, Divider, Badge, Spin, Tooltip,
} from 'antd';
import {
  SaveOutlined,
  UndoOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  AccountBookOutlined,
  SwapOutlined,
  SafetyCertificateOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { useRiskStore, checkOrderWithRules } from '../../store/riskStore';
import type { RiskRuleConfig } from '../../types/risk';

const { Text, Title } = Typography;

const LAYER_INFO: Record<number, { name: string; icon: React.ReactNode }> = {
  1: { name: '市场风险', icon: <ThunderboltOutlined /> },
  2: { name: '账户风险', icon: <AccountBookOutlined /> },
  3: { name: '交易执行', icon: <SwapOutlined /> },
};

const RULE_META: Record<string, { name: string; desc: string; min: number; max: number; step: number; unit: string; isPercent: boolean }> = {
  R5_VOLATILITY:     { name: '波动率', desc: '年化波动率阈值', min: 0.01, max: 0.1, step: 0.005, unit: '', isPercent: true },
  R6_LIQUIDITY:      { name: '流动性', desc: '流动性比率最低要求', min: 0.5, max: 5, step: 0.1, unit: '', isPercent: false },
  R10_MACRO_CIRCUIT_BREAKER: { name: '宏观熔断', desc: '宏观因子复合评分触发阈值', min: 0.3, max: 1.0, step: 0.05, unit: '', isPercent: true },
  R2_DAILY_LOSS:     { name: '单日亏损', desc: '当日最大亏损限额（元）', min: 10000, max: 200000, step: 5000, unit: '¥', isPercent: false },
  R7_CONSECUTIVE_LOSS: { name: '连续亏损', desc: '连续亏损笔数上限', min: 2, max: 10, step: 1, unit: '笔', isPercent: false },
  R11_DISPOSITION_EFFECT: { name: '处置效应', desc: '触发处置效应引导的持仓天数', min: 1, max: 30, step: 1, unit: '天', isPercent: false },
  R1_SINGLE_SYMBOL:  { name: '单品种仓位', desc: '单品种最大保证金占比', min: 10, max: 50, step: 5, unit: '%', isPercent: true },
  R4_TOTAL_MARGIN:   { name: '总保证金', desc: '总保证金占权益上限', min: 20, max: 80, step: 5, unit: '%', isPercent: true },
  R3_PRICE_LIMIT:    { name: '涨跌停', desc: '涨跌停板幅度校验', min: 0, max: 1, step: 1, unit: '', isPercent: false },
  R8_TRADING_HOURS:  { name: '交易时间', desc: '交易时段限制', min: 0, max: 1, step: 1, unit: '', isPercent: false },
  R9_CAPITAL_SUFFICIENCY: { name: '资金充足', desc: '可用资金最低倍数', min: 1, max: 5, step: 0.5, unit: '倍', isPercent: false },
  R12_CANCEL_LIMIT:   { name: '撤单限制', desc: '日内撤单次数上限', min: 3, max: 30, step: 1, unit: '次', isPercent: false },
};

/** 三档预设配置 */
const PRESETS: Record<string, { name: string; desc: string; rules: Partial<Record<string, number>> }> = {
  conservative: {
    name: '保守',
    desc: '低风险偏好，严格止损，小额仓位',
    rules: {
      R5_VOLATILITY: 0.02,
      R2_DAILY_LOSS: 20000,
      R7_CONSECUTIVE_LOSS: 2,
      R1_SINGLE_SYMBOL: 15,
      R4_TOTAL_MARGIN: 30,
      R9_CAPITAL_SUFFICIENCY: 3,
      R12_CANCEL_LIMIT: 5,
    },
  },
  moderate: {
    name: '稳健',
    desc: '中等风险偏好，适度杠杆',
    rules: {
      R5_VOLATILITY: 0.03,
      R2_DAILY_LOSS: 50000,
      R7_CONSECUTIVE_LOSS: 3,
      R1_SINGLE_SYMBOL: 30,
      R4_TOTAL_MARGIN: 50,
      R9_CAPITAL_SUFFICIENCY: 1.5,
      R12_CANCEL_LIMIT: 10,
    },
  },
  aggressive: {
    name: '激进',
    desc: '高风险偏好，大仓位允许',
    rules: {
      R5_VOLATILITY: 0.05,
      R2_DAILY_LOSS: 100000,
      R7_CONSECUTIVE_LOSS: 5,
      R1_SINGLE_SYMBOL: 45,
      R4_TOTAL_MARGIN: 70,
      R9_CAPITAL_SUFFICIENCY: 1.2,
      R12_CANCEL_LIMIT: 20,
    },
  },
};

interface Props {}

interface RuleConfigState extends RiskRuleConfig {
  dirty: boolean;
  /** 保存时的原始 threshold（reset 目标值） */
  savedThreshold: number;
  /** P2-2: 预设 diff - 与预设值的差异 */
  presetDiff?: number;
}

/**
 * 风控规则配置页面 — 三层可调风控，含三档预设（保守/稳健/激进）
 */
const RiskConfigPage: React.FC<Props> = () => {
  const { rules: savedRules, fetchRules, updateRules } = useRiskStore();
  const [localRules, setLocalRules] = useState<RuleConfigState[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRules().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (savedRules.length > 0 && localRules.length === 0) {
      const allRuleIds = Object.keys(RULE_META);
      const mapped: RuleConfigState[] = allRuleIds.map((ruleId) => {
        const exist = savedRules.find(r => r.ruleId === ruleId);
        const meta = RULE_META[ruleId];
        const threshold = exist?.threshold ?? meta.min + (meta.max - meta.min) / 2;
        return {
          id: exist?.id ?? ruleId,
          ruleId: ruleId as RiskRuleConfig['ruleId'],
          name: exist?.name ?? meta.name,
          enabled: exist?.enabled ?? true,
          layer: exist?.layer ?? (ruleId.startsWith('R5') || ruleId.startsWith('R6') ? 2 : 1) as 1 | 2 | 3,
          threshold,
          currentValue: exist?.currentValue ?? 0,
          unit: exist?.unit ?? meta.unit,
          dirty: false,
          savedThreshold: threshold, // 记录保存时的值
        };
      });
      setLocalRules(mapped);
    }
  }, [savedRules]);

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spin tip="加载配置…" /></div>;
  }

  const handleToggle = (ruleId: string) => {
    setLocalRules(prev => prev.map(r => r.ruleId === ruleId ? { ...r, enabled: !r.enabled, dirty: true } : r));
  };

  const handleThreshold = (ruleId: string, val: number | null) => {
    if (val === null) return;
    setLocalRules(prev => prev.map(r => r.ruleId === ruleId ? { ...r, threshold: val, dirty: true } : r));
  };

  /** 重置：恢复所有规则为已保存状态 */
  const handleReset = () => {
    setLocalRules(prev => prev.map(r => ({
      ...r,
      threshold: r.savedThreshold,
      dirty: false,
      presetDiff: undefined,
    })));
    setSelectedPreset(null);
  };

  const handleApplyPreset = (key: string) => {
    const preset = PRESETS[key];
    setSelectedPreset(key);
    setLocalRules(prev => prev.map(r => {
      const pv = preset.rules[r.ruleId];
      const newThreshold = pv !== undefined ? pv : r.threshold;
      const diff = pv !== undefined ? newThreshold - r.threshold : 0;
      return {
        ...r,
        threshold: newThreshold,
        enabled: true,
        dirty: true,
        presetDiff: diff,
      };
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    const toSave: RiskRuleConfig[] = localRules
      .filter(r => r.dirty)
      .map(({ dirty, savedThreshold, presetDiff, ...rest }) => rest);
    try {
      await updateRules(toSave);
      message.success('风控规则已保存');
      // 保存后更新 savedThreshold = 当前 threshold
      setLocalRules(prev => prev.map(r => ({
        ...r,
        dirty: false,
        savedThreshold: r.dirty ? r.threshold : r.savedThreshold,
        presetDiff: undefined,
      })));
      setSelectedPreset(null);
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  /** 预检：基于当前阈值模拟一笔测试订单 */
  const handlePrecheck = () => {
    const enabledRules = localRules.filter(r => r.enabled).map(({ dirty, savedThreshold, ...rest }) => rest);
    const result = checkOrderWithRules(enabledRules, {
      symbol: 'RB',
      direction: 'long',
      volume: 5,
      price: 3700,
    });
    if (result.pass) {
      message.success('预检通过：当前阈值配置下允许开仓');
    } else {
      message.error(`预检拦截：${result.message}`);
    }
  };

  const dirtyCount = localRules.filter(r => r.dirty).length;

  const byLayer = (() => {
    const m: Record<number, RuleConfigState[]> = { 1: [], 2: [], 3: [] };
    localRules.forEach(r => {
      const layer = r.ruleId.startsWith('R5') || r.ruleId.startsWith('R6') || r.ruleId === 'R10_MACRO_CIRCUIT_BREAKER'
        ? 1 : r.ruleId === 'R2_DAILY_LOSS' || r.ruleId === 'R7_CONSECUTIVE_LOSS' || r.ruleId === 'R11_DISPOSITION_EFFECT'
        ? 2 : 3;
      if (m[layer]) m[layer].push(r);
    });
    return m;
  })();

  const tabItems = ([1, 2, 3] as const).map(layer => ({
    key: String(layer),
    label: (
      <Space>
        {LAYER_INFO[layer].icon}
        <span>{LAYER_INFO[layer].name}</span>
        <Badge count={byLayer[layer].length} style={{ backgroundColor: '#1677ff' }} />
      </Space>
    ),
    children: (
      <div style={{ padding: '8px 0' }}>
        {byLayer[layer].map(rule => {
          const meta = RULE_META[rule.ruleId];
          if (!meta) return null;
          return (
            <Card
              key={rule.ruleId}
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <Space>
                  <Badge status={rule.enabled ? 'success' : 'default'} />
                  <Text strong>{rule.ruleId}</Text>
                  <Text type="secondary">— {meta.name}</Text>
                  {rule.dirty && <Tag color="orange">已修改</Tag>}
                </Space>
              }
              extra={
                <Switch
                  checked={rule.enabled}
                  onChange={() => handleToggle(rule.ruleId)}
                  checkedChildren="启用"
                  unCheckedChildren="禁用"
                />
              }
            >
              <Tooltip title={meta.desc}>
                <Text type="secondary"><InfoCircleOutlined /> {meta.desc}</Text>
              </Tooltip>

              <Divider style={{ margin: '8px 0' }} />

              <Row gutter={16} align="middle">
                <Col span={16}>
                  <Slider
                    min={meta.min}
                    max={meta.max}
                    step={meta.step}
                    value={rule.threshold}
                    onChange={v => handleThreshold(rule.ruleId, v)}
                    disabled={!rule.enabled}
                  />
                </Col>
                <Col span={8}>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <InputNumber
                      style={{ width: '100%' }}
                      min={meta.min}
                      max={meta.max}
                      step={meta.step}
                      value={rule.threshold}
                      onChange={v => handleThreshold(rule.ruleId, v)}
                      disabled={!rule.enabled}
                      addonAfter={meta.unit}
                      formatter={v => meta.isPercent ? `${(Number(v) * 100).toFixed(1)}%` : `${v}`}
                      parser={v => meta.isPercent ? Number(v?.replace('%', '')) / 100 : Number(v)}
                    />
                    {/* P2-2: 预设 diff 高亮 */}
                    {rule.presetDiff !== undefined && rule.presetDiff !== 0 && (
                      <Text style={{ fontSize: 11, color: rule.presetDiff > 0 ? '#ff4d4f' : '#52c41a' }}>
                        {rule.presetDiff > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                        {meta.isPercent
                          ? `${Math.abs(rule.presetDiff * 100).toFixed(1)}%`
                          : `${Math.abs(rule.presetDiff).toFixed(0)}${meta.unit}`}
                      </Text>
                    )}
                  </Space>
                </Col>
              </Row>
              <Descriptions size="small" style={{ marginTop: 8 }}>
                <Descriptions.Item label="范围">
                  {meta.min}{meta.unit} ~ {meta.max}{meta.unit}
                </Descriptions.Item>
                <Descriptions.Item label="步长">{meta.step}{meta.unit}</Descriptions.Item>
              </Descriptions>
            </Card>
          );
        })}
      </div>
    ),
  }));

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <Card
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>风控配置模板</span>
          </Space>
        }
      >
        <Row gutter={12}>
          {Object.entries(PRESETS).map(([key, preset]) => (
            <Col span={8} key={key}>
              <Card
                size="small"
                hoverable
                onClick={() => handleApplyPreset(key)}
                style={{
                  border: selectedPreset === key ? '2px solid #1890ff' : undefined,
                  cursor: 'pointer',
                }}
              >
                <Title level={5} style={{ margin: 0 }}>{preset.name}</Title>
                <Text type="secondary">{preset.desc}</Text>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      <Card
        title={<span>风控规则配置（{dirtyCount} 项待保存）</span>}
        extra={
          <Space>
            <Button
              icon={<ThunderboltOutlined />}
              onClick={handlePrecheck}
            >
              预检
            </Button>
            <Button
              icon={<UndoOutlined />}
              onClick={handleReset}
              disabled={dirtyCount === 0}
            >
              重置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              disabled={dirtyCount === 0}
            >
              保存 (R1-R12)
            </Button>
          </Space>
        }
      >
        <Tabs defaultActiveKey="1" items={tabItems} size="large" />
      </Card>
    </div>
  );
};

export default RiskConfigPage;
