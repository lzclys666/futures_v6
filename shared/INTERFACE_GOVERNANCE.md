# 接口治理手册 v1.0

> **版本**: v1.0  
> **日期**: 2026-05-01  
> **状态**: 初始版本  
> **维护人**: 项目经理

---

## 一、文档目的

随着系统扩大，Bug修复和功能开发经常需要多人联动修改同一模块。本文档建立**接口所有权**和**契约文档**机制，将联动修改控制在最小范围。

---

## 二、系统全接口盘点

### 2.1 接口分类总览

| 类别 | 接口形式 | 当前位置 | 解耦程度 | 风险等级 |
|------|---------|---------|---------|---------|
| **A. 数据流接口** | CSV文件 | `macro_engine/output/*.csv` | ✅ 已解耦 | ⚠️ 中 |
| **B. API接口** | FastAPI端点 | `api/macro_api_server.py` | ⚠️ 可控 | ⚠️ 中 |
| **C. 配置接口** | YAML配置文件 | `macro_engine/risk_rules.yaml` | ❌ 强耦合 | 🔴 高 |
| **D. 类型接口** | Pydantic ↔ TypeScript | `api/schemas.py` + `frontend/src/types/` | ❌ 不同步 | 🔴 高 |
| **E. 事件接口** | PaperBridge/定时任务 | `scripts/` + `api/` | ✅ 已解耦 | ✅ 低 |

---

## 三、接口契约定义

### 3.1 A类 — 数据流接口（CSV文件）

#### 契约文件位置
```
D:\futures_v6\shared\DATA_CONTRACT.md  (待创建)
```

#### 当前CSV结构（v1.0，2026-05-01生效）

**文件命名规范**：
```
{symbol}_macro_daily_{YYYYMMDD}.csv
示例: RU_macro_daily_20260501.csv
```

**列定义**：

| 列名 | 类型 | 说明 | 版本 | 备注 |
|------|------|------|------|------|
| symbol | string | 品种代码（RU/CU/AU/AG/ZN等） | v1.0 | |
| date | string | 日期（YYYY-MM-DD） | v1.0 | |
| rowType | string | `SUMMARY` 或 `FACTOR` | v1.0 | SUMMARY为汇总行，FACTOR为因子行 |
| compositeScore | float | 综合得分（-1 ~ +1） | v1.0 | SUMMARY行有效 |
| direction | string | `LONG`/`NEUTRAL`/`SHORT` | v1.0 | SUMMARY行有效 |
| factorCount | int | 因子数量 | v1.0 | SUMMARY行有效 |
| updatedAt | string | 引擎更新时间（ISO8601） | v1.0 | |
| engineVersion | string | 引擎版本标识 | v1.0 | 如 `d_engine_v1.0` |
| factorCode | string | 因子代码 | v1.0 | FACTOR行有效 |
| factorName | string | 因子中文名 | v1.0 | FACTOR行有效 |
| rawValue | float | 因子原始值 | v1.0 | FACTOR行有效 |
| normalizedScore | float | 标准化得分 | v1.0 | FACTOR行有效 |
| weight | float | 因子权重（0~1） | v1.0 | FACTOR行有效 |
| contribution | float | 因子贡献度 | v1.0 | FACTOR行有效 |
| contributionPolarity | string | `positive`/`negative`/`neutral` | v1.0 | FACTOR行有效 |
| icValue | float | 因子IC值 | v1.0 | FACTOR行有效 |

**版本升级规则**：
- 禁止删除已有列
- 禁止修改已有列的数据类型
- 新增列必须放在末尾，并更新 `engineVersion` 字段
- 重大变更（删除列/改类型）需要 L2 技术议会表决

#### 读写权限

| 模块 | 读 | 写 | 限制 |
|------|---|---|------|
| factor_collector_main.py | — | ✅ | 唯一写入方 |
| macro_scoring_engine.py | ✅ | ✅ | 读取+追加因子 |
| VNpy策略 | ✅ | — | 只读，禁止写 |
| API服务器 | ✅ | — | 只读 |

#### 触发联动修改的场景

| 修改类型 | 需通知Owner | 影响范围 |
|---------|------------|---------|
| 新增列 | YIYI + deep + Lucy | 全部读取方 |
| 修改列名/类型 | YIYI + deep + Lucy | 全部读取方 |
| 删除列 | 技术议会表决 | 全局 |

---

### 3.2 B类 — API接口（FastAPI端点）

#### 契约文件位置
```
D:\futures_v6\shared\API_CONTRACT.md  (待创建)
```

#### 当前API端点清单

**宏观信号类**（`macro_api_server.py`）：

| 方法 | 端点 | 响应类型 | Owner | 状态 |
|------|------|---------|-------|------|
| GET | `/api/macro/signal/{symbol}` | `MacroSignal` | deep | ✅ 已实现 |
| GET | `/api/macro/signal/all` | `List[MacroSignal]` | deep | ✅ 已实现 |
| GET | `/api/macro/score-history/{symbol}` | `List[ScoreHistory]` | deep | ⚠️ 无历史数据 |
| GET | `/api/macro/factor/{symbol}` | `List[FactorDetail]` | deep | ✅ 已实现 |

**交易类**：

| 方法 | 端点 | 响应类型 | Owner | 状态 |
|------|------|---------|-------|------|
| GET | `/api/vnpy/status` | `VnpyStatus` | deep | ✅ Mock |
| GET | `/api/vnpy/account` | `AccountInfo` | deep | ✅ Mock |
| GET | `/api/vnpy/positions` | `List[Position]` | deep | ✅ Mock |
| GET | `/api/vnpy/orders` | `List[Order]` | deep | ✅ Mock |
| POST | `/api/trading/order` | `{vtOrderId: string}` | deep | ✅ Mock |
| DELETE | `/api/trading/order/{vt_orderid}` | `{success: bool}` | deep | ✅ Mock |

**风控类**：

| 方法 | 端点 | 响应类型 | Owner | 状态 |
|------|------|---------|-------|------|
| GET | `/api/trading/risk-status` | `RiskStatus` | deep | ✅ 已实现 |
| GET | `/api/trading/risk-rules` | `List[RiskRuleConfig]` | deep | ✅ 已实现 |
| PUT | `/api/trading/rules` | `List[RiskRuleConfig]` | deep | ✅ 已实现 |
| POST | `/api/risk/simulate` | `List[StressTestResult]` | deep | ⚠️ Phase 3 |
| POST | `/api/risk/kelly` | `KellyResult` | deep | ⚠️ Phase 3 |

**系统类**：

| 方法 | 端点 | 响应类型 | Owner | 状态 |
|------|------|---------|-------|------|
| GET | `/health` | `{status: string, version: string}` | deep | ✅ 已实现 |
| GET | `/api/health` | `ApiResponse` | deep | ✅ 已实现 |
| WS | `/ws/trading` | EventStream | deep | ❌ 未实现 |

#### 响应模型定义（schemas.py）

**MacroSignal**：
```python
{
    "symbol": "RU",
    "compositeScore": 0.45,       # float, -1~1
    "direction": "LONG",           # LONG | NEUTRAL | SHORT
    "updatedAt": "2026-05-01T14:30:02+08:00",
    "factors": [                   # FactorDetail[]
        {
            "factorCode": "RU_TS_ROLL_YIELD",
            "factorName": "RU期限利差",
            "contributionPolarity": "positive",  # positive | negative | neutral
            "normalizedScore": 0.23,
            "weight": 0.35,
            "contribution": 0.08,
            "factorIc": -0.12       # 可选，IC值
        }
    ]
}
```

#### 触发联动修改的场景

| 修改类型 | 需通知 | 影响范围 |
|---------|--------|---------|
| 新增端点 | Lucy（前端调用方） | 新页面开发 |
| 删除/重命名端点 | Lucy（前端调用方） | 前端404 |
| 修改响应字段 | Lucy（前端调用方） | 前端类型错误 |
| 修改请求参数 | Lucy（前端调用方） | 前端调用失败 |

---

### 3.3 C类 — 配置接口（risk_rules.yaml）

#### 契约文件位置
```
D:\futures_v6\shared\RISK_CONFIG_OWNER.md  (待创建)
```

#### 配置文件位置
```
D:\futures_v6\macro_engine\risk_rules.yaml
```

#### 单一所有权规则

| 操作 | 权限 |
|------|------|
| 读取 | 所有人 |
| 修改 | **仅 deep** |
| 新增规则 | **仅 deep**（L2议会授权后可临时开放） |
| 删除规则 | **仅 deep**（L2议会表决） |

#### 跨模块读取规则（重要）

```
❌ 禁止：frontend 直接读取 risk_rules.yaml
✅ 正确：frontend 通过 GET /api/trading/risk-rules 获取配置

❌ 禁止：VNpy策略直接读取 risk_rules.yaml
✅ 正确：通过 PaperBridge 事件获取风控状态
```

#### 当前规则ID清单（v1.0）

| 规则ID | 名称 | Layer | Owner |
|--------|------|-------|-------|
| R1 | 仓位限制 | L2-账户风险 | deep |
| R2 | 动态止损 | L2-账户风险 | deep |
| R3 | 集中度限制 | L2-账户风险 | deep |
| R4 | 时段交易限制 | L3-执行风险 | deep |
| R5 | ATR仓位计算 | L2-账户风险 | deep |
| R6 | 流动性限制 | L2-账户风险 | deep |
| R7 | 波动率限仓 | L2-账户风险 | deep |
| R8 | 保证金监控 | L2-账户风险 | deep |
| R9 | 冻结资金管理 | L3-执行风险 | deep |
| R10 | 熔断机制 | L1-市场风险 | deep |
| R11 | 处置效应监控 | L2-账户风险 | deep |

#### 触发联动修改的场景

| 修改类型 | 需通知 | 影响范围 |
|---------|--------|---------|
| 修改阈值 | Lucy（前端展示） | 风控配置面板 |
| 新增规则 | Lucy（前端展示）+ VNpy | 配置面板+策略逻辑 |
| 删除规则 | Lucy + VNpy | 配置面板崩溃+策略漏风控 |
| 修改规则ID | Lucy + VNpy + YIYI（IC计算） | 全系统不一致 |

---

### 3.4 D类 — 类型接口（Pydantic ↔ TypeScript）

#### 契约文件位置
```
D:\futures_v6\shared\TYPE_CONTRACT.md  (待创建)
```

#### 当前类型定义分布

| 语言 | 文件位置 | 定义类型 |
|------|---------|---------|
| Python | `api/schemas.py` | Pydantic BaseModel |
| TypeScript | `frontend/src/types/macro.ts` | interface |
| TypeScript | `frontend/src/types/risk.ts` | interface |
| TypeScript | `frontend/src/types/trading.ts` | interface |

#### 当前类型不一致风险（已发现）

| 字段路径 | Python定义 | TS定义 | 风险 |
|---------|-----------|--------|------|
| MacroSignal.score | float（非空） | `score?`（可空） | ⚠️ 运行时可能undefined |
| MacroSignal.signal | 无此字段 | `signal: string` | 🔴 TS多余字段，API返回无此字段 |
| FactorDetail.factor_ic | `Optional[float]` | `factorIc: number` | ⚠️ 命名差异（snake vs camel） |
| RiskRuleConfig.layer | int（1/2/3） | `layerId: string` | 🔴 类型不一致 |

#### 类型对齐规则

**规则1：TypeScript类型文件为唯一真值**
- `frontend/src/types/macro.ts` 中定义的接口为前端标准
- 后端 `schemas.py` 必须对齐 TS 定义
- 禁止在前后端任意一方单独修改类型定义

**规则2：命名规范**
- Python端：使用 Pydantic `Field(alias="camelCase")` 支持两种命名
- TypeScript端：必须使用 camelCase
- 共享字段命名对照表：

```
Python (Pydantic)          TypeScript (TS)
─────────────────────────────────────────
compositeScore       ↔    compositeScore
factorCode           ↔    factorCode
factorIc             ↔    factorIc
contributionPolarity ↔   contributionPolarity
updatedAt            ↔    updatedAt
```

**规则3：新增字段流程**
```
1. 前端在 TYPE_CONTRACT.md 中声明新字段（TS格式）
2. 通知 deep 在 schemas.py 中添加对应 Pydantic 字段
3. deep 确认后，前端在 types/ 中添加 TS 类型
4. 双方测试通过后，提交 TYPE_CONTRACT.md 更新
```

#### 触发联动修改的场景

| 修改类型 | 需通知 | 影响范围 |
|---------|--------|---------|
| 新增字段 | deep（后端）+ Lucy（前端） | API契约 |
| 删除字段 | deep（后端）+ Lucy（前端） | API契约 |
| 修改字段类型 | deep（后端）+ Lucy（前端） | API契约 |
| 重命名字段 | deep（后端）+ Lucy（前端） | API契约 |

---

### 3.5 E类 — 事件接口（PaperBridge/定时任务）

#### 契约文件位置
```
D:\futures_v6\shared\EVENTS_CONTRACT.md  (待创建)
```

#### 当前事件类型

**PaperBridge事件**（进程间通信）：

| 事件名 | 数据格式 | 触发方 | 接收方 | 状态 |
|--------|---------|-------|-------|------|
| `signal_updated` | `{symbol, direction, score}` | macro_scoring_engine | VNpy策略 | ⚠️ 未实现 |
| `order_filled` | `{vtOrderId, symbol, volume, price}` | VNpy | FastAPI | ⚠️ 未实现 |
| `risk_triggered` | `{ruleId, severity, message}` | riskEngine | VNpy策略 | ⚠️ 未实现 |

**定时任务事件**：

| 任务名 | 脚本 | 调度时间 | 触发动作 | Owner |
|--------|------|---------|---------|-------|
| 日终打分 | `daily_scoring.py` | 14:30 CST | 生成CSV | YIYI |
| 因子采集 | `factor_collector_main.py` | 20:00 CST | 更新PIT数据库 | YIYI |
| 历史回算 | `macro_history_backfill.py` | 手动触发 | 回填历史数据 | YIYI |

#### 触发联动修改的场景

| 修改类型 | 需通知 | 影响范围 |
|---------|--------|---------|
| 新增事件类型 | VNpy + FastAPI + 前端 | 全部订阅方 |
| 修改事件payload | 全部订阅方 | 消费方解析错误 |
| 删除事件类型 | 全部订阅方 | 事件丢失 |

---

## 四、模块所有权矩阵（RACI）

### 4.1 接口Owner定义

| 接口/文件 | Owner | Reviewer | 其他人可读 | 其他人可写 |
|-----------|-------|---------|-----------|-----------|
| CSV数据文件 | YIYI | deep | 所有人 | 仅YIYI |
| API端点 | deep | Lucy | 所有人 | 仅deep |
| schemas.py | deep | Lucy | 所有人 | 仅deep |
| risk_rules.yaml | deep | Lucy | 所有人 | 仅deep |
| frontend/src/types/ | Lucy | deep | 所有人 | 仅Lucy |
| 爬虫脚本 | YIYI | — | 所有人 | 仅YIYI |
| factor_collector_main.py | YIYI | — | 所有人 | 仅YIYI |
| daily_scoring.py | YIYI | deep | 所有人 | 仅YIYI |

### 4.2 跨模块修改规则

**当需要修改他人负责的接口时**：

```
1. 在 decisions_log.md 中记录修改提案
2. 联系该接口的 Owner 进行 review
3. Owner 确认后，方可修改
4. 修改完成后，在 decisions_log.md 中记录决策
```

---

## 五、版本与变更管理

### 5.1 契约文档版本规则

| 契约类型 | 版本格式 | 变更触发条件 |
|---------|---------|-------------|
| DATA_CONTRACT | v1.0, v1.1, v2.0 | 列定义变更 |
| API_CONTRACT | v1.0, v1.1, v2.0 | 端点/响应格式变更 |
| TYPE_CONTRACT | v1.0, v1.1, v2.0 | 类型定义变更 |
| RISK_CONFIG_OWNER | v1.0 | Owner变更时更新 |
| EVENTS_CONTRACT | v1.0, v1.1 | 事件类型变更 |

**重大变更**（v2.0）：删除列/端点/类型，修改数据类型  
**轻微变更**（v1.x）：新增列/端点/字段

### 5.2 变更通知流程

```
Owner修改接口
    ↓
在 decisions_log.md 中记录变更内容
    ↓
通过工作群通知所有相关方（参考 RACI 矩阵）
    ↓
相关方在 24小时内 确认影响
    ↓
更新对应 CONTRACT 文档版本号
```

---

## 六、待完成项

| 优先级 | 任务 | Owner | 截止日期 | 状态 |
|--------|------|-------|---------|------|
| P0 | 创建 `shared/DATA_CONTRACT.md` | YIYI | 2026-05-02 | ❌ 待创建 |
| P0 | 创建 `shared/API_CONTRACT.md` | deep | 2026-05-02 | ❌ 待创建 |
| P0 | 创建 `shared/TYPE_CONTRACT.md` 并对齐TS↔Python | deep+Lucy | 2026-05-03 | ❌ 待创建 |
| P0 | 声明 `risk_rules.yaml` Owner规则 | deep | 2026-05-02 | ❌ 待创建 |
| P1 | 创建 `shared/EVENTS_CONTRACT.md` | deep | 2026-05-05 | ❌ 待创建 |
| P1 | 修复已知类型不一致（见3.4节） | deep+Lucy | 2026-05-05 | ❌ 待修复 |
| P2 | 实现 PaperBridge 事件总线 | deep | Phase 3 | ❌ 未开始 |

---

## 七、文档目录结构（目标状态）

```
D:\futures_v6\
├── shared\                          # ⭐ 接口契约中心
│   ├── INTERFACE_GOVERNANCE.md      # 本文档
│   ├── DATA_CONTRACT.md              # CSV数据格式契约
│   ├── API_CONTRACT.md               # API端点契约
│   ├── TYPE_CONTRACT.md              # 跨语言类型契约
│   ├── RISK_CONFIG_OWNER.md         # 风控配置所有权
│   └── EVENTS_CONTRACT.md           # 事件总线契约
│
├── modules\                          # 各模块文档
│   ├── backend\
│   ├── frontend\
│   ├── factors\
│   └── engineering\
│
├── docs\                             # 治理层文档
│   ├── GOVERNANCE.md
│   └── decisions_log.md
│
└── 系统架构\                          # 技术层文档
    └── 技术架构文档_V6.0.docx
```

---

## 八、联调触发场景速查表

| 场景 | 先检查 | 需通知 | 契约依据 |
|------|--------|--------|---------|
| 修改CSV列 | DATA_CONTRACT | YIYI+deep+Lucy | 列名/类型/顺序 |
| 新增API端点 | API_CONTRACT | Lucy | 端点+响应格式 |
| 修改risk_rules阈值 | RISK_CONFIG_OWNER | Lucy | 配置字段 |
| 前端新增类型 | TYPE_CONTRACT | deep | TS↔Python对齐 |
| 修改数据库表结构 | DATA_CONTRACT | YIYI+deep | PIT表定义 |
| 新增定时任务 | EVENTS_CONTRACT | 全部相关方 | 任务+调度时间 |

---

*本文档为初始版本，后续根据实际联调案例持续更新。*
*最后更新：2026-05-01 by 项目经理*
