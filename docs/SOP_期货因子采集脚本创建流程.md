# 期货因子采集脚本创建 SOP

> 基于 `D:\futures_v6\macro_engine` 工程实践
> 最后更新：2026-05-04

---

## 一、前置准备

### 1.1 读取操作手册
```
D:\futures_v6\系统架构\期货基本面量化数据系统·操作手册 V7.0.txt
```

### 1.2 确认品种信息
- **品种代码**：如 `AU`、`CU`、`AL`、`RB`、`NR` 等
- **批次优先级**：P0（免费源可采集）→ P1（部分付费）→ P2（高度依赖付费源）
- **因子清单**：从因子分析师获取，或查看 `config/factors/{SYMBOL}/` 目录下的 YAML 配置

### 1.3 检查目录结构
```
macro_engine/                    ← 项目根目录（不是 crawlers/ 下）
├── pit_data.db                  ← 主数据库（在此层级，不是 crawlers/common/）
├── crawlers/
│   ├── common/                  # 公共模块
│   │   ├── db_utils.py          # save_to_db / save_l4_fallback / get_pit_dates
│   │   ├── io_win.py            # fix_encoding（可选，未被所有脚本调用）
│   │   ├── market_data.py       # 统一行情获取
│   │   ├── check_health.py      # 数据健康检查
│   │   └── web_utils.py         # 网络工具
│   ├── {SYMBOL}/               # 品种目录
│   │   ├── {SYMBOL}_因子名.py   # 因子采集脚本（独立文件）
│   │   └── {SYMBOL}_run_all.py  # 品种总调度脚本
│   └── logs/                   # 运行日志（由 run_all.py 自动创建）
```

---

## 二、脚本创建规范

### 2.1 命名规范

> 权威来源：`FACTOR_COLLECTION_SPEC_v1.md` §2.1

| 文件类型 | 命名格式 | 示例 |
|---------|---------|------|
| 因子采集脚本 | `{SYMBOL}_{操作类型}{标的}.py` | `RU_抓取仓单.py`、`AG_计算沪银COMEX比价.py` |
| 品种总调度 | `{SYMBOL}_run_all.py` | `AU_run_all.py`、`NR_run_all.py` |
| 历史回填脚本 | `{SYMBOL}_回填历史数据.py` | `NR_回填历史数据.py` |

**操作类型定义**（三选一）：

| 操作类型 | 含义 | 典型数据源 |
|---------|------|----------|
| `抓取` | 原始数据从外部来源获取 | requests / AKShare / fetch_url |
| `计算` | 派生指标从内部数据计算 | 价差 / 比值 / 收益率 |
| `输入` | 人工录入数据 | 手动输入 / CSV 导入 |

> ⚠️ 禁止使用双前缀命名，如 `AU_AU_xxx.py`
>
> **过渡期兼容**：61% 的历史脚本（178/293）仍用旧式命名（如 `AU_黄金现货.py`、`AU_期货收盘价.py`）。
> 旧脚本暂时保留，但 run_all.py 中的引用路径必须与实际文件名一致。
> 新脚本必须使用 `{SYMBOL}_{操作类型}_{标的}.py` 格式。
> 旧脚本修改功能时，趁机重命名为标准格式。

### 2.2 脚本 Header 模板

每个因子脚本头部必须包含以下结构化文档：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{SYMBOL}_{因子中文名}.py
因子: {FACTOR_CODE} = {中文描述}

公式: {计算公式（如果有）}

当前状态: [✅正常 | ⚠️待修复 | ⛔永久跳过]
- 失败原因或跳过原因（无免费源/付费订阅/接口失效等）
- 尝试过的数据源及结果
- 解决方案（付费订阅/手动录入/等待接口恢复）

订阅优先级: ★~★★★★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
```

**Header 填写说明：**
- `因子代码`：必须与引擎 YAML 文件名完全一致
- `中文描述`：因子中文名称
- `公式`：因子计算公式（如有）
- `当前状态`：根据实际数据采集结果填写
- `订阅优先级`：仅付费数据源需要标注

**状态标签含义：**
- ✅ 正常：数据可正常采集，数值在合理范围内
- ⚠️ 待修复：数据可写但质量待确认，或有已知问题需后续修复
- ⛔ 永久跳过：无免费数据源，需付费订阅或手动录入，明确标注"不写占位符"

### 2.3 三层数据采集策略

**核心原则：每个脚本预设三层，执行时按序尝试，成功即停。**

三层架构说明：
- **定义层**：每个脚本都必须预设第一层、第二层、第三层的代码结构
- **执行层**：运行时顺序尝试（第一层 → 第二层 → 第三层），任意一层成功则写入数据库并停止，不再尝试下层
- **备源缺失**：如果某因子确实没有备源，第二层代码位置必须写明`# 无备源（原因：xxx）`，不得空缺

```
┌─────────────────────────────────────────────────────────┐
│  第一层：首选抓取（免费 & 权威）     source_confidence=1.0 │
│  ─────────────────────────────────────────────────────  │
│  • AKShare（pip install akshare）                        │
│  • 美联储 FRED API（80万+经济序列）                       │
│  • 交易所官网：SHFE/DCE/CZCE/INE                         │
│  • 国家统计局、海关总署公开接口                           │
│  → 成功则 save_to_db() 写入，停止，不再尝试下层          │
│  → 失败则进入第二层                                       │
├─────────────────────────────────────────────────────────┤
│  第二层：备选抓取（免费替代源）     source_confidence=0.9 │
│  ─────────────────────────────────────────────────────  │
│  • AKShare 接口变体 / 参数枚举（symbol=焦煤→炼焦煤……）    │
│  • 交易所官网备用查询接口                                │
│  • 东方财富/同花顺公开页面                               │
│  • 海关总署/数据公开平台 CSV 下载                         │
│  → 仅在第一层失败时执行                                  │
│  → 成功则 save_to_db() 写入，停止                        │
│  → 失败则进入第三层                                       │
├─────────────────────────────────────────────────────────┤
│  第三层：兜底保障（历史回填 + 手动录入）source_confidence=0.5/0.6 │
│  ─────────────────────────────────────────────────────  │
│  • 调用 save_l4_fallback() 读取 pit_data.db 最近记录      │
│  • 手动录入：可靠渠道填入 source_confidence=0.6           │
│  → 仅在第一层+第二层都失败时执行                         │
│  → save_l4_fallback() 也无历史值 → 标记 ⛔永久跳过       │
│                                                         │
│  ⚠️ 旧脚本迁移：如果脚本用 get_latest_value() +          │
│     save_to_db() 做回补，需改为 save_l4_fallback()，      │
│     否则 obs_date 会被覆盖为今天（数据完整性问题）        │
└─────────────────────────────────────────────────────────┘
```

**执行规则（三层串行，成功即停）：**
1. 每个脚本必须预设三层代码结构（哪怕某些层只有一个备源选项）
2. 执行时从第一层开始，任意一层成功即写入数据库并停止
3. 第一层失败 → 尝试第二层；第二层失败 → 尝试第三层
4. 三层全部失败 → 标记 ⛔永久跳过，不写 DB 占位符
5. 如果某因子没有备源，第二层必须写明`# 无备源（原因：xxx）`

**与 db_utils.py 函数的对应关系：**

| 层 | 写入函数 | source_confidence |
|----|---------|-------------------|
| 第一层（首选抓取） | `save_to_db(..., source='akshare', source_confidence=1.0)` | 1.0 |
| 第二层（备选抓取） | `save_to_db(..., source='site_xxx', source_confidence=0.9)` | 0.9 |
| 第三层（兜底保障） | `save_l4_fallback(factor_code, symbol, pub_date, obs_date)` | 0.5 |
| 第三层（手动录入） | `save_to_db(..., source='manual', source_confidence=0.6)` | 0.6 |

> ⚠️ **第三层兜底保障必须使用 `save_l4_fallback()`**，它保留原始 obs_date（不以今天覆盖），详见 `common/db_utils.py`。
>
> **旧脚本迁移现状**：当前 184 个脚本仍使用 `get_latest_value()` + `save_to_db()` 的旧模式。
> 新脚本必须使用 `save_l4_fallback()`。旧脚本在修改功能时顺便迁移，无需批量重写。

### 2.4 PIT 日期规范

**必须从 `common.db_utils` 导入，禁止在脚本中重复实现。**

```python
from common.db_utils import get_pit_dates

pub_date, obs_date = get_pit_dates()
```

`get_pit_dates()` 内部行为（供参考，无需重写）：

| 星期 | Python dow | pub_date | obs_date |
|------|-----------|----------|----------|
| 周一 | 0 | today | 上周五 (-3天) |
| 周二~周五 | 1-4 | today | today（当天） |
| 周六 | 5 | today | 周五 (-1天) |
| 周日 | 6 | today | 周五 (-2天) |

> ⚠️ `pub_date` 始终为 `today`（脚本运行日），`obs_date` 是数据观测日。两者不同！

**历史补采模式**：设置环境变量 `BACKFILL_DATE=YYYY-MM-DD` 后，`get_pit_dates()` 以该日期为 obs_date，pub_date 也设为该日期。

### 2.5 数据库写入规范

```python
from common.db_utils import save_to_db, save_l4_fallback

# === save_to_db 完整签名 ===
save_to_db(
    factor_code,       # str: 因子代码，如 "AU_FUT_CLOSE"
    symbol,            # str: 品种，如 "AU"
    pub_date,          # date: 脚本运行日期
    obs_date,          # date: 数据观测日期
    raw_value,         # float/int: 数值，None 时写 NULL
    source_confidence=1.0,  # float: 置信度（见 §2.3 对应表）
    source=''          # str: 来源描述，如 'akshare'/'manual'/'Mysteel(年费)'
)

# === 第三层兜底保障专用函数（保留原始 obs_date） ===
save_l4_fallback(
    factor_code, symbol, pub_date, today_obs_date,
    before_date=None,  # 只取此日期之前的记录，None=取最新
    extra_msg=''       # 附加日志信息
)
```

**写入规则：**
- `raw_value` 必须是数值型（int/float）或 None，禁止字符串
- `INSERT OR REPLACE`：同 pub_date+obs_date 已有更高置信度时跳过（保护高质量数据）
- 写入前必须校验 bounds，超出范围打印 `[WARN]`
- 内置重试：locked 重试3次，其他错误重试2次，权限/磁盘满不重试

### 2.6 参数自适应

AKShare 接口签名变化是常态，必须循环尝试多种参数组合。**统一使用 dict 模式**（与 §6.4 一致）：

```python
# 示例：futures_spot_price 多合约尝试
SYM_ALTERNATIVES = {
    "JM": ["焦煤", "炼焦煤", "JM", "jm"],
    "RU": ["橡胶", "天然橡胶", "RU", "ru"],
    "BR": ["丁二烯橡胶", "丁二烯", "BR", "br"]
}

for sym in SYM_ALTERNATIVES.get(symbol, [symbol]):
    try:
        df = akshare.futures_spot_price(symbol=sym, date=date_str)
        if df is not None and not df.empty:
            print(f"[OK] symbol={sym} 有效")
            break
    except Exception as e:
        print(f"[WARN] symbol={sym} 失败: {e}")
        continue
```

### 2.7 Windows 编码处理

所有脚本必须在开头调用编码修复：

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 或使用公共模块
from common.io_win import fix_encoding
fix_encoding()
```

**emoji 使用注意：**
- ✅/⚠️/❌ 等 emoji 在 Windows cmd/GBK 环境下会乱码
- **Python print() 输出**统一替换为：`[OK]` / `[WARN]` / `[ERR]`
- **SOP/文档/注释**中可以使用 emoji（UTF-8 文件无此问题）
- 日志输出避免使用 emoji，改用文字标签

---

### 2.8 跨品种因子注册（强制）

当一个脚本的数据**同时服务多个品种**时（如 LME 铜升贴水同时喂 CU 和 NI），必须在注册表中登记，避免其他开发者重复建脚本。

**注册表路径**：`crawlers/_shared/cross_symbol_factors.yaml`

**注册格式**（YAML）：
```yaml
CU_NI:                              # 跨品种目录名
  description: "LME 铜升贴水 跨品种共享"
  factor_scripts:
    - name: "CU_NI_抓取LME升贴水_EVENT"
      file: "CU_NI/CU_NI_抓取LME升贴水_EVENT.py"
      factor_codes:
        - "CU_NI_LME升贴水"
  served_symbols:                     # 受益品种列表
    - CU
    - NI
```

**适用场景**：
| 场景 | 是否注册 |
|------|----------|
| 脚本只服务 1 个品种（如 `AU_黄金现货.py`） | ❌ 不需要 |
| 脚本数据服务 2+ 品种（如 `CU_NI_抓取LME升贴水.py`） | ✅ 必须注册 |
| 通用工具模块（如 `common/market_data.py`） | ❌ 不需要 |

> ⚠️ 未注册的跨品种脚本会被 `check_factors_l1.py` 标记为「未注册」。创建跨品种脚本时必须同步更新此 YAML。

### 3.1 调度模式选择

| 模式 | 适用场景 | 实现方式 |
|------|---------|---------|
| Subprocess 模式 | 子脚本输出复杂（含 emoji/进度条） | `subprocess.run([python, "-X utf8=1", script, "--auto"])` |
| Import 模式 | 子脚本无输出或纯数据 | `spec.loader.exec_module()` |

### 3.2 Subprocess 模式模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
from datetime import date

# Windows UTF-8 支持
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ── 重要：导入公共 PIT 日期，禁止本地重写 ──
import common  # noqa: ensure common/ is importable
from common.db_utils import get_pit_dates

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

def run(script_name, desc):
    path = os.path.join(SCRIPT_DIR, script_name)
    print(f"▶ {desc}...", end=" ", flush=True)
    result = subprocess.run(
        [PYTHON, "-X utf8=1", path, "--auto"],
        capture_output=True,
        text=False  # Windows: use bytes, decode manually
    )
    if result.returncode == 0:
        print("[OK]")
        return True
    else:
        stderr = result.stderr.decode("utf-8", errors="replace")
        print(f"[ERR] exit={result.returncode}")
        if stderr:
            print(f"  stderr: {stderr[:200]}")
        return False

def main():
    pub_date, obs_date = get_pit_dates()
    print(f"=== {pub_date} | obs={obs_date} ===")
    
    scripts = [
        ("AU_黄金现货.py", "黄金现货"),
        ("AU_白银现货.py", "白银现货"),
        # ... 更多脚本
    ]
    
    ok = sum(run(s, d) for s, d in scripts)
    print(f"\n{'='*40}")
    print(f"完成: {ok}/{len(scripts)} 成功")

if __name__ == "__main__":
    main()
```

### 3.3 Auto / Manual 双模式（推荐）

对于有付费源因子的品种（如 JM），推荐将 run_all.py 拆分为两个执行列表：

```python
# === 自动执行（免费源）===
auto_scripts = [
    "JM_期货收盘价.py",     # AKShare 免费
    "JM_期货持仓量.py",     # AKShare 免费
    "JM_进口量.py",         # 海关总署 免费
    # ... 所有首选抓取可用的因子
]

# === 手动执行（付费源 / 兜底保障回补）===
manual_scripts = [
    "JM_矿山开工率.py",           # Mysteel(年费)
    "JM_甘其毛都口岸蒙煤价格.py",  # 汾渭(年费)
    # ... 无免费源的因子，脚本内部为兜底保障逻辑
]
```

通过 `--auto` / `--manual` 命令行参数控制运行模式：
- `python JM_run_all.py --auto` → 只跑 auto_scripts
- `python JM_run_all.py --manual` → 只跑 manual_scripts
- 不加参数默认跑 auto

实现方式（在 run_all.py 中添加）：

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--auto', action='store_true', help='只跑免费源脚本')
parser.add_argument('--manual', action='store_true', help='只跑付费源/兜底脚本')
args = parser.parse_args()

if args.manual:
    scripts = manual_scripts
else:
    scripts = auto_scripts  # 默认跑 auto
```

---

## 四、开发后检查清单

完成一个新因子脚本后，必须逐项验证：

### 4.1 单脚本测试
```bash
cd D:\futures_v6\macro_engine
python crawlers\AU\AU_黄金现货.py
```
- [ ] 脚本运行无报错
- [ ] 数据正确写入 `pit_data.db`
- [ ] 无需手动输入（或明确标记为手动模式）

### 4.2 run_all.py 更新
- [ ] 新脚本已添加到 `{SYMBOL}_run_all.py`
- [ ] 调度顺序正确（依赖关系：现货→期货→价差→比价）
- [ ] 批量运行所有脚本成功率 100%
- [ ] **跨品种脚本**：已同步更新 `crawlers/_shared/cross_symbol_factors.yaml`（§2.8）

### 4.3 数据质量检查
```bash
python crawlers/common/check_health.py
```
- [ ] 无 CRITICAL 告警
- [ ] 兜底保障回补率 < 10%
- [ ] 数值在合理 bounds 范围内

### 4.4 部署到定时任务

新脚本开发完成后，添加到定时调度。系统使用两种调度方式：

**方式一：OpenClaw cron（推荐，当前系统使用）**

由因子分析师通过 cron 管理，mimo 只需保证脚本路径和参数正确。

**方式二：Windows schtasks（备选）**

```bash
# 每日 20:00 执行品种全量采集
schtasks /create /tn "futures_{SYMBOL}_daily" /tr "python D:\futures_v6\macro_engine\crawlers\{SYMBOL}\{SYMBOL}_run_all.py --auto" /sc daily /st 20:00
```

> 📌 新脚本开发完成后，通知因子分析师添加到对应品种的 cron 任务中。

---

## 五、红线禁止行为

| 禁止项 | 说明 |
|-------|------|
| ❌ 硬编码 obs_date | 必须 `from common.db_utils import get_pit_dates` |
| ❌ 忽略 AKShare TypeError | 接口变化时必须适配新签名 |
| ❌ 静默跳过数据失败 | 每层失败必须记录日志 |
| ❌ 写入非数值型 raw_value | 数据库字段为 REAL，允许 None |
| ❌ 因子命名与 YAML 不一致 | 必须完全匹配引擎配置 |
| ❌ 跳过备源直接兜底保障 | 首选抓取失败后必须尝试至少 1 个备选抓取（除非脚本注释明确标注“无备源”） |
| ❌ 两源都没试就标记 ⛔永久跳过 | 必须首选抓取+备选抓取都失败后才能下结论 |
| ❌ 跨品种脚本未注册 | 服务 2+ 品种的脚本必须注册到 `cross_symbol_factors.yaml`（§2.8） |

---

## 六、数据源自我纠正机制

### 6.1 核心问题

因子分析师提供的数据源存在以下风险：
- 接口已失效（网站改版、API 404）
- 名称/参数错误（AKShare symbol 名称不匹配）
- 遗漏其他可用免费源
- 付费源描述不准确

### 6.2 自动发现与纠正流程

```
收到分析师数据源 → 第一层首选尝试验证 →
│ 成功 → save_to_db 写入（source_confidence=1.0）
│ 失败 → 枚举备选抓取（AKShare 变体 / 交易所官网 / 东方财富等） →
│   发现可用备选 → save_to_db 写入（source_confidence=0.9）+ 通知分析师
│   备选也失败 → save_l4_fallback() 兜底保障回补
│   无历史值 → 标记 ⛔永久跳过 + 记录到 ISSUES.md
```

### 6.3 替代数据源枚举表

> ⚠️ 替代源直接写在**每个因子脚本的第一层/第二层注释**中，不依赖外部注册文件。
> 下面的 `BACKUP_PATTERNS` 仅作为**备选思路参考**，不要求维护为独立文件。

在脚本内维护首选→备选映射（示例）：

```python
"""
第一层（首选）: akshare.futures_main_sina(symbol='AU0')     # 上海黄金T+D
第二层（备选）: akshare.spot_golden_benchmark_sge()         # SGE现货基准价
             + akshare.futures_zh_daily_sina('AU9999')  # 9999合约行情
第三层（兜底）: save_l4_fallback()                          # 历史值回补
"""
```

各品种常见备选思路（不强制，供编写脚本时参考）：

```python
# 编写脚本时参考以下思路，实际备源写在脚本注释中
# AU: 黄金现货 → spot_golden_benchmark_sge / futures_main_sina('AU0')
# JM: 焦煤现货 → futures_spot_price(symbol=焦煤/炼焦煤) / 兜底保障回补
# CU: 铜库存 → futures_shfe_warehouse_receipt / futures_inventory_em
```

### 6.4 参数自适应枚举（强制规范）

**AKShare symbol 参数枚举规则**：因子分析师给的 symbol 名称往往只是其中一个变体，必须多试：

```python
# 场景1：futures_spot_price 合约名称变体
SYM_ALTERNATIVES = {
    "JM": ["焦煤", "炼焦煤", "JM", "jm", "jmk"],
    "RU": ["橡胶", "天然橡胶", "RU", "ru"],
    "BR": ["丁二烯橡胶", "丁二烯", "BR", "br"]
}

for sym in SYM_ALTERNATIVES.get("JM", ["JM"]):
    try:
        df = akshare.futures_spot_price(symbol=sym, date=date_str)
        if df is not None and len(df) > 0:
            print(f"[OK] symbol={sym} 有效")
            break
    except Exception as e:
        print(f"[WARN] symbol={sym} 失败: {e}")
        continue

# 场景2：futures_inventory_em 品种名变体
INV_ALTERNATIVES = {
    "AG": ["白银", "黄金", "铜", "铝"],
    "AU": ["黄金", "白银"],
    "BR": ["丁二烯橡胶"]
}
```

**接口名称变体**：同一个数据可能由多个 AKShare 接口提供：

```python
# 同一数据，多个接口尝试
INTERFACE_ALTERNATIVES = {
    "黄金现货价": [
        ("spot_golden_benchmark_sge", {}),
        ("futures_main_sina", {"symbol": "AU0"}),
        ("spot_precious_metal_sge", {})
    ],
    "橡胶期货价": [
        ("futures_main_sina", {"symbol": "NR0"}),
        ("futures_zh_subscribe", {})  # 可能是旧接口
    ],
    "BDI指数": [
        ("macro_shipping_bdi", {}),
        ("fredgraph_csv", {"series_id": "BALTECHALLINDEX"})
    ]
}
```


### 6.5 失败日志与 ISSUES.md 更新

**每个因子脚本必须记录尝试过的所有失败源**：

```python
failed_sources = []

try:
    df = akshare.spot_golden_benchmark_sge()
except Exception as e:
    failed_sources.append(f"spot_golden_benchmark_sge: {e}")

try:
    r = fetch_url(...)
except Exception as e:
    failed_sources.append(f"新浪行情: {e}")


if failed_sources:
    print(f"[WARN] 数据源尝试记录: {failed_sources}")
    # 写入数据库 兜底保障回补值（如果有）
    # 并追加到 ISSUES.md 待解决清单
```

**ISSUES.md 记录规范**（路径：`D:\futures_v6\macro_engine\ISSUES.md`）：
```markdown
## P1 - JM_焦煤现货（无免费源）
- 因子分析师推荐: futures_spot_price(symbol="焦煤")
- 实际结果: AKShare返回空DataFrame
- 尝试过的替代源:
  - futures_spot_price 变体（焦煤/炼焦煤/JM）→ 均空
  - SHFE官网 → 404 Not Found
  - 东方财富 → 需登录
- 当前状态: ⛔永久跳过（汾渭/ Mysteel 付费）
- 解决方式: 付费订阅 / 手动录入
```


### 6.6 数据源有效性预检（开发阶段）


在正式编写脚本前，先用以下命令预检数据源是否有效：

```python
import akshare as ak
# 快速验证接口是否存在 + 是否返回数据
df = ak.spot_golden_benchmark_sge()
print(df.head(3))
print(df.columns.tolist())
print(df.dtypes)
```

**预检不通过的标准**：
- 接口抛出 `AttributeError`（方法不存在，AKShare 版本问题）
- 返回空 DataFrame（数据源确实没有）
- 返回 404/403（网站改版或需要登录）
- 超时（5秒内无响应）

预检通过后再编写脚本，避免白写。

### 6.7 通知机制（可选）

当脚本发现比分析师推荐更好的数据源时，记录到日志并通知：
```python
# 发现新数据源时
print(f"[INFO] 发现更优数据源: {new_source} (替代分析师推荐: {analyst_source})")
# 追加到脚本注释中，后续交接有据可查
```

---

## 七、永久跳过因子标记规范

`⛔永久跳过` 标记必须在首选抓取+备选抓取都失败后才使用，不能仅凭首选抓取失败就下结论。

脚本头部状态标注格式：

```python
"""
当前状态: [✅正常 | ⚠️待修复 | ⛔永久跳过]
- 首选抓取尝试结果（如 AKShare 失败原因）
- 备选抓取尝试结果（如交易所官网失败原因）
- 解决方案（付费订阅/手动录入/等待接口恢复）
- 不写占位符（兜底保障回补也无效时才写 ⛔）

订阅优先级: ★~★★★★★（仅付费源标注）
替代付费源: 具体平台名称
"""
```

**判断标准**：同时满足以下两点才标记 ⛔：
1. 首选抓取失败 + 备选抓取失败（至少尝试了2个数据源）
2. `save_l4_fallback()` 也无法回补（无历史数据）

---

## 八、快速参考

| 操作 | 命令/路径 |
|------|----------|
| 操作手册 | `D:\futures_v6\macro_engine\references\` |
| 数据库 | `D:\futures_v6\macro_engine\pit_data.db` |
| 品种目录 | `D:\futures_v6\macro_engine\crawlers\{SYMBOL}\` |
| 引擎配置 | `D:\futures_v6\macro_engine\config\factors\{SYMBOL}\` |
| 公共模块 | `D:\futures_v6\macro_engine\crawlers\common\` |
| 跨品种注册 | `D:\futures_v6\macro_engine\crawlers\_shared\cross_symbol_factors.yaml` |
| 健康检查 | `cd D:\futures_v6\macro_engine && python crawlers/common/check_health.py` |
| 数据验证 | `cd D:\futures_v6\macro_engine && python crawlers/common/check_health.py --alert` |
| 兜底保障函数 | `from common.db_utils import save_l4_fallback` |
| 历史补采 | `set BACKFILL_DATE=2024-01-15 && python {脚本}.py --auto`（cmd）或 `$env:BACKFILL_DATE="2024-01-15"; python {脚本}.py --auto`（PowerShell） |

---

*本文档基于 `D:\futures_v6\macro_engine` 工程实践总结，适用于 AKShare + SQLite 技术栈的期货基本面数据采集系统。*
