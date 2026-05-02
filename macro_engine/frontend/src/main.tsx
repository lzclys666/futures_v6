import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import { MacroDashboard, PositionBoard, TradingPanel } from './components/macro'
import { ConfigProvider, Tabs, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'

type TabKey = 'macro' | 'positions' | 'trading'

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('macro')

  return (
    <ConfigProvider locale={zhCN} theme={{ algorithm: theme.darkAlgorithm }}>
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as TabKey)}
        items={[
          {
            key: 'macro',
            label: '宏观打分',
            children: <MacroDashboard />,
          },
          {
            key: 'positions',
            label: '持仓看板',
            children: <PositionBoard />,
          },
          {
            key: 'trading',
            label: '交易面板',
            children: <TradingPanel />,
          },
        ]}
        style={{ padding: '0 16px' }}
      />
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
