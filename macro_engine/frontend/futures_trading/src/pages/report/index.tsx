import React, { useState } from 'react';
import {
  Card, Button, DatePicker, Radio, Select, Typography,
  Space, Row, Col, Statistic, Divider, Table, message, Spin, Empty,
} from 'antd';
import {
  FilePdfOutlined, FileExcelOutlined, DownloadOutlined,
  CalendarOutlined, CheckCircleOutlined, RiseOutlined, FallOutlined,
} from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;

interface MonthlySummary {
  totalTrades: number;
  winRate: number;
  totalPnl: number;
  sharpeRatio: number;
  maxDrawdown: number;
  avgWinLossRatio: number;
  bestTrade: number;
  worstTrade: number;
  totalFees: number;
}

interface DailyPnl {
  date: string;
  pnl: number;
  trades: number;
  cumulativePnl: number;
}

function generateMockSummary(): MonthlySummary {
  return { totalTrades: 47, winRate: 0.532, totalPnl: 28450, sharpeRatio: 1.87, maxDrawdown: -12400, avgWinLossRatio: 1.42, bestTrade: 5200, worstTrade: -3800, totalFees: 2350 };
}

function generateMockDailyPnl(): DailyPnl[] {
  const dates: DailyPnl[] = [];
  let cumulative = 0;
  for (let i = 29; i >= 0; i--) {
    const d = dayjs().subtract(i, 'day');
    const pnl = Math.round((Math.random() - 0.45) * 8000);
    cumulative += pnl;
    dates.push({ date: d.format('YYYY-MM-DD'), pnl, trades: Math.floor(Math.random() * 4) + 1, cumulativePnl: cumulative });
  }
  return dates;
}

const ReportExport: React.FC = () => {
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([dayjs().subtract(30, 'day'), dayjs()]);
  const [format, setFormat] = useState<'csv' | 'pdf'>('csv');
  const [generating, setGenerating] = useState(false);
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [dailyData, setDailyData] = useState<DailyPnl[]>([]);

  const handleGenerate = async () => {
    setGenerating(true);
    await new Promise(r => setTimeout(r, 1200));
    setSummary(generateMockSummary());
    setDailyData(generateMockDailyPnl());
    setGenerating(false);
    message.success('报告已生成');
  };

  const handleExport = () => {
    if (!summary) return;
    if (format === 'csv') {
      const headers = 'date,pnl,trades,cumulativePnl';
      const rows = dailyData.map(d => `${d.date},${d.pnl},${d.trades},${d.cumulativePnl}`).join('\n');
      const content = `${headers}\n${rows}\n\nSummary:\ntotalTrades,${summary.totalTrades}\nwinRate,${summary.winRate}\ntotalPnl,${summary.totalPnl}\nsharpeRatio,${summary.sharpeRatio}`;
      const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trading_report_${dayjs().format('YYYYMMDD')}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('CSV 已下载');
    } else {
      window.print();
      message.info('请使用浏览器「另存为 PDF」功能导出');
    }
  };

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4}><FilePdfOutlined /> 月度报告导出</Title>
      <Text type="secondary">生成交易绩效报告并导出 CSV / PDF</Text>
      <Divider />
      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card size="small" title="报告配置">
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>时间范围</Text>
                <RangePicker value={dateRange} onChange={v => v && setDateRange(v)} style={{ width: '100%' }} />
              </div>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>导出格式</Text>
                <Radio.Group value={format} onChange={e => setFormat(e.target.value)}>
                  <Radio.Button value="csv"><FileExcelOutlined /> CSV</Radio.Button>
                  <Radio.Button value="pdf"><FilePdfOutlined /> PDF</Radio.Button>
                </Radio.Group>
              </div>
              <Button type="primary" block icon={<CalendarOutlined />} onClick={handleGenerate} loading={generating}>生成报告</Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          {summary ? (
            <>
              <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={32}>
                  <Col><Statistic title="总交易笔数" value={summary.totalTrades} /></Col>
                  <Col><Statistic title="胜率" value={`${(summary.winRate * 100).toFixed(1)}%`} valueStyle={{ color: summary.winRate >= 0.5 ? '#52c41a' : '#ff4d4f' }} /></Col>
                  <Col><Statistic title="总盈亏" value={`¥${summary.totalPnl.toLocaleString()}`} valueStyle={{ color: summary.totalPnl >= 0 ? '#52c41a' : '#ff4d4f' }} prefix={summary.totalPnl >= 0 ? <RiseOutlined /> : <FallOutlined />} /></Col>
                  <Col><Statistic title="夏普比率" value={summary.sharpeRatio} valueStyle={{ color: summary.sharpeRatio >= 1 ? '#52c41a' : '#faad14' }} /></Col>
                  <Col><Statistic title="最大回撤" value={`¥${summary.maxDrawdown.toLocaleString()}`} valueStyle={{ color: '#ff4d4f' }} /></Col>
                </Row>
              </Card>
              <Card size="small" title="日度盈亏明细" extra={<Button type="primary" size="small" icon={<DownloadOutlined />} onClick={handleExport}>导出 {format.toUpperCase()}</Button>}>
                <Table
                  dataSource={dailyData}
                  columns={[
                    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
                    { title: '盈亏', dataIndex: 'pnl', key: 'pnl', render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v >= 0 ? '+' : ''}¥{v.toLocaleString()}</Text> },
                    { title: '交易笔数', dataIndex: 'trades', key: 'trades', width: 90 },
                    { title: '累计盈亏', dataIndex: 'cumulativePnl', key: 'cumulativePnl', render: (v: number) => <Text strong style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>¥{v.toLocaleString()}</Text> },
                  ]}
                  rowKey="date"
                  size="small"
                  pagination={{ pageSize: 10, size: 'small' }}
                />
              </Card>
            </>
          ) : (
            <Card><Empty description="点击「生成报告」查看交易绩效" /></Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default ReportExport;
