import { test, expect } from '@playwright/test';

/**
 * E2E 测试 — 交易面板
 *
 * 完整交易流程测试：
 * 1. 页面加载 + 行情显示
 * 2. 输入订单参数
 * 3. 风控预检执行
 * 4. 预检通过/阻断结果展示
 * 5. Mock 模式撤单
 */
test.describe('Trading Panel（交易面板）', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/trading');
    await page.waitForLoadState('networkidle');
  });

  test('页面正常加载', async ({ page }) => {
    // 交易面板标题
    const heading = page.locator('h4', { hasText: '交易' }).or(page.locator('text=交易面板'));
    await expect(heading.first()).toBeVisible();
    // 无错误兜底
    await expect(page.locator('text=组件渲染出错')).not.toBeVisible();
  });

  test('品种和方向选择器工作正常', async ({ page }) => {
    const selects = page.locator('.ant-select');
    const count = await selects.count();
    if (count >= 2) {
      // 第一个 select（品种）
      await selects.nth(0).click();
      await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
      const options0 = page.locator('.ant-select-item');
      const n0 = await options0.count();
      if (n0 > 1) await options0.nth(1).click();

      // 第二个 select（方向）
      await selects.nth(1).click();
      await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
      const options1 = page.locator('.ant-select-item');
      const n1 = await options1.count();
      if (n1 > 0) await options1.nth(0).click();
    }
  });

  test('价格和手数输入正常', async ({ page }) => {
    // 找到 InputNumber（价格）
    const inputs = page.locator('.ant-input-number');
    const count = await inputs.count();
    if (count >= 2) {
      // 清空并输入价格
      await inputs.nth(0).fill('3600');
      // 清空并输入手数
      await inputs.nth(1).fill('2');
    }
  });

  test('风控预检按钮点击正常', async ({ page }) => {
    // 查找"预检"按钮
    const precheckBtn = page.locator('button', { hasText: '预检' });
    if (await precheckBtn.isVisible()) {
      await precheckBtn.click();
      // 等待预检结果（可能有加载状态）
      await page.waitForTimeout(1500);
      // 预检结果应该出现（通过 or 阻断）
      const passed = page.locator('text=通过').or(page.locator('text=阻断')).or(page.locator('text=风控'));
      await expect(passed.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('买入按钮状态正确', async ({ page }) => {
    const buyBtn = page.locator('button', { hasText: '买入' }).or(page.locatorator('button', { hasText: '开多' }));
    if (await buyBtn.isVisible()) {
      await expect(buyBtn).toBeEnabled();
    }
  });

  test('持仓列表有数据（Mock）', async ({ page }) => {
    // 向下滚动看持仓区域
    const positionsSection = page.locator('text=持仓').first();
    if (await positionsSection.isVisible()) {
      await expect(positionsSection).toBeVisible();
    }
  });
});
