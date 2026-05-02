import React, { useState } from 'react';
import {
  Card, Form, InputNumber, Button, Result, Row, Col, Statistic,
  Typography, Divider, Space, Alert, Slider, Segmented,
} from 'antd';
import {
  CalculatorOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import type { KellyInput, KellyResult } from '../../types/risk';

const { Text, Title, Paragraph } = Typography;

/** Kelly 公式计算核心 */
function calculateKelly(input: KellyInput & { volatility?: number }): KellyResult {
  const { winRate, profitLossRatio, equity, volatility = 0.15 } = input;
  
  // 全凯利 f* = p - q/b, q = 1-p
  const fullKelly = winRate - (1 - winRate) / profitLossRatio;
  
  // 半凯利
  const halfKelly = fullKelly / 2;
  
  // 波动率调整（使用用户配置的波动率）
  const vol = volatility;
  const volAdjusted = fullKelly * (1 - vol / (Math.abs(fullKelly) || 1));
  
  // 建议
  let suggestion = '';
  if (fullKelly <= 0) {
    suggestion = '负期望，不建议交易';
  } else if (fullKelly < 0.05) {
    suggestion = '全凯利仓位过小，建议使用半凯利';
  } else if (fullKelly > 0.25) {
    suggestion = '风险过高，强烈建议使用半凯利或更低仓位';
  } else if (fullKelly > 0.1) {
    suggestion = '建议使用半凯利仓位';
  } else {
    suggestion = '全凯利仓位合适';
  }
  
  return {
    fullKelly: Math.max(0, fullKelly),
    halfKelly: Math.max(0, halfKelly),
    volAdjusted: Math.max(0, volAdjusted),
    suggestion,
  };
}

interface FormValues extends KellyInput {}

/**
 * 凯利公式计算器页面 — 基于历史胜率/盈亏比计算最优仓位
 */
const KellyPage: React.FC = () => {
  const [result, setResult] = useState<KellyResult | null>(null);
  const [calculatorMode, setCalculatorMode] = useState<string>('simple');
  const [form] = Form.useForm<FormValues>();

  const handleCalculate = (values: FormValues) => {
    const kellyResult = calculateKelly(values);
    setResult(kellyResult);
  };

  const handleReset = () => {
    form.resetFields();
    setResult(null);
  };

  const kellyMode = calculatorMode === 'simple';

  return (
    <div style={{ padding: 16, maxWidth: 800, margin: '0 auto' }}>
      {/* 说明卡片 */}
      <Alert
        style={{ marginBottom: 16 }}
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="凯利公式说明"
        description={
          <Paragraph style={{ marginBottom: 0 }}>
            凯利公式是用于确定最优投资仓位的数学公式：<Text code>f* = p - q/b</Text>，
            其中 p 为胜率，q=1-p 为败率，b 为盈亏比。强烈建议使用半凯利以降低极端波动风险。
          </Paragraph>
        }
      />

      {/* 计算模式选择 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>计算模式：</Text>
          <Segmented
            value={calculatorMode}
            onChange={v => { setCalculatorMode(v as string); handleReset(); }}
            options={[
              { label: '简单模式', value: 'simple' },
              { label: '高级模式', value: 'advanced' },
            ]}
          />
        </Space>
      </Card>

      {/* 输入表单 */}
      <Card
        title={
          <Space>
            <CalculatorOutlined />
            <span>输入参数</span>
          </Space>
        }
        extra={
          <Button type="link" onClick={handleReset}>
            重置
          </Button>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCalculate}
          initialValues={{
            winRate: 0.5,
            profitLossRatio: 2,
            equity: 100000,
            volatility: 0.15,
          }}
        >
          <Row gutter={16}>
            <Col span={kellyMode ? 24 : 12}>
              <Form.Item
                label={
                  <Space>
                    <span>历史胜率</span>
                    <Tooltip title="基于至少30笔历史交易计算的成功率，样本越多越可靠">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
                    </Tooltip>
                  </Space>
                }
                name="winRate"
                rules={[{ required: true, message: '请输入胜率' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.01 as number}
                  max={0.99 as number}
                  step={0.01 as number}
                  precision={2}
                  addonAfter="%"
                  formatter={v => `${(Number(v) * 100).toFixed(0)}%`}
                  parser={v => Number(v?.replace('%', '')) / 100}
                />
              </Form.Item>
            </Col>
            <Col span={kellyMode ? 24 : 12}>
              <Form.Item
                label={
                  <Space>
                    <span>盈亏比</span>
                    <Tooltip title="平均盈利金额 ÷ 平均亏损金额，建议基于历史数据计算">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
                    </Tooltip>
                  </Space>
                }
                name="profitLossRatio"
                rules={[{ required: true, message: '请输入盈亏比' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.1}
                  max={10}
                  step={0.1}
                  precision={2}
                  addonAfter=":1"
                />
              </Form.Item>
            </Col>
          </Row>

          {!kellyMode && (
            <>
              <Form.Item
                label={
                  <Space>
                    <span>当前权益</span>
                    <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} title="可用于交易的资金" />
                  </Space>
                }
                name="equity"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={1000 as number}
                  max={100000000 as number}
                  step={1000 as number}
                  precision={0}
                  formatter={v => `¥${Number(v).toLocaleString()}`}
                  parser={v => Number(v?.replace(/¥|,/g, ''))}
                />
              </Form.Item>
              <Form.Item
                label={
                  <Space>
                    <span>波动率</span>
                    <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} title="年化波动率，影响波动率调整仓位计算。默认15%适用于多数期货品种" />
                  </Space>
                }
                name="volatility"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.01 as number}
                  max={1 as number}
                  step={0.01 as number}
                  precision={2}
                  addonAfter="%"
                  formatter={v => `${(Number(v) * 100).toFixed(0)}%`}
                  parser={v => Number(v?.replace('%', '')) / 100}
                />
              </Form.Item>
            </>
          )}

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<CalculatorOutlined />}
              size="large"
              block
            >
              计算凯利仓位
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 计算结果 */}
      {result && (
        <Card
          style={{ marginTop: 16 }}
          title={
            <Space>
              <ExperimentOutlined />
              <span>计算结果</span>
            </Space>
          }
        >
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="全凯利仓位"
                value={result.fullKelly}
                precision={2}
                valueStyle={{ color: result.fullKelly > 0.25 ? '#ff4d4f' : '#1890ff' }}
                suffix={
                  <Text type="secondary">
                    ({kellyMode ? '' : `¥${(result.fullKelly * (form.getFieldValue('equity') || 100000)).toFixed(0)}`})
                  </Text>
                }
                prefix={<ThunderboltOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="半凯利仓位"
                value={result.halfKelly}
                precision={2}
                valueStyle={{ color: result.halfKelly > 0.1 ? '#faad14' : '#52c41a' }}
                suffix={
                  <Text type="secondary">
                    ({kellyMode ? '' : `¥${(result.halfKelly * (form.getFieldValue('equity') || 100000)).toFixed(0)}`})
                  </Text>
                }
                prefix={<ThunderboltOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="波动率调整"
                value={result.volAdjusted}
                precision={2}
                valueStyle={{ color: '#52c41a' }}
                suffix={
                  <Text type="secondary">
                    ({kellyMode ? '' : `¥${(result.volAdjusted * (form.getFieldValue('equity') || 100000)).toFixed(0)}`})
                  </Text>
                }
                prefix={<ThunderboltOutlined />}
              />
            </Col>
          </Row>

          <Divider />

          <Result
            status={result.fullKelly <= 0 ? 'warning' : 'success'}
            title="建议"
            subTitle={result.suggestion}
            extra={[
              <Alert
                key="warning"
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                message="风险提示"
                description={
                  <Text type="secondary">
                    凯利公式假设交易相互独立且胜率稳定。实际交易中建议使用半凯利仓位，
                    避免连续亏损导致的权益大幅波动。历史胜率需基于足够样本（30+ 笔）才能可靠。
                  </Text>
                }
              />,
            ]}
          />
        </Card>
      )}

      {/* 参考表格 */}
      <Card style={{ marginTop: 16 }} size="small" title="凯利仓位参考表">
        <Row gutter={8}>
          <Col span={6}><Text type="secondary">胜率</Text></Col>
          <Col span={3}><Text type="secondary">1.5:1</Text></Col>
          <Col span={3}><Text type="secondary">2:1</Text></Col>
          <Col span={3}><Text type="secondary">2.5:1</Text></Col>
          <Col span={3}><Text type="secondary">3:1</Text></Col>
          <Col span={3}><Text type="secondary">半凯利(2:1)</Text></Col>
        </Row>
        <Divider style={{ margin: '8px 0' }} />
        {[
          [0.3, 0.033],
          [0.4, 0.133],
          [0.5, 0.25],
          [0.6, 0.4],
          [0.7, 0.567],
          [0.8, 0.75],
        ].map(([wr, fk], i) => (
          <Row key={i} gutter={8} style={{ marginBottom: 4 }}>
            <Col span={6}><Text>{(wr * 100).toFixed(0)}%</Text></Col>
            <Col span={3}><Text>{(fk * 1.5 * 100).toFixed(0)}%</Text></Col>
            <Col span={3}><Text>{(fk * 2 * 100).toFixed(0)}%</Text></Col>
            <Col span={3}><Text>{(fk * 2.5 * 100).toFixed(0)}%</Text></Col>
            <Col span={3}><Text>{(fk * 3 * 100).toFixed(0)}%</Text></Col>
            <Col span={3}><Text type="secondary">{((fk * 2 / 2) * 100).toFixed(0)}%</Text></Col>
          </Row>
        ))}
      </Card>
    </div>
  );
};

export default KellyPage;