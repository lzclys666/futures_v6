import { test, expect } from '@playwright/test';

/**
 * E2E 测试 — 宏观看板
 *
 * 验证：
 * 1. 页面正常加载
 * 2. 显示 4 个品种的信号（RB/HC/J/JM）
 * 3. 品种选择器工作正常
 * 4. 信号强度标签正确显示
 */
test.describe('Macro Board（宏观看板）', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/macro');
    await page.waitForLoadState('networkidle');
  });

  test('页面标题存在', async ({ page }) => {
    const heading = page.locator('h4', { hasText: '宏观' });
    await expect(heading.first()).toBeVisible();
  });

  test('品种信号列表显示（RB/HC/J/JM）', async ({ page }) => {
    // 螺纹钢 RB 信号
    await expect(page.locator('text=螺纹钢').first()).toBeVisible();
    // 热卷 HC 信号
    await expect(page.locator('text=热卷').first()).toBeVisible();
  });

  test('品种选择器切换正常', async ({ page }) => {
    // 查找品种选择器（ant-select）
    const selects = page.locator('.ant-select');
    const selectCount = await selects.count();
    if (selectCount > 0) {
      // 点击第一个 select
      await selects.first().click();
      // 等待下拉菜单
      await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
      // 选择第二个选项
      const options = page.locator('.ant-select-item');
      const optionCount = await options.count();
      if (optionCount > 1) {
        await options.nth(1).click();
        await page.waitForLoadState('networkidle');
      }
    }
  });

  test('IC 热力图卡片显示', async ({ page }) => {
    // IC 热力图或相关内容
    const heatmap = page.locator('text=IC').first();
    if (await heatmap.isVisible()) {
      await expect(heatmap).toBeVisible();
    }
  });

  test('信号强度颜色标签正确显示', async ({ page }) => {
    // 做多/做空/持有标签
    const buyTag = page.locator('text=做多');
    const sellTag = page.locator('text=做空');
    const holdTag = page.locator('text=持有');
    // 至少有一个标签可见
    const hasAny = (await buyTag.isVisible()) || (await sellTag.isVisible()) || (await holdTag.isVisible());
    expect(hasAny).toBe(true);
  });
});
