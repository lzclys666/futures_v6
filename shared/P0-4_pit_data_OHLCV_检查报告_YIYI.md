# P0-4 pit_data.db OHLCV 表检查报告
**检查时间**：2026-05-01 20:00 GMT+8
**检查人**：因子分析师 YIYI

---

## 一、现有数据库状态

### 1.1 pit_data.db 实际情况

| 项目 | 状态 |
|------|------|
| 路径 | `D:\futures_v6\macro_engine\data\pit_data.db` |
| 文件大小 | **0 字节（空文件）** |
| 表数量 | **0** — 数据库完全为空，不存在任何表 |

### 1.2 其他相关数据库

| 数据库 | 路径 | 表情况 |
|--------|------|--------|
| `parameter_db.db` | `macro_engine\data\` | `optimal_parameters`（参数优化结果） |
| `knowledge_base.db` | `macro_engine\data\` | `failure_events`（故障记录） |
| `annotations.db` | `macro_engine\data\` | `annotations`（标注数据） |
| `futures_data.db` | `macro_engine\data\` | 0 字节，空文件 |

**结论**：整个 `macro_engine\data\` 目录下，**没有任何一个数据库包含 OHLCV 表**。

---

## 二、缺失品种清单

任务描述的 7 个品种（AU/AG/CU/RU/NI/RB/ZN）均缺失，但实际上**所有品种的 OHLCV 表都不存在**。

| 品种 | 表名（预期） | 状态 |
|------|-------------|------|
| AU 黄金 | `au_futures_ohlcv` | ❌ 不存在 |
| AG 白银 | `ag_futures_ohlcv` | ❌ 不存在 |
| CU 沪铜 | `cu_futures_ohlcv` | ❌ 不存在 |
| RU 天然橡胶 | `ru_futures_ohlcv` | ❌ 不存在 |
| NI 沪镍 | `ni_futures_ohlcv` | ❌ 不存在 |
| RB 螺纹钢 | `rb_futures_ohlcv` | ❌ 不存在 |
| ZN 沪锌 | `zn_futures_ohlcv` | ❌ 不存在 |

---

## 三、OHLCV 表标准 Schema

基于 `fetch_futures_history.py` 中的 `ensure_ohlcv_table()` 定义：

```sql
CREATE TABLE IF NOT EXISTS {SYMBOL}_futures_ohlcv (
    pub_date     TEXT,      -- 数据发布/入库日期
    obs_date     TEXT,      -- 观察日期（交易日，T 日）
    contract     TEXT,      -- 合约代码，如 "AU0"（主力合约）
    trade_date   TEXT,      -- 交易日期（同 obs_date）
    open         REAL,      -- 开盘价
    high         REAL,      -- 最高价
    low          REAL,      -- 最低价
    close        REAL,      -- 收盘价
    volume       INTEGER,   -- 成交量
    hold         INTEGER,   -- 持仓量（open_interest）
    settle       REAL,      -- 结算价
    PRIMARY KEY (obs_date, contract)
);
```

---

## 四、数据来源分析

### 4.1 可用数据源

| 数据源 | 路径 | 情况 |
|--------|------|------|
| AKShare `futures_main_sina` | 通过网络获取 | ✅ **主力源**，已实现 `fetch_futures_history.py` |
| `D:\futures_v6\macro_engine\output\` CSV | 本地 | ❌ 仅包含因子信号（composite_score/direction），无 OHLCV |
| `D:\futures_v6\data\historical\` CSV | 本地 | ⚠️ 1 分钟 tick 数据（NI2505/RB2505/RB2510/RU2505/ZN2505），仅覆盖单日，**不适用于日线 OHLCV** |

### 4.2 结论

- **CSV 历史文件**：无法使用，`output/` 是因子信号而非价格数据，`data\historical` 是分钟级 tick 而非日线
- **AKShare**：唯一可用主力源，`fetch_futures_history.py` 已实现采集逻辑，可直接复用
- **Tushare**：备选源，暂不需要

---

## 五、修复方案

### 方案：直接调用 AKShare 采集（推荐）

已有脚本可直接使用：

```bash
# 单品种采集（示例：AU 黄金，近 2 年数据）
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol AU --days 504

# 一次性采集全部 7 个缺失品种
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol AU --days 504
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol AG --days 504
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol CU --days 504
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol RU --days 504
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol NI --days 504
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol RB --days 504
python D:\futures_v6\macro_engine\scripts\fetch_futures_history.py --symbol ZN --days 504
```

### 5.1 注意事项

**`fetch_futures_history.py` 存在 Bug**：脚本中 `ensure_ohlcv_table()` 硬编码了 `jm_futures_ohlcv`，未动态化为 `{SYMBOL}_futures_ohlcv`。deep 需先修复此 Bug，或在调用脚本前先手动创建正确表名：

```sql
-- 手动建表（7 个品种）
CREATE TABLE IF NOT EXISTS au_futures_ohlcv (
    pub_date TEXT, obs_date TEXT, contract TEXT, trade_date TEXT,
    open REAL, high REAL, low REAL, close REAL,
    volume INTEGER, hold INTEGER, settle REAL,
    PRIMARY KEY (obs_date, contract)
);
-- AG/CU/RU/NI/RB/ZN 同理，将 au 替换为对应品种小写
```

### 5.2 备选方案：直接 SQL 导入（无 AKShare 时）

若无法使用 AKShare，可改用 Tushare 或其他源获取 CSV 后导入：

```sql
-- 导入 CSV 到已建表
.mode csv
.import 'D:\path\to\AU_daily.csv' au_futures_ohlcv
```

**前提**：CSV 列顺序需与上述 Schema 一致（pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle）

---

## 六、给 deep 的具体指令

1. **先修复** `fetch_futures_history.py` 中 `ensure_ohlcv_table()` 的硬编码问题，改为动态表名
2. **逐品种执行**采集脚本（AU/AG/CU/RU/NI/RB/ZN）
3. **验证**：采集完成后用以下 SQL 检查数据量：

```sql
SELECT 'AU' as symbol, COUNT(*) as cnt FROM au_futures_ohlcv
UNION ALL SELECT 'AG', COUNT(*) FROM ag_futures_ohlcv
UNION ALL SELECT 'CU', COUNT(*) FROM cu_futures_ohlcv
UNION ALL SELECT 'RU', COUNT(*) FROM ru_futures_ohlcv
UNION ALL SELECT 'NI', COUNT(*) FROM ni_futures_ohlcv
UNION ALL SELECT 'RB', COUNT(*) FROM rb_futures_ohlcv
UNION ALL SELECT 'ZN', COUNT(*) FROM zn_futures_ohlcv;
```

每品种预期 ≥ 504 条（约 2 年交易日数据）。

---

## 七、AKShare 采集函数参考

```
数据源：akshare.futures_main_sina(symbol="AU0")
覆盖品种：AU/AG/CU/ZN/NI/RU/RB 均可通过 SYMBOL_MAP 映射到 AKShare 合约代码
返回字段：日期, 开盘价, 最高价, 最低价, 收盘价, 成交量, 持仓量, 结算价
```
