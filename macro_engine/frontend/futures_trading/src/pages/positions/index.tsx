import React, { useEffect, useMemo, memo } from 'react';
import { Typography, Card, Table, Tag, Button, Space, Statistic, Row, Col, Empty, message, Modal, Typography as TY } from 'antd';
import { useVnpyStore } from '../../store/vnpyStore';
import { useTradingStore } from '../../store/tradingStore';
import { usePolling } from '../../hooks/usePolling';
import type { Position } from '../../types/trading';

const { Title, Text } = Typography;

/**
 * 持仓看板页面
 * 展示当前持仓、盈亏、可用资金等信息
 * P2-4: 用React.memo避免5s轮询导致的无意义重渲染
 * 注意：connected 状态不再阻断数据展示，Mock模式下始终可用
 */
const PositionsBoard: React.FC = memo(() => {
  const { connected, fetchAccount, account } = useVnpyStore();
  const { positions, placeOrder, fetchPositions: fetchPositionsFromTrading } = useTradingStore();

  // 自动刷新：5s 轮询（同时更新 tradingStore 持仓 + vnpyStore 账户）
  usePolling(() => {
    fetchPositionsFromTrading();
    fetchAccount();
  }, 5000);

  // 初始加载
  useEffect(() => {
    fetchAccount();
    fetchPositionsFromTrading();
  }, []);

  // 平仓 —— 反向下一等价单（LONG->卖，SELL->买）
  const handleClosePosition = async (position: Position) => {
    const oppositeDir = position.direction === 'LONG' ? 'short' : 'long';
    const dirLabel = position.direction === 'LONG' ? '卖出' : '买入';
    Modal.confirm({
      title: '确认平仓',
      content: `${dirLabel} ${position.volume} 手${position.symbol}，当前价 ${position.lastPrice?.toFixed(2)}`,
      okText: '确认平仓',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        const res = await placeOrder({
          symbol: position.symbol,
          direction: oppositeDir,
          price: position.lastPrice,
          volume: position.volume,
        });
        if (res) {
          message.success(`${position.symbol} 平仓委托已提交`);
          await fetchPositions();
          await fetchAccount();
        } else {
          message.error('平仓委托失败');
        }
      },
    });
  };

  // 一键平仓 —— 遍历所有持仓反向开单
  const handleCloseAll = async () => {
    if (positions.length === 0) return;
    const estimatedMarginRelease = positions.reduce((s, p) => s + (p.margin || 0), 0);
    const estimatedPnlChange = positions.reduce((s, p) => s + (p.unrealizedPnl || 0), 0);
    Modal.confirm({
      title: '确认一键平仓',
      icon: <Typography.Text type="danger" style={{ fontSize: 18 }}>!</Typography.Text>,
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Paragraph style={{ marginBottom: 4 }}>
            即将对全部<Typography.Text strong>{positions.length}</Typography.Text> 个持仓进行反向开单。
          </Typography.Paragraph>
          <ul style={{ margin: '4px 0 0 20px', paddingLeft: 0 }}>
            <li>保证金预计释放：<Typography.Text strong>{estimatedMarginRelease.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY', minimumFractionDigits: 0 })}</Typography.Text></li>
            <li>浮动盈亏将转为实际盈亏：<Typography.Text strong type={estimatedPnlChange >= 0 ? 'success' : 'danger'}>{estimatedPnlChange >= 0 ? '+' : ''}{estimatedPnlChange.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY', minimumFractionDigits: 2 })}</Typography.Text></li>
          </ul>
        </Space>
      ),
      okText: '确认平仓',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        let failed = 0;
        for (const pos of positions) {
          const oppositeDir = pos.direction === 'LONG' ? 'short' : 'long';
          const res = await placeOrder({
            symbol: pos.symbol,
            direction: oppositeDir,
            price: pos.lastPrice,
            volume: pos.volume,
          });
          if (!res) failed++;
        }
        if (failed === 0) {
          message.success(`一键平仓委托已全部提交（${positions.length} 笔）`);
        } else {
          message.warning(`一键平仓完成，${failed} 笔失败`);
        }
        await fetchPositions();
        await fetchAccount();
      },
    });
  };

  // 持仓表格列定义 —— 用useMemo缓存避免每次渲染重建
  const columns = useMemo(() => [
    {
      title: '品种',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      render: (dir: string) => (
        <Tag color={dir === 'LONG' ? '#52c41a' : '#ff4d4f'}>
          {dir === 'LONG' ? '多' : '空'}
        </Tag>
      ),
    },
    {
      title: '持仓量',
      dataIndex: 'volume',
      key: 'volume',
      align: 'right' as const,
    },
    {
      title: '持仓均价',
      dataIndex: 'avgPrice',
      key: 'avgPrice',
      align: 'right' as const,
      render: (price: number) => price?.toFixed(2) || '-',
    },
    {
      title: '当前价',
      dataIndex: 'lastPrice',
      key: 'lastPrice',
      align: 'right' as const,
      render: (price: number) => price?.toFixed(2) || '-',
    },
    {
      title: '浮动盈亏',
      dataIndex: 'unrealizedPnl',
      key: 'unrealizedPnl',
      align: 'right' as const,
      render: (pnl: number) => (
        <Text style={{ color: pnl >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {pnl >= 0 ? '+' : ''}{pnl?.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '保证金',
      dataIndex: 'margin',
      key: 'margin',
      align: 'right' as const,
      render: (m: number) => m?.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY', minimumFractionDigits: 0 }) || '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Position) => (
        <Space>
          <Button size="small" type="primary" danger onClick={() => handleClosePosition(record)}>
            平仓
          </Button>
        </Space>
      ),
    },
  ], []);

  // 计算总盈亏
  const totalPnl = positions.reduce((sum, p) => sum + (p.unrealizedPnl ?? 0) + (p.realizedPnl ?? 0), 0);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>持仓看板</Title>
        <Text type="secondary">实时持仓与账户状态</Text>
      </div>

      {/* 账户概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="总资金"
              value={account?.balance ?? 0}
              precision={2}
              prefix="¥"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="可用资金"
              value={account?.available ?? 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="冻结资金"
              value={account?.frozen ?? 0}
              precision={2}
              prefix="¥"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="总浮动盈亏"
              value={totalPnl}
              precision={2}
              prefix="¥"
              valueStyle={{ color: totalPnl >= 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 持仓表格 */}
      <Card
        size="small"
        title={`持仓列表 (${positions.length})`}
        extra={
          <Space>
            {connected === false && (
              <Tag color="warning" style={{ fontSize: 11 }}>CTP 未连接，展示模拟数据</Tag>
            )}
            <Button
              type="primary"
              danger
              size="small"
              onClick={handleCloseAll}
              disabled={positions.length === 0}
            >
              一键平仓
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={positions}
          columns={columns}
          rowKey="vtSymbol"
          pagination={false}
          size="small"
          virtual
          scroll={{ x: 'max-content', y: 300 }}
        />
      </Card>
    </div>
  );
});

export default PositionsBoard;
