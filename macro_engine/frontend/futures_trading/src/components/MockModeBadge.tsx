import React from 'react';
import { Tag, Tooltip, Typography } from 'antd';
import { BugOutlined } from '@ant-design/icons';
import { IS_MOCK_MODE } from '../api/client';

const { Text } = Typography;

/**
 * Mock 模式指示器 — Phase 5
 * 展示当前数据源模式（Mock / Real API）
 * 位于顶栏右侧 VNpy 连接状态旁
 */
const MockModeBadge: React.FC = () => {
  if (!IS_MOCK_MODE) {
    return null; // 生产模式不显示
  }

  return (
    <Tooltip
      title={
        <div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Mock 数据模式</div>
          <div style={{ fontSize: 11, lineHeight: 1.6 }}>
            当前使用模拟数据，非真实交易环境<br />
            切换方式：<br />
            1. 创建 <code>.env.local</code> 文件<br />
            2. 添加 <code>VITE_USE_MOCK=false</code><br />
            3. 重启开发服务器 <code>npm run dev</code>
          </div>
        </div>
      }
      placement="bottomRight"
    >
      <Tag
        icon={<BugOutlined />}
        color="warning"
        style={{ cursor: 'default', fontSize: 12 }}
      >
        Mock
      </Tag>
    </Tooltip>
  );
};

export default MockModeBadge;
