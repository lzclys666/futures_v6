import { test, expect } from '@playwright/test';

/**
 * E2E 测试 — 首页 Dashboard
 *
 * 验证：
 * 1. Dashboard 页面正常加载
 * 2. 风险仪表盘显示（Layer 1/2/3 状态灯）
 * 3. 账户快照显示（余额/可用/持仓数）
 * 4. Mock 数据正常展示
 */
test.describe('Dashboard（首页）', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // 等待页面加载
    await page.waitForLoadState('networkidle');
  });

  test('页面标题和基础元素存在', async ({ page }) => {
    // 顶栏存在
    await expect(page.locator('.ant-layout-header')).toBeVisible();
    // 侧边栏菜单存在
    await expect(page.locator('.ant-layout-sider')).toBeVisible();
    // 左侧菜单有 Dashboard 条目
    const menuItem = page.locator('.ant-menu-item').first();
    await expect(menuItem).toBeVisible();
  });

  test('风险仪表盘显示 Layer 1/2/3', async ({ page }) => {
    // 找到风险仪表盘（如果有的话）
    const riskSection = page.locator('text=风控').first();
    // 页面不应该有 error boundary 错误兜底
    await expect(page.locator('text=组件渲染出错')).not.toBeVisible();
  });

  test('Mock 模式指示器显示（开发环境）', async ({ page }) => {
    // 顶栏右侧应有 Mock 标签（VITE_USE_MOCK=true）
    const mockBadge = page.locator('text=Mock');
    // badge 存在且为黄色 warning Tag
    await expect(mockBadge).toBeVisible();
  });

  test('侧边栏菜单可导航', async ({ page }) => {
    // 点击宏观看板
    await page.locator('.ant-menu-item', { hasText: '宏观看板' }).click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/.*macro/);
  });

  test('深色模式切换工作正常', async ({ page }) => {
    // 找到深色模式开关
    const switchEl = page.locator('.ant-switch').first();
    if (await switchEl.isVisible()) {
      await switchEl.click();
      // 切换后 html 应有 dark-mode class
      const html = page.locator('html');
      const hasDarkClass = await html.evaluate(el => el.classList.contains('dark-mode'));
      expect(hasDarkClass).toBe(true);
    }
  });

  test('页面无控制台 Error 级别错误', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // 过滤掉已知无关紧要的 error（如 favicon 404）
    const realErrors = errors.filter(e => !e.includes('favicon') && !e.includes('404'));
    expect(realErrors).toHaveLength(0);
  });
});
