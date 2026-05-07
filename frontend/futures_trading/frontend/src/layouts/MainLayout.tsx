/**
 * 全局布局：侧边栏 + 顶栏 + 内容区
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Switch, Avatar, Dropdown, Typography, Badge } from 'antd'
import type { MenuProps } from 'antd'
import {
  DashboardOutlined,
  FundOutlined,
  TableOutlined,
  SwapOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  CalculatorOutlined,
  UserOutlined,
  ControlOutlined,
  LogoutOutlined,
  SunOutlined,
  MoonOutlined,
  BarChartOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  HeatMapOutlined,
} from '@ant-design/icons'
import { useVnpyStore } from '../store/useVnpyStore'
import { useRiskStore } from '../store/useRiskStore'
import { useUserStore } from '../store/useUserStore'
import './MainLayout.css'

const { Header, Sider, Content } = Layout
const { Text } = Typography

interface NavItem {
  key: string
  icon: React.ReactNode
  label: string
  badge?: number
}

const navItems: NavItem[] = [
  { key: '/', icon: <DashboardOutlined />, label: '首页' },
  { key: '/macro', icon: <FundOutlined />, label: '宏观看板' },
  { key: '/positions', icon: <TableOutlined />, label: '持仓看板' },
  { key: '/trading', icon: <SwapOutlined />, label: '交易面板' },
  { key: '/risk', icon: <SafetyCertificateOutlined />, label: '风控面板' },
  { key: '/risk/config', icon: <SettingOutlined />, label: '风控配置' },
  { key: '/stress-test', icon: <ThunderboltOutlined />, label: '压力测试' },
  { key: '/kelly', icon: <CalculatorOutlined />, label: '凯利计算器' },
  { key: '/kelly-calculator', icon: <CalculatorOutlined />, label: '凯利计算器(本地)' },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心' },
  { key: '/admin', icon: <ControlOutlined />, label: '系统管理' },
  { key: '/factor-dashboard', icon: <BarChartOutlined />, label: '因子仪表盘' },
  { key: '/rule-simulator', icon: <ExperimentOutlined />, label: '规则模拟器' },
  { key: '/report', icon: <FileTextOutlined />, label: '月度报告' },
  { key: '/ic-heatmap', icon: <HeatMapOutlined />, label: 'IC 热力图' },
]

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // 主题
  const { profile, toggleTheme } = useUserStore()
  const isDark = profile?.preferences?.theme === 'dark'

  // VNpy 状态
  const vnpyStatus = useVnpyStore((s) => s.status)
  const isConnected = vnpyStatus?.state === 'connected'

  // 风控状态
  const riskStatus = useRiskStore((s) => s.status)
  const triggeredCount = riskStatus?.triggeredCount ?? 0
  const overallSeverity = riskStatus?.overallStatus ?? 'PASS'

  // 当前路由对应的菜单 key
  const selectedKey = '/' + location.pathname.split('/').filter(Boolean).join('/') || '/'

  // 用户下拉菜单
  const userMenuItems: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: '个人中心', onClick: () => navigate('/profile') },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={200}
        style={{
          background: isDark ? '#141414' : '#fff',
          borderRight: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
        }}
      >
        {/* Logo 区域 */}
        <div className="sider-logo">
          {!collapsed ? (
            <Text strong style={{ fontSize: 16, color: '#1890ff' }}>
              🎯 期货智能交易
            </Text>
          ) : (
            <Text strong style={{ fontSize: 18, color: '#1890ff' }}>🎯</Text>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={navItems.map((item) => ({
            key: item.key,
            icon: item.icon,
            label: (
              <span>
                {item.label}
                {item.key === '/risk' && triggeredCount > 0 && (
                  <Badge
                    count={triggeredCount}
                    size="small"
                    style={{ marginLeft: 8 }}
                    color={overallSeverity === 'BLOCK' ? '#ff4d4f' : '#faad14'}
                  />
                )}
              </span>
            ),
          }))}
          onClick={({ key }) => navigate(key)}
          style={{ borderInlineEnd: 'none' }}
        />
      </Sider>

      <Layout>
        {/* 顶栏 */}
        <Header
          className="layout-header"
          style={{
            background: isDark ? '#141414' : '#fff',
            borderBottom: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
          }}
        >
          <div className="header-left">
            {/* VNpy 连接状态灯 */}
            <Badge
              status={isConnected ? 'success' : 'error'}
              text={
                <Text type="secondary" style={{ fontSize: 13 }}>
                  {isConnected ? 'VNpy 已连接' : 'VNpy 未连接'}
                </Text>
              }
            />
          </div>

          <div className="header-right">
            {/* 深色模式开关 */}
            <Switch
              checkedChildren={<MoonOutlined />}
              unCheckedChildren={<SunOutlined />}
              checked={isDark}
              onChange={toggleTheme}
              style={{ marginRight: 16 }}
            />

            {/* 用户 */}
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <Text>{profile?.displayName || '用户'}</Text>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* 内容区 */}
        <Content className="layout-content" style={{ background: isDark ? '#000' : '#f0f2f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
