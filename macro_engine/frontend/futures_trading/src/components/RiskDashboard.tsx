import React, { useEffect } from 'react';
import { Card, Tag, Row, Col, Spin, Typography, Space } from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useRiskStore } from '../store/riskStore';
import type { RiskRuleStatus } from '../types/risk';

const { Text } = Typography;

/** 严重度 → 颜色 */
const severityColor = (s: string): string =>
  s === 'PASS' || s === 'LOW' ? '#52c41a' : s === 'MEDIUM' ? '#faad14' : '#ff4d4f';

/** 严重度 → 图标 */
const severityIcon = (s: string): React.ReactNode =>
  s === 'PASS' || s === 'LOW' ? <CheckCircleOutlined /> : s === 'MEDIUM' ? <WarningOutlined /> : <CloseCircleOutlined />;

const LAYER_NAMES: Record<number, string> = { 1: '市场风险', 2: '账户风险', 3: '交易执行' };

interface Props { collapsed?: boolean; }

/**
 * 风险仪表盘 — 常驻顶部，展示 11 条风控规则状态（三栏 Layer 分组）
 */
const RiskDashboardBase: React.FC<Props> = ({ collapsed = false }) => {
  const { status, loading, fetchStatus } = useRiskStore();

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 10000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const rules = status?.rules ?? getMockRules();
  const passCount = status?.passCount ?? rules.filter((r: RiskRuleStatus) => r.severity === 'PASS').length;
  const overall = status?.overall ?? 'LOW';

  if (loading && !status) {
    return (
      <Card size="small">
        <Spin tip="加载风控状态…"><div style={{ height: 60 }} /></Spin>
      </Card>
    );
  }

  if (collapsed) {
    return (
      <Card size="small" title={<SafetyCertificateOutlined />}>
        <Text type={overall === 'PASS' ? 'success' : 'danger'}>
          {passCount}/{rules.length} 通过
        </Text>
      </Card>
    );
  }

  const byLayer: Record<number, RiskRuleStatus[]> = { 1: [], 2: [], 3: [] };
  rules.forEach((r: RiskRuleStatus) => { if (byLayer[r.layer]) byLayer[r.layer].push(r); });

  return (
    <Card
      size="small"
      title={
        <Space>
          <SafetyCertificateOutlined />
          <span>风控仪表盘</span>
          <Tag color={overall === 'PASS' ? 'success' : overall === 'HIGH' ? 'error' : 'warning'}>
            {passCount}/{rules.length}
          </Tag>
        </Space>
      }
    >
      <Row gutter={[12, 8]}>
        {([1, 2, 3] as const).map(layer => (
          <Col span={8} key={layer}>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>{LAYER_NAMES[layer]}</Text>
            {byLayer[layer].map(rule => (
              <div key={rule.ruleId} style={{ marginBottom: 6 }}>
                <Space size={4}>
                  <span style={{ color: severityColor(rule.severity) }}>{severityIcon(rule.severity)}</span>
                  <Text style={{ fontSize: 12 }}>{rule.name}</Text>
                </Space>
                {/* 迷你进度条：当前值/阈值 */}
                {rule.currentValue !== undefined && rule.threshold !== undefined && (
                  <div style={{ marginTop: 2, marginLeft: 20 }}>
                    <div style={{
                      height: 3,
                      width: 60,
                      backgroundColor: '#f0f0f0',
                      borderRadius: 2,
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${Math.min(100, Math.abs(rule.currentValue) / Math.abs(rule.threshold) * 100)}%`,
                        height: '100%',
                        backgroundColor: severityColor(rule.severity),
                      }} />
                    </div>
                    <Text type="secondary" style={{ fontSize: 10 }}>
                      {rule.currentValue} / {rule.threshold}
                    </Text>
                  </div>
                )}
              </div>
            ))}
          </Col>
        ))}
      </Row>
      {!status && (
        <p style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center', marginTop: 8, marginBottom: 0 }}>
          非交易时段 — Mock 数据
        </p>
      )}
    </Card>
  );
};

function getMockRules(): RiskRuleStatus[] {
  return [
    { ruleId: 'R5_VOLATILITY', name: '波动率', layer: 1, severity: 'PASS', currentValue: 0.015, threshold: 0.03, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R6_LIQUIDITY', name: '流动性', layer: 1, severity: 'PASS', currentValue: 1, threshold: 1, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R10_MACRO_CIRCUIT_BREAKER', name: '宏观熔断', layer: 1, severity: 'PASS', currentValue: 0, threshold: 1, message: '未触发', updatedAt: new Date().toISOString() },
    { ruleId: 'R2_DAILY_LOSS', name: '单日亏损', layer: 2, severity: 'PASS', currentValue: 0, threshold: 50000, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R7_CONSECUTIVE_LOSS', name: '连续亏损', layer: 2, severity: 'PASS', currentValue: 0, threshold: 3, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R11_DISPOSITION_EFFECT', name: '处置效应', layer: 2, severity: 'PASS', currentValue: 0, threshold: 1, message: '未触发', updatedAt: new Date().toISOString() },
    { ruleId: 'R1_SINGLE_SYMBOL', name: '单品种仓位', layer: 3, severity: 'PASS', currentValue: 20, threshold: 30, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R4_TOTAL_MARGIN', name: '总保证金', layer: 2, severity: 'PASS', currentValue: 25, threshold: 50, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R3_PRICE_LIMIT', name: '涨跌停', layer: 3, severity: 'PASS', currentValue: 0, threshold: 1, message: '正常', updatedAt: new Date().toISOString() },
    { ruleId: 'R8_TRADING_HOURS', name: '交易时间', layer: 3, severity: 'PASS', currentValue: 1, threshold: 1, message: '交易时段', updatedAt: new Date().toISOString() },
    { ruleId: 'R9_CAPITAL_SUFFICIENCY', name: '资金充足', layer: 3, severity: 'PASS', currentValue: 1, threshold: 0.8, message: '充足', updatedAt: new Date().toISOString() },
  ];
}

const RiskDashboard = React.memo(RiskDashboardBase);
export default RiskDashboard;
