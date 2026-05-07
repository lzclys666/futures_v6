# 宏观熔断方案设计文档

**版本**: v1.0  
**日期**: 2026-05-06  
**作者**: 因子分析师YIYI  
**状态**: 初始设计

---

## 1. 背景与目标

### 1.1 问题描述

现有风控规则 R10 仅针对单品种的仓位和亏损进行保护，缺乏**宏观层面的整体风控**。当市场出现系统性风险事件（如黑天鹅、政策突变、流动性危机）时，宏观信号会同时影响所有品种，单品种级别的风控无法有效应对。

### 1.2 设计目标

- 基于宏观信号（compositeScore）实现跨品种的系统性风险熔断
- 渐进式响应：警告 → 限制 → 熔断，避免过度反应
- 与现有 R10 规则形成互补，不冲突、不重叠

---

## 2. 触发条件

### 2.1 三级响应机制

| 级别 | 状态 | 条件 | 动作 |
|------|------|------|------|
| **L1 - 警告** | `WARNING` | compositeScore 绝对值 0.4 ~ 0.5 | 记录日志、前端黄色标识 |
| **L2 - 限制** | `LIMITED` | compositeScore 绝对值 0.5 ~ 0.7 | 新开仓位减半、前端橙色标识 |
| **L3 - 熔断** | `CIRCUIT_BREAK` | compositeScore 绝对值 > 0.7 | 禁止新开仓、前端红色标识 |

### 2.2 全局熔断

当系统中活跃品种的 compositeScore 出现同向极端时，触发全局熔断：

```
定义：N_active = 当前活跃品种总数
条件：
  - 多头熔断：count(score > threshold) >= N_active * 0.75
  - 空头熔断：count(score < -threshold) >= N_active * 0.75

示例（4个活跃品种，阈值0.5）：
  - 3个品种 score < -0.5 → 触发全局空头熔断
  - 3个品种 score > 0.5  → 触发全局多头熔断
```

### 2.3 板块熔断

当同一板块内多个品种同时出现极端信号时，触发板块级熔断：

```
定义：板块内品种集合（如：黑色系 = RB + HC + I + J + JM）
条件：板块内 count(|score| > threshold) >= 板块熔断阈值

示例（黑色系板块，阈值0.5，板块熔断数量=3）：
  - RB score=0.6, HC score=0.7, I score=0.55 → 触发黑色系板块熔断
```

**板块划分**：
| 板块 | 品种 |
|------|------|
| 贵金属 | AU, AG |
| 有色 | CU, AL, ZN, NI, PB |
| 黑色 | RB, HC, I, J, JM |
| 能源 | FU, BU, SC |
| 化工 | TA, EG, PP, NR |
| 油脂油料 | M, Y, P |
| 橡胶 | RU, NR |

---

## 3. 解除条件

### 3.1 自动解除

```
条件（必须同时满足）：
  1. 持续时间 >= 最短持续时间（默认30分钟）
  2. 所有触发品种的 |compositeScore| < 解除阈值（默认0.3）

状态转换：
  CIRCUIT_BREAK → LIMITED → WARNING → NORMAL
  （逐级降级，不可跳级）
```

### 3.2 手动解除

```
操作：通过风控面板的"手动解除"按钮
权限：需要风控主管权限
记录：解除原因、操作人、时间戳写入审计日志
```

### 3.3 解除验证

自动解除时需验证：
- 信号稳定性：解除前10分钟内，score 波动 < 0.1
- 非单点恢复：不是单个品种拉低均值，而是整体回落

---

## 4. 参数配置表（三档）

| 参数 | 保守 | 中等（默认） | 激进 | 说明 |
|------|------|-------------|------|------|
| **全局熔断阈值** | 0.5 | 0.7 | 0.9 | 触发熔断的 score 绝对值下限 |
| **板块熔断数量** | 2 | 3 | 4 | 板块内触发熔断的最少品种数 |
| **最短持续时间** | 60min | 30min | 15min | 熔断解除的最短等待时间 |
| **解除阈值** | 0.2 | 0.3 | 0.4 | 自动解除的 score 绝对值上限 |
| **警告阈值** | 0.3 | 0.4 | 0.5 | L1 警告的触发下限 |
| **限制阈值** | 0.4 | 0.5 | 0.6 | L2 限制的触发下限 |
| **仓位削减比例** | 75% | 50% | 25% | L2 限制时新开仓的削减幅度 |
| **信号波动容忍** | 0.05 | 0.10 | 0.15 | 解除验证时的波动容忍 |

**档位选择建议**：
- 保守：适合资金量大、风险厌恶型策略
- 中等：适合一般交易场景（推荐默认）
- 激进：适合高波动品种、短线策略

---

## 5. 集成点

### 5.1 数据来源

```
接口：GET /api/macro/signal/all
字段：compositeScore（各品种的宏观综合评分，范围 [-1, 1]）

数据流：
  宏观信号服务 → /api/macro/signal/all → 熔断检查模块 → 风控引擎
```

### 5.2 执行位置

**现有流程**：
```
订单提交 → R1~R9 规则检查 → R10 仓位/亏损检查 → 执行
```

**新增流程**：
```
订单提交 → R1~R9 规则检查 → R10 仓位/亏损检查 → R11 宏观熔断检查 → 执行
```

**关键**：宏观熔断作为 **R11** 独立规则，不修改现有 R10 逻辑。

### 5.3 前端展示

风控面板新增"宏观熔断状态"卡片：
- 当前状态：NORMAL / WARNING / LIMITED / CIRCUIT_BREAK
- 触发原因：全局/板块/品种级别
- 持续时间：已持续 XX 分钟
- 触发品种列表及对应 score
- 手动解除按钮（需权限）

### 5.4 与现有 R10 规则的差异

| 维度 | R10 现有规则 | R11 宏观熔断 |
|------|-------------|-------------|
| **保护对象** | 单品种仓位和亏损 | 系统性宏观风险 |
| **触发依据** | 仓位比例、累计亏损 | compositeScore 宏观信号 |
| **作用范围** | 单品种 | 跨品种、全局 |
| **响应方式** | 拒绝订单 | 渐进式（警告→限制→熔断） |
| **解除机制** | 仓位降低后自动解除 | 信号回归中性 + 最短持续时间 |
| **数据源** | 内部持仓和PnL | 外部宏观信号API |
| **设计哲学** | 事后保护（已亏损才触发） | 事前预防（信号极端就触发） |

**互补关系**：
- R10 处理"已经发生的亏损"——止损
- R11 处理"即将发生的系统风险"——预防
- 两者独立运行，不互相覆盖

---

## 6. 实现方案

### 6.1 需要修改的文件清单

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `src/risk/macroCircuitBreaker.ts` | **新增** - 宏观熔断核心逻辑 | P0 |
| `src/risk/riskEngine.ts` | 新增 R11 规则调用入口 | P0 |
| `src/risk/riskConfig.ts` | 新增熔断参数配置 | P0 |
| `src/api/macroSignal.ts` | 新增 `/api/macro/signal/all` 调用封装 | P1 |
| `src/components/RiskPanel.vue` | 前端熔断状态展示 | P1 |
| `src/store/riskStore.ts` | 熔断状态管理 | P2 |
| `docs/risk-rules.md` | 更新风控规则文档 | P2 |

### 6.2 核心数据结构

```typescript
// 熔断状态枚举
enum CircuitBreakerLevel {
  NORMAL = 'NORMAL',
  WARNING = 'WARNING',
  LIMITED = 'LIMITED',
  CIRCUIT_BREAK = 'CIRCUIT_BREAK'
}

// 熔断触发记录
interface CircuitBreakerTrigger {
  id: string;
  level: CircuitBreakerLevel;
  triggerType: 'global' | 'sector' | 'symbol';
  triggerReason: string;
  triggerSymbols: string[];        // 触发的品种列表
  triggerScores: Map<string, number>; // 品种对应的 score
  triggeredAt: number;             // 触发时间戳
  resolvedAt: number | null;       // 解除时间戳
  resolvedBy: 'auto' | 'manual';  // 解除方式
  resolvedReason: string;
}

// 熔断配置
interface CircuitBreakerConfig {
  enabled: boolean;
  mode: 'conservative' | 'moderate' | 'aggressive';
  globalThreshold: number;         // 全局熔断阈值
  sectorThreshold: number;         // 板块熔断阈值
  sectorMinCount: number;          // 板块熔断最少品种数
  minDurationMs: number;           // 最短持续时间（毫秒）
  resolveThreshold: number;        // 解除阈值
  warningThreshold: number;        // 警告阈值
  limitThreshold: number;          // 限制阈值
  positionCutRatio: number;        // 仓位削减比例
  signalVolatilityTolerance: number; // 信号波动容忍
}
```

### 6.3 关键逻辑伪代码

```typescript
// === 宏观熔断检查主函数 ===
function checkMacroCircuitBreaker(order: Order): RiskCheckResult {
  // 1. 获取最新宏观信号
  const signals = await fetchMacroSignals();
  
  // 2. 检查当前熔断状态
  const currentState = getBreakerState();
  
  // 3. 如果已熔断，检查是否可解除
  if (currentState.level === CIRCUIT_BREAK) {
    if (canResolve(currentState, signals)) {
      resolveBreaker(currentState, 'auto');
    } else {
      return reject('宏观熔断中，禁止新开仓');
    }
  }
  
  // 4. 评估当前信号
  const evaluation = evaluateSignals(signals);
  
  // 5. 渐进式响应
  switch (evaluation.level) {
    case CIRCUIT_BREAK:
      triggerBreaker(evaluation);
      return reject('宏观信号极端，触发熔断');
    case LIMITED:
      triggerLimit(evaluation);
      return partialReject(order, config.positionCutRatio);
    case WARNING:
      triggerWarning(evaluation);
      return allow();  // 允许但记录
    default:
      return allow();
  }
}

// === 信号评估 ===
function evaluateSignals(signals: MacroSignal[]): Evaluation {
  const scores = signals.map(s => s.compositeScore);
  
  // 全局熔断检查
  const extremePositive = scores.filter(s => s > config.globalThreshold).length;
  const extremeNegative = scores.filter(s => s < -config.globalThreshold).length;
  const totalActive = scores.length;
  
  if (extremePositive >= totalActive * 0.75 || 
      extremeNegative >= totalActive * 0.75) {
    return { level: CIRCUIT_BREAK, type: 'global', reason: '全局同向极端' };
  }
  
  // 板块熔断检查
  for (const sector of SECTORS) {
    const sectorScores = getSectorScores(signals, sector);
    const sectorExtreme = sectorScores.filter(s => 
      Math.abs(s) > config.sectorThreshold
    ).length;
    
    if (sectorExtreme >= config.sectorMinCount) {
      return { level: CIRCUIT_BREAK, type: 'sector', 
               reason: `${sector.name}板块熔断` };
    }
  }
  
  // 限制级别检查
  const maxScore = Math.max(...scores.map(Math.abs));
  if (maxScore > config.limitThreshold) {
    return { level: LIMITED, type: 'symbol', reason: '个别品种信号极端' };
  }
  
  // 警告级别检查
  if (maxScore > config.warningThreshold) {
    return { level: WARNING, type: 'symbol', reason: '信号偏强' };
  }
  
  return { level: NORMAL };
}

// === 解除检查 ===
function canResolve(state: BreakerState, signals: MacroSignal[]): boolean {
  // 条件1：最短持续时间
  const elapsed = Date.now() - state.triggeredAt;
  if (elapsed < config.minDurationMs) return false;
  
  // 条件2：信号回归中性
  const scores = signals.map(s => s.compositeScore);
  const allNeutral = scores.every(s => Math.abs(s) < config.resolveThreshold);
  if (!allNeutral) return false;
  
  // 条件3：信号稳定性（波动小）
  const recentHistory = getRecentScores(10 * 60 * 1000); // 最近10分钟
  const isStable = recentHistory.every(h => 
    Math.abs(h.max - h.min) < config.signalVolatilityTolerance
  );
  
  return isStable;
}
```

### 6.4 集成到现有系统

```typescript
// src/risk/riskEngine.ts - 新增 R11 规则

async function checkAllRules(order: Order): Promise<RiskCheckResult> {
  // 现有规则 R1~R10
  const r1toR9 = await checkBasicRules(order);
  if (!r1toR9.passed) return r1toR9;
  
  const r10 = await checkPositionAndLoss(order);
  if (!r10.passed) return r10;
  
  // 新增 R11 宏观熔断
  const r11 = await checkMacroCircuitBreaker(order);
  if (!r11.passed) return r11;
  
  return { passed: true };
}
```

---

## 7. 监控与告警

### 7.1 日志记录

每次状态变更记录：
- 时间戳
- 变更前/后状态
- 触发原因
- 涉及品种和 score
- 操作人（自动/手动）

### 7.2 告警通知

| 事件 | 通知方式 | 延迟 |
|------|---------|------|
| 进入 WARNING | 日志 + 风控面板 | 实时 |
| 进入 LIMITED | 日志 + 风控面板 + 消息推送 | 实时 |
| 进入 CIRCUIT_BREAK | 日志 + 风控面板 + 消息推送 + 电话 | 实时 |
| 自动解除 | 日志 + 消息推送 | 实时 |
| 手动解除 | 日志 + 消息推送 + 审计 | 实时 |

---

## 8. 测试计划

### 8.1 单元测试

- [ ] 全局熔断触发逻辑
- [ ] 板块熔断触发逻辑
- [ ] 渐进式响应（警告→限制→熔断）
- [ ] 自动解除条件判断
- [ ] 参数配置切换（三档）

### 8.2 集成测试

- [ ] 与 R10 规则的兼容性
- [ ] API 数据获取异常处理
- [ ] 前端状态展示正确性
- [ ] 手动解除权限控制

### 8.3 压力测试

- [ ] 高频信号更新下的性能
- [ ] 多品种同时触发的处理
- [ ] API 超时的降级策略

---

## 9. 降级策略

当宏观信号 API 不可用时：

```
降级方案：
  1. 使用最近一次有效信号（缓存15分钟）
  2. 缓存超过15分钟 → 自动降级为"仅R10模式"
  3. 降级时前端显示"宏观信号离线"标识
  4. API 恢复后自动退出降级模式
```

---

## 10. 时间线

| 阶段 | 内容 | 预计工期 |
|------|------|---------|
| Phase 1 | 核心逻辑开发（macroCircuitBreaker.ts） | 2天 |
| Phase 2 | 集成到风险引擎 + API 封装 | 1天 |
| Phase 3 | 前端展示 | 1天 |
| Phase 4 | 测试 + 文档 | 1天 |
| **总计** | | **5天** |

---

## 附录 A：术语表

| 术语 | 定义 |
|------|------|
| compositeScore | 宏观综合评分，范围 [-1, 1]，正值看多，负值看空 |
| 全局熔断 | 所有活跃品种同向极端时触发的最高级别熔断 |
| 板块熔断 | 同一板块内多品种同向极端时触发的熔断 |
| 渐进式响应 | 警告→限制→熔断的逐级升级机制 |

## 附录 B：参考

- 现有 R10 规则文档
- 宏观信号 API 文档 (`/api/macro/signal/all`)
- 风控引擎架构文档

---

**文档结束**
