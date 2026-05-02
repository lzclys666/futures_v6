# 前端 API 接口文档 v1.0

> 更新日期：2026-04-24
> 服务地址：http://127.0.0.1:8000
> 前端代理：/api → http://127.0.0.1:8000

---

## 接口清单

### 宏观信号（已验证 ✅）

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| GET | `/api/macro/signal/{symbol}` | 单品种信号（含因子明细） | ✅ 200 |
| GET | `/api/macro/signal/all` | 全品种信号列表 | ✅ 200 |
| GET | `/api/macro/factor/{symbol}` | 因子明细 | ✅ 200 |
| GET | `/api/macro/score-history/{symbol}?days=30` | 历史打分序列 | ✅ 200 |

### 交易与风控（已验证 ✅）

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| GET | `/api/trading/positions` | 当前持仓 | ✅ 200（Mock 数据） |
| GET | `/api/trading/risk-status` | 风控状态 | ✅ 200（Mock 数据） |
| GET | `/api/trading/orders` | 当日订单 | ✅ 200（空数组） |
| GET | `/api/trading/trades` | 当日成交 | ✅ 200（空数组） |
| GET | `/api/trading/account` | 账户资金 | ✅ 200（null） |
| POST | `/api/trading/order` | 下单 | ⚠️ 503（VNpyBridge 未初始化） |
| DELETE | `/api/trading/order/{vt_orderid}` | 撤单 | ⚠️ 503（VNpyBridge 未初始化） |

### 系统

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| GET | `/health` | 健康检查 | ✅ 200 |
| GET | `/docs` | Swagger UI | ✅ 200 |

---

## 数据一致性验证

| 验证项 | 结果 |
|--------|------|
| signal vs score-history 今日分值 | ✅ 一致（RU: 0.1252） |
| 响应字段格式 | ✅ camelCase |
| 错误响应格式 | ✅ {code, message, data} |

---

## 前端类型定义

见 `src/types/macro.ts`

## API 封装

见 `src/api/macro.ts`、`src/api/trading.ts`

---

## 已知问题

1. **Pydantic 弃用警告**：`class Config` 已弃用，建议升级到 `ConfigDict`（不影响功能）
2. **VNpyBridge 未连接**：交易接口返回 503，等 deep 完成 VNpy 策略加载后恢复
3. **WebSocket 未启用**：`/ws/trading` 端点存在但无实际推送

---

## 下一步

- Phase 1.2：响应字段校验（TypeScript 严格模式）
- Phase 1.3：ErrorBoundary + 重试逻辑
