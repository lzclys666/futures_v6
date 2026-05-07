# 事件接口契约 EVENTS_CONTRACT v1.1

> **版本**: v1.1
> **日期**: 2026-05-06
> **状态**: Phase 3 核心已实现，文档已更新
> **维护人**: deep / 程序员mimo

---

## 一、文档目的

本文档定义 **PaperBridge 事件总线** 的事件类型、数据格式、触发条件和订阅关系。事件总线是进程间/模块间通信的核心机制，用于解耦宏观信号引擎、VNpy 策略和风控引擎。

---

## 二、事件总线架构

### 2.1 技术选型

| 方案 | 状态 | 说明 |
|------|------|------|
| **FastAPI WebSocket** | ✅ 已实现 | `/ws/signal` + `/ws/risk` 分端点推送 |
| **CSV 文件轮询** | ✅ 已实现 | `macro_engine/output/*.csv`，VNpy 策略读取 |
| **进程间信号** | ⚠️ 未实现 | Unix domain socket / named pipe |
| **Redis Pub/Sub** | ❌ 不采用 | 过度设计 |

### 2.2 当前数据流（已实现）

```
macro_scoring_engine.py
    ↓ [CSV 文件] / ↓ [SignalBridge /ws/signal]
VNpy 策略（macro_demo_strategy.py）
    ↓ [CTP 接口]
VNpy Gateway
```

**现状**：VNpy 策略可通过两种方式获取信号：
- CSV 轮询（兼容模式）
- SignalBridge WebSocket `/ws/signal` 推送（Phase 3 已实现）

### 2.3 风控数据流（已实现）

```
risk.py
    ↓ risk_status_update [WebSocket /ws/risk 每5秒广播]
前端 / VNpy 策略
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
**传输通道**：CSV 文件（兼容）/ WebSocket `/ws/signal`（Phase 3 ✅ 已实现）

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

**触发方**：`core/risk/risk.py`（deep）
**接收方**：VNpy 策略 / 前端
**传输通道**：WebSocket `/ws/risk`（Phase 3 ✅ 已实现）

---

### 3.5 signal_update — SignalBridge 信号推送事件（新增）

**触发时机**：SignalBridge 检测到 CSV 信号文件变化时，通过 `/ws/signal` 推送

**数据格式**：
```json
{
  "type": "signal_update",
  "data": {
    "symbol": "RU",
    "direction": "LONG",
    "compositeScore": 0.45,
    "updatedAt": "2026-05-06T14:30:00+08:00"
  }
}
```

**触发方**：`core/signal_bridge.py`（SignalBridge）
**接收方**：VNpy 策略 / 前端
**传输通道**：WebSocket `/ws/signal`

---

### 3.6 risk_status_update — 风控状态广播事件（新增）

**触发时机**：`/ws/risk` 端点每 5 秒定时广播

**数据格式**：
```json
{
  "type": "risk_status_update",
  "data": {
    "overallStatus": "PASS",
    "rules": [
      {
        "ruleId": "R1",
        "ruleName": "单品种最大持仓",
        "status": "PASS",
        "currentValue": 5,
        "thresholdValue": 10
      }
    ],
    "updatedAt": "2026-05-06T16:00:00+08:00"
  }
}
```

**触发方**：`core/risk/risk.py`
**接收方**：前端 / VNpy 策略
**传输通道**：WebSocket `/ws/risk`

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
| **PaperBridge 加载到 FastAPI** | ✅ | `app.py` 已挂载 |
| **/api/risk/precheck** | ✅ | 风控预检接口 |
| **WebSocket /ws/signal** | ✅ | SignalBridge CSV→WS 推送 |
| **WebSocket /ws/risk** | ✅ | 风控状态每5秒广播 |
| **成交回报推送** | ❌ | Phase 4 |

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
| signal_updated | macro_scoring_engine | VNpy 策略 | P0 | CSV 轮询 ✅ / WS `/ws/signal` ✅ |
| signal_update | SignalBridge | VNpy 策略 / 前端 | P0 | WS `/ws/signal` ✅ |
| order_filled | VNpy Gateway | FastAPI | P0 | 内存模拟 ✅ |
| risk_triggered | risk.py | VNpy 策略 | P0 | WS `/ws/risk` ✅ |
| risk_status_update | risk.py | 前端 / VNpy 策略 | P0 | WS `/ws/risk` ✅ 每5秒广播 |
| circuit_breaker_triggered | risk.py | VNpy 策略 + 前端 | P1 | 规则已定义，推送待接入 |

---

## 六、WebSocket 接口（Phase 3 ✅ 已实现）

### 6.1 连接端点

| 端点 | 用途 | 状态 |
|------|------|------|
| `WS /ws/signal` | SignalBridge 信号推送 | ✅ 已实现 |
| `WS /ws/risk` | 风控状态广播（每5秒） | ✅ 已实现 |

### 6.2 认证

```
Header: X-Session-Token: <token>
```

### 6.3 /ws/signal 消息格式

**服务端推送**（CSV 信号变化时触发）：
```json
{
  "type": "signal_update",
  "data": {
    "symbol": "RU",
    "direction": "LONG",
    "compositeScore": 0.45,
    "updatedAt": "2026-05-06T14:30:00+08:00"
  }
}
```

### 6.4 /ws/risk 消息格式

**服务端广播**（每 5 秒）：
```json
{
  "type": "risk_status_update",
  "data": {
    "overallStatus": "PASS",
    "rules": [
      {
        "ruleId": "R1",
        "ruleName": "单品种最大持仓",
        "status": "PASS",
        "currentValue": 5,
        "thresholdValue": 10
      }
    ],
    "updatedAt": "2026-05-06T16:00:00+08:00"
  }
}
```

### 6.5 客户端命令

| 命令 | 响应 | 说明 |
|------|------|------|
| `ping` | `pong` | 心跳保活 |
| `get_status` | 最新状态快照 | 获取当前信号/风控状态 |

---

## 七、Phase 3 实施计划

### 阶段一：WebSocket 基础设施（deep）
- [x] FastAPI 添加 `/ws/signal` + `/ws/risk` 端点
- [x] Session 管理（Token 验证）
- [x] 订阅/取消订阅逻辑

### 阶段二：事件接入（deep）
- [x] risk.py → `/ws/risk` 推送（每5秒广播）
- [ ] VNpy Gateway → order_filled 推送
- [x] 前端 RuleSimulatorPage WebSocket 订阅

### 阶段三：信号实时推送（YIYI + deep）
- [x] SignalBridge → `/ws/signal` 推送（CSV watch → WS）
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

*本文档随 Phase 实施持续更新。*
*v1.0 (2026-05-03) — 初始版本 by deep*
*v1.1 (2026-05-06) — Phase 3 状态更新，补充 /ws/signal + /ws/risk 端点定义 by 程序员mimo*
