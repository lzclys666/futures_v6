import { test, expect } from '@playwright/test';

/**
 * E2E 测试 — 导航与全页面健康
 *
 * 验证：
 * 1. 所有 10+ 页路由可达
 * 2. 侧边栏菜单全部可点击
 * 3. 无 404 或崩溃
 */
test.describe('Navigation（导航与全页面健康检查）', () => {
  const routes = [
    { path: '/', name: '首页' },
    { path: '/macro', name: '宏观看板' },
    { path: '/positions', name: '持仓看板' },
    { path: '/trading', name: '交易面板' },
    { path: '/risk', name: '风控面板' },
    { path: '/risk/config', name: '风控规则配置' },
    { path: '/stress-test', name: '压力测试' },
    { path: '/kelly', name: '凯利计算器' },
    { path: '/factor-dashboard', name: '因子仪表盘' },
    { path: '/rule-simulator', name: 'Rule Simulator' },
    { path: '/profile', name: '个人中心' },
    { path: '/admin', name: '系统管理' },
  ];

  test('所有页面路由可达且无崩溃', async ({ page }) => {
    for (const route of routes) {
      await page.goto(route.path);
      await page.waitForLoadState('networkidle');
      // 无 Error Boundary 崩溃
      await expect(page.locator('text=组件渲染出错')).not.toBeVisible({ timeout: 3000 });
      // 无空白页（#root 下有内容）
      const rootContent = await page.locator('#root > *').count();
      expect(rootContent).toBeGreaterThan(0);
    }
  });

  test('侧边栏菜单点击导航正常', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 逐个点击菜单
    const menuItems = page.locator('.ant-menu-item');
    const count = await menuItems.count();

    for (let i = 0; i < Math.min(count, 8); i++) {
      const item = menuItems.nth(i);
      if (await item.isVisible()) {
        await item.click();
        await page.waitForLoadState('networkidle');
        // 不应该崩溃
        await expect(page.locator('text=组件渲染出错')).not.toBeVisible({ timeout: 2000 });
      }
    }
  });

  test('持仓看板页面正常显示', async ({ page }) => {
    await page.goto('/positions');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=持仓')).toBeVisible();
  });

  test('压力测试页面正常显示', async ({ page }) => {
    await page.goto('/stress-test');
    await page.waitForLoadState('networkidle');
    const heading = page.locator('h4', { hasText: '压力测试' });
    await expect(heading.first()).toBeVisible();
  });

  test('Rule Simulator 页面正常显示', async ({ page }) => {
    await page.goto('/rule-simulator');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Rule Simulator')).toBeVisible();
  });

  test('个人中心页面正常显示', async ({ page }) => {
    await page.goto('/profile');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=个人中心')).toBeVisible();
  });
});
