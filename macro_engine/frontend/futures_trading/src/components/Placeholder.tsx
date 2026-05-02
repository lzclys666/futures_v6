import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';

interface Props {
  pageName: string;       // 页面中文名
  description?: string;   // 补充说明
}

/**
 * 占位页面组件 — 用于尚未实现的 Phase 2-4 页面
 * 显示页面名称 + "即将上线"提示 + 返回首页按钮
 */
const Placeholder: React.FC<Props> = ({ pageName, description }) => {
  const navigate = useNavigate();
  return (
    <Result
      status="info"
      title={pageName}
      subTitle={description ?? `${pageName}页面正在开发中，预计后续版本上线`}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          返回首页
        </Button>
      }
    />
  );
};

export default Placeholder;
