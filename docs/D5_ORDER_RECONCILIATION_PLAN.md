# D5 订单对账 — 深化方案（修订版）

> **目标**：建立订单↔成交↔持仓↔账户的四向对账体系，确保交易链路端到端可审计、可验证。
> **预估工时**：8h（含联调）
> **前置依赖**：C3（OrderResponse）、E8（API鉴权）已完成 ✅
> **版本**：v2（基于审查意见修订）

---

## ⚠️ 审查意见处理摘要

| 编号 | 问题 | 处理结果 |
|------|------|----------|
| 1.1 | recon_id 三表语义混乱 | ✅ 采纳：重命名为 order_uuid / ref_order_uuid / ref_discrepancy_uuid |
| 1.2 | 今仓/昨仓未参与对账 | ✅ 采纳：规则2补充今昨仓独立校验 + 日终结转逻辑 |
| 1.3 | filled_volume 双触发源 | ✅ 采纳：改为查询时计算字段，不冗余存储 |
| 1.4 | 去重逻辑错误 | ✅ 部分采纳：改用 client_order_id，需扩展 PaperBridge |
| 2.1 | API 字段名误判 | ❌ 驳回：expected_value/actual_value 本为独立列，示例仅排版问题 |
| 2.2 | 权益公式缺出入金 | ✅ 采纳：增加 ±cash_flow 项 |
| 2.3 | 重启兜底缺失 | ✅ 采纳：补充三类场景兜底逻辑 |
| 3.1 | 清理策略缺失 | ✅ 采纳：增加归档策略 |
| 3.2 | CTP 状态映射缺失 | ✅ 采纳：增加映射表 |
| 3.3 | 时间戳格式不统一 | ✅ 采纳：统一为 ISO 8601 +08:00 |
| 3.4 | WebSocket 推送缺失 | ⚠️ 部分：AlertManager 已有告警推送，recon_discrepancies 接入之 |
| 路径参数 | resolve/{recon_id}→{id} | ✅ 采纳 |
| PaperBridge | 无法测出 Order↔Trade | ✅ 注明为已知局限 |
| total_volume | REAL→INTEGER | ✅ 采纳 |

---

## 一、现状盘点

### 1.1 已有数据源

| 数据层 | 来源 | 持久化 | 可用性 |
|--------|------|--------|--------|
| 订单 | `VNpyBridge.orders` / `PaperBridge._orders` | 内存（重启丢） | ✅ API `/trading/orders` |
| 成交 | `VNpyBridge.trades` / `PaperBridge._trades` | 内存（重启丢） | ✅ API `/trading/trades` |
| 持仓 | `VNpyBridge.positions` / `PaperBridge._positions` | 内存（重启丢） | ✅ API `/portfolio` |
| 账户 | `VNpyBridge.account` / `PaperBridge._account` | 内存（重启丢） | ✅ API `/account` |
| 审计日志 | `AuditService.audit.db` (audit_log表) | SQLite持久化 | ✅ run.py启动时注册 |
| 风控日志 | `AlertManager.alerts.db` | SQLite持久化 | ✅ API `/risk/alerts` |

### 1.2 已有对账能力

| 维度 | 现状 | 缺口 |
|------|------|------|
| 订单→成交 | 无 | ❌ 订单发出后无法追踪成交匹配 |
| 持仓验证 | 无 | ❌ 无持仓来源对账 |
| 账户一致性 | 简化估算 | ❌ 无精确权益计算 |
| 换日重启 | 全量内存丢失 | ❌ 重启后订单/持仓/账户全部归零 |
| 重复订单检测 | 无 | ❌ 无去重机制 |

### 1.3 PaperBridge vs VNpyBridge 差异

| 特性 | PaperBridge | VNpyBridge（真实CTP） |
|------|------------|---------------------|
| send_order 行为 | 立即"filled"，同步更新持仓 | 发单到CTP，等待成交回报 |
| 持仓更新 | 同步计算（内存） | 依赖CTP持仓回报事件 |
| cancel_order | 仅检查订单是否存在 | 发送CTP撤单指令 |
| 重启后状态 | **完全丢失** | 依赖CTP侧持仓同步 |
| 成交推送 | 无（同步假成交） | 异步成交事件推送 |
| client_order_id | 无（内部UUID） | 可从 CTP 拿到交易所订单号 |

> **已知局限**：PaperBridge 模式下 Order↔Trade 对账永远通过（因假成交是同步发生的），无法真实测试对账逻辑。测试时需使用 VNpyBridge + SimNow 环境覆盖此场景。

---

## 二、设计方案

### 2.1 核心原则

1. **不修 PaperBridge 本身** — 不改 VNpy 的 PaperAccount 行为，只在桥接层做补偿
2. **四向对账** — Order ↔ Trade ↔ Position ↔ Account，每向都必须连通
3. **写时记账** — 以成交表为权威数据源，订单表持仓仅作缓存
4. **今仓昨仓分离** — CTP 实盘强依赖今仓/昨仓分开计算
5. **差量日志** — 只记录差异事件，不记录全量流水

### 2.2 架构

```
api/routes/trading.py
    │
    ├── send_order() ──────→ ReconciliationEngine.record_order()
    │                              │
    │                              ▼
    │                      ReconciliationEngine
    │                              │
    │         ┌────────────────────┼────────────────────┐
    │         ▼                    ▼                    ▼
    │   reconcile_order()    reconcile_trade()    reconcile_position()
    │         │                    │                    │
    │         └────────────────────┴────────────────────┘
    │                              │
    │                              ▼
    │                    SQLite (recon.db)  ← 持久化
    │
    └── VNpyBridge ──→ 事件驱动 → ReconciliationEngine.on_trade_event()
```

### 2.3 时间戳规范（统一）

所有 TEXT 类型时间字段统一格式：

```
YYYY-MM-DDTHH:MM:SS+08:00
示例：2026-05-07T12:30:00+08:00
```

理由：
- CTP 使用北京时间（+08:00）
- 服务器日志可能是 UTC，存储时统一转为北京时间
- ISO 8601 + 时区后缀确保跨时区可解析

### 2.4 SQLite 持久化设计

**文件**：`D:\futures_v6\macro_engine\recon.db`

**表1：`recon_orders`（订单流水）**
```sql
CREATE TABLE recon_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_uuid TEXT UNIQUE NOT NULL,          -- 订单唯一UUID（PK别名）
    client_order_id TEXT,                     -- 客户端订单ID（去重依据，CTP柜台返回）
    vt_orderid TEXT,                         -- 交易所订单ID（CTP报单编号）
    symbol TEXT NOT NULL,                     -- 品种代码（如 RU2505）
    exchange TEXT NOT NULL,                   -- 交易所（SHFE/DCE/ZCE/INE）
    direction TEXT NOT NULL,                  -- LONG / SHORT
    offset TEXT NOT NULL,                     -- OPEN / CLOSE / CLOSETODAY / CLOSEYESTERDAY
    price REAL NOT NULL,                      -- 委托价格
    volume INTEGER NOT NULL,                 -- 委托数量（手，整数）
    status TEXT NOT NULL DEFAULT 'PENDING',   -- PENDING/PARTIAL/FILLED/CANCELLED/REJECTED
    rejection_reason TEXT,                    -- 拒单原因（REJECTED时填写）
    created_at TEXT NOT NULL,                 -- 发单时间（ISO 8601 +08:00）
    updated_at TEXT NOT NULL,                -- 最后更新时间
    source TEXT NOT NULL DEFAULT 'unknown',   -- api / strategy / paper / ctp
    version INTEGER DEFAULT 1                 -- 乐观锁版本号
);
CREATE INDEX idx_orders_uuid ON recon_orders(order_uuid);
CREATE INDEX idx_orders_client ON recon_orders(client_order_id);  -- 去重索引
CREATE INDEX idx_orders_vt ON recon_orders(vt_orderid);
CREATE INDEX idx_orders_symbol ON recon_orders(symbol);
CREATE INDEX idx_orders_status ON recon_orders(status);
CREATE INDEX idx_orders_created ON recon_orders(created_at);
```

**表2：`recon_trades`（成交流水）**
```sql
CREATE TABLE recon_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_uuid TEXT UNIQUE NOT NULL,          -- 成交唯一UUID
    ref_order_uuid TEXT NOT NULL,             -- 关联订单UUID（外键 → recon_orders.order_uuid）
    vt_tradeid TEXT UNIQUE NOT NULL,         -- 交易所成交ID（去重依据）
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    offset TEXT NOT NULL,                     -- OPEN 时 = 今仓；CLOSE 时需参考订单的 close_today 标记
    price REAL NOT NULL,
    volume INTEGER NOT NULL,                  -- 成交手数（整数）
    trade_time TEXT NOT NULL,                -- 成交时间（交易所时间戳）
    created_at TEXT NOT NULL,                 -- 入库时间
    source TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (ref_order_uuid) REFERENCES recon_orders(order_uuid)
);
CREATE INDEX idx_trades_uuid ON recon_trades(trade_uuid);
CREATE INDEX idx_trades_order ON recon_trades(ref_order_uuid);
CREATE INDEX idx_trades_vt ON recon_trades(vt_tradeid);
```

**关键变更说明**：
- `order_uuid` 替代原 `recon_id`（消除歧义）
- `ref_order_uuid` 显式标注为外键（替代原 `recon_id`）
- `client_order_id` 新增（去重检测依据）
- `filled_volume` 不再存储，改为查询时计算：`SELECT SUM(volume) FROM recon_trades WHERE ref_order_uuid = ?`
- `volume` 改为 INTEGER（成交量是整数手数）

**表3：`recon_positions`（持仓快照）**
```sql
CREATE TABLE recon_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,                  -- LONG / SHORT
    today_volume INTEGER NOT NULL DEFAULT 0,  -- 今仓手数（今日开仓）
    yd_volume INTEGER NOT NULL DEFAULT 0,    -- 昨仓手数（昨日留仓）
    total_volume INTEGER NOT NULL DEFAULT 0, -- 总持仓 = today + yd
    avg_price REAL NOT NULL DEFAULT 0.0,      -- 开仓均价
    last_price REAL NOT NULL DEFAULT 0.0,     -- 最新行情价
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    market_value REAL NOT NULL DEFAULT 0.0,   -- 市值 = total_volume * last_price * multiplier
    settlement_price REAL,                     -- 结算价（日终对账用）
    recorded_at TEXT NOT NULL,                 -- 快照时间
    source TEXT NOT NULL DEFAULT 'calculated', -- calculated / broker
    FOREIGN KEY (symbol, exchange, direction)
        REFERENCES recon_positions(symbol, exchange, direction)
);
CREATE UNIQUE INDEX idx_pos_symbol_dir ON recon_positions(symbol, exchange, direction);
CREATE INDEX idx_pos_recorded ON recon_positions(recorded_at);
```

**关键变更说明**：
- 今仓/昨仓分离（today_volume / yd_volume）
- 总持仓 = today_volume + yd_volume
- 日终对账需分别处理今仓昨仓

**表4：`recon_discrepancies`（差异记录）**
```sql
CREATE TABLE recon_discrepancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discrepancy_uuid TEXT UNIQUE NOT NULL,   -- 差异记录自己的UUID
    ref_order_uuid TEXT,                     -- 关联订单UUID（可空）
    discrepancy_type TEXT NOT NULL,          -- ORDER_TRADE_MISMATCH / POSITION_MISMATCH / BALANCE_MISMATCH / DUPLICATE_ORDER
    severity TEXT NOT NULL DEFAULT 'WARNING', -- WARNING / CRITICAL
    description TEXT NOT NULL,               -- 可读描述
    expected_value TEXT,                     -- JSON字符串，如：{"filled_volume": 5}
    actual_value TEXT,                       -- JSON字符串，如：{"filled_volume": 2}
    resolved INTEGER DEFAULT 0,              -- 0=未解决 1=已解决
    resolved_reason TEXT,                    -- 解决原因（手动填写）
    resolved_at TEXT,                        -- 解决时间
    created_at TEXT NOT NULL
);
CREATE INDEX idx_disc_type ON recon_discrepancies(discrepancy_type);
CREATE INDEX idx_disc_resolved ON recon_discrepancies(resolved);
CREATE INDEX idx_disc_created ON recon_discrepancies(created_at);
```

**关键变更说明**：
- `discrepancy_uuid` 为差异记录自己的唯一ID（替代歧义的 `recon_id`）
- `ref_order_uuid` 为关联订单UUID（命名清晰）
- expected_value / actual_value 为独立列（驳回2.1的误判）

**表5：`recon_daily_summary`（日终对账单）**
```sql
CREATE TABLE recon_daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT UNIQUE NOT NULL,         -- 交易日期 2026-05-07（北京时间）
    total_orders INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    total_volume INTEGER DEFAULT 0,          -- 整数手数
    total_turnover REAL DEFAULT 0.0,          -- 成交金额
    realized_pnl REAL DEFAULT 0.0,
    starting_equity REAL DEFAULT 0.0,        -- 日初权益
    cash_flow REAL DEFAULT 0.0,               -- 出入金（+为入金，-为出金）
    commission REAL DEFAULT 0.0,
    ending_equity REAL DEFAULT 0.0,          -- 日终权益
    frozen_margin REAL DEFAULT 0.0,
    unrealized_pnl REAL DEFAULT 0.0,
    alerts_count INTEGER DEFAULT 0,
    discrepancies_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'OK',                -- OK / RECONCILED / HAS_ISSUES
    created_at TEXT NOT NULL
);
CREATE INDEX idx_summary_date ON recon_daily_summary(trade_date);
```

---

## 三、关键对账规则

### 规则1：Order ↔ Trade 匹配

```
预期：每笔订单的 filled_volume = sum(该订单所有成交.volume)
filled_volume 由查询计算得出（不在 recon_orders 存储）：
  filled_volume = SELECT SUM(volume) FROM recon_trades WHERE ref_order_uuid = order_uuid

验证：
  - 若 filled_volume < 委托volume → PARTIAL（正常）
  - 若有订单在60分钟内无任何成交且状态=PENDING → 超时告警（WARNING）
  - 若成交volume之和 > 委托volume → 严重错误（CRITICAL）
  - 若 vt_tradeid 重复 → 重复成交（CRITICAL）
  - 若 client_order_id 重复 → DUPLICATE_ORDER（WARNING）
```

**重复订单检测逻辑（修复1.4）**：
```python
# 正确方式：以 client_order_id 去重
def check_duplicate(client_order_id: str, created_at: str) -> bool:
    # 5分钟窗口内的相同 client_order_id 才算重复
    window_start = (parse(created_at) - timedelta(minutes=5)).isoformat()
    existing = db.execute("""
        SELECT 1 FROM recon_orders
        WHERE client_order_id = ?
        AND created_at >= ?
        LIMIT 1
    """, (client_order_id, window_start)).fetchone()
    return existing is not None
```
> **注意**：当前 PaperBridge 无 client_order_id，需在 PaperBridge.send_order() 中生成内部 UUID 作为 client_order_id。

### 规则2：Position 校验（今仓/昨仓分离）【修订】

```
预期持仓计算（按 symbol + direction 分组）：
  today_volume = sum(OPEN成交.volume)  -- 今仓
  yd_volume    = 上日 total_volume + sum(CLOSETODAY成交.volume) - sum(CLOSEYESTERDAY成交.volume)
  total_volume = today_volume + yd_volume

校验公式（允许 ±1 tick 误差）：
  |calculated_today - broker_today| ≤ 1
  |calculated_yd - broker_yd| ≤ 1
  |calculated_avg_price - broker_avg_price| ≤ 1 tick

平仓指令生成规则（CTP 实盘强相关）：
  - 平今仓：offset = CLOSETODAY
  - 平昨仓：offset = CLOSEYESTERDAY
  - CTP 优先平今仓（郑商所规则），但需在发单时明确指定
```

**日终 yd_volume 结转逻辑**：
```
每日 15:00（日盘结束）/ 23:00（夜盘结束）自动触发：

1. 读取当日 final_positions（来自 CTP 日终持仓回报）
2. 对每个 symbol+direction：
   yd_volume[next_day] = total_volume（当日收盘持仓作为次日昨仓）
3. 清空 today_volume（次日开盘置零）
4. 写入 recon_daily_summary 快照
5. 若 CTP 持仓回报缺失 → 使用 recon_trades 计算值替代，并标记 source='calculated'
```

### 规则3：Account 权益校验【修订】

```
权益公式（含出入金）：
  ending_equity = starting_equity + realized_pnl - commission + unrealized_pnl + cash_flow

验证：
  - 每次成交后实时更新权益估算
  - 日终精确权益计算（用结算价）vs broker 权益
  - 若 |calculated - broker| > 100元 → BALANCE_MISMATCH（WARNING）
  - 若 |calculated - broker| > 1000元 → CRITICAL
  - 若 |calculated - broker| > 10000元 → 阻止启动（数据异常）

cash_flow 来源：
  - CTP 账户可通过 account_df 读取（若有出入金回报）
  - 若无：假设 cash_flow = 0，并在差异描述中注明"未计入出入金"
```

### 规则4：换日重启校验【修订】

```
启动时检测流程：

Step 1: 读取 recon_positions 最近一条记录（按 recorded_at DESC LIMIT 1）
Step 2: 计算记录年龄 = now - recorded_at

├── < 24h：正常恢复
│   └── 使用 recon_positions 数据初始化 VNpyBridge / PaperBridge 持仓
│
├── 24h ~ 7天：数据过期警告（WARNING）
│   └── 仍使用 recon_positions 恢复，但：
│       - 在 recon_discrepancies 记录 POSITION_STALE 差异
│       - 启动后立即发起 CTP 持仓同步请求
│       - 对账后修正 recon_positions
│
├── > 7天 或 无记录 且 持仓 ≠ 0：数据不可用（CRITICAL）
│   └── 三选一（启动参数控制）：
│       ① BLOCK：阻止启动，要求人工确认
│       ② RECOVERY_MODE：清除所有挂单，进入安全模式（只读）
│       ③ FORCE：强制使用 recon_positions，但记录 disclaimer
│
└── recon.db 文件损坏/丢失
    └── BLOCK：拒绝启动，必须从备份恢复
```

启动参数（`run.py` 新增）：
```python
--recon-recovery-mode: block | recovery | force  (default: block)
```

### 规则5：重复订单检测【修订】

```
检测依据：client_order_id（客户端订单ID）

正确逻辑：
  - 网络重试导致的重复：相同 client_order_id 在5分钟窗口内出现多次 → DUPLICATE_ORDER
  - 用户合法分批建仓：不同 client_order_id → 不视为重复（允许）
  - cl_orderid 生成规则：
      • CTP实盘：使用 CTP 柜台返回的 local_order_id
      • PaperBridge：生成内部 UUID
      • API下单：前端传入 client_order_id（可自己生成UUID）
```

---

## 四、API 端点设计

### 4.1 GET /api/recon/status
```json
{
  "code": 0,
  "data": {
    "last_recon_time": "2026-05-07T12:30:00+08:00",
    "orders_count": 15,
    "trades_count": 12,
    "positions_count": 3,
    "discrepancies": {
      "unresolved": 0,
      "WARNING": 0,
      "CRITICAL": 0
    },
    "engine_status": "ok"
  }
}
```

### 4.2 GET /api/recon/discrepancies
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 1,
        "discrepancy_uuid": "uuid-xxx",
        "ref_order_uuid": "uuid-yyy",
        "discrepancy_type": "ORDER_TRADE_MISMATCH",
        "severity": "WARNING",
        "description": "订单RU2505.LONG.FILLED成交不足：委托5手，仅成交2手",
        "expected_value": {"filled_volume": 5},
        "actual_value": {"filled_volume": 2},
        "created_at": "2026-05-07T12:15:00+08:00",
        "resolved": false
      }
    ],
    "total": 1
  }
}
```

> **说明**：expected_value / actual_value 为独立字段，各自在数据库中存储 JSON 字符串。上例仅为展示，实际存储如：`expected_value = '{"filled_volume": 5}'`。

### 4.3 POST /api/recon/reconcile（手动触发对账）
```json
// Request
{ "scope": "full" } // full | positions | orders

// Response
{
  "code": 0,
  "data": {
    "checked_orders": 15,
    "checked_trades": 12,
    "checked_positions": 3,
    "new_discrepancies": 0,
    "resolved_discrepancies": 0,
    "duration_ms": 45
  }
}
```

### 4.4 GET /api/recon/daily/{date}
```json
{
  "code": 0,
  "data": {
    "trade_date": "2026-05-07",
    "total_orders": 15,
    "total_trades": 12,
    "total_volume": 45,
    "total_turnover": 675000.00,
    "realized_pnl": 3200.00,
    "starting_equity": 1000000.00,
    "cash_flow": 0.0,
    "commission": 125.50,
    "ending_equity": 1003200.00,
    "alerts_count": 2,
    "discrepancies_count": 0,
    "status": "OK"
  }
}
```

### 4.5 POST /api/recon/resolve/{id}【修复路径参数】
```json
// Request（路径参数 id 为 recon_discrepancies 表的 INTEGER 主键）
{
  "reason": "已知晓，CTP持仓同步延迟导致，次日自动恢复"
}
```
> **修复说明**：原方案错误使用 `resolve/{recon_id}`，应使用 `id`（INTEGER 自增主键）。

---

## 五、CTP 订单状态映射表【新增】

| CTP 状态（中文） | CTP 状态码 | 映射到 | 说明 |
|----------------|----------|--------|------|
| 报单中 | 0 | PENDING | 已提交，等待交易所确认 |
| 已报 | 1 | PENDING | 已到达交易所，等待成交 |
| 部成 | 2 | PARTIAL | 部分成交 |
| 已成 | 3 | FILLED | 全部成交 |
| 未成 | 4 | PENDING | 未成交（直接拒单） |
| 已撤 | 5 | CANCELLED | 用户主动撤单 |
| 部撤 | 6 | PARTIAL + CANCELLED | 部分成交后撤单 |
| 废单 | 7 | REJECTED | 交易所拒绝 |

> 实现时在 `services/vnpy_bridge.py` 中增加 `CTP_STATUS_MAP` 字典：
```python
CTP_STATUS_MAP = {
    0: "PENDING",    # 报单中
    1: "PENDING",    # 已报
    2: "PARTIAL",   # 部成
    3: "FILLED",    # 已成
    4: "PENDING",   # 未成
    5: "CANCELLED", # 已撤
    6: "PARTIAL",   # 部撤（取 PARTIAL，附带 CANCELLED 标记）
    7: "REJECTED",  # 废单
}
```

---

## 六、WebSocket 推送对账差异【新增】

在现有 AlertManager 基础上，接入 `recon_discrepancies`：

```python
# ReconciliationEngine 中
def _emit_discrepancy_alert(self, disc: dict):
    mgr = get_alert_manager()
    severity = "CRITICAL" if disc["severity"] == "CRITICAL" else "WARNING"
    mgr.add_alert(
        level=severity,
        category="recon_discrepancy",
        message=f"[对账差异] {disc['discrepancy_type']}: {disc['description']}",
        details=disc
    )
```

> **说明**：AlertManager 已实现 WebSocket 推送（`/ws/risk`），recon_discrepancies 通过 AlertManager 间接接入，无需额外实现推送层。

---

## 七、数据清理策略【新增】

### 7.1 归档规则

| 表 | 保留策略 | 归档操作 |
|----|---------|---------|
| recon_orders | 90天 | 超期记录转 `recon_orders_archive` 表 |
| recon_trades | 90天 | 同上 |
| recon_positions | 30天（仅保留每日最终快照） | 压缩为日粒度 |
| recon_discrepancies | 永久保留 | 不可删除（审计要求） |
| recon_daily_summary | 永久保留 | 不可删除（审计要求） |

### 7.2 清理触发

- 每日 09:00（日盘开盘前）自动执行
- 独立 cron 任务，不影响交易

### 7.3 级联处理

删除 recon_orders 时：
- 自动删除关联的 recon_trades（CASCADE）
- 保留 recon_discrepancies（独立表，不级联）

---

## 八、实现步骤

### D5a：ReconciliationEngine 核心（2h）
- 创建 `services/reconciliation_engine.py`
- 实现 SQLite recon.db 初始化（5张表，按修订版 schema）
- 实现 `record_order() / record_trade() / record_position()` 写入API
- 实现 `check_order_trade_match()`（含 filled_volume 查询计算）
- 实现 `check_position_consistency()`（今仓/昨仓分离）
- 实现 `check_account_equity()`（含 cash_flow）
- 实现差异告警触发（调用 AlertManager）

### D5b：API 端点集成（1h）
- 创建 `api/routes/recon.py`（4个端点，路径用 `/{id}` 而非 `/{recon_id}`）
- 在 `trading.py` 的 `create_order()` 末尾集成 `ReconciliationEngine.record_order()`
- 在 VNpyBridge 的 `on_trade_event` 中集成 `record_trade()`
- 集成 CTP 状态映射（CTP_STATUS_MAP）

### D5c：重启恢复（3h）
- 实现 `recon_positions` 持久化读取（启动时从 SQLite 恢复持仓）
- 实现三档重启兜底逻辑（block / recovery / force）
- 实现日终快照写入 + yd_volume 自动结转
- 实现 `--recon-recovery-mode` 命令行参数

### D5d：端到端验证（2h）
- PaperTrade 场景：下单→成交→持仓→对账全链路测试
- 重启后持仓恢复验证（三种模式各测一次）
- 差异告警触发验证
- CTP 状态映射验证（需 SimNow）

---

## 九、验收标准

1. **D5a**：单元测试通过（5条对账规则各自独立测试）
2. **D5b**：`GET /recon/status` 返回正确统计；路径参数 `resolve/{id}` 正确
3. **D5c**：重启后持仓从 SQLite 恢复（三种模式各验证）
4. **D5d**：完整场景测试：
   - 下单 → 检查 orders_count +1
   - 成交 → 检查 trades_count +1，filled_volume 由查询计算得出
   - 持仓变化 → 检查 recon_positions.today_volume / yd_volume 正确
   - 制造重复 client_order_id → 检查 DUPLICATE_ORDER 差异记录
   - 权益差异 > 1000元 → CRITICAL 告警入库

---

## 十、已知局限

| 局限 | 说明 | 规避方式 |
|------|------|---------|
| PaperBridge Order↔Trade 永远通过 | 假成交同步发生，无法测试对账规则1 | 测试时使用 VNpyBridge + SimNow |
| PaperBridge 无 client_order_id | 重复检测依赖 client_order_id | PaperBridge.send_order() 生成内部 UUID |
| 出入金无法精确追踪 | cash_flow 可能为0 | 日终对账时注明数据来源 |
| recon.db 文件损坏 | 无自动修复 | 拒绝启动，要求人工介入 |
