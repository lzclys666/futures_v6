# 系统接口对齐深度扫描报告

> **日期**: 2026-05-06 13:45 | **扫描人**: 项目经理 | **范围**: Python API ↔ TypeScript 前端全链路

---

## 扫描范围

检查了以下模块的输入/输出字段对齐：

| 模块 | Python 文件 | TS 文件 | 状态 |
|------|------------|---------|------|
| FactorDetail | `api/schemas.py` | `types/macro.ts` + `api/macro.ts` | 🔴 断裂 |
| MacroSignal | `api/schemas.py` | `types/macro.ts` + `api/macro.ts` | 🟡 有适配器 |
| RiskStatusResponse | `api/routes/risk.py` | `types/risk.ts` + `api/risk.ts` | ✅ 对齐 |
| RiskRuleId | `api/routes/risk.py` | `types/risk.ts` | ✅ 对齐 |
| RiskRule | `api/routes/risk.py` | `types/risk.ts` | ✅ 对齐 |
| OrderResponse | `api/routes/trading.py` | `types/trading.ts` | 🔴 完全不同 |
| CancelOrderResponse | `api/routes/trading.py` | `types/trading.ts` | 🔴 缺字段 |
| Portfolio | `api/routes/trading.py` | `types/macro.ts` | ✅ 有适配器 |
| KellyRequest/Response | `api/routes/risk.py` | `types/risk.ts` | ✅ 对齐 |
| StressTestReport | `api/routes/risk.py` | `types/risk.ts` | ✅ 对齐 |
| SimulateResponse | `api/routes/risk.py` | — | 🟡 pass_ 别名问题 |
| vnpy_bridge 导入 | `api/routes/trading.py` + `risk.py` | — | 🔴 路径断裂 |

---

## 🔴 问题 1：FactorDetail 字段命名断裂

**严重度**: 🔴 致命 — 前端因子数据全部 undefined

### 现状

Python `schemas.py` 定义了 camelCase alias：
```python
factor_code: str = Field(..., alias="factorCode")
factor_weight: float = Field(..., alias="weight")  # 注意：alias 是 "weight" 不是 "factorWeight"
factor_ic: Optional[float] = Field(None, alias="factorIc")
```

但 `macro_api_server.py` L1189 调用 `model_dump()` **未传 `by_alias=True`**：
```python
return _wrap(data.model_dump())  # 返回 snake_case！
```

实际 API 返回：
```json
{"factor_code": "RU_TS_ROLL_YIELD", "factor_weight": 0.15, "factor_ic": -0.402}
```

TS `_adaptFactor` 期望：
```typescript
o.factorCode  // undefined（API 返回 factor_code）
o.weight      // undefined（API 返回 factor_weight）
o.rawValue    // undefined（API 返回 raw_value）
```

### 影响

- 前端 FactorCard、FactorDashboard、SignalChart 所有因子展示全部显示 undefined
- `weight` 字段缺失导致贡献度计算失败
- `factorIc` 字段缺失导致 IC 热力图空白

### 修复方案

**方案 A（推荐）**: `macro_api_server.py` L1189 + L1318 改为 `model_dump(by_alias=True)`
```python
return _wrap(data.model_dump(by_alias=True))
```

**方案 B**: 更新 `_adaptFactor` 增加 snake_case 回退
```typescript
weight: (o.weight ?? o.factor_weight) as number,
```

---

## 🔴 问题 2：vnpy_bridge 导入路径断裂

**严重度**: 🔴 致命 — 所有交易/风控端点 500

### 现状

`api/routes/trading.py` L1 和 `api/routes/risk.py` L388/L598/L652/L716 均导入：
```python
from services.vnpy_bridge import get_vnpy_bridge
```

但 `D:\futures_v6\api\services\vnpy_bridge.py` **不存在**！

实际文件在 `D:\futures_v6\services\vnpy_bridge.py`（54KB，包含 VNpyBridge + PaperBridge + _BridgeProxy）。

### 影响

- `GET /api/trading/positions` → ImportError → 500
- `GET /api/trading/account` → ImportError → 500
- `GET /api/trading/portfolio` → ImportError → 500
- `POST /api/trading/order` → ImportError → 500
- `GET /api/risk/status` → ImportError → 500（降级到 PaperBridge 前的 try 块）
- `GET /api/risk/rules` → ImportError → 500

### 修复方案

**方案 A（推荐）**: 创建 `D:\futures_v6\api\services\vnpy_bridge.py` 作为 re-export：
```python
# api/services/vnpy_bridge.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from services.vnpy_bridge import get_vnpy_bridge
```

**方案 B**: 在 `macro_api_server.py` 启动时添加 `sys.path`：
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

**方案 C**: 修改所有 import 为绝对路径（改动大，不推荐）

---

## 🔴 问题 3：OrderResponse 完全不对齐

**严重度**: 🔴 致命 — 前端下单后无法正确解析响应

### 现状

**Python `trading.py` OrderResponse:**
```python
class OrderResponse(BaseModel):
    success: bool
    order_id: Optional[str] = None
    message: str
    timestamp: str
```

**TS `trading.ts` OrderResponse:**
```typescript
export interface OrderResponse {
    orderId: string
    symbol: string
    direction: OrderDirection
    price: number
    volume: number
    tradedVolume: number
    status: OrderStatus
    createdAt: string
    updatedAt: string
    message?: string
}
```

**差异**: Python 返回 4 个字段（success/order_id/message/timestamp），TS 期望 10 个字段（包含 symbol/direction/price/volume/tradedVolume/status）。**完全不匹配**。

### 修复方案

统一为 TS 期望的格式（Python 端修改）：
```python
class OrderResponse(BaseModel):
    orderId: str
    symbol: str
    direction: str
    price: float
    volume: int
    tradedVolume: int
    status: str  # PENDING/SUBMITTING/NOT_TRADED/PART_TRADED/ALL_TRADED/CANCELLED/REJECTED
    createdAt: str
    updatedAt: str
    message: Optional[str] = None
```

---

## 🔴 问题 4：CancelOrderResponse 缺字段

**严重度**: 🟡 中 — 撤单后前端无法显示订单 ID

### 现状

**Python CancelResponse:**
```python
class CancelResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
```

**TS CancelOrderResponse:**
```typescript
export interface CancelOrderResponse {
    orderId: string
    success: boolean
    message?: string
}
```

**差异**: Python 缺 `orderId`，TS 缺 `timestamp`。

### 修复方案

Python 端增加 `orderId` 字段：
```python
class CancelResponse(BaseModel):
    success: bool
    orderId: str
    message: str
    timestamp: str
```

---

## 🟡 问题 5：SimulateResponse `pass` 别名

**严重度**: 🟡 中 — 风控预检结果可能解析失败

### 现状

**Python SimulateResponse:**
```python
class SimulateResponse(BaseModel):
    pass_: bool = Field(alias="pass")
    violations: list[SimulateViolation]
```

当使用 `model_dump()`（无 `by_alias=True`）时返回 `pass_` 而非 `pass`。

### 修复方案

确保 simulate 端点返回时使用 `by_alias=True`：
```python
return {"pass": result.pass_, "violations": [v.model_dump() for v in result.violations]}
```

---

## ✅ 已对齐的接口

| 接口 | Python | TS | 状态 |
|------|--------|-----|------|
| RiskStatusResponse | routes/risk.py L186 | types/risk.ts | ✅ 字段完全一致 |
| RiskRuleId | routes/risk.py L98 | types/risk.ts | ✅ 12 条规则完全一致 |
| RiskRule | routes/risk.py L206 | types/risk.ts | ✅ 字段完全一致 |
| KellyRequest | routes/risk.py L278 | types/risk.ts | ✅ 字段完全一致 |
| KellyResponse | routes/risk.py L298 | types/risk.ts | ✅ 字段完全一致 |
| StressTestReport | routes/risk.py L340 | types/risk.ts | ✅ 字段完全一致 |
| StressTestResult | routes/risk.py L320 | types/risk.ts | ✅ 字段完全一致 |
| Portfolio | trading.py | types/macro.ts | ✅ 有 snake→camel 适配器 |
| MacroSignal | schemas.py | types/macro.ts | ✅ 有 _adaptSignal 适配器 |

---

## 汇总：按紧急度排序的修复清单

| # | 问题 | 严重度 | 修复方 | 工时 | 修复内容 |
|---|------|--------|--------|------|----------|
| **1** | vnpy_bridge 导入路径 | 🔴 致命 | deep | 15min | 创建 api/services/vnpy_bridge.py re-export |
| **2** | FactorDetail model_dump 缺 by_alias | 🔴 致命 | deep | 5min | L1189+L1318 加 `by_alias=True` |
| **3** | OrderResponse 格式完全不同 | 🔴 致命 | deep+Lucy | 2h | Python 端重写 + TS 端适配 |
| **4** | CancelOrderResponse 缺 orderId | 🟡 中 | deep | 30min | Python 端增加 orderId |
| **5** | SimulateResponse pass 别名 | 🟡 中 | deep | 15min | 确保 by_alias 或手动构造 |

**总计**: 4h 修复，其中 #1+#2 是阻塞全链路的 20 分钟快修。

---

## 关键发现

### 深层原因

1. **schemas.py 定义了 alias 但未使用** — `model_config = ConfigDict(populate_by_name=True)` + `Field(alias="weight")` 是正确的设计，但 `model_dump()` 调用时忘记传 `by_alias=True`

2. **vnpy_bridge 路径假设错误** — 代码假设 `services/` 在 `api/` 同级，但实际 API 从 `api/` 目录启动，`services/` 不在 Python path 上

3. **OrderResponse 设计脱节** — Python 端按"简单确认"设计（success/order_id），TS 端按"完整订单对象"设计，两套设计从未对齐过

### 影响面

- **vnpy_bridge 断裂** → 所有交易端点 500 → Lucy Phase 2 全部 Mock
- **FactorDetail 断裂** → 所有因子展示 undefined → YIYI IC 热力图空白
- **OrderResponse 断裂** → 下单后前端无法显示订单状态 → 交易面板不可用

### 修复优先级

**今天必须修**：#1 vnpy_bridge 路径（15min）+ #2 FactorDetail by_alias（5min）
**本周内修**：#3 OrderResponse 格式对齐（2h）
**可延后**：#4 #5 格式细节（45min）
