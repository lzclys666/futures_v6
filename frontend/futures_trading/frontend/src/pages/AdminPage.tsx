import React from 'react'
import { Card, Typography, Tabs, Table, Tag, Switch, Button, Alert, Row, Col, Statistic } from 'antd'
import { ControlOutlined, UserOutlined, SettingOutlined, FileTextOutlined, SafetyOutlined } from '@ant-design/icons'
import { useUserStore } from '../store/useUserStore'

const { Title } = Typography

const mockUsers = [
  { id: '1', username: 'admin', role: '管理员', status: 'active', lastLogin: '2026-04-27 09:30:00' },
  { id: '2', username: 'trader1', role: '交易员', status: 'active', lastLogin: '2026-04-27 08:15:00' },
  { id: '3', username: 'viewer1', role: '观察员', status: 'inactive', lastLogin: '2026-04-26 16:00:00' },
]

const mockLogs = [
  { id: '1', time: '2026-04-27 09:30:00', level: 'INFO', module: 'VNpy', message: 'CTP 网关连接成功' },
  { id: '2', time: '2026-04-27 09:28:00', level: 'WARN', module: 'Risk', message: 'R5 波动率接近阈值: 0.048' },
  { id: '3', time: '2026-04-27 09:25:00', level: 'ERROR', module: 'Macro', message: '宏观数据更新失败: 连接超时' },
  { id: '4', time: '2026-04-27 09:20:00', level: 'INFO', module: 'Trading', message: '订单成交: RU2501 多开 2手 @14500' },
]

const AdminPage: React.FC = () => {
  const { profile, savePreferences } = useUserStore()

  const userColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '角色', dataIndex: 'role', key: 'role', render: (v: string) => <Tag color={v === '管理员' ? 'red' : v === '交易员' ? 'blue' : 'default'}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'active' ? 'success' : 'default'}>{v === 'active' ? '启用' : '禁用'}</Tag> },
    { title: '最后登录', dataIndex: 'lastLogin', key: 'lastLogin' },
    { title: '操作', key: 'action', render: () => <Button size="small" type="link">编辑</Button> },
  ]

  const logColumns = [
    { title: '时间', dataIndex: 'time', key: 'time', width: 180 },
    { title: '级别', dataIndex: 'level', key: 'level', width: 80, render: (v: string) => <Tag color={v === 'ERROR' ? 'error' : v === 'WARN' ? 'warning' : 'default'}>{v}</Tag> },
    { title: '模块', dataIndex: 'module', key: 'module', width: 100 },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <ControlOutlined style={{ marginRight: 8 }} />
        系统管理
      </Title>

      <Tabs
        items={[
          {
            key: 'users',
            label: <span><UserOutlined style={{ marginRight: 4 }} />用户管理</span>,
            children: (
              <Card size="small">
                <Table columns={userColumns} dataSource={mockUsers} rowKey="id" pagination={false} size="small" />
              </Card>
            ),
          },
          {
            key: 'settings',
            label: <span><SettingOutlined style={{ marginRight: 4 }} />系统设置</span>,
            children: (
              <Card size="small" title="偏好设置">
                <Row gutter={[16, 16]}>
                  <Col span={24}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <div>
                        <div style={{ fontWeight: 500 }}>深色模式</div>
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>切换系统为深色主题</div>
                      </div>
                      <Switch
                        checked={profile?.preferences?.theme === 'dark'}
                        onChange={(checked) => savePreferences({ theme: checked ? 'dark' : 'light' })}
                      />
                    </div>
                  </Col>
                  <Col span={24}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <div>
                        <div style={{ fontWeight: 500 }}>自动刷新</div>
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>页面数据自动轮询更新</div>
                      </div>
                      <Switch defaultChecked />
                    </div>
                  </Col>
                  <Col span={24}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <div>
                        <div style={{ fontWeight: 500 }}>通知提醒</div>
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>风控触发时推送通知</div>
                      </div>
                      <Switch defaultChecked />
                    </div>
                  </Col>
                  <Col span={24}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
                      <div>
                        <div style={{ fontWeight: 500 }}>模拟交易模式</div>
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>使用 Mock 数据而非真实交易</div>
                      </div>
                      <Switch defaultChecked disabled />
                    </div>
                  </Col>
                </Row>
              </Card>
            ),
          },
          {
            key: 'logs',
            label: <span><FileTextOutlined style={{ marginRight: 4 }} />系统日志</span>,
            children: (
              <Card size="small">
                <Table columns={logColumns} dataSource={mockLogs} rowKey="id" pagination={{ pageSize: 10 }} size="small" scroll={{ x: 800 }} />
              </Card>
            ),
          },
          {
            key: 'security',
            label: <span><SafetyOutlined style={{ marginRight: 4 }} />安全审计</span>,
            children: (
              <Card size="small">
                <Alert message="安全状态" description="系统安全运行中，最近 7 天无异常登录记录。" type="success" showIcon style={{ marginBottom: 16 }} />
                <Row gutter={[16, 16]}>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="登录次数" value={128} suffix="次" /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="异常尝试" value={0} suffix="次" valueStyle={{ color: '#52c41a' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="风控触发" value={3} suffix="次" valueStyle={{ color: '#faad14' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="系统运行" value={15} suffix="天" /></Card>
                  </Col>
                </Row>
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}

export default AdminPage
