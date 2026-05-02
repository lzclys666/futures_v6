# 技术议会提案
**日期**: 2026-04-22 16:00
**起草人**: YIYI（因子分析师）
**状态**: 待审议

---

## 提案一：AKShare 单点故障风险 — 抽象适配层建设

### 现状摘要

| 指标 | 数据 |
|------|------|
| 提及 AKShare 的文件数 | **193 个** |
| 直接依赖 AKShare 的爬虫数 | **146 个** |
| 涉及品种 | 全部 22 个品种 |
| AKShare 角色 | 多品种主力数据源 |

### 风险分析

**单点故障场景**：

1. **AKShare 官方 API 变更**（高风险）
   - 接口返回格式变化 → 146 个爬虫同时失效
   - 历史案例：AKShare 2024 年多次调整期货接口，导致大批爬虫集体报错

2. **网络/IP 限制**（中风险）
   - AKShare 服务器限流/封 IP → 所有品种数据同时中断
   - 无降级路径，数据真空

3. **维护中断**（低-中风险）
   - 维护窗口/节假日 → 系统级数据缺口
   - 影响所有基于 AKShare 的因子计算

**根本问题**：146 个爬虫**直接硬编码** `import akshare`，数据源与业务逻辑强耦合。

### 治理方案

#### 方案 A：抽象适配层（推荐）

```
数据请求层
    │
    ├── AKShareAdapter     ← 当前主力
    ├── TushareAdapter     ← 备用通道 1
    ├── ExchangeAdapter     ← 备用通道 2（交易所直连）
    └── CustomAdapter       ← 备用通道 3（自定义爬虫）
```

**核心接口**：
```python
class DataSourceAdapter(Protocol):
    def futures_spot_price(self, symbol: str, date: str) -> Optional[pd.DataFrame]
    def futures_inventory(self, symbol: str) -> Optional[pd.DataFrame]
    def bond_yield(self, bond_type: str) -> Optional[pd.DataFrame]
    # 通用接口，按需扩展
```

**切换逻辑**：
- 主adapter失败 → 自动切换备用adapter
- 配置中心控制各品种的 adapter 优先级
- 降级链路可配置、可监控

**改造工作量估算**：
- 新建 `adapters/` 目录，定义抽象接口：约 **1 周**
- 将 146 个爬虫分批迁移：约 **2-3 周**（按品种）
- 测试与并行运行验证：约 **1 周**

#### 方案 B：本地缓存 + 定时预拉（应急补丁）

- 每日闭市后批量从 AKShare 拉取数据到本地 SQLite
- 网络故障时切换本地数据
- **局限**：只能缓解，不能根本解决依赖问题

### 建议决议

> **通过方案 A**，授权程序员mimo/程序员deep组成专项小组，2周内完成抽象层设计与品种试点。

---

## 提案二：db_utils.py 集中耦合分析

### 现状摘要

| 指标 | 数据 |
|------|------|
| 依赖 db_utils 的文件数 | **257 个** |
| db_utils 路径 | `macro_engine/crawlers/common/db_utils.py` |
| 代码行数 | 约 130 行（含空行/注释） |
| 品种覆盖 | 全部 22 个品种 |

### 耦合结构分析

`db_utils.py` 提供 4 个核心函数：

| 函数 | 功能 | 调用频率 |
|------|------|----------|
| `ensure_table()` | 建表/表结构迁移 | 每次爬虫运行 |
| `save_to_db()` | 带重试的因子写入 | 高频 |
| `get_latest_value()` | L4 兜底数据获取 | 中频 |
| `get_pit_dates()` | PIT 日期处理 | 每次爬虫运行 |

**依赖树示例**（以 AG 品种为例）：
```
AG_抓取现货价.py
  └─ from ..common.db_utils import save_to_db, get_pit_dates

AG_抓取期货日行情.py
  └─ from ..common.db_utils import save_to_db, ensure_table, get_pit_dates

AG_计算期现基差.py
  └─ from ..common.db_utils import get_latest_value
```

### 耦合风险

1. **单一文件损坏** → 所有 257 个文件同时受影响
2. **表结构变更** → 所有爬虫行为可能不一致
3. **数据库路径硬编码** → 迁移困难
4. **无法独立测试** → 每个爬虫都依赖真实数据库

### 解耦建议

#### 第一步：接口化（低风险，可渐进）

将 `db_utils.py` 改造为标准接口，底层实现可替换：

```python
# 新的 adapters/db_adapter.py
class DBTablesAdapter(Protocol):
    def ensure_table(self) -> None: ...
    def save(self, factor_code, symbol, pub_date, obs_date, raw_value, ...) -> bool: ...
    def get_latest(self, factor_code, symbol, before_date=None) -> Optional[float]: ...

class SQLiteAdapter(DBTablesAdapter):
    def __init__(self, db_path: str): ...

# db_utils.py 变成薄封装
from adapters.db_adapter import SQLiteAdapter
_db = SQLiteAdapter(DB_PATH)
save_to_db = _db.save
```

#### 第二步：依赖注入（中等风险）

爬虫不再直接 `from common.db_utils import`，而是从配置注入：

```python
# 爬虫改造示例
def main(adapter: DBTablesAdapter = None):
    adapter = adapter or SQLiteAdapter(DB_PATH)
    adapter.save(...)
```

#### 第三步：按品种拆分（高风险，远期）

按品种拆分 `common/` 目录，降低故障爆炸半径：
- `crawlers/AG/common/` → AG 专用
- `crawlers/AU/common/` → AU 专用
- `crawlers/_shared/common/` → 共用工具

**问题**：改动面太大，短期不推荐。

### 建议决议

> **通过第一步 + 第二步**，将 db_utils 改造为标准接口，6 周内完成评审。
> 独立测试框架建设：每批次爬虫改造后必须通过 `common/test_db_utils.py` 回归测试。

---

## 提案三：Paper Trading 启动确认 — AG 先行计划

### 背景

技术议会在 2026-04-20 验证了 Phase 4 宏观因子，金银比因子表现**极其突出**：

### 金银比因子（AG_MACRO_GOLD_SILVER_RATIO）核心指标

| 指标 | 数值 | 评级 |
|------|------|------|
| IC 均值（10日持有） | **-0.402** | 🟢 EXCELLENT |
| IR | **-1.819** | 🟢 EXCELLENT（因子库第一） |
| t 统计量 | **-61** | 🟢 EXCELLENT |
| 胜率 | **93%+** | 🟢 EXCELLENT |
| 方向 | 负向（金银比↑ → AG↓） | 经济逻辑清晰 |

**经济含义**：金银比（SGE Au / SGE Ag）反映贵金属相对价值。当金银比上升（黄金相对更贵），通常对应美元走强/实际利率上行/避险情绪，白银工业属性导致跌幅更大。适用于 AG 的**择时过滤**。

### AG 先行计划详情

#### 品种选择理由

1. **因子质量最优**：金银比 IR=-1.819，为因子库最高
2. **数据已就绪**：AG 宏观因子已在 `output/AG_macro_daily_*.csv` 稳定输出
3. **策略接口成熟**：`MacroDemoStrategy` 已有完整框架，AG 是默认测试品种
4. **波动适中**：白银波动率低于黄金，Paper Trade 资金曲线更平稳

#### 已验证因子池（AG）

| 因子代码 | 因子名称 | IC 方向 | 状态 |
|----------|----------|---------|------|
| AG_MACRO_GOLD_SILVER_RATIO | 金银比 | **核心（IR=-1.819）** | ✅ 入池 |
| AG_POS_NET | 上期所沪银前20净持仓 | 正向 | ✅ 入池 |
| AG_POS_CFTC_NET | CFTC白银净持仓 | 正向 | ✅ 入池 |
| AG_INV_SHFE_AG | 上期所沪银仓单 | 负向 | ✅ 入池 |
| AG_MACRO_DXY | 美元指数 | 负向 | ✅ 入池 |
| AG_FUT_CLOSE | AG 期货收盘价 | 正向 | ✅ 入池 |
| AG_SPD_BASIS | 沪银期现基差 | 正向 | ✅ 入池 |

#### USD/CNY 暂不入池理由

| 问题 | 说明 |
|------|------|
| **方法论瑕疵** | 之前验证时用因子自身价格做基准，存在逻辑问题 |
| **方向待确认** | 点IC正但滚动IR负，信号不一致 |
| **与金银比共线性** | USD/CNY 与金银比高度相关（r>0.7），多重共线性干扰 |
| **验证时间不足** | 仅凭 2020-2025 年数据，未做独立样本外测试 |

**结论**：USD/CNY 因子需要**重新设计验证方案**（用独立价格基准），暂不入池，待下次议会再审。

### Paper Trading 启动步骤

| 阶段 | 内容 | 负责 |
|------|------|------|
| 1 | AG 品种 vnpy 策略加载 + signal CSV 对接 | 程序员doudou |
| 2 | 金银比因子信号接入（10日持有，负向过滤） | YIYI |
| 3 | Paper Trade 账户开仓（AG 多头/空头） | 项目经理 |
| 4 | 5交易日监控 + 回测对比 | YIYI |
| 5 | 评估决策：扩展到 AU/CU 或调整参数 | 议会 |

### 预期产出

- Paper Trade 运行日志：`D:\futures_v6\logs\paper_trade_ag_{date}.log`
- 每日信号记录：`D:\futures_v6\output\AG_macro_daily_{date}.csv`
- 周度评估报告：下周二议会汇报

### 建议决议

> **通过 AG 先行计划**，即日起至下周二 paper trade 运行5个交易日，16:00 议会评估扩展方案。

---

## 附：本次议会行动清单

| 序号 | 行动项 | 负责 | 截止 |
|------|--------|------|------|
| P1 | AKShare 抽象适配层设计与评审 | mimo + deep | 2周 |
| P2 | db_utils 接口化改造（第一步） | deep | 3周 |
| P3 | AG Paper Trade 启动 | doudou | 即日 |
| P4 | AG Paper Trade 周报 | YIYI | 下周二 |
| P5 | USD/CNY 因子重验证方案 | YIYI | 下下次议会 |

---

*本提案由 YIYI 基于 2026-04-22 13:38 项目经理任务单起草*
