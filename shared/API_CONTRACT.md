# API契约 — FastAPI端点定义

> **版本**: v1.0  
> **生效日期**: 2026-05-01  
> **Owner**: deep  
> **状态**: 初始版本

---

## 一、宏观信号类端点

### GET /api/macro/signal/{symbol}

获取指定品种的宏观信号。

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| symbol | string | 品种代码（RU/CU/AU/AG） |

**响应** `200 OK`：
```json
{
  "success": true,
  "data": {
    "symbol": "RU",
    "compositeScore": 0.45,
    "direction": "LONG",
    "updatedAt": "2026-05-01T14:30:02+08:00",
    "factors": [
      {
        "factorCode": "RU_TS_ROLL_YIELD",
        "factorName": "RU期限利差",
        "contributionPolarity": "positive",
        "normalizedScore": 0.23,
        "weight": 0.35,
        "contribution": 0.08,
        "factorIc": -0.12
      }
    ]
  },
  "message": "ok"
}
```

**响应字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | ✅ | 品种代码 |
| compositeScore | float | ✅ | 综合得分，-1~1 |
| direction | string | ✅ | LONG/NEUTRAL/SHORT |
| updatedAt | string | ✅ | ISO8601时间 |
| factors | FactorDetail[] | ✅ | 因子明细数组 |

---

### GET /api/macro/signal/all

获取所有品种的宏观信号。

**响应** `200 OK`：
```json
{
  "success": true,
  "data": [
    { "symbol": "RU", "compositeScore": 0.45, "direction": "LONG", ... },
    { "symbol": "CU", "compositeScore": -0.32, "direction": "SHORT", ... }
  ],
  "message": "ok"
}
```

---

### GET /api/macro/score-history/{symbol}

获取品种历史打分。

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| symbol | string | 品种代码 |

**查询参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| days | int | 30 | 历史天数 |

**响应** `200 OK`：
```json
{
  "success": true,
  "data": [
    { "date": "2026-05-01", "score": 0.45, "direction": "LONG" },
    { "date": "2026-04-30", "score": 0.38, "direction": "LONG" }
  ],
  "message": "ok"
}
```

**注意**：当前无历史数据返回空数组（待 YIYI 回填）

---

### GET /api/macro/factor/{symbol}

获取品种因子明细。

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| symbol | string | 品种代码 |

**响应** `200 OK`：
```json
{
  "success": true,
  "data": [
    {
      "factorCode": "RU_TS_ROLL_YIELD",
      "factorName": "RU期限利差",
      "contributionPolarity": "positive",
      "normalizedScore": 0.23,
      "weight": 0.35,
      "contribution": 0.08,
      "factorIc": -0.12
    }
  ],
  "message": "ok"
}
```

---

## 二、交易类端点

### GET /api/vnpy/status

VNpy网关状态。

**响应** `200 OK`：
```json
{
  "success": true,
  "data": {
    "connected": true,
    "gateway": "CTP",
    "gatewayStatus": "connected",
    "tradingDay": "2026-05-01",
    "marketSession": "open",
    "sessionEndTime": "15:00:00"
  },
  "message": "ok"
}
```

---

### GET /api/vnpy/positions

持仓列表。

**响应** `200 OK`：
```json
{
  "success": true,
  "data": [
    {
      "vtSymbol": "RB2505",
      "symbol": "RB",
      "exchange": "SHFE",
      "direction": "long",
      "volume": 10,
      "avgPrice": 3500,
      "lastPrice": 3600,
      "unrealizedPnl": 10000,
      "realizedPnl": 5000,
      "margin": 35000,
      "openTime": "2026-04-25 09:30:00"
    }
  ],
  "message": "ok"
}
```

---

### POST /api/trading/order

下单。

**请求体**：
```json
{
  "symbol": "RB",
  "exchange": "SHFE",
  "direction": "buy",
  "offset": "OPEN",
  "volume": 5,
  "price": 3550,
  "orderType": "limit"
}
```

**响应** `200 OK`：
```json
{
  "success": true,
  "data": { "vtOrderId": "ord_001" },
  "message": "ok"
}
```

---

### DELETE /api/trading/order/{vt_orderid}

撤单。

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| vt_orderid | string | 订单ID |

**响应** `200 OK`：
```json
{
  "success": true,
  "data": { "success": true },
  "message": "ok"
}
```

---

## 三、风控类端点

### GET /api/trading/risk-status

风控状态总览。

**响应** `200 OK`：
```json
{
  "success": true,
  "data": {
    "overallRiskLevel": "NORMAL",
    "marginUtilization": 0.15,
    "dailyPnL": 12500,
    "openPositionCount": 3
  },
  "message": "ok"
}
```

---

### GET /api/trading/risk-rules

风控规则列表。

**响应** `200 OK`：
```json
{
  "success": true,
  "data": [
    {
      "ruleId": "R1",
      "ruleName": "仓位限制",
      "layer": 2,
      "status": "ENABLED",
      "config": { "maxPositionRatio": 0.3 }
    }
  ],
  "message": "ok"
}
```

**注意**：`layer` 字段类型为 `int`（1/2/3），前端 TypeScript 定义为 `layerId: string`，需对齐（见 TYPE_CONTRACT）。

---

## 四、系统类端点

### GET /health

健康检查。

**响应** `200 OK`：
```json
{
  "status": "healthy",
  "version": "d_engine_v1.0"
}
```

---

## 五、版本变更规则

### 轻微变更（v1.x）— 无需投票
- 新增可选查询参数
- 新增响应字段（不影响现有解析）

### 重大变更（v2.0）— 需要L2技术议会表决
- 删除端点
- 修改端点路径
- 修改请求参数类型
- 删除或修改响应必填字段

### 升级版本号时的操作
1. 更新本文档版本号
2. 在 `decisions_log.md` 中记录变更
3. 通知 Lucy（前端调用方）

---

## 六、前端调用方（Owner: Lucy）

| 页面 | 调用的端点 |
|------|-----------|
| 信号页面 | `/api/macro/signal/{symbol}` |
| 持仓页面 | `/api/vnpy/positions` |
| 风控配置 | `/api/trading/risk-rules` |
| 下单面板 | `POST /api/trading/order` |

---

## 七、版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-05-01 | 初始版本，17个端点定义 |
