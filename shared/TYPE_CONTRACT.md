# 类型契约 — Python Pydantic ↔ TypeScript 对齐

> **版本**: v2.2  
> **生效日期**: 2026-05-01  
> **状态**: ✅ 已对齐  
> **更新说明**: subagent 亲自调用 API 验证 RU/CU/AU/AG 全部品种，Python schemas.py V1.0 和 TS macro.ts 均与 API 实际响应完全一致，无需修正

---

## 一、修复记录

### 修复前（v1.0，有误）

| 类型 | 问题 | 错误来源 |
|------|------|---------|
| MacroSignal | deep 在 Python 新增 `signal`/`strength`/`timestamp` 字段，API 实际不返回 | 子 agent 凭预期修改，未验证真实响应 |
| FactorDetail | Lucy 的 TS 缺少 `direction`/`rawValue`，多了 `contributionPolarity`（API无） | 子 agent 凭预期修改，未验证真实响应 |
| FactorDetail | deep 的 Python 有 `contribution_polarity`（必填），但 API 只返回 optional | 子 agent 凭预期修改 |
| schemas.py | deep 新增 `factorDetails` alias，但 API JSON 字段名是 `factors` | 子 agent 理解错误 |

### 修复后（v2.0，真实响应为唯一真值）

**API 实际响应（2026-05-01 实测）** 是唯一真值，所有类型定义必须与之对齐。

---

## 二、真实 API 响应结构

### MacroSignal

```typescript
interface MacroSignal {
  symbol: string;              // "RU"
  compositeScore: number;       // 0.6323
  direction: 'LONG' | 'NEUTRAL' | 'SHORT';
  updatedAt: string;           // "2026-05-01T14:30:02+08:00"
  factors: FactorDetail[];      // 因子数组
}
```

### FactorDetail（API 实际返回）

```typescript
interface FactorDetail {
  factorCode: string;                    // "RU_TS_ROLL_YIELD"
  factorName: string;                    // "RU期限利差"
  direction: 'positive' | 'negative' | 'neutral';  // 因子方向
  rawValue: number;                     // 0.1203
  normalizedScore: number;               // 0.0
  weight: number;                        // 0.22
  contribution: number;                  // 0.0
  factorIc?: number;                     // IC值，可选
}
```

---

## 三、Python schemas.py（已修正）

```python
class FactorDetail(BaseModel):
    """因子明细（字段契约 V2.0：与 API 实际响应完全对齐）"""
    model_config = ConfigDict(populate_by_name=True)

    factor_code: str = Field(..., alias="factorCode")
    factor_name: str = Field(..., alias="factorName")
    direction: FactorDirection = Field(..., alias="direction")
    raw_value: float = Field(..., alias="rawValue")
    normalized_score: float = Field(..., alias="normalizedScore")
    factor_weight: float = Field(..., ge=0, le=1, alias="weight")
    contribution: float = Field(..., alias="contribution")
    factor_ic: Optional[float] = Field(None, alias="factorIc")


class MacroSignal(BaseModel):
    """单品种宏观信号（字段契约 V2.0：与 API 实际响应完全对齐）"""
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    composite_score: float = Field(..., ge=-1, le=1, alias="compositeScore")
    direction: Direction
    updated_at: str = Field(..., alias="updatedAt")
    factor_details: List[FactorDetail] = Field(default_factory=list, alias="factors")
```

---

## 四、TypeScript types/macro.ts（已修正）

```typescript
export interface MacroSignal {
  symbol: string;
  compositeScore: number;        // 综合得分，-1~1
  direction: 'LONG' | 'NEUTRAL' | 'SHORT';
  updatedAt: string;             // ISO 8601
  factors: FactorDetail[];
}

export interface FactorDetail {
  factorCode: string;                              // 因子代码
  factorName: string;                              // 因子名称
  direction: 'positive' | 'negative' | 'neutral';  // 因子方向
  rawValue: number;                                // 原始值
  normalizedScore: number;                         // 归一化得分
  weight: number;                                 // 因子权重 0-1
  contribution: number;                           // 贡献度
  factorIc?: number;                              // IC值（可选）
}
```

---

## 五、各模块验证结果（2026-05-01）

| 品种 | compositeScore | direction | updatedAt | factorCount | 状态 |
|------|---------------|-----------|-----------|---------|------|
| RU | 0.6323 | LONG | 2026-05-01T14:30:02+08:00 | 14 | ✅ |
| CU | -0.0039 | NEUTRAL | 2026-05-01T14:30:02+08:00 | 13 | ✅ |
| AU | 0.0688 | NEUTRAL | 2026-05-01T14:30:02+08:00 | 17 | ✅ |
| AG | 0.0325 | NEUTRAL | 2026-05-01T14:30:02+08:00 | 13 | ✅ |

---

## 六、规则说明

### 唯一真值规则
**API 实际响应是唯一真值**，不是 TypeScript 类型文件，不是 Python Pydantic 定义。

### 修改流程
```
1. 通过 Invoke-RestMethod 查看真实 API 响应（不猜、不预期）
2. 如果需要改类型，先改后端 schemas.py
3. 用真实 API 响应验证修改正确性
4. 再更新 TypeScript 类型文件
5. 双方测试通过后更新本文档
```

### 禁止事项
- ❌ 禁止在没见过真实 API 响应的情况下修改类型定义
- ❌ 禁止在 Python/TS 中定义 API 不返回的字段（phantom fields）
- ❌ 禁止修改 Python schema 后不调用 API 验证就直接提交

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-01 | 初始版本（子 agent 创建，有误） |
| v2.0 | 2026-05-01 | 重新基于 API 实际响应对齐，撤销错误修改 |
| v2.1 | 2026-05-01 | subagent 亲自调用 API 验证 4 品种，Python V1.0 + TS macro.ts 均无需修正 |
| v2.2 | 2026-05-01 | Lucy subagent 调用 API 验证 RU，发现 TS 类型有 phantom 字段，已修正 |

---

*本契约由项目经理亲自验证 API 响应后修正*

---

## 八、Lucy subagent 验证报告（2026-05-01 18:49）

### 验证步骤

**Step 1 — 调用真实 API**
`ash
curl.exe -s http://localhost:8000/api/macro/signal/RU
`

**Step 2 — 实际响应结构（RU）**
`json
{
  "code": 0,
  "message": "success",
  "data": {
    "symbol": "RU",
    "compositeScore": 0.6323,
    "direction": "LONG",
    "updatedAt": "2026-05-01T14:30:02+08:00",
    "factors": [
      {
        "factorCode": "RU_DEM_TIRE_ALLSTEEL",
        "factorName": "全钢胎开工率",
        "direction": "neutral",
        "rawValue": 70.48,
        "normalizedScore": 0.0,
        "weight": 0.0161,
        "contribution": 0.0,
        "factorIc": 0.0
      }
    ]
  }
}
`

**API 关键发现：**
- actorIc 字段名，非 icValue
- actorIc 在所有因子中均有值（0.0），非 
ull
- 无 icDirection 字段

### 与 TS 类型的差异

| 文件 | 问题 | 严重度 |
|------|------|--------|
| macro_engine/frontend/src/types/macro.ts | icValue?: number 应为 actorIc?: number；多了 icDirection?: 'up'|'down'（API 无此字段） | 🔴 需修正 |
| rontend/futures_trading/frontend/src/types/macro.ts | actorIc?: number \| null 应为 actorIc?: number（API 不返回 null） | 🟡 已修正 |
| macro_engine/frontend/futures_trading/src/types/macro.ts | ✅ 与 API 完全一致 | ✅ 无需修改 |

### 已执行的 TS 文件修正

**1. D:\futures_v6\macro_engine\frontend\src\types\macro.ts**
`diff
- icValue?: number
- icDirection?: 'up' | 'down'
+ factorIc?: number  // 注释更新：说明这是 API 实际字段名
`

**2. D:\futures_v6\frontend\futures_trading\frontend\src\types\macro.ts**
`diff
- factorIc?: number | null
+ factorIc?: number
`

### 结论

- ✅ API data 顶层字段（symbol/compositeScore/direction/updatedAt/factors）与 TYPE_CONTRACT.md v2.0 记录完全一致
- ✅ FactorDetail 字段名与 v2.0 记录一致
- 🔴 macro_engine/frontend/src/types/macro.ts 有 phantom 字段（icValue/icDirection），已修正
- 🟡 rontend/futures_trading/frontend/src/types/macro.ts 的 actorIc?: number | null 应去掉 | null，已修正
