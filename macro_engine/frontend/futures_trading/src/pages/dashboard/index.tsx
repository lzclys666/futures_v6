import React, { useEffect } from 'react';
import { Typography, Divider, Row, Col, Alert, Space } from 'antd';
import { ClockCircleOutlined, DashboardOutlined, CloudServerOutlined, AreaChartOutlined } from '@ant-design/icons';
import RiskDashboard from '../../components/RiskDashboard';
import AccountSnapshot from '../../components/AccountSnapshot';
import SignalBriefTable from '../../components/SignalBrief';
import IcHeatmapCard from '../../components/IcHeatmapCard';
import SignalSystemCard from '../../components/SignalSystemCard';
import { useVnpyStore } from '../../store/vnpyStore';
import { useMacroStore } from '../../store/macroStore';

const { Title, Text } = Typography;

/**
 * 首页 Dashboard
 * 布局：风控仪表盘（顶部导航）| 账户快照 | 信号概要 | IC热量图 | 信号系统
 */
/** 当前是否为交易时段（简单判断：工作日09:00-15:00和21:00-23:00）*/
function isTradingSession(): boolean {
  const now = new Date();
  const h = now.getHours();
  const dow = now.getDay(); // 0=周日, 6=周六
  if (dow === 0 || dow === 6) return false;
  return (h >= 9 && h < 15) || (h >= 21 && h < 23);
}

const Dashboard: React.FC = () => {
  const { gateway } = useVnpyStore();
  const { fetchIcHeatmap, fetchBatchSignals } = useMacroStore();
  const connected = gateway?.gatewayStatus === 'connected';
  const inSession = isTradingSession();
  const isMockMode = !connected;

  useEffect(() => {
    // 加载因子分析数据
    fetchIcHeatmap();
    fetchBatchSignals();
    
    // 定期刷新
    const id = setInterval(() => {
      fetchIcHeatmap();
      fetchBatchSignals();
    }, 30000);
    
    return () => clearInterval(id);
  }, [fetchIcHeatmap, fetchBatchSignals]);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Dashboard</Title>
        <Text type="secondary">交易系统运行状态总览</Text>
      </div>

      {/* 非交易时段 / Mock 模式状态提示 */}
      {(isMockMode || !inSession) && (
        <Alert
          type={isMockMode ? 'info' : 'warning'}
          icon={<ClockCircleOutlined />}
          message={
            isMockMode
              ? '开发者模式：正在使用 Mock 数据'
              : '当前为非交易时段，数据仅供参股'
          }
          description={
            isMockMode
              ? '真实数据将在交易时段（周一至周五 09:00-15:00 / 21:00-23:00）显示。切换生产模式：设置 VITE_USE_MOCK=false'
              : '账户数据和持仓信号将在交易时段（周一至周五 09:00-15:00 / 21:00-23:00）实时更新'
          }
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Section 分区标题 - 监控区 */}
      <Divider orientation="left" style={{ margin: '8px 0 16px 0' }}>
        <Space size={8}>
          <DashboardOutlined style={{ color: '#1890ff' }} />
          <span style={{ fontSize: 14, fontWeight: 500, color: '#262626' }}>监控区</span>
        </Space>
      </Divider>

      <RiskDashboard />

      <Divider style={{ margin: '16px 0' }} />

      <AccountSnapshot />

      <Divider style={{ margin: '24px 0 16px 0' }} />

      {/* Section 分区标题 - 信号区 */}
      <Divider orientation="left" style={{ margin: '8px 0 16px 0' }}>
        <Space size={8}>
          <CloudServerOutlined style={{ color: '#52c41a' }} />
          <span style={{ fontSize: 14, fontWeight: 500, color: '#262626' }}>信号区</span>
        </Space>
      </Divider>

      <SignalBriefTable />

      <Divider style={{ margin: '16px 0' }} />

      {/* Section 分区标题 - 分析区 */}
      <Divider orientation="left" style={{ margin: '8px 0 16px 0' }}>
        <Space size={8}>
          <AreaChartOutlined style={{ color: '#722ed1' }} />
          <span style={{ fontSize: 14, fontWeight: 500, color: '#262626' }}>分析区</span>
        </Space>
      </Divider>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <IcHeatmapCard />
        </Col>
        <Col span={12}>
          <SignalSystemCard />
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
