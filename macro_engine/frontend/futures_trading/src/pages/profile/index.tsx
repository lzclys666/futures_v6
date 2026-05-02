import React, { useState } from 'react';
import {
  Card, Row, Col, Statistic, Typography, Space, Tag,
  Radio, Divider, message, Spin, Upload, Avatar, Switch, Modal, Table,
} from 'antd';
import {
  UserOutlined, RiseOutlined, FallOutlined, TrophyOutlined,
  SafetyCertificateOutlined, BellOutlined, CameraOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import { useUserStore } from '../../store/userStore';
import type { RiskProfile } from '../../types';

const { Text, Title } = Typography;

interface EquityPoint {
  date: string;
  equity: number;
  return: number;
}

interface NotificationPrefs {
  riskBlock: boolean;
  dispositionEffect: boolean;
  dailyReport: boolean;
}

function generateMockEquity(): EquityPoint[] {
  const points: EquityPoint[] = [];
  let equity = 500000;
  for (let i = 90; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const ret = (Math.random() - 0.48) * 0.015;
    equity *= (1 + ret);
    points.push({
      date: d.toISOString().slice(0, 10),
      equity: Math.round(equity),
      return: parseFloat((ret * 100).toFixed(2)),
    });
  }
  return points;
}

const RISK_PROFILES: { value: RiskProfile; label: string; desc: string; color: string; impact: string[] }[] = [
  { value: 'conservative', label: '保守型', desc: '最大回撤 < 5%，年化目标 8-12%', color: '#52c41a', impact: ['单品种仓位 ≤ 15%', '总保证金 ≤ 30%', '单日亏损限额 ¥20,000', '波动率阈值 2%', '连续亏损上限 2 笔'] },
  { value: 'moderate', label: '稳健型', desc: '最大回撤 < 10%，年化目标 12-20%', color: '#1890ff', impact: ['单品种仓位 ≤ 30%', '总保证金 ≤ 50%', '单日亏损限额 ¥50,000', '波动率阈值 3%', '连续亏损上限 3 笔'] },
  { value: 'aggressive', label: '激进型', desc: '最大回撤 < 20%，年化目标 20%+', color: '#ff4d4f', impact: ['单品种仓位 ≤ 45%', '总保证金 ≤ 70%', '单日亏损限额 ¥100,000', '波动率阈值 5%', '连续亏损上限 5 笔'] },
];

const AVATAR_KEY = 'futures_user_avatar';
const PREFS_KEY = 'futures_notification_prefs';

const DEFAULT_PREFS: NotificationPrefs = {
  riskBlock: true,
  dispositionEffect: true,
  dailyReport: false,
};

/**
 * 个人中心 — Phase 4 完整版
 * 风险画像 + 绩效曲线 + 通知偏好 + 头像上传
 * P1-1 修复：通知偏好 Switch 可交互 + localStorage 持久化
 */
const PersonalCenter: React.FC = () => {
  const { profile, setProfile } = useUserStore();
  const [equityData] = useState(() => generateMockEquity());
  const [saving, setSaving] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string>(() => localStorage.getItem(AVATAR_KEY) ?? '');
  const [uploading, setUploading] = useState(false);

  // P1-1: 通知偏好状态，从 localStorage 初始化
  const [prefs, setPrefs] = useState<NotificationPrefs>(() => {
    try {
      const stored = localStorage.getItem(PREFS_KEY);
      return stored ? { ...DEFAULT_PREFS, ...JSON.parse(stored) } : DEFAULT_PREFS;
    } catch {
      return DEFAULT_PREFS;
    }
  });

  const handleProfileChange = (newProfile: RiskProfile) => {
    const current = profile?.riskProfile ?? 'moderate';
    const currentLabel = RISK_PROFILES.find(p => p.value === current)?.label ?? '';
    const newLabel = RISK_PROFILES.find(p => p.value === newProfile)?.label ?? '';
    const newProfileData = RISK_PROFILES.find(p => p.value === newProfile);

    // P2-3: 风险画像切换前弹出影响预览
    Modal.confirm({
      title: '确认切换风险画像',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <Typography.Paragraph>
            即将从 <Typography.Text strong>{currentLabel}</Typography.Text> 切换为 <Typography.Text strong>{newLabel}</Typography.Text>
          </Typography.Paragraph>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
            切换后将自动调整以下风控规则：
          </Typography.Paragraph>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {newProfileData?.impact.map((item, i) => (
              <li key={i} style={{ fontSize: 13 }}><Typography.Text type="secondary">{item}</Typography.Text></li>
            ))}
          </ul>
        </div>
      ),
      okText: '确认切换',
      cancelText: '取消',
      onOk: () => {
        setSaving(true);
        setTimeout(() => {
          setProfile({ riskProfile: newProfile });
          setSaving(false);
          message.success(`风险画像已切换为「${newLabel}」`);
        }, 500);
      },
    });
  };

  /** 头像上传：读取文件 → 转 data URL → localStorage */
  const handleAvatarChange = (file: File) => {
    if (!file.type.startsWith('image/')) {
      message.error('请上传图片文件');
      return false;
    }
    if (file.size > 2 * 1024 * 1024) {
      message.error('图片大小不能超过 2MB');
      return false;
    }
    setUploading(true);
    const reader = new FileReader();
    reader.onload = (e) => {
      const url = e.target?.result as string;
      localStorage.setItem(AVATAR_KEY, url);
      setAvatarUrl(url);
      setUploading(false);
      message.success('头像已更新');
    };
    reader.onerror = () => {
      setUploading(false);
      message.error('上传失败');
    };
    reader.readAsDataURL(file);
    return false;
  };

  // P1-1: 通知偏好切换，持久化到 localStorage
  const handlePrefChange = (key: keyof NotificationPrefs, checked: boolean) => {
    const next = { ...prefs, [key]: checked };
    setPrefs(next);
    localStorage.setItem(PREFS_KEY, JSON.stringify(next));
    message.success(`通知「${key === 'riskBlock' ? '风控阻断通知' : key === 'dispositionEffect' ? '处置效应提醒' : '日度报告'}」已${checked ? '开启' : '关闭'}`);
  };

  const totalReturn = ((equityData[equityData.length - 1].equity - equityData[0].equity) / equityData[0].equity * 100);
  const maxDrawdown = Math.min(...equityData.map((d, i) => {
    const peak = Math.max(...equityData.slice(0, i + 1).map(e => e.equity));
    return (d.equity - peak) / peak * 100;
  }));

  const equityChartOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: equityData.map(d => d.date.slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10, formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` } },
    series: [{
      type: 'line',
      data: equityData.map(d => d.equity),
      smooth: true,
      lineStyle: { color: '#1890ff', width: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(24,144,255,0.3)' },
            { offset: 1, color: 'rgba(24,144,255,0.05)' },
          ],
        },
      },
      itemStyle: { color: '#1890ff' },
    }],
  };

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4}><UserOutlined /> 个人中心</Title>
      <Text type="secondary">风险画像 · 绩效追踪 · 偏好设置</Text>

      <Divider />

      <Row gutter={16}>
        {/* 左侧：头像 + 画像 + 绩效 */}
        <Col xs={24} lg={12}>
          {/* 头像 + 基本信息 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space size={16}>
              <Upload showUploadList={false} beforeUpload={handleAvatarChange} accept="image/*">
                <div style={{ cursor: 'pointer', position: 'relative' }} title="点击更换头像">
                  <Avatar size={80} src={avatarUrl} icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                  {uploading && (
                    <div style={{
                      position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.4)',
                      borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Spin size="small" />
                    </div>
                  )}
                  <div style={{
                    position: 'absolute', bottom: 0, right: 0, background: '#1890ff', borderRadius: '50%',
                    width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: '2px solid white',
                  }}>
                    <CameraOutlined style={{ color: 'white', fontSize: 12 }} />
                  </div>
                </div>
              </Upload>
              <div>
                <Title level={5} style={{ margin: 0 }}>交易员</Title>
                <Text type="secondary">trader_001</Text>
                <div style={{ marginTop: 4 }}>
                  <Tag icon={<SafetyCertificateOutlined />} color="blue">已实名认证</Tag>
                </div>
              </div>
            </Space>
          </Card>

          {/* 风险画像 */}
          <Card size="small" title={<><SafetyCertificateOutlined /> 风险画像</>} style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">当前画像：</Text>
              <Radio.Group
                value={profile?.riskProfile ?? 'moderate'}
                onChange={e => handleProfileChange(e.target.value)}
                buttonStyle="solid"
                style={{ width: '100%' }}
              >
                {RISK_PROFILES.map(p => (
                  <Radio.Button key={p.value} value={p.value} style={{ width: '33.33%' }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ color: p.color, fontWeight: 'bold' }}>{p.label}</div>
                      <div style={{ fontSize: 11, color: '#8c8c8c' }}>{p.desc}</div>
                    </div>
                  </Radio.Button>
                ))}
              </Radio.Group>
              {saving && <Spin size="small" tip="保存中…" />}
            </Space>
          </Card>

          {/* 绩效摘要 */}
          <Card size="small" title={<><TrophyOutlined /> 绩效摘要（近90日）</>}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="总收益率"
                  value={`${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`}
                  valueStyle={{ color: totalReturn >= 0 ? '#52c41a' : '#ff4d4f' }}
                  prefix={totalReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic title="最大回撤" value={`${maxDrawdown.toFixed(2)}%`} valueStyle={{ color: '#ff4d4f' }} />
              </Col>
              <Col span={12}>
                <Statistic title="当前权益" value={`¥${equityData[equityData.length - 1].equity.toLocaleString()}`} />
              </Col>
              <Col span={12}>
                <Statistic title="初始权益" value={`¥${equityData[0].equity.toLocaleString()}`} />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 右侧：资金曲线 */}
        <Col xs={24} lg={12}>
          <Card size="small" title="资金曲线" style={{ height: '100%' }}>
            <ReactECharts option={equityChartOption} style={{ height: 380 }} />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* P1-1 修复：通知偏好 Switch 可交互 + localStorage 持久化 */}
      <Card size="small" title={<><BellOutlined /> 通知偏好</>}>
        <Row gutter={[32, 16]}>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: '#f6ffed' }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text strong>风控阻断通知</Text>
                  <Switch
                    size="small"
                    checked={prefs.riskBlock}
                    onChange={checked => handlePrefChange('riskBlock', checked)}
                  />
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>任何规则触发 HIGH 时推送</Text>
                <Text style={{ fontSize: 12, color: prefs.riskBlock ? '#52c41a' : '#8c8c8c' }}>
                  {prefs.riskBlock ? '✓ 已开启' : '— 已关闭'}
                </Text>
              </Space>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: '#fff7e6' }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text strong>处置效应提醒</Text>
                  <Switch
                    size="small"
                    checked={prefs.dispositionEffect}
                    onChange={checked => handlePrefChange('dispositionEffect', checked)}
                  />
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>R11 触发时弹窗提醒</Text>
                <Text style={{ fontSize: 12, color: prefs.dispositionEffect ? '#faad14' : '#8c8c8c' }}>
                  {prefs.dispositionEffect ? '✓ 已开启' : '— 已关闭'}
                </Text>
              </Space>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: '#e6f7ff' }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text strong>日度报告</Text>
                  <Switch
                    size="small"
                    checked={prefs.dailyReport}
                    onChange={checked => handlePrefChange('dailyReport', checked)}
                  />
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>每日 18:00 发送绩效摘要</Text>
                <Text style={{ fontSize: 12, color: prefs.dailyReport ? '#1890ff' : '#8c8c8c' }}>
                  {prefs.dailyReport ? '✓ 已开启' : '— 已关闭'}
                </Text>
              </Space>
            </Card>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default PersonalCenter;
