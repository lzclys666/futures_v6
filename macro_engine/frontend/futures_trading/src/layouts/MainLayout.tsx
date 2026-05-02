import React from 'react';
import { Layout, Menu, Typography, Space, Tag, Switch, Tooltip } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined, FundViewOutlined, TableOutlined, SwapOutlined,
  SafetyCertificateOutlined, SettingOutlined, ThunderboltOutlined,
  CalculatorOutlined, UserOutlined, ControlOutlined,
  ExperimentOutlined, FilePdfOutlined, AuditOutlined,
  LineChartOutlined, MoonOutlined, SunOutlined,
} from '@ant-design/icons';
import { useWebSocketLifecycle } from '../hooks/useWebSocket';
import { useTheme } from '../contexts/AppThemeProvider';
import ConnectionStatusBadge from '../components/ConnectionStatusBadge';
import MockModeBadge from '../components/MockModeBadge';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

/** 侧边栏菜单配置（/risk/config 作为 /risk 子菜单） */
const MENU_ITEMS = [
  { key: '/', icon: <DashboardOutlined />, label: '首页' },
  { key: '/macro', icon: <FundViewOutlined />, label: '宏观看板' },
  { key: '/positions', icon: <TableOutlined />, label: '持仓看板' },
  { key: '/trading', icon: <SwapOutlined />, label: '交易面板' },
  {
    key: '/risk',
    icon: <SafetyCertificateOutlined />,
    label: '风控面板',
    children: [
      { key: '/risk', label: '风控面板', icon: <SafetyCertificateOutlined /> },
      { key: '/risk/config', label: '风控规则配置', icon: <SettingOutlined /> },
    ],
  },
  { key: '/stress-test', icon: <ThunderboltOutlined />, label: '压力测试' },
  { key: '/kelly', icon: <CalculatorOutlined />, label: '凯利计算器' },
  { key: '/factor-dashboard', icon: <LineChartOutlined />, label: '因子仪表盘' },
  { key: '/rule-simulator', icon: <ExperimentOutlined />, label: 'Rule Simulator' },
  { key: '/report', icon: <FilePdfOutlined />, label: '月度报告' },
  { key: '/audit-log', icon: <AuditOutlined />, label: '审计日志' },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心' },
  { key: '/admin', icon: <ControlOutlined />, label: '系统管理' },
];

/**
 * 全局布局组件
 * - 左侧可折叠侧边栏（14 项菜单，含风控子菜单）
 * - 顶栏：系统名称 + 连接状态 + 深色模式开关
 * - 内容区：Routed 页面
 * - WebSocket 生命周期在此级管理
 */
const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode, setDarkMode } = useTheme();

  // 应用级 WebSocket 生命周期
  useWebSocketLifecycle();

  const selectedKey = React.useMemo(() => {
    const exact = MENU_ITEMS.find(m => m.key === location.pathname);
    if (exact) return exact.key;
    if (location.pathname.startsWith('/risk/')) return '/risk';
    return '/';
  }, [location.pathname]);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={200}
        collapsible
        breakpoint="lg"
      >
        <div style={{ height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid var(--border)' }}>
          <Text strong style={{ fontSize: 15 }}>期货智能交易 V6</Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={MENU_ITEMS}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
          <Space>
            <Text type="secondary" style={{ fontSize: 13 }}>
              {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
            </Text>
          </Space>
          <Space size={16}>
            <ConnectionStatusBadge />
            <MockModeBadge />
            <Tooltip title={darkMode ? '切换浅色模式' : '切换深色模式'}>
              <Switch
                checked={darkMode}
                onChange={setDarkMode}
                checkedChildren={<MoonOutlined />}
                unCheckedChildren={<SunOutlined />}
                size="small"
              />
            </Tooltip>
            <Tag color="blue">前端 5173</Tag>
          </Space>
        </Header>
        <Content style={{ margin: 16, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
