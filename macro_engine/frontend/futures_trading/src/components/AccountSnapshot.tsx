import React from 'react';
import { Card, Statistic, Row, Col, Spin, Tag } from 'antd';
import { WalletOutlined } from '@ant-design/icons';
import { useVnpyStore } from '../store/vnpyStore';

/**
 * 账户快照组件 — 展示 6 项账户关键指标
 * 总资产 | 可用资金 | 保证金 | 当日盈亏 | 累计盈亏 | 资金使用率
 */
const AccountSnapshotBase: React.FC = () => {
  const { account, gateway, loading, fetchAccount, fetchGatewayStatus } = useVnpyStore();

  React.useEffect(() => {
    fetchGatewayStatus();
    fetchAccount();
    const id = setInterval(() => { fetchGatewayStatus(); fetchAccount(); }, 5000);
    return () => clearInterval(id);
  }, [fetchGatewayStatus, fetchAccount]);

  if (loading && !account) {
    return (
      <Card size="small">
        <Spin tip="加载账户…"><div style={{ height: 60 }} /></Spin>
      </Card>
    );
  }

  const connected = gateway?.gatewayStatus === 'connected';
  const session = gateway?.marketSession;

  const acc = account ?? {
    balance: 1_000_000,
    available: 850_000,
    frozen: 0,
    margin: 150_000,
    positionPnl: 12_500,
    closePnl: 45_000,
    riskRatio: 0.15,
  };

  return (
    <Card
      size="small"
      title={
        <span>
          <WalletOutlined style={{ marginRight: 6 }} />账户快照
          {!connected && <Tag color="red" style={{ marginLeft: 8 }}>VNpy 未连接</Tag>}
          {connected && session && <Tag color="blue" style={{ marginLeft: 8 }}>{session === 'open' ? '交易中' : '休市'}</Tag>}
        </span>
      }
    >
      <Row gutter={[12, 12]}>
        <Col span={8}>
          <Statistic title="总资产" value={acc.balance} precision={0} prefix="¥" />
        </Col>
        <Col span={8}>
          <Statistic title="可用资金" value={acc.available} precision={0} prefix="¥" valueStyle={{ color: '#52c41a' }} />
        </Col>
        <Col span={8}>
          <Statistic title="保证金" value={acc.margin} precision={0} prefix="¥" />
        </Col>
        <Col span={8}>
          <Statistic
            title="当日持仓盈亏"
            value={acc.positionPnl}
            precision={0}
            prefix="¥"
            valueStyle={{ color: acc.positionPnl >= 0 ? '#52c41a' : '#ff4d4f' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="累计平仓盈亏"
            value={acc.closePnl}
            precision={0}
            prefix="¥"
            valueStyle={{ color: acc.closePnl >= 0 ? '#52c41a' : '#ff4d4f' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="资金使用率"
            value={acc.riskRatio * 100}
            precision={1}
            suffix="%"
            valueStyle={{ color: acc.riskRatio > 0.5 ? '#ff4d4f' : acc.riskRatio > 0.3 ? '#faad14' : '#52c41a' }}
          />
        </Col>
      </Row>
      {!account && (
        <p style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center', marginTop: 8, marginBottom: 0 }}>
          非交易时段 — Mock 数据
        </p>
      )}
    </Card>
  );
};

const AccountSnapshot = React.memo(AccountSnapshotBase);
export default AccountSnapshot;
