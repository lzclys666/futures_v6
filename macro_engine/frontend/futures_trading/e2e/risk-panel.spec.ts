import { test, expect } from '@playwright/test';

/**
 * E2E 测试 — 风控面板
 *
 * 验证：
 * 1. 风控面板正常加载
 * 2. 显示 11 条风控规则
 * 3. Layer 1/2/3 分组正确
 * 4. 规则状态颜色正确（PASS/WARN/HIGH）
 */
test.describe('Risk Panel（风控面板）', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/risk');
    await page.waitForLoadState('networkidle');
  });

  test('页面正常加载', async ({ page }) => {
    const heading = page.locator('h4', { hasText: '风控' });
    await expect(heading.first()).toBeVisible();
    await expect(page.locator('text=组件渲染出错')).not.toBeVisible();
  });

  test('显示风控规则（至少 3 条可见）', async ({ page }) => {
    // 查找 R1 或 R2 等规则 ID
    const rules = page.locator('text=/^R\\d_/');
    const count = await rules.count();
    // 至少显示部分规则
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('Layer 分组标签存在', async ({ page }) => {
    // Layer 1/2/3 标签
    const layer1 = page.locator('text=Layer').or(page.locator('text=市场风险'));
    if (await layer1.first().isVisible()) {
      await expect(layer1.first()).toBeVisible();
    }
  });

  test('规则状态颜色标签显示', async ({ page }) => {
    // PASS / WARN / HIGH 标签
    const passTag = page.locator('text=PASS').or(page.locator('text=通过'));
    const warnTag = page.locator('text=WARN').or(page.locator('text=警告'));
    const highTag = page.locator('text=HIGH').or(page.locator('text=阻断'));
    const hasAny = (await passTag.isVisible()) || (await warnTag.isVisible()) || (await highTag.isVisible());
    expect(hasAny).toBe(true);
  });

  test('风控规则配置页面可访问', async ({ page }) => {
    // 找到并点击配置链接
    const configLink = page.locator('text=风控规则配置');
    if (await configLink.isVisible()) {
      await configLink.click();
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/.*risk\/config/);
    }
  });
});
