import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Spin } from 'antd';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/dashboard';
import MacroPage from './pages/macro';
import PositionBoard from './pages/positions';
import ErrorBoundary from './components/ErrorBoundary';
import { AppThemeProvider } from './contexts/AppThemeProvider';

/** 代码分割 — 重型页面懒加载（Phase 5 优化） */
const TradingPanel = lazy(() => import('./pages/trading'));
const RiskPanel = lazy(() => import('./pages/risk'));
const RiskConfigPage = lazy(() => import('./pages/risk/config'));
const StressTestReport = lazy(() => import('./pages/stress-test'));
const KellyPage = lazy(() => import('./pages/kelly'));
const FactorDashboard = lazy(() => import('./pages/factor-dashboard'));
const RuleSimulator = lazy(() => import('./pages/rule-simulator'));
const ReportExport = lazy(() => import('./pages/report'));
const AuditLog = lazy(() => import('./pages/audit-log'));
const AdminPage = lazy(() => import('./pages/admin'));
const PersonalCenter = lazy(() => import('./pages/profile'));

/** 懒加载 fallback */
const PageLoader: React.FC = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 240 }}>
    <Spin size="large" tip="加载中…" />
  </div>
);

/**
 * 应用入口 — 路由配置
 * 10 页路由表对齐 UI 设计文档 v2.0
 * Phase 3/4/5：全部页面上线，支持懒加载 + 错误边界
 * 深色模式通过 AppThemeProvider + theme.darkAlgorithm 实现
 */
const App: React.FC = () => (
  <ErrorBoundary>
    <AppThemeProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="macro" element={<MacroPage />} />
              <Route path="positions" element={<PositionBoard />} />
              <Route path="trading" element={<TradingPanel />} />
              <Route path="risk" element={<RiskPanel />} />
              <Route path="risk/config" element={<RiskConfigPage />} />
              <Route path="stress-test" element={<StressTestReport />} />
              <Route path="kelly" element={<KellyPage />} />
              <Route path="factor-dashboard" element={<FactorDashboard />} />
              <Route path="rule-simulator" element={<RuleSimulator />} />
              <Route path="report" element={<ReportExport />} />
              <Route path="audit-log" element={<AuditLog />} />
              <Route path="profile" element={<PersonalCenter />} />
              <Route path="admin" element={<AdminPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AppThemeProvider>
  </ErrorBoundary>
);

export default App;
