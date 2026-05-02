import React from 'react';
import { Card, Typography, Button, Space } from 'antd';
import { ExclamationCircleOutlined, ReloadOutlined, CloseCircleOutlined } from '@ant-design/icons';

interface Props {
  children: React.ReactNode;
  /** 是否显示"清除错误"按钮（默认 true） */
  showDismiss?: boolean;
  /** 错误恢复时的回调 */
  onRecover?: (error: Error) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * 全局错误边界 — Phase 4
 * P4-3: 增强 — 添加 dismiss 恢复 + onRecover 回调 + 更好的样式
 *
 * 功能：
 * - 捕获 React 渲染错误，防止白屏崩溃
 * - 显示错误名称 + 消息 + 组件堆栈摘要
 * - 支持"清除错误"按钮（局部恢复，不刷新页面）
 * - 支持 onRecover 回调
 */
class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] 捕获到错误:', error);
    console.error('[ErrorBoundary] 组件栈:', errorInfo.componentStack);
    this.setState({ errorInfo });
  }

  handleDismiss = () => {
    const { onRecover, error } = this.props;
    if (onRecover && error) {
      onRecover(error);
    }
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const { error, errorInfo } = this.state;
    const { showDismiss = true } = this.props;

    // 提取堆栈关键行（前 3 行）
    const stackLines = errorInfo?.componentStack?.split('\n').slice(0, 3).join('\n') ?? '';

    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '60vh',
        padding: '24px',
      }}>
        <Card
          style={{ width: 520, textAlign: 'center', maxWidth: '95vw' }}
          styles={{ body: { padding: '32px 24px' } }}
        >
          <ExclamationCircleOutlined
            style={{ fontSize: 52, color: '#ff4d4f', marginBottom: 20 }}
          />
          <Typography.Title level={4} style={{ color: '#ff4d4f', marginBottom: 12 }}>
            组件渲染出错
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 20 }}>
            系统遇到了意外错误，已自动记录错误日志。
            <br />
            请尝试以下操作：
          </Typography.Paragraph>

          {error && (
            <Card
              size="small"
              style={{
                background: 'rgba(255,77,79,0.06)',
                border: '1px solid rgba(255,77,79,0.2)',
                marginBottom: 20,
                textAlign: 'left',
              }}
              styles={{ body: { padding: '12px' } }}
            >
              <Typography.Text
                strong
                style={{ fontSize: 13, color: '#ff4d4f', display: 'block', marginBottom: 4 }}
              >
                {error.name}
              </Typography.Text>
              <Typography.Text
                style={{
                  fontSize: 12,
                  fontFamily: 'Consolas, monospace',
                  color: '#8c8c8c',
                  wordBreak: 'break-all',
                }}
              >
                {error.message}
              </Typography.Text>
              {stackLines && (
                <Typography.Text
                  type="secondary"
                  style={{
                    display: 'block',
                    fontSize: 11,
                    marginTop: 8,
                    fontFamily: 'Consolas, monospace',
                    whiteSpace: 'pre-wrap',
                    color: '#595959',
                  }}
                >
                  {stackLines}
                </Typography.Text>
              )}
            </Card>
          )}

          <Space size={12} wrap justify="center">
            {showDismiss && (
              <Button
                icon={<CloseCircleOutlined />}
                onClick={this.handleDismiss}
              >
                清除错误
              </Button>
            )}
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={this.handleReload}
            >
              刷新页面
            </Button>
          </Space>
        </Card>
      </div>
    );
  }
}

export default ErrorBoundary;
