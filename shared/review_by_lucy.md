## Lucy 审查报告

### 1. fetchRiskStatus() 调用修复
✅ **通过**

`trading.ts` 中 `fetchRiskStatus()` 已正确修改：
- 使用 `riskHttp = createClient('/api/risk')` 新建独立 client
- 调用 `riskHttp.get('/status')`，实际路径 `/api/risk/status`
- 不再使用旧的 `http.get('/risk-status')`（路径 `/api/trading/risk-status`）

---

### 2. 类型定义正确性
✅ **通过**

`types/risk.ts` 中类型定义正确：
- `RiskSeverity = 'PASS' | 'WARN' | 'BLOCK'` ✅
- `RiskLayerKey = 1 | 2 | 3` ✅
- `RiskStatusResponse` 接口完整，包含 `rules: RiskRuleStatus[]` 和 `circuitBreaker` 字段

---

### 3. 前端API结构
⚠️ **发现问题 — 存在两套并行的风控 API 实现**

| 文件 | 类型 | 使用的类型 |
|------|------|------------|
| `api/trading.ts` → `fetchRiskStatus()` | 调用 `/api/risk/status` | `RiskStatusData`（来自 `types/macro.ts`，旧格式） |
| `api/risk.ts` → `fetchRiskStatusResponse()` | 调用 `/api/risk/status` | `RiskStatusResponse`（来自 `types/risk.ts`，新格式） |

**问题**：`fetchRiskStatus()` 和 `fetchRiskStatusResponse()` 调用同一后端端点，但返回类型不同。

**建议**：统一使用 `api/risk.ts` 中的实现，`trading.ts` 中的 `fetchRiskStatus()` 应改为直接 import 并调用 `fetchRiskStatusResponse()`。

---

### 4. validateRiskStatusData 兼容性
❌ **需修复**

**核心问题**：`tradingValidators.ts` 中 `validateRiskStatusData()` 校验的是旧格式：

```typescript
// tradingValidators.ts 第 62 行
if (!['正常', '告警', '触发'].includes(r.overallStatus as string)) {
  errors.push('overallStatus 必须是 正常|告警|触发')
}
```

但 `/api/risk/status` 后端返回的是新格式：

```typescript
// types/risk.ts — RiskStatusResponse
overallStatus: RiskSeverity  // 'PASS' | 'WARN' | 'BLOCK'
rules: RiskRuleStatus[]
circuitBreaker: boolean
```

**后果**：`fetchRiskStatus()` 在调用真实 API 时，`validateRiskStatusData()` 会因为 `overallStatus` 不匹配而返回 `valid: false`，导致抛出异常 `"overallStatus 必须是 正常|告警|触发"`。

**建议**：
- `trading.ts` 中的 `fetchRiskStatus()` 应改用 `api/risk.ts` 的 `fetchRiskStatusResponse()`（自带正确校验）
- 或者新增 `validateRiskStatusResponse()` 校验函数匹配新格式
- 旧的 `validateRiskStatusData`（校验 `levels[]` 结构）应标记为 deprecated

---

### 5. 残留路径检查
✅ **通过**

- 没有文件再调用 `/api/trading/risk-status`（旧路径）
- `createClient('/api/trading')` 返回的 `http` 实例仅被 `fetchPortfolio()` 使用，无 risk 相关调用
- `createClient('/api/risk')` 在 `api/risk.ts` 和 `api/circuitBreaker.ts` 中正确使用

---

### 总体结论
⚠️ **需修复**

**关键问题**：`validateRiskStatusData()` 与新 API 响应格式不兼容，会导致运行时校验失败。

**修复优先级**：
1. **P0**：修复 `validateRiskStatusData()` 的 `overallStatus` 校验，或让 `fetchRiskStatus()` 直接使用 `api/risk.ts` 的实现
2. **P1**：统一风控 API 调用路径，避免 `trading.ts` 和 `api/risk.ts` 并行重复实现
