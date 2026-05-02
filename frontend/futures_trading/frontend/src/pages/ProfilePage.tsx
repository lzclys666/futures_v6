/**
 * 个人中心页面
 * @author Lucy
 * @date 2026-04-27
 */

import React, { useEffect } from 'react'
import { Card, Descriptions, Tag, Statistic, Row, Col, Typography } from 'antd'
import { UserOutlined, TrophyOutlined, PercentageOutlined, RiseOutlined } from '@ant-design/icons'
import { useUserStore } from '../store/useUserStore'

const { Title } = Typography

const ProfilePage: React.FC = () => {
  const { profile, loadProfile } = useUserStore()

  useEffect(() => {
    loadProfile()
  }, [])

  if (!profile) {
    return <Card loading />
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <UserOutlined style={{ marginRight: 8 }} />
        个人中心
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={16}>
          <Card title="基本信息" size="small">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="用户名">{profile.username}</Descriptions.Item>
              <Descriptions.Item label="显示名">{profile.displayName}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{profile.email}</Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag color={profile.role === 'admin' ? 'red' : profile.role === 'trader' ? 'blue' : 'default'}>
                  {profile.role === 'admin' ? '管理员' : profile.role === 'trader' ? '交易员' : '观察者'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{profile.createdAt}</Descriptions.Item>
              <Descriptions.Item label="最近登录">{profile.lastLoginAt}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="风控画像" size="small" style={{ marginTop: 16 }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="风险偏好">
                {profile.riskProfile.riskTolerance === 'conservative' ? '保守' : profile.riskProfile.riskTolerance === 'moderate' ? '稳健' : '激进'}
              </Descriptions.Item>
              <Descriptions.Item label="最大回撤容忍">{profile.riskProfile.maxDrawdown}%</Descriptions.Item>
              <Descriptions.Item label="日内最大亏损">{profile.riskProfile.maxDailyLoss} 元</Descriptions.Item>
              <Descriptions.Item label="单品种仓位上限">{profile.riskProfile.maxSingleSymbolPct}%</Descriptions.Item>
              <Descriptions.Item label="总仓位上限">{profile.riskProfile.maxTotalPositionPct}%</Descriptions.Item>
              <Descriptions.Item label="杠杆上限">{profile.riskProfile.maxLeverage}x</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Card title="交易绩效" size="small">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic title="累计收益" value={profile.cumulativeReturn} precision={2} suffix="%" valueStyle={{ color: profile.cumulativeReturn >= 0 ? '#52c41a' : '#ff4d4f' }} prefix={<RiseOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="胜率" value={profile.winRate} precision={1} suffix="%" prefix={<PercentageOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="夏普比率" value={profile.sharpeRatio ?? '--'} precision={2} />
              </Col>
              <Col span={12}>
                <Statistic title="最大回撤" value={profile.maxHistoricalDrawdown ?? '--'} precision={2} suffix="%" valueStyle={{ color: '#ff4d4f' }} />
              </Col>
              <Col span={24}>
                <Statistic title="累计交易天数" value={profile.totalTradingDays} suffix="天" prefix={<TrophyOutlined />} />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ProfilePage
