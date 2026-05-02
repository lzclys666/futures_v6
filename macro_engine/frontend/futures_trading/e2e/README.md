# E2E 测试说明

## 快速开始

```bash
# 1. 安装浏览器（仅首次）
npx playwright install chromium

# 2. 安装依赖
npm ci

# 3. 运行所有测试
npm run test:e2e

# 4. 查看 HTML 报告
npm run test:e2e:report
```

## 测试文件

| 文件 | 覆盖页面 |
|------|---------|
| `dashboard.spec.ts` | 首页 Dashboard |
| `macro-board.spec.ts` | 宏观看板 |
| `trading-panel.spec.ts` | 交易面板 |
| `risk-panel.spec.ts` | 风控面板 |
| `navigation.spec.ts` | 全页面路由健康检查 |

## 运行选项

```bash
npm run test:e2e          # CI 模式（headless）
npm run test:e2e:headed   # 浏览器可见
npm run test:e2e:ui       # Playwright UI 模式
```

## 前置条件

- Node.js 18+
- 前端运行在 `http://localhost:5173`（`npm run dev`）
- `VITE_USE_MOCK=true`（默认，无需改）

## Mock 数据说明

所有 E2E 测试在 `VITE_USE_MOCK=true` 模式下运行，不依赖真实后端。
Mock 数据定义在 `src/api/client.ts` 的 `ALL_MOCKS` 映射表中。
