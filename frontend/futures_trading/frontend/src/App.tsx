import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import MainLayout from './layouts/MainLayout'
import DashboardPage from './pages/DashboardPage'
import MacroPage from './pages/MacroPage'
import PositionPage from './pages/PositionPage'
import TradingPage from './pages/TradingPage'
import RiskPage from './pages/RiskPage'
import RiskConfigPage from './pages/RiskConfigPage'
import StressTestPage from './pages/StressTestPage'
import KellyPage from './pages/KellyPage'
import ProfilePage from './pages/ProfilePage'
import AdminPage from './pages/AdminPage'
import FactorDashboardPage from './pages/FactorDashboardPage'
import RuleSimulatorPage from './pages/RuleSimulatorPage'
import ReportPage from './pages/ReportPage'
import { useUserStore } from './store/useUserStore'

const App: React.FC = () => {
  const isDark = useUserStore((s) =>
    s.darkAlgorithm
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : s.profile?.preferences?.theme === 'dark'
  )

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          colorSuccess: '#52c41a',
          colorWarning: '#faad14',
          colorError: '#ff4d4f',
          borderRadius: 4,
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="macro" element={<MacroPage />} />
            <Route path="positions" element={<PositionPage />} />
            <Route path="trading" element={<TradingPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="risk/config" element={<RiskConfigPage />} />
            <Route path="stress-test" element={<StressTestPage />} />
            <Route path="kelly" element={<KellyPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="factor-dashboard" element={<FactorDashboardPage />} />
            <Route path="rule-simulator" element={<RuleSimulatorPage />} />
            <Route path="report" element={<ReportPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
