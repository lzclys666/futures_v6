# Phantom Function Fix Report — Lucy

## 问题

前端编译警告：
```
[IMPORT_IS_UNDEFINED] `fetchEquityCurve` will always be undefined
because there is no matching export in 'src/api/user.ts'
```

`src/store/userStore.ts:37` 调用 `userApi.fetchEquityCurve(days)`，但 `src/api/user.ts` 并未导出此函数。
实际导出的是 `fetchEquityHistory`，功能相同只是命名不一致。

## 分析结论

- **不是死代码**：`fetchEquityCurve` 是 Zustand store 中 `fetchEquityCurve` action 的实现，被该 action 调用
- **原因**：`userStore` 和 `userApi` 之间命名不匹配——store 用 `fetchEquityCurve`，API 用 `fetchEquityHistory`

## 修复方案

在 `src/api/user.ts` 中添加 alias 导出，指向已有的 `fetchEquityHistory`：

```ts
/** fetchEquityCurve — alias for fetchEquityHistory (used by userStore) */
export const fetchEquityCurve = fetchEquityHistory;
```

## 修改文件

- `src/api/user.ts` — 新增 1 行（alias export）

## 验证

```bash
npm run build
```

结果：`✓ built in 6.87s` — 编译通过，phantom function 警告消失。

（chunk size 警告与此次修复无关，为既有警告。）
