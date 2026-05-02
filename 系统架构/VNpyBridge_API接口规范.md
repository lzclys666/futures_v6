# VNpyBridge API 接口规范 V1.0

> 文档版本: 1.0
> 更新时间: 2026-04-26
> 目标读者: 前端开发（Lucy）

---

## 概述

VNpyBridge 是期货交易系统的核心桥接层，提供:
- VNpy 引擎生命周期管理
- 策略管理（添加/初始化/启动/停止）
- 持仓/账户/订单/成交数据查询
- WebSocket 实时推送
- RESTful API 接口

**服务地址:**
- REST API: http://localhost:8000/api/
- WebSocket: ws://localhost:8000/ws/trading 或 /ws/vnpy

---

## REST API

### 1. 交易相关

#### 1.1 获取持仓列表
GET /api/trading/positions

响应: { date, total_equity, available_cash, positions[], total_position_pct, daily_pnl, daily_return }

#### 1.2 获取订单列表
GET /api/trading/orders

#### 1.3 获取成交列表
GET /api/trading/trades

#### 1.4 获取账户信息
GET /api/trading/account

#### 1.5 下单
POST /api/trading/order
Body: { vt_symbol, direction, offset, price, volume }
返回: { vt_orderid }

#### 1.6 撤单
DELETE /api/trading/order/{vt_orderid}

---

## WebSocket API

### 方式一: /ws/trading (基础)
- 客户端发送: ping / status / positions
- 服务端推送: position, order, trade, account, risk_event, log

### 方式二: /ws/vnpy (推荐，结构化)
- subscribe / unsubscribe: 订阅事件类型
- ping / get_status / get_positions / get_account / get_strategies
- start_strategy / stop_strategy

---

## 前端对接建议

### 持仓看板 (Lucy Phase 2)
- /api/trading/positions 初始加载
- /ws/vnpy 订阅 position + account 实时更新

### 风控面板 (远期 Phase 4/5)
- /api/trading/risk-status 状态
- /ws/vnpy 订阅 risk_event 预警

---

Swagger: http://localhost:8000/docs
