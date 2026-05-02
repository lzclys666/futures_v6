import React from 'react'
import { Alert, Button, Result, Spin } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

/**
 * 全局错误边界
 * 捕获组件树中的 JavaScript 错误，防止整个应用崩溃
 */
export class GlobalErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面发生错误"
          subTitle={this.state.error?.message || '未知错误'}
          extra={[
            <Button
              key="reload"
              type="primary"
              icon={<ReloadOutlined />}
              onClick={this.handleReload}
            >
              刷新页面
            </Button>,
          ]}
        >
          {this.state.errorInfo && (
            <div style={{ textAlign: 'left', background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {this.state.errorInfo.componentStack}
              </pre>
            </div>
          )}
        </Result>
      )
    }

    return this.props.children
  }
}

/**
 * 组件级错误边界（用于局部错误处理）
 */
export class ComponentErrorBoundary extends React.Component<
  Props & { fallback?: React.ReactNode },
  State
> {
  constructor(props: Props & { fallback?: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ComponentErrorBoundary caught:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return <>{this.props.fallback}</>
      }

      return (
        <Alert
          message="组件加载失败"
          description={this.state.error?.message || '未知错误'}
          type="error"
          showIcon
          action={
            <Button size="small" type="primary" onClick={this.handleRetry}>
              重试
            </Button>
          }
        />
      )
    }

    return this.props.children
  }
}

/**
 * API 错误展示组件
 */
export const ApiErrorAlert: React.FC<{ error: string; onRetry?: () => void }> = ({
  error,
  onRetry,
}) => (
  <Alert
    message="数据加载失败"
    description={error}
    type="error"
    showIcon
    action={
      onRetry ? (
        <Button size="small" type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
          重试
        </Button>
      ) : null
    }
    style={{ margin: '16px 0' }}
  />
)

/**
 * 加载状态组件
 */
export const LoadingSpinner: React.FC<{ tip?: string }> = ({ tip = '加载中...' }) => (
  <div style={{ textAlign: 'center', padding: '40px 0' }}>
    <Spin size="large" tip={tip} />
  </div>
)
