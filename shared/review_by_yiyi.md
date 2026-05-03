## YIYI 审查报告

> 审查时间：2026-05-03
> 审查范围：接口一致性（风控 API 路径统一 + IC 计算脚本）
> 审查视角：因子/数据视角

---

### 1. API_CONTRACT 一致性

⚠️ **发现问题**

`API_CONTRACT.md` 定义 `/api/risk/status` 的响应格式为：
```json
{
  "overallRiskLevel": "NORMAL",
  "marginUtilization": 0.15,
  "dailyPnL": 12500,
  "openPositionCount": 3
}
```

但 `risk.py` 中 `RiskStatusResponse` Pydantic 模型定义的字段为：
```python
date: str
overallStatus: RiskSeverity   # PASS/WARN/BLOCK
rules: list[RiskRuleStatusItem]
triggeredCount: int
circuitBreaker: bool
updatedAt: str
```

两者**完全不兼容**——字段名不同（`overallRiskLevel` vs `overallStatus`）、字段集合不同（API_CONTRACT 有 `marginUtilization/dailyPnL/openPositionCount`，RiskStatusResponse 没有；RiskStatusResponse 有 `rules/triggeredCount`，API_CONTRACT 没有）。

实际 `get_risk_status()`（`vnpy_bridge.py`）返回的是：
```python
{
    "status": self.status.value,        # 如 "normal"
    "active_rules": list(range(1, 12)),
    "recent_events": [...]
}
```
同样与两者都不匹配。

**结论**：`/api/risk/status` 的响应格式存在三层不一致：API_CONTRACT vs Pydantic模型 vs vnpy_bridge 实际返回值。需要三方对齐。

---

### 2. INTERFACE_GOVERNANCE 状态标注

⚠️ **发现问题**

`INTERFACE_GOVERNANCE.md` 风控类端点清单中，将 `/api/trading/risk-rules` 标注为状态 ✅ 已实现，但实际该端点路径为 `/api/risk/rules`（对应 `risk.py` 中的 `GET /risk/rules`）。

此外，清单缺少以下已实现的端点：
- `GET /api/risk/rules`（✅ 已实现）
- `PUT /api/risk/rules/{rule_id}`（✅ 已实现）
- `POST /api/risk/kelly`（✅ 已实现）
- `POST /api/risk/stress-test`（✅ 已实现）

API 路径已从 `/api/trading/risk-status` 迁移到 `/api/risk/status`，但 GOVERNANCE 文档未同步更新此路径变更。

**结论**：INTERFACE_GOVERNANCE.md 的风控端点清单不完整、未反映最新路径，需修订。

---

### 3. IC计算脚本依赖

✅ **通过（无问题）**

`compute_ic_heatmap.py` 的依赖链：
- 数据源：`pit_factor_observations` 表 + 各品种 OHLCV 表（`{symbol}_futures_ohlcv` 或 `jm_futures_ohlcv`）
- 输出：`ic_heatmap` SQLite 表
- 路径：`D:\futures_v6\macro_engine\...`

该脚本与风控 API（`/api/risk/status`）**完全解耦**，无任何依赖关系。IC 计算脚本走的是数据库 SQLite 路径，风控 API 走的是 FastAPI + vnpy_bridge 路径，两者独立。

路径映射确认：
- 脚本读取：`DB_PATH = Path(__file__).parent.parent / "pit_data.db"`
- 输出写入：`ic_heatmap` 表
- API 读取：`vnpy_bridge.get_risk_status()`（不涉及 ic_heatmap）

**结论**：IC 计算脚本不受风控 API 路径变更影响，也与风控系统无数据依赖。

---

### 4. 因子评分与风控接口契约

⚠️ **需修复**

`risk.py` 中 `simulate` 端点（R10 宏观熔断）在降级路径里直接调用了 `macro_scoring_engine.get_latest_signal(main_symbol)`：

```python
signal_data = engine.get_latest_signal(main_symbol)
if signal_data:
    score = signal_data.get("compositeScore", 0)
    if req.direction.upper() == "LONG" and score < -0.5:
        violations.append(...)
```

这是**隐式耦合**——风控模块直接 import 并调用宏观引擎，存在以下风险：

1. **循环依赖风险**：若宏观引擎也引用风控模块，可能导致初始化失败
2. **接口脆弱性**：`get_latest_signal()` 返回格式未在 API_CONTRACT 中定义，属于隐形接口
3. **信号源单一**：风控预检直接读引擎内存状态，未通过标准 API 路径（`/api/macro/signal/{symbol}`），若引擎与 API 服务分离部署会失效

从因子评分视角看，风控使用 `compositeScore` 作为熔断依据，但该分数本身由 IC 加权计算而来（`compute_ic_heatmap.py` 输出到 `ic_heatmap` 表）。**当前路径**：`ic_heatmap` 表 → 宏观引擎 → 风控熔断，整个链路未在文档中明确定义。

**结论**：风控使用因子评分信号存在隐式耦合，建议通过标准化 API（`/api/macro/signal/{symbol}`）获取信号，而非直接 import 引擎模块。

---

### 5. 路径一致性

⚠️ **需修复（部分）**

**API 路径**：✅ 已统一
- 旧路径 `/api/trading/risk-status` → 新路径 `/api/risk/status` ✅ 正确

**IC 计算脚本输出路径**：✅ 无问题
- 写入 `ic_heatmap` SQLite 表（`pit_data.db`）
- 不涉及文件系统路径一致性检查

**数据流路径**（发现隐患）：
- `compute_ic_heatmap.py` → `ic_heatmap` 表（数据终点）
- 但 `ic_heatmap` 表的数据消费者是谁？**文档未明确**
- API 服务器（FastAPI）是否读取 `ic_heatmap` 表？—— 经检查，**不读取**。API 服务器数据来源是 `vnpy_bridge`（内存态），与 `ic_heatmap` 表完全独立
- 这意味着 IC 计算结果**未通过 API 对外暴露**，宏观引擎获取因子权重时是否用到 IC 表，路径不清晰

**结论**：IC 计算输出到 `ic_heatmap` 表，但该表数据消费者路径未文档化，属于隐性数据流。

---

### 总体结论

⚠️ **需修复**

| 检查项 | 状态 | 严重度 |
|--------|------|--------|
| API_CONTRACT vs Pydantic vs vnpy_bridge 响应格式三方不一致 | ⚠️ 需修复 | 🔴 高 |
| INTERFACE_GOVERNANCE 风控端点清单未同步路径变更 | ⚠️ 需修复 | 🟠 中 |
| IC 计算脚本与风控 API 解耦 | ✅ 通过 | — |
| 风控→因子评分存在隐式 import 耦合 | ⚠️ 需修复 | 🟠 中 |
| IC 输出表数据消费者路径未文档化 | ⚠️ 需修复 | 🟠 中 |

**必须修复项**：
1. 统一 `/api/risk/status` 的响应格式——API_CONTRACT、Pydantic 模型、vnpy_bridge 三方必须对齐
2. 更新 INTERFACE_GOVERNANCE.md 的风控端点清单，反映实际路径 `/api/risk/*`

**建议修复项**：
3. 风控熔断改用标准 API（`/api/macro/signal/{symbol}`）获取宏观打分，消除直接 import
4. 明确 `ic_heatmap` 表的数据消费路径，在 DATA_CONTRACT 或 EVENTS_CONTRACT 中定义

---

*审查人：因子分析师 YIYI*
*日期：2026-05-03*
