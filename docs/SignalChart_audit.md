# SignalChart 组件现状审计报告

**审计人**: Lucy (UI Designer)  
**日期**: 2026-04-22  
**状态**: 🔴 存在严重字段映射问题，需与程序员deep确认

---

## 一、当前已有接口列表

| 接口 | 方法 | 路径 | 返回类型 |
|------|------|------|----------|
| I001 | GET | `/api/macro/signal/all` | `MacroSignalSummary[]` |
| I002 | GET | `/api/macro/signal/{symbol}` | `MacroSignal` (含 factors) |
| I003 | GET | `/api/macro/factor/{symbol}` | `FactorDetail[]` |
| I004 | GET | `/api/macro/score-history/{symbol}` | `ScoreHistoryPoint[]` |

### 接口字段详情

**MacroSignalSummary** (I001 返回):
```typescript
{
  symbol: string
  compositeScore: number      // -1 ~ 1
  direction: SignalDirection // LONG | NEUTRAL | SHORT
  updatedAt: string           // ISO8601
}
```

**MacroSignal** (I002 返回):
```typescript
{
  symbol: string
  compositeScore: number
  direction: SignalDirection
  updatedAt: string
  factors: FactorDetail[]
}
```

**ScoreHistoryPoint[]** (I004 返回):
```typescript
{
  date: string    // YYYY-MM-DD
  score: number
  direction: SignalDirection
}
```

---

## 二、SignalChart 组件接口

组件 props 定义 (`types/macro.ts`):

```typescript
interface SignalChartProps {
  symbol: string
  history: ScoreHistoryPoint[]
  loading?: boolean
}
```

组件内部使用 ECharts 渲染历史走势，`history` 数组直接来自 `scoreHistory` store 字段。

---

## 三、缺失的数据字段

### 3.1 已确认缺失

| 缺失字段 | 所属接口 | 说明 | 责任方 |
|----------|----------|------|--------|
| `raw_value` / `rawValue` | I002/I003 factors | 因子原始值（用于判断数据是否可用） | 后端已有，CSV 可能为空 |
| `factor_ic` / `factorIc` | I002/I003 factors | 因子 IC 值（用于展示数据质量） | 后端已有 |
| 品种中文名 `symbolName` | I001/I002 | 如 "橡胶" / "铜" | **缺失，需产品数据** |

### 3.2 前端需要但未实现

| 字段 | 用途 | 当前状态 |
|------|------|----------|
| 置信度 / confidence | 显示信号可信程度 | 未实现 |
| 同类品种对比 | 跨品种横向比较 | 未实现 |
| 信号有效期 | 多头/空头持续预期 | 未实现 |

---

## 四、渲染异常/问题清单

### 🔴 P0 - 严重问题

#### 问题1: `direction` 字段类型混淆

**现象**: `FactorDetail.direction` 前端定义为 `'positive' | 'negative' | 'neutral'`，但 API 实际返回的是交易方向 `LONG | NEUTRAL | SHORT`。

**根因**: 后端 `schemas.py` 中 `FactorDetail.factor_direction` alias 为 `"direction"`，但 `_build_factor_details_from_csv()` 返回的 `factor_direction` 是英文的 positive/negative/neutral，不是交易方向。前端 `_adapt()` 函数试图处理这个，但类型定义本身就错了。

**影响**: FactorCard 组件显示 direction badge 颜色/文案可能错误。

**修复方案**: 
- 确认 `FactorDetail.direction` 应为因子贡献方向 (`positive/negative/neutral`)，不是交易方向
- 前端类型保持不变，后端 `_build_factor_details_from_csv()` 已返回正确值

---

#### 问题2: Mock 数据与 CSV 数据的字段名不一致

**现象**: 
- Mock 数据 (`_build_factor_details_from_mock`): 返回 **camelCase** 字段 (`factorCode`, `factorName`, `contributionPolarity`, `rawValue`, `normalizedScore`, `weight`, `factorIc`)
- CSV 数据 (`_build_factor_details_from_csv`): 返回 **snake_case** 字段 (`factor_code`, `factor_name`, `factor_direction`, `raw_value`, `factor_value`, `factor_weight`, `factor_ic`)

**根因**: 两个函数由不同人/时期编写，未统一字段风格。

**影响**: 前端 `_adapt()` 只处理了 snake_case 路径，Mock 路径会漏掉 camelCase 字段适配（虽然 transformResponse 会直接透传，但 FactorCard 等组件按 snake_case 编写的访问逻辑会失败）。

**修复方案**:
- 统一为 **camelCase**（前端 TypeScript 标准）
- 或统一为 **snake_case**（Python/Pydantic 标准）

---

### 🟡 P1 - 需要确认

#### 问题3: `factor_direction` vs `contributionPolarity` 字段名未统一

**现象**: 
- CSV 路径: `factor_direction` (英文 positive/negative/neutral)
- Mock 路径: `contributionPolarity` (英文 positive/negative/neutral)

**需要确认**: 前端 `FactorDetail.direction` 字段实际对应的是哪个？

---

#### 问题4: `normalizedScore` vs `factor_value` 字段名未统一

**现象**:
- CSV 路径: `factor_value` (已标准化的分数)
- Mock 路径: `normalizedScore` (同样含义)

**前端类型**: `FactorDetail.normalizedScore`

**需要确认**: CSV 路径应统一为 `normalizedScore`。

---

## 五、与 API 字段的映射关系

### 5.1 I002 `/api/macro/signal/{symbol}` → MacroSignal

| 前端字段 | API 字段 (FastAPI) | Pydantic alias | 后端实际返回 (CSV路径) | 后端实际返回 (Mock路径) | 状态 |
|----------|-------------------|-----------------|------------------------|------------------------|------|
| symbol | symbol | - | symbol | symbol | ✅ 一致 |
| compositeScore | compositeScore | alias="compositeScore" | compositeScore | compositeScore | ✅ 一致 |
| direction | direction | - | direction (LONG/SHORT/NEUTRAL) | direction (LONG/SHORT/NEUTRAL) | ✅ 一致 |
| updatedAt | updatedAt | alias="updatedAt" | updatedAt | updatedAt | ✅ 一致 |
| factors | factors | alias="factors" | factors[] (snake_case) | factors[] (camelCase) | ⚠️ 不一致 |

### 5.2 FactorDetail 字段映射

| 前端类型字段 | Pydantic alias | CSV路径返回 | Mock路径返回 | 状态 |
|-------------|----------------|------------|-------------|------|
| factorCode | alias="factorCode" | factor_code | factorCode | ⚠️ 不一致 |
| factorName | alias="factorName" | factor_name | factorName | ⚠️ 不一致 |
| direction | alias="direction" | factor_direction | contributionPolarity | ⚠️ 字段名不同 |
| rawValue | - | raw_value (可能为null) | rawValue | ⚠️ 不一致 |
| normalizedScore | alias="normalizedScore" | factor_value | normalizedScore | ⚠️ 字段名不同 |
| weight | alias="weight" | factor_weight | weight | ⚠️ 不一致 |
| contribution | alias="contribution" | contribution | contribution | ✅ 一致 |
| factorIc | alias="factorIc" | factor_ic | factorIc | ⚠️ 不一致 |

---

## 六、与程序员deep的确认事项

### 需确认问题清单

#### Q1: 字段命名规范
**问题**: 统一用 camelCase 还是 snake_case？
- **选项A**: 后端统一返回 camelCase（前端 TypeScript 标准）
- **选项B**: 前端统一适配 snake_case（后端 Python/Pydantic 默认）
- **推荐**: 选项A（后端主动转型，符合前端契约优先原则）

#### Q2: `factor_direction` → `contributionPolarity` / `direction` 统一
**问题**: FactorDetail.direction 实际含义是因子贡献方向（positive/negative/neutral），字段名应统一为什么？
- **推荐**: 统一为 `contributionDirection`（明确语义）

#### Q3: `factor_value` → `normalizedScore` 统一
**问题**: 已标准化的因子得分字段名应统一为什么？
- **推荐**: 统一为 `normalizedScore`（业界通用术语）

#### Q4: `rawValue` 空值处理
**问题**: CSV 中 `raw_value` 为空时，前端应显示什么？
- **推荐**: 显示 "N/A" 并灰显该因子行

#### Q5: 品种中文名
**问题**: 是否需要新增 `symbolName` 字段（如 "橡胶" / "铜" / "黄金"）？
- **推荐**: 从 FACTOR_META 或单独配置文件读取

---

## 七、SignalChart 组件渲染状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 初始化 ECharts 实例 | ✅ 正常 | useEffect 正确 |
| window resize 监听 | ✅ 正常 | 已修复 |
| loading 状态 | ✅ 正常 | Spin 组件 |
| 日期/分数数据渲染 | ✅ 正常 | tooltip formatter 已修复 |
| 多头/空头阈值线 | ✅ 正常 | markLine 配置正确 |
| 无数据时图表隐藏 | ✅ 正常 | `!history.length` 时不渲染 |

**SignalChart 组件本身无渲染异常**，问题全部在 API 字段映射层。

---

## 八、结论

1. **SignalChart 组件代码质量**: ✅ 无渲染问题，Props 接口清晰
2. **API 字段映射**: 🔴 严重不一致，Mock/CSV 两套字段名
3. **类型安全**: 🟡 部分字段类型定义与实际返回值有偏差
4. **下一步**: 等待程序员deep确认字段映射统一方案后，更新 `api/macro.ts` 的 `_adapt()` 函数
