## mimo 审查报告

### 1. 架构合理性
**⚠️ 需修复**

**问题A：`trading.ts` 中 `fetchRiskStatus()` 重复创建 `riskHttp` client**

`frontend/src/api/trading.ts` 的 `fetchRiskStatus()` 绕过了 `risk.ts` 已有的 `fetchRiskStatus()` 函数，重复创建独立的 `riskHttp = createClient('/api/risk')` client 实例：

```typescript
// trading.ts 中
const riskHttp = createClient('/api/risk')
const res = await riskHttp.get<unknown>('/status')
```

这导致：
1. 两个独立的 Axios 实例（`risk.ts` 一个 + `trading.ts` 一个）
2. 两套不同的响应验证逻辑（`trading.ts` 用 `validateRiskStatusData`，`risk.ts` 直接类型断言）
3. 类型不一致风险：`trading.ts` 返回 `RiskStatusData`，`risk.ts` 返回 `RiskStatusResponse`，两者字段不同

**建议**：`trading.ts` 的 `fetchRiskStatus()` 应直接调用 `risk.ts` 导出的 `fetchRiskStatus()`，而不是自己重新实现。

**问题B：响应类型不一致**

- `risk.ts` → `RiskStatusResponse`：字段含 `overallStatus`、`rules[]`、`triggeredCount`、`circuitBreaker`、`date`、`updatedAt`
- `trading.ts` → `RiskStatusData`：字段含 `overallStatus`、`levels[]`、`equity`、`drawdown`、各类 `drawdown*` 阈值

两者都声称来自同一个 API 端点 `/api/risk/status`。这两个类型本质上是**同一个 API 的不同解释**，说明前端对风控状态的认知在两个模块中不统一。

**问题C：`/api/risk/status` 实际返回格式与 API_CONTRACT.md 不符**

`routes/risk.py` 的 `RiskStatusResponse` 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "date": "2026-05-03",
    "overallStatus": "PASS",    // 注：不是 overallRiskLevel
    "rules": [...],
    "triggeredCount": 0,
    "circuitBreaker": false,
    "updatedAt": "..."
  }
}
```

但 `API_CONTRACT.md` 定义的 `/api/risk/status` 响应格式为：
```json
{
  "data": {
    "overallRiskLevel": "NORMAL",     // 字段名不同！
    "marginUtilization": 0.15,        // 字段不存在
    "dailyPnL": 12500,                // 字段不存在
    "openPositionCount": 3            // 字段不存在
  }
}
```

这是 **P0 类型不匹配**：实际 API 返回字段与文档定义完全不同。

---

### 2. 向后兼容性
**⚠️ 需修复**

**问题D：`macro_api_server.py` 中 `/api/risk/status` 旧端点是否真的被删除了？**

审计报告称"旧风控端点（232行）已由 `routes/risk.py` 接管"，但 `macro_api_server.py` 全文中没有定义任何 `/api/risk/*` 端点（`risk_router` 注册在 `app.include_router(risk_router)`），这意味着旧端点已成功迁移。但需人工确认：
- 确认没有其他文件（脚本、定时任务、其他 agent 的代码）仍调用旧路径
- 建议 grep 全项目搜索 `127.0.0.1:8000/api/risk` 或 `/api/risk/status` 的调用

**问题E：API_CONTRACT.md 定义的 `/api/trading/risk-rules` 与代码不符**

文档定义：
- `GET /api/trading/risk-rules` → 风控规则列表
- `PUT /api/trading/rules` → 更新风控规则

实际代码（`routes/risk.py`）：
- `GET /api/risk/rules` → 风控规则列表
- `PUT /api/risk/rules/{rule_id}` → 更新单条规则

实际代码（`macro_api_server.py`）：没有 `/api/trading/risk-rules`

**这是文档与实现的双重不一致。**

---

### 3. 代码质量
**✅ 通过（有小瑕疵）**

**循环依赖检查：**
- `macro_api_server.py` → `from routes.risk import router` → `app.include_router(risk_router)`：✅ 单向注册，无循环
- `routes/risk.py` → `from services.vnpy_bridge import get_vnpy_bridge`：✅ 运行时导入，不形成编译期循环
- `routes/risk.py` 内部 `from risk.risk_engine import ...`：✅ `_CORE_RISK_DIR` 正确设置在 `sys.path` 前

**小瑕疵：**
- `routes/risk.py` 第 23 行 `_CORE_RISK_DIR = Path(__file__).parent.parent.parent / "core"`：向上三级目录跳到 `D:\futures_v6\`，然后拼接 `core`，得到 `D:\futures_v6\core`，正确。但这种跨目录 path 操作没有单元测试。

**`/api/trading/` 端点重复定义问题：**

`macro_api_server.py` 和 `routes/trading.py` 都定义了以下端点：
- `/api/trading/order`（POST）
- `/api/trading/positions`（GET）
- `/api/trading/account`（GET）
- `/api/trading/orders`（GET）
- `/api/trading/trades`（GET）
- `DELETE /api/trading/order/{vt_orderid}`

FastAPI 后注册的路由会覆盖先注册的。如果 `routes/trading.py` 先被 `include_router` 注册到 `macro_api_server.py`，然后 `macro_api_server.py` 又用 `@app.get/post/delete` 定义了同名端点，**后者会覆盖前者**。需要确认哪个版本是"真实执行"的逻辑。

---

### 4. 文档一致性
**⚠️ 需修复**

**INTERFACE_GOVERNANCE.md 与代码的差异：**

| 端点（文档） | 方法 | 文档路径 | 实际路径 | 状态 |
|------------|------|---------|---------|------|
| 风控规则列表 | GET | `/api/trading/risk-rules` | `/api/risk/rules` | ❌ 不一致 |
| 更新风控规则 | PUT | `/api/trading/rules` | `/api/risk/rules/{rule_id}` | ❌ 不一致 |
| 风控状态 | GET | `/api/risk/status` | `/api/risk/status` | ✅ 一致（但响应字段不符） |
| 风控预检 | POST | `/api/risk/simulate` | `/api/risk/simulate` | ✅ 一致 |
| 凯利公式 | POST | `/api/risk/kelly` | `/api/risk/kelly` | ✅ 一致 |
| 压力测试 | POST | `/api/risk/stress-test` | `/api/risk/stress-test` | ✅ 一致 |

**API_CONTRACT.md 与代码的差异：**

1. `/api/risk/status` 响应字段名不匹配（见问题C）
2. `/api/trading/risk-rules` 在代码中不存在
3. `DELETE /api/trading/order/{vt_orderid}` 的路径参数在文档中写作 `vt_orderid`，在代码中也是 `vt_orderid`，✅ 一致
4. `/api/trading/portfolio` 在 `routes/trading.py` 中已实现，但 `API_CONTRACT.md` 中无定义

**INTERFACE_GOVERNANCE.md 自身问题：**

- 文档中风控规则只有 R1~R11，但代码中已有 R12（`R12_CANCEL_LIMIT`）
- 文档中 R4 名称为"时段交易限制"，代码中为"R4_TOTAL_MARGIN"（总保证金上限），严重不一致

---

### 5. 测试覆盖
**⚠️ 覆盖不足**

`test_api_e2e_part2.py` 中对 `/api/risk/status` 的测试：

```python
r = client.get('/api/risk/status')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    d = data.get('data', {})
    print(f'  Overall: {d.get("overall_status")}')
    print(f'  Levels count: {len(d.get("levels", []))}')
```

**问题：**
1. **只验证 status code = 200，未验证实际字段值**
2. `d.get("levels", [])` 是错误的字段名（实际字段是 `rules`），这个断言永远不会失败因为默认值是空 list
3. 未测试 `pass` 路径（VNpyBridge 初始化成功时的返回）
4. 未测试 `fail` 路径（异常抛出时返回 `code: 1`）

---

### 6. 其他架构问题
**⚠️ 需修复**

**问题F：`macro_engine/frontend/` 删除确认**

✅ 目录已删除（`Test-Path` 返回 `DELETED`）

**问题G：`routes/trading.py` 中的 `/api/trading/portfolio` 端点无文档**

`routes/trading.py` 第 215 行定义了 `GET /api/trading/portfolio`，但 `API_CONTRACT.md` 和 `INTERFACE_GOVERNANCE.md` 均无此端点记录。这属于文档遗漏。

**问题H：统一 client 模式缺失**

`trading.ts` 创建 `riskHttp = createClient('/api/risk')`，`risk.ts` 也创建 `client = createClient('/api/risk')`。两处独立创建会导致：
- 拦截器被注册两次
- 请求日志重复
- `USE_MOCK` 切换时需要改两处

建议在 `client.ts` 中导出预配置的 `riskClient = createClient('/api/risk')`，所有风控 API 调用统一引用。

---

### 总体结论
**⚠️ 需修复**

| 维度 | 结论 | 严重度 |
|------|------|--------|
| 架构合理性 | ⚠️ 需修复 | P1 |
| 向后兼容性 | ⚠️ 需修复 | P1 |
| 代码质量 | ✅ 通过（有瑕疵） | P2 |
| 文档一致性 | ⚠️ 需修复 | P1 |
| 测试覆盖 | ⚠️ 需修复 | P2 |
| 其他架构 | ⚠️ 需修复 | P2 |

**必须修复的问题（P1）：**
1. 统一 `trading.ts` 和 `risk.ts` 对 `/api/risk/status` 的调用，消除重复 client 实例
2. 修正 `API_CONTRACT.md` 中 `/api/risk/status` 的响应字段定义（`overallRiskLevel` → `overallStatus`，补充 `rules[]` 等）
3. 统一 `INTERFACE_GOVERNANCE.md` 中的风控规则 R1~R12 与代码一致（R4 名称、添加 R12）
4. 将 `routes/trading.py` 中的 `/api/trading/portfolio` 补充到 `API_CONTRACT.md`

**建议修复的问题（P2）：**
5. 解决 `macro_api_server.py` 和 `routes/trading.py` 中 `/api/trading/*` 端点重复定义问题
6. 修复 `test_api_e2e_part2.py` 中 `/api/risk/status` 测试的断言逻辑（`levels` → `rules`）
7. 在 `client.ts` 中导出统一的 `riskClient` 预配置实例
