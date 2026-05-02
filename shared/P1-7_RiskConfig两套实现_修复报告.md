# P1-7 RiskConfig 前后端契约对齐 — 最终修复报告 v2

## 问题根因

1. **命名不对齐**：后端 `RiskRuleId` type 和 simulate/stress-test 端点硬编码返回的 ruleId 与前端 `RULE_META` key 不一致 → `savedRules.find()` 永远匹配不上 → 用户配置无法生效
2. **语义错配**：后端代码里规则编号和风控手册定义不一致（如"可用资金不足"用 R4 而非 R9，"亏损超10%"用 R8 而非 R2）

## 修复内容

### 修改文件：`D:\futures_v6\api\routes\risk.py`

#### 1. RiskRuleId type — 去掉后端别名，只保留前端名
```python
RiskRuleId = Literal[
    'R1_SINGLE_SYMBOL', 'R2_DAILY_LOSS', 'R3_PRICE_LIMIT',
    'R4_TOTAL_MARGIN', 'R5_VOLATILITY', 'R6_LIQUIDITY',
    'R7_CONSECUTIVE_LOSS', 'R8_TRADING_HOURS', 'R9_CAPITAL_SUFFICIENCY',
    'R10_MACRO_CIRCUIT_BREAKER', 'R11_DISPOSITION_EFFECT',
]
```

#### 2. simulate 端点 — 规则语义修正

| 注释 | 旧 ruleId | 新 ruleId | 修正理由（按风控手册V6.1） |
|------|----------|----------|-------------------------|
| 交易时段检查 | `R8_DRAWDOWN` | `R8_TRADING_HOURS` | R8=交易时间 |
| 可用资金不足 | `R4_MARGIN_RATIO` | **`R9_CAPITAL_SUFFICIENCY`** | R9=资金充足性，非R4总保证金 |
| 单品种持仓超限 | `R1_SINGLE_SYMBOL` | `R1_SINGLE_SYMBOL` | ✅ 不变 |
| 总持仓比例超80% | `R4_TOTAL_MARGIN` | `R4_TOTAL_MARGIN` | ✅ 总保证金占用=持仓比例 |
| 涨跌停检查 | `R3_TOTAL_POSITION` | `R3_PRICE_LIMIT` | R3=涨跌停 |
| 宏观熔断 | `R10_CIRCUIT_BREAKER` | `R10_MACRO_CIRCUIT_BREAKER` | R10=宏观熔断 |

**关键语义修正**：`可用资金不足` 从 R4_TOTAL_MARGIN → R9_CAPITAL_SUFFICIENCY。风控手册明确定义 R4=总保证金占用上限（仓位比例），R9=资金充足性（可用资金是否足够）。

#### 3. stress-test 端点 — 规则语义修正

| 条件 | 旧 ruleId | 新 ruleId | 修正理由 |
|------|----------|----------|---------|
| 亏损超10% | `R8_TRADING_HOURS` | **`R2_DAILY_LOSS`** | R2=单日亏损，非R8交易时段 |
| 保证金变化<-5000 | `R4_TOTAL_MARGIN` | **`R9_CAPITAL_SUFFICIENCY`** | 保证金减少→资金充足性风险 |

#### 4. 注释同步修正
所有 simulate 端点的中文注释从"规则1/2/3/4/5/6"改为与 ruleId 对应的"R8/R9/R1/R4/R3/R10"

### 前端无需修改
- `config.tsx` RULE_META — 11条 key 不变
- `riskStore.ts` checkOrderWithRules() — ruleId 引用不变
- `types/risk.ts` — 类型定义不变

## 验证
- 旧名残留检查：0 结果 ✅
- `npm run build` → ✓ built in 1.81s ✅

## 风控手册 ↔ API ruleId 完整映射

| R# | API ruleId | 手册V6.1语义 | simulate触发条件 |
|----|-----------|-------------|-----------------|
| R1 | `R1_SINGLE_SYMBOL` | 单品种最大持仓 | 单品种持仓超20手 |
| R2 | `R2_DAILY_LOSS` | 单日最大亏损 | stress-test亏损超10% |
| R3 | `R3_PRICE_LIMIT` | 涨跌停限制 | 委托价超±8% |
| R4 | `R4_TOTAL_MARGIN` | 总保证金占用上限 | 总持仓比例超80% |
| R5 | `R5_VOLATILITY` | 波动率异常 | stress-test波动超5% |
| R6 | `R6_LIQUIDITY` | 流动性检查 | — |
| R7 | `R7_CONSECUTIVE_LOSS` | 连续亏损 | — |
| R8 | `R8_TRADING_HOURS` | 交易时间检查 | 非交易时段下单 |
| R9 | `R9_CAPITAL_SUFFICIENCY` | 资金充足性 | 可用资金不足/stress-test保证金减少 |
| R10 | `R10_MACRO_CIRCUIT_BREAKER` | 宏观熔断 | 宏观打分过低/过高 |
| R11 | `R11_DISPOSITION_EFFECT` | 处置效应监控 | — |

## 遗留问题
1. **YAML R3/R4/R8/R9 语义与 API ruleId 不完全对应**：YAML 里 R3 是"总持仓"、R4 是"保证金比例"、R9 是"品种集中度"，与 API ruleId 的涨跌停/总保证金/资金充足性不一致。YAML 是后端自用配置，暂不冲突但长期需统一
2. **R12 撤单限制**：YAML 有定义但前后端 RiskRuleId 均未纳入
3. **R6/R7/R11 无 simulate 触发逻辑**：流动性/连续亏损/处置效应目前无检查代码
