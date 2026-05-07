# D5 订单对账实施追踪

## 任务状态
| 子任务 | 负责人 | 状态 | 完成时间 |
|--------|--------|------|---------|
| D5a 核心引擎 | deep | ✅ 完成 | 12:27 |
| D5b API端点集成 | deep | ✅ 完成 | 12:44 |
| D5c 重启恢复 | deep | 进行中 | — |
| D5d E2E验证 | PM | 待启动 | — |

## 审查意见处理（14项）
| 编号 | 问题 | 处理结果 |
|------|------|---------|
| 1.1 | recon_id 三表语义混乱 | ✅ 改为 order_uuid/ref_order_uuid/discrepancy_uuid |
| 1.2 | 今仓/昨仓未参与对账 | ✅ 规则2补充今昨仓独立校验 |
| 1.3 | filled_volume 双源 | ✅ 改为查询时计算 |
| 1.4 | 去重逻辑错误 | ✅ 改用 client_order_id |
| 2.1 | API字段名误判 | ❌ 驳回（独立列仅示例排版问题） |
| 2.2 | 权益公式缺出入金 | ✅ 增加 ±cash_flow |
| 2.3 | 重启兜底缺失 | ✅ 三档兜底逻辑 |
| 3.1 | 清理策略缺失 | ✅ 归档规则写入方案 |
| 3.2 | CTP状态映射缺失 | ✅ 8状态映射表 |
| 3.3 | 时间戳规范缺失 | ✅ 统一+08:00 |
| 3.4 | WebSocket推送缺失 | ⚠️ 接入AlertManager |
| 路径参数 | recon_id→id | ✅ 修复 |
| total_volume | REAL→INTEGER | ✅ 修复 |
| PaperBridge | 无法测试对账 | ✅ 已知局限 |

## 关键实现细节

### 字段命名（消除歧义）
- recon_orders: `order_uuid`（PK）
- recon_trades: `ref_order_uuid`（FK→recon_orders.order_uuid）
- recon_discrepancies: `discrepancy_uuid`（PK）+ `ref_order_uuid`（FK，可空）

### filled_volume 处理
- 不在 recon_orders 存储
- 查询时计算：`SELECT SUM(volume) FROM recon_trades WHERE ref_order_uuid = ?`

### 今仓/昨仓分离
- today_volume: sum(OPEN成交.volume)
- yd_volume: 上日total_volume + CLOSETODAY成交 - CLOSEYESTERDAY成交
- total_volume = today_volume + yd_volume

### 重启三档
- `< 24h`: 正常恢复
- `24h~7d`: WARNING + 立即同步
- `> 7d / 无记录`: BLOCK/RECOVERY/FORCE（参数控制）

## 下一步
D5a 完成后 → D5b（API端点 + CTP状态映射）
