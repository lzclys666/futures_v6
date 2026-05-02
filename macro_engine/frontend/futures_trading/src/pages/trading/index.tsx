import React, { useState } from 'react';
import { Typography, Card, Form, Input, Select, Button, Row, Col, InputNumber, Table, Tag, Space, Divider, Alert, Collapse } from 'antd';
import { CheckCircleOutlined, StopOutlined, WarningOutlined, InfoCircleOutlined, DownOutlined } from '@ant-design/icons';
import { useVnpyStore } from '../../store/vnpyStore';
import { useTradingStore } from '../../store/tradingStore';
import { useRiskStore, type RiskCheckDetail } from '../../store/riskStore';

const { Title, Text } = Typography;
const { Option } = Select;

/**
 * 交易面板页面
 * 提供下单、撤单、订单查询功能
 * 集成风控预检
 *
 * 订单数据走 tradingStore（下单/撤单也在 tradingStore）
 * connected 状态从 vnpyStore 获取
 */
const TradingPanel: React.FC = () => {
  const [form] = Form.useForm();
  const { connected } = useVnpyStore();
  const { orders, placeOrder, cancelOrder } = useTradingStore();
  const { checkOrder } = useRiskStore();
  const [submitting, setSubmitting] = useState(false);
  const [riskResult, setRiskResult] = useState<RiskCheckDetail | null>(null);

  // 品种列表
  const symbols = [
    { code: 'RB2505', name: '螺纹钢' },
    { code: 'HC2505', name: '热卷' },
    { code: 'J2505', name: '焦炭' },
    { code: 'JM2505', name: '焦煤' },
    { code: 'I2505', name: '铁矿石' },
    // 信号系统覆盖 RB/HC/J/JM；AU/AG 待 Phase 3 扩展信号覆盖后再添加
  ];

  // 处理下单
  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    setRiskResult(null);

    // Form 值 'BUY'/'SELL' → store 期望的 'long'/'short'
    const dirMap: Record<string, 'long' | 'short'> = { BUY: 'long', SELL: 'short' };

    try {
      // 风控预检（本地规则）
      const riskCheck = await checkOrder({
        symbol: values.symbol,
        direction: dirMap[values.direction] ?? values.direction,
        volume: values.volume,
        price: values.price,
      });

      if (!riskCheck.pass) {
        setRiskResult(riskCheck);
        setSubmitting(false);
        return;
      }

      // 提交订单（走 tradingStore）
      const result = await placeOrder({
        symbol: values.symbol,
        direction: dirMap[values.direction] ?? values.direction,
        volume: values.volume,
        price: values.price,
        orderType: values.orderType,
      });

      if (result) {
        setRiskResult({ pass: true, failedRules: [], message: `订单提交成功: ${result.vtOrderId}` });
        form.resetFields();
      }
    } catch (e) {
      setRiskResult({ pass: false, failedRules: [], message: String(e) });
    } finally {
      setSubmitting(false);
    }
  };

  // 订单表格列
  const orderColumns = [
    {
      title: '订单号',
      dataIndex: 'orderId',
      key: 'orderId',
    },
    {
      title: '品种',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      render: (dir: string) => (
        <Tag color={dir === 'LONG' ? '#52c41a' : '#ff4d4f'}>
          {dir === 'LONG' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '开平',
      dataIndex: 'offset',
      key: 'offset',
      render: (offset: string) => offset === 'OPEN' ? '开仓' : offset === 'CLOSE' ? '平仓' : offset,
    },
    {
      title: '数量',
      dataIndex: 'volume',
      key: 'volume',
      align: 'right' as const,
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      align: 'right' as const,
      render: (price: number) => price?.toFixed(2),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'orange',
          filled: 'green',
          partial: 'blue',
          cancelled: 'red',
          rejected: 'red',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button
          size="small"
          danger
          disabled={record.status === 'filled' || record.status === 'cancelled'}
          onClick={() => cancelOrder(record.orderId)}
        >
          撤单
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>交易面板</Title>
        <Text type="secondary">下单、撤单与订单管理</Text>
      </div>

      {!connected && (
        <Alert
          message="VNPy 未连接"
          description="请先连接 VNPy 网关后再进行交易操作"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]}>
        {/* 下单表单 */}
        <Col span={8}>
          <Card size="small" title="下单">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{
                direction: 'BUY',
                orderType: 'LIMIT',
                volume: 1,
              }}
            >
              <Form.Item
                name="symbol"
                label="品种"
                rules={[{ required: true, message: '请选择品种' }]}
              >
                <Select placeholder="选择品种">
                  {symbols.map((s) => (
                    <Option key={s.code} value={s.code}>{s.name} ({s.code})</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="direction"
                label="方向"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="BUY">买入</Option>
                  <Option value="SELL">卖出</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="offset"
                label="开平"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="OPEN">开仓</Option>
                  <Option value="CLOSE">平仓</Option>
                  <Option value="CLOSE_TODAY">平今</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="volume"
                label="数量"
                rules={[{ required: true, min: 1 }]}
              >
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>

              <Form.Item
                name="price"
                label="价格"
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: '100%' }} min={0} step={0.5} precision={2} />
              </Form.Item>

              <Form.Item
                name="orderType"
                label="订单类型"
              >
                <Select>
                  <Option value="LIMIT">限价</Option>
                  <Option value="MARKET">市价</Option>
                </Select>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={submitting}
                  disabled={!connected}
                  block
                >
                  提交订单
                </Button>
              </Form.Item>
            </Form>

            {riskResult && (
              <div>
                {riskResult.pass ? (
                  <Alert
                    message="风控预检通过"
                    description={riskResult.message}
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                    style={{ marginTop: 12 }}
                  />
                ) : (
                  <Alert
                    message={
                      <span>
                        <StopOutlined style={{ marginRight: 6 }} />
                        风控拦截 — {riskResult.failedRules.length} 条规则未通过
                      </span>
                    }
                    description={
                      <div>
                        {/* 触发规则明细 */}
                        <Collapse
                          ghost
                          style={{ marginTop: 8 }}
                          items={[{
                            key: 'details',
                            label: <Text style={{ fontSize: 12 }}>查看详情</Text>,
                            children: (
                              <Space direction="vertical" style={{ width: '100%' }} size={4}>
                                {riskResult.failedRules.map(rule => (
                                  <div key={rule.ruleId} style={{ padding: '4px 8px', background: '#fff1f0', borderRadius: 4, borderLeft: '3px solid #ff4d4f' }}>
                                    <Space>
                                      <StopOutlined style={{ color: '#ff4d4f' }} />
                                      <Text strong style={{ fontSize: 13 }}>{rule.name}</Text>
                                    </Space>
                                    <div style={{ marginTop: 2, paddingLeft: 24 }}>
                                      <Text type="secondary" style={{ fontSize: 12 }}>
                                        当前值：<Text strong>{rule.currentValue.toLocaleString()} {rule.unit}</Text>
                                        {' '}&nbsp;阈值：<Text strong>{rule.threshold.toLocaleString()} {rule.unit}</Text>
                                      </Text>
                                      <div style={{ marginTop: 2 }}>
                                        <Text style={{ fontSize: 12, color: '#595959' }}>{rule.message}</Text>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </Space>
                            ),
                          }]}
                        />
                        {/* 通用修复建议 */}
                        <Alert
                          type="warning"
                          icon={<WarningOutlined />}
                          showIcon
                          message="建议"
                          description={
                            <Text style={{ fontSize: 12 }}>
                              降低下单手数、等待次日亏损清零，或前往「风控配置」调整相关规则阈值。
                            </Text>
                          }
                          style={{ marginTop: 8 }}
                        />
                      </div>
                    }
                    type="error"
                    style={{ marginTop: 12 }}
                  />
                )}
              </div>
            )}
          </Card>
        </Col>

        {/* 订单列表 */}
        <Col span={16}>
          <Card size="small" title={`订单列表 (${orders.length})`}>
            <Table
              dataSource={orders}
              columns={orderColumns}
              rowKey="orderId"
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TradingPanel;
