import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 配置 — 期货智能交易系统 V6
 *
 * 运行方式：
 *   npx playwright test                 # 运行全部测试
 *   npx playwright test dashboard        # 运行指定文件
 *   npx playwright test --ui            # 图形界面
 *   npx playwright test --headed        # 浏览器可见
 *
 * 首次使用需要安装浏览器：
 *   npx playwright install chromium
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
