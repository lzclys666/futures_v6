# 事件接口契约 EVENTS_CONTRACT v1.0

> **版本**: v1.0
> **日期**: 2026-05-03
> **状态**: 初始版本
> **维护人**: deep

---

## 一、文档目的

本文档定义 **PaperBridge 事件总线** 的事件类型、数据格式、触发条件和订阅关系。事件总线是进程间/模块间通信的核心机制，用于解耦宏观信号引擎、VNpy 策略和风控引擎。

---

## 二、事件总线架构

### 2.1 技术选型

| 方案 | 状态 | 说明 |
|------|------|------|
| **FastAPI WebSocket** | ✅ 规划中 | 主要推送通道（Phase 3 实现） |
| **CSV 文件轮询** | ✅ 已实现 | `macro_engine/output/*.csv`，VNpy 策略读取 |
| **进程间信号** | ⚠️ 未实现 | Unix domain socket / named pipe |
| **Redis Pub/Sub** | ❌ 不采用 | 过度设计 |

### 2.2 当前数据流（已实现）

```
macro_scoring_engine.py
    ↓ [CSV 文件]
VNpy 策略（macro_demo_strategy.py）
    ↓ [CTP 接口]
VNpy Gateway
```

**现状**：VNpy 策略通过轮询 CSV 文件获取宏观信号，不依赖实时事件推送。

### 2.3 目标数据流（Phase 3）

```
macro_scoring_engine
    ↓ signal_updated [WebSocket]
VNpy 策略
    ↓ order_filled [WebSocket]
FastAPI (PaperBridge)
    ↓ risk_triggered [WebSocket]
VNpy 策略（风控拦截）
```

---

## 三、事件类型定义

### 3.1 signal_updated — 宏观信号更新事件

**触发时机**：日终打分完成后（14:30 CST）或实时信号计算完成后

**数据格式**：
```json
{
  "event": "signal_updated",
  "timestamp": "2026-05-03T14:30:02+08:00",
  "data": {
    "symbol": "RU",
    "direction": "LONG",
    "compositeScore": 0.45,
    "factors": [
      {
        "factorCode": "RU_TS_ROLL_YIELD",
        "normalizedScore": 0.23,
        "contribution": 0.08
      }
    ],
    "engineVersion": "d_engine_v1.0"
  }
}
```

**触发方**：`macro_scoring_engine.py`（YIYI）
**接收方**：VNpy 策略（`macro_demo_strategy.py`）
**传输通道**：CSV 文件（当前）→ WebSocket（Phase 3）

---

### 3.2 order_filled — 订单成交事件

**触发时机**：VNpy Gateway 收到成交回报时

**数据格式**：
```json
{
  "event": "order_filled",
  "timestamp": "2026-05-03T21:05:12+08:00",
  "data": {
    "vtOrderId": "RU2506-LONG-001",
    "symbol": "RU2506",
    "direction": "long",
    "offset": "open",
    "volume": 5,
    "price": 15200.0,
    "filledVolume": 5,
    "filledPrice": 15195.0,
    "commission": 12.50
  }
}
```

**触发方**：VNpy Gateway（VNpy 核心）
**接收方**：FastAPI（PaperBridge，用于更新持仓和账户）
**传输通道**：VNpy CTP 接口（CTP 回报）→ FastAPI

---

### 3.3 risk_triggered — 风控触发事件

**触发时机**：任一风控规则触发（Layer 1 最严 / Layer 2 中等 / Layer 3 宽松）

**数据格式**：
```json
{
  "event": "risk_triggered",
  "timestamp": "2026-05-03T21:10:05+08:00",
  "data": {
    "ruleId": "R1",
    "ruleName": "单品种最大持仓",
    "layer": 2,
    "severity": "WARN",
    "symbol": "RU",
    "currentValue": 15,
    "thresholdValue": 10,
    "message": "RU持仓15手，超过单品种上限10手（L2-账户风险）",
    "action": "BLOCK"
  }
}
```

**触发方**：`core/risk/risk_engine.py`（deep）
**接收方**：VNpy 策略（`macro_demo_strategy.py`）
**传输通道**：WebSocket（Phase 3）

---

### 3.4 circuit_breaker_triggered — 熔断触发事件

**触发时机**：连续同向开仓达到熔断阈值（R10）

**数据格式**：
```json
{
  "event": "circuit_breaker_triggered",
  "timestamp": "2026-05-03T21:15:00+08:00",
  "data": {
    "ruleId": "R10",
    "ruleName": "熔断机制",
    "consecutiveSameDirection": 3,
    "threshold": 3,
    "triggeredAt": "2026-05-03T21:15:00+08:00",
    "action": "PAUSE",
    "autoResumeAt": null
  }
}
```

**触发方**：`core/risk/risk_engine.py`（deep）
**接收方**：VNpy 策略 + 前端（RuleSimulatorPage）
**传输通道**：WebSocket

---

## 四、PaperBridge 实现现状

### 4.1 类定义位置

```
D:\futures_v6\services\vnpy_bridge.py
```
- `class VNpyBridge`（生产版，连接真实 CTP）
- `class PaperBridge`（模拟版，Paper Trading 使用）

### 4.2 PaperBridge 当前功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 模拟账户初始化 | ✅ | balance = 1,000,000 |
| 订单模拟（开仓/平仓） | ✅ | 内存模拟，无真实成交 |
| 持仓管理 | ✅ | `_positions` 字典 |
| 风控规则加载 | ✅ | 从 `risk/rules/risk_rules.yaml` 加载 |
| **WebSocket 事件推送** | ❌ | Phase 3 实现 |
| **信号订阅** | ❌ | Phase 3 实现 |
| **成交回报推送** | ❌ | Phase 3 实现 |

### 4.3 PaperBridge 与 VNpyBridge 的关系

```
services/vnpy_bridge.py
    ├── class VNpyBridge  （生产连接 CTP）
    └── class PaperBridge （模拟模式，等效接口）
```

PaperBridge 和 VNpyBridge 实现**相同的接口**，切换方式：
```python
# 生产
bridge = VNpyBridge()

# 模拟（Paper Trading）
bridge = PaperBridge()
```

---

## 五、订阅关系矩阵

| 事件 | 触发方 | 订阅方 | 优先级 | 状态 |
|------|--------|--------|--------|------|
| signal_updated | macro_scoring_engine | VNpy 策略 | P0 | CSV 轮询 ✅ |
| order_filled | VNpy Gateway | FastAPI | P0 | 内存模拟 ✅ |
| risk_triggered | risk_engine | VNpy 策略 | P0 | ❌ Phase 3 |
| circuit_breaker_triggered | risk_engine | VNpy 策略 + 前端 | P1 | ❌ Phase 3 |

---

## 六、WebSocket 接口（Phase 3 目标）

### 6.1 连接端点

```
WS /ws/events
```

### 6.2 认证

```
Header: X-Session-Token: <token>
```

### 6.3 订阅消息格式

```json
{
  "action": "subscribe",
  "events": ["signal_updated", "risk_triggered"]
}
```

### 6.4 推送消息格式

```json
{
  "event": "risk_triggered",
  "timestamp": "2026-05-03T21:10:05+08:00",
  "data": { ... }
}
```

---

## 七、Phase 3 实施计划

### 阶段一：WebSocket 基础设施（deep）
- [ ] FastAPI 添加 `/ws/events` 端点
- [ ] Session 管理（Token 验证）
- [ ] 订阅/取消订阅逻辑

### 阶段二：事件接入（deep）
- [ ] risk_engine → WebSocket 推送
- [ ] VNpy Gateway → order_filled 推送
- [ ] 前端 RuleSimulatorPage WebSocket 订阅

### 阶段三：信号实时推送（YIYI + deep）
- [ ] macro_scoring_engine → signal_updated 推送
- [ ] VNpy 策略从 CSV 轮询切换到 WebSocket

---

## 八、错误处理

### 8.1 WebSocket 断连

- 客户端断连后，服务器保留 Session 状态 5 分钟
- 重连后发送 `session_resumed` 事件，包含断连期间错过的所有事件

### 8.2 事件顺序保证

- 每个事件携带递增 `sequence` 序号
- 客户端按序号排序，丢弃重复事件

### 8.3 事件积压

- 服务器最多缓存 1000 个事件（按需保留）
- 客户端重连后最多补发最近 100 个事件

---

*本文档为初始版本，随着 Phase 3 实施持续更新。*
*最后更新：2026-05-03 by 项目经理*
