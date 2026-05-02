import React, { useEffect } from 'react';
import { Card, Table, Tag, Typography, Divider, Tooltip, Space } from 'antd';
import { CaretUpOutlined, CaretDownOutlined, MinusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useMacroStore } from '../store/macroStore';

const { Text } = Typography;

/**
 * 信号摘要 — 4 品种信号一览表格
 * 数据来自 fetchAllSignals（端口 8000）
 * 非交易时段使用 store mock fallback
 */
const SignalBriefTableBase: React.FC = () => {
  const { signals, fetchAllSignals } = useMacroStore();

  useEffect(() => {
    fetchAllSignals();
    const id = setInterval(fetchAllSignals, 30000);
    return () => clearInterval(id);
  }, [fetchAllSignals]);

  const columns = [
    { title: '品种', dataIndex: 'symbolName', key: 'symbolName', width: 80 },
    {
      title: (
        <Space size={4}>
          综合得分
          <Tooltip title="基于26个宏观因子加权计算，60分以上偏多，40分以下偏空">
            <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
          </Tooltip>
        </Space>
      ), dataIndex: 'compositeScore', key: 'compositeScore', width: 100,
      render: (v: number) => (
        <Text style={{ color: v > 60 ? '#52c41a' : v < 40 ? '#ff4d4f' : '#faad14', fontWeight: 600 }}>
          {typeof v === 'number' ? v.toFixed(1) : '--'}
        </Text>
      ),
    },
    {
      title: '方向', dataIndex: 'signal', key: 'signal', width: 70,
      render: (s: string) => {
        if (s === 'BUY') return <Tag icon={<CaretUpOutlined />} color="green">多</Tag>;
        if (s === 'SELL') return <Tag icon={<CaretDownOutlined />} color="red">空</Tag>;
        return <Tag icon={<MinusOutlined />} color="default">中性</Tag>;
      },
    },
    {
      title: '强度', dataIndex: 'strength', key: 'strength', width: 70,
      render: (s: string) => {
        if (s === 'STRONG') return <Tag color="green">强</Tag>;
        if (s === 'WEAK') return <Tag color="red">弱</Tag>;
        return <Tag color="default">中</Tag>;
      },
    },
    { title: '日期', dataIndex: 'date', key: 'date', width: 90 },
  ];

  return (
    <Card
      size="small"
      title="信号摘要"
      extra={<Text type="secondary" style={{ fontSize: 12 }}>非交易时段 — Mock 数据</Text>}
    >
      {/* 信号强度速查指南 */}
      <div style={{ marginBottom: 8, padding: '4px 8px', backgroundColor: '#fafafa', borderRadius: 4 }}>
        <Text style={{ fontSize: 11 }}>
          <Text strong>综合得分：</Text>
          <Text style={{ color: '#52c41a' }}> 60+ 偏多</Text> |
          <Text style={{ color: '#faad14' }}> 40-60 中性</Text> |
          <Text style={{ color: '#ff4d4f' }}> &lt;40 偏空</Text>
          <Divider type="vertical" />
          <Text strong>强度：</Text>
          <Tag color="green" style={{ marginLeft: 4, fontSize: 10 }}>强</Tag>
          <Tag color="default" style={{ fontSize: 10 }}>中</Tag>
          <Tag color="red" style={{ fontSize: 10 }}>弱</Tag>
        </Text>
      </div>
      <Table
        dataSource={signals}
        columns={columns}
        rowKey="symbol"
        pagination={false}
        size="small"
        scroll={{ x: 'max-content' }}
      />
    </Card>
  );
};

const SignalBriefTable = React.memo(SignalBriefTableBase);
export default SignalBriefTable;
