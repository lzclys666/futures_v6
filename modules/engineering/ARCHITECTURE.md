# 程序员mimo 工程实践手册

> 作者: 程序员mimo 🕷️  
> 版本: v1.0  
> 更新: 2026-05-01  
> 定位: 期货基本面量化系统的数据采集工程师，系统的数据供给者

---

## 一、身份与职责

**我是谁:** 期货智能交易系统的数据采集工程师。引擎程序员、测试程序员、UI设计师都依赖我产出的数据。数据质量有问题，系统输出就不可信。

**核心职责:**
1. 为每个品种每个因子编写独立爬虫脚本
2. 按 PIT（Point-in-Time）规范写入数据库
3. 保证数据质量：每日日志确认 + 每周 check_health.py
4. 历史数据回填：至少 2023-01-01 至今

**不归我管的事:** 因子分析、策略开发、引擎配置yaml以外的逻辑

---

## 二、核心工程原则

### 2.1 四层漏斗数据采集策略（最高优先级）

**原则：免费优先，收费兜底。每层独立try-except，上一层成功即写入，不再尝试下层。**

| 层级 | 来源 | source_confidence | 强制要求 |
|------|------|------------------|---------|
| L1 免费+权威 | 官方API（FRED/交易所）、AKShare、 Sina/腾讯财经实时行情 | 1.0 | 必须首先尝试 |
| L2 免费+聚合 | BigQuant、JoinQuant、Alpha Vantage、东方财富公开页面 | 0.9 | L1失败后 |
| L3 付费+爬虫 | 隆众资讯、SMM、Mysteel（年费）、汾渭能源（年费） | 0.8 | L2失败后，需标注付费来源 |
| L4 兜底 | 数据库历史最新值回补、手动录入 | 0.5/0.6 | 所有外部源失效时 |

**禁止行为:**
- 跳过L1直接宣告"无免费数据源"
- 数据失败时静默跳过整条链路
- 付费数据源未在脚本头部标注来源

### 2.2 PIT 日期规范

```
pub_date  = 脚本运行日期（脚本自身获取）
obs_date  = 数据观测日期（外部数据实际发生的日期）

周一 obs_date 处理：
  today = date.today()
  dow = today.weekday()  # Monday=0
  if dow == 0:  # 周一
      obs_date = today - timedelta(days=3)  # 回退到上周五
```

**禁止行为:**
- 硬编码 obs_date（如 `date="20260417"`）
- pub_date 和 obs_date 混淆

### 2.3 数据写入规范

```python
# ✅ 正确：数值型 raw_value
raw_value = float(df.iloc[0]['close'])

# ❌ 错误：字符串 raw_value
raw_value = df.iloc[0]['name']  # '螺纹钢' → TypeError 或数据污染

# ✅ 正确：合理性校验 + bounds
if not (MIN_VALUE <= raw_value <= MAX_VALUE):
    print(f"[WARN] {factor_code}={raw_value} 超出范围 [{MIN_VALUE}, {MAX_VALUE}]")

# ✅ 正确：INSERT OR REPLACE + 3次重试
for attempt in range(3):
    try:
        db_utils.save_to_db(factor_code, obs_date, raw_value, source, source_confidence)
        break
    except Exception as e:
        if attempt == 2:
            raise
```

---

## 三、已验证的免费数据源资产

> 以下是经过实战验证的稳定免费数据源，是我的"宝藏地图"。

### 3.1 宏观/外汇

| 数据 | 来源 | 接口/URL | 备注 |
|------|------|---------|------|
| USDCNY 汇率 | 新浪财经 | `hq.sinajs.cn/list=USDCNY` | 实时，close price at parts[8] |
| DXY 美元指数 | FRED CSV | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS` | trade-weighted broad dollar index |
| 美国10Y国债收益率 | FRED CSV | `fredgraph.csv?id=DGS10` | 替代失效的 AKShare bond_zh_us_rate |
| 美国10Y通胀保护国债(TIPS) | FRED CSV | `fredgraph.csv?id=DFII10` | TA_CST_BRENT bounds校准用 |
| 金银比 | SGE | `spot_golden_benchmark_sge` + `spot_silver_benchmark_sge` | 白银单位是 CNY/kg，需÷1000 |

### 3.2 期货行情

| 数据 | 来源 | 接口 | 备注 |
|------|------|------|------|
| 主力期货价格+持仓量 | AKShare | `futures_main_sina(symbol)` | 支持 RU0/AL0/NR0 等 |
| 期货日行情 | AKShare | `futures_zh_daily_sina(symbol)` | 包含 open/close/high/low |
| SHFE/DCE持仓排名 | AKShare | `get_shfe_rank_table()` / `get_dce_rank_table()` | 仅支持沪铜/螺纹等 |
| 仓单/库存 | AKShare | `futures_inventory_em(symbol)` | 部分品种可用 |

### 3.3 特殊发现

| 发现 | 来源 | 说明 |
|------|------|------|
| EIA BRENT原油 | `https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO_KEY` | **无需注册**，返回 UK Brent $/BBL |
| COMEX白银 | `ak.futures_main_sina("SI0")` | 返回 COMEX 白银期货数据（美分/oz） |
| BDI 波罗的海指数 | AKShare | `macro_shipping_bdi()` 返回 1988-10 至今，9435行 |
| 新浪 ALU.cn LME铝 | `hq.sinajs.cn/list=ALU.cn` | GB2312编码，需 `r.encoding='gbk'` |

---

## 四、踩坑编年史（事故档案）

> 每一个坑都有代价。记录它们，不要重蹈覆辙。

### 4.1 批量脚本覆盖事故（P0级别）⛔

**日期:** 2026-04-18  
**事故:** `update_scripts.py` 误执行，覆盖了103个脚本，项目几近毁灭  
**根因:** 未验证脚本安全性，未做快照就执行危险操作  
**代价:** 花了数小时从桌面备份和会话临时文件逐个恢复  
**教训:**
- **危险操作（批量写文件/修改）前必须先 `git add -A; git commit` 做快照**
- 恢复后立即 commit，建立安全基准线
- 批量脚本写入后必须立即 `git diff` 验证

### 4.2 db_utils.save_to_db() 参数顺序颠倒（P0级别）

**日期:** 2026-04-19  
**事故:** 约72处调用中 source 和 source_confidence 参数顺序颠倒  
**根因:** 函数签名和调用处参数名相似，容易搞混  
**修复:** 统一为 `save_to_db(factor_code, obs_date, raw_value, source, source_confidence)`  
**教训:** 有歧义的参数顺序是隐性炸弹，发现后立即全量扫描替换

### 4.3 M_STK_WARRANT 数据源张冠李戴

**日期:** 2026-04-19  
**事故:** M_抓取仓单.py 错误使用 CZCE 菜粕(RM)仓单数据，而非豆粕(M)  
**根因:** AKShare `futures_inventory_em(symbol='豆粕')` 返回的是 RM(菜粕)数据  
**正确数据源:** `akshare_futures_inventory_em(symbol='豆粕')`  
**教训:** AKShare 的 symbol 名称和实际品种并非总是精确匹配，需要实测验证

### 4.4 SHFE 仓单/持仓接口全面失效

**日期:** 2026-04-20  
**事故:** SHFE 官网所有数据接口返回 404（网站改版），AKShare `futures_shfe_warehouse_receipt` JSONDecodeError  
**影响品种:** AL(RB)_INV_SHFE 永久跳过  
**教训:** 交易所官网接口不是可靠的 L1 数据源，需要多源冗余

### 4.5 NR橡胶历史数据断档

**日期:** 2026-04-19  
**事故:** NR 橡胶数据库只有37行（最近1-3天），每日 run_all 只采集当天数据  
**根因:** 没有一次性批量回补机制  
**修复:** `NR_回填历史数据.py` 一次性回填 4807行（2023-01-01 → 2026-04-17）  
**教训:** 新品种上线第一天就要确认历史数据是否完整

### 4.6 AU黄金因子重建：SHFE/SDR/FOMC全失效

**日期:** 2026-04-20  
**事故:** 5个因子发现无免费源：AU_SPD_GLD(SPDR改版)/AU_SHFE_RANK(SHFE改版)/AU_FED_DOT(FOMC改版)  
**教训:**
- AKShare 不支持 SHFE 的 DCE 席位排名（只能DCE）
- FOMC projections 页面返回404/403（FRED超时）
- SPDR 网站需要 JS 加载，Yahoo 403

### 4.7 全量硬编码日期扫描

**日期:** 2026-04-19  
**发现:** 11处 `date="20260417"` 硬编码，涉及 AG/AL/BR/M/RU/SA 等9个文件  
**修复:** 统一替换为 `date=obs_date.strftime("%Y%m%d")`  
**教训:** AKShare 接口调用中的日期参数必须动态传入，不能偷懒

### 4.8 TA_PX 历史数据污染

**日期:** 2026-04-19  
**事故:** TA_CST_PX 污染值 850.00 来自 AKShare 错误数据（2025-04-15的旧值）  
**修复:** DELETE + UPDATE 清理重复记录 + UPDATE raw_value  
**教训:** PTA 加工差(PX CFR)无免费可靠源，需订阅隆众/普氏

---

## 五、Windows 编码处理规范

> 这是最容易踩的坑，也是最容易忽略的坑。

### 5.1 核心原则

Windows cmd/powershell 默认 GBK 编码。Python 子进程输出中文时：
- **emoji（⚠️ ❌ ✅）= 100% 乱码**
- **中文日志 = 高概率乱码**

### 5.2 解决方案

**方案A：所有子脚本输出 [OK]/[WARN]/[ERR] 替代 emoji**

```python
# ✅ 正确
print("[OK] 数据写入成功")
print(f"[WARN] {factor_code}={raw_value} 超出 bounds")

# ❌ 错误
print("✅ 数据写入成功")  # cmd 中乱码
```

**方案B：subprocess 调用时强制 UTF-8**

```python
# ✅ 正确：-X utf8=1 标志
result = subprocess.run(
    [python, "-X", "utf8=1", script, "--auto"],
    capture_output=True,
    env={**os.environ, "PYTHONIOENCODING": "utf-8"}
)
# 注意：capture_output=True 不能与 stderr=DEVNULL 共用
# → 用 stdout=PIPE, stderr=PIPE

# ✅ 正确：子脚本内部 fix_encoding()
from common.io_win import fix_encoding
fix_encoding()  # 必须在本模块 import 任何可能输出中文的库之前调用
```

**方案C：io_win.py 标准化封装**

```python
# crawlers/common/io_win.py 是所有爬虫的标准入口
from common.io_win import fix_encoding
fix_encoding()  # 在任何其他 import 之前调用
```

### 5.3 三种运行模式下的编码处理

| 模式 | 父进程 | 子进程 | 注意事项 |
|------|--------|--------|---------|
| 直接运行 `python xx.py` | 自动 UTF-8 | - | 无需处理 |
| subprocess.run() | capture_output | 必须 `-X utf8=1` | 不用 DEVNULL |
| cron/自动采集 | 系统编码 | 必须 `-X utf8=1` | PYTHONIOENCODING=utf-8 |

---

## 六、AKShare 适配经验

### 6.1 版本敏感性

- 当前环境: akshare 1.14.23
- 接口签名可能随版本变化，升级后必须验证
- 不存在的接口: `currency_zh_usd_spot`, `futures_investing_base`, `energy_oil_hist`(BRENT)

### 6.2 常见失败模式

```python
# 失败模式1：返回空 DataFrame
df = akshare.futures_spot_price(date=obs_date.strftime("%Y%m%d"))
if df.empty:
    # 尝试备用参数组合
    for start_date, end_date in param_combos:
        df = akshare.futures_spot_price(start_date=start_date, end_date=end_date)
        if not df.empty:
            break

# 失败模式2：TypeError 签名变化
try:
    df = akshare.futures_xxx(symbol="RU0", date="20260420")
except TypeError as e:
    # 尝试不同参数顺序或参数名
    df = akshare.futures_xxx("RU0")

# 失败模式3：KeyError 列名变化
try:
    price = df["close"]
except KeyError:
    # 尝试自动匹配列名
    price_col = [c for c in df.columns if "close" in c.lower() or "结算" in c][0]
    price = df[price_col]
```

### 6.3 品种代码映射

| AKShare symbol | 实际品种 |
|----------------|---------|
| "AL0" | 沪铝 |
| "RU0" | 橡胶 |
| "NR0" | NR橡胶 |
| "M0" | 豆粕 |
| "Y0" | 豆油 |
| "PP0" | 聚丙烯 |
| "PB0" | 铅 |
| "EG0" | 乙二醇 |
| "SI0" | COMEX白银 |

---

## 七、批量操作安全规范

> 这是最容易被突破的红线。每次都是"就改一点点"的心态出的事。

### 7.1 操作分级

| 级别 | 操作 | 安全要求 |
|------|------|---------|
| **危险** | 批量写文件、sed/replace 全量替换、git reset --hard | **必须先 git commit 快照** |
| **敏感** | 修改 run_all.py、新增因子脚本 | 修改后立即手动运行验证 |
| **常规** | 单个脚本调试、数据库查询 | 无特殊要求 |

### 7.2 危险操作检查清单

```bash
# 批量写文件前必须执行
git add -A && git commit -m "快照: 批量修改前"

# 修改后必须验证
git diff --stat

# 确认无问题后
git push
```

### 7.3 run_all.py 设计原则

- **不要从外部传入 obs_date** — 每个因子脚本内部自己用 `get_pit_dates()` 获取
- **统一 subprocess 调用方式** — `python "-X" "utf8=1"` 是标准写法
- **不要在 run_all.py 里硬编码任何数据**

---

## 八、cron 任务管理

### 8.1 任务配置规范

```python
# 标准 cron 任务 payload
payload = {
    "script": "D:\\futures_v6\\macro_engine\\crawlers\\{品种}\\run_all.py",
    "workdir": "D:\\futures_v6\\macro_engine\\crawlers\\{品种}",
    "python": "python"
}

# 标准触发时间
schedule = "0 20 * * 1-5"  # 周一~周五 20:00 CST
```

### 8.2 触发后必做验证

1. 检查 cron runs 历史是否有失败
2. 查看 `crawlers/logs/` 最新日志
3. 运行 `check_health.py --alert` 确认无CRITICAL告警

---

## 九、数据质量检查

### 9.1 check_health.py 使用

```bash
# 标准检查
python crawlers/common/check_health.py

# 精简告警
python crawlers/common/check_health.py --alert

# JSON格式（供程序解析）
python crawlers/common/check_health.py --json
```

### 9.2 关注指标

| 指标 | 阈值 | 处理方式 |
|------|------|---------|
| L4回补率 | > 10% 需关注 | 检查对应品种数据源是否失效 |
| bounds异常 | 0个为正常 | 检查因子计算逻辑 |
| 超过30天无数据 | 需清理 | 检查脚本是否正常运行 |
| symbol=None | 必须为0 | DELETE 清理脏数据 |

---

## 十、永久跳过因子策略

> 这是经过验证的结论：无免费源的因子，永远不写占位符，不做无意义的L4回补。

### 10.1 永久跳过清单（按品种）

| 品种 | 因子 | 无免费源原因 | 付费替代 |
|------|------|------------|---------|
| TA | TA_CST_PX (PTA加工差) | 隆众/普氏付费 | 隆众资讯年费 |
| TA | TA_CST_PROCESSING_FEE | 依赖PX | 同上 |
| SA | 区域纯碱现货价格(3个) | 无区域覆盖 | 隆众资讯年费 |
| BR | 丁二烯/轮胎开工率/汽车销量 | 隆众/SMM付费 | 同上 |
| JM | 焦煤口岸/库存/利润 | 汾渭/Mysteel付费 | 汾渭年费 |
| RB | 螺纹钢表需/社会库存 | Mysteel付费 | Mysteel年费 |
| AL | 批次2/3/4 | SMM/Mysteel/铝道网付费 | SMM年费 |
| M | 豆类USDA/生猪存栏 | USDA/卓创付费 | USDA付费接口 |
| NR | NR_STK_WARRANT | INE无公开仓单 | 无 |
| AU | AU_SPD_GLD | SPDR改版/Yahoo 403 | 无免费替代 |
| AU | AU_SHFE_RANK | SHFE改版404 | 无免费替代 |
| AU | AU_FED_DOT | FOMC改版404 | 无免费替代 |
| AL | AL_INV_SHFE | SHFE官网404+AKShare失效 | Mysteel年费 |
| RB | RB_INV_SHFE | 同上 | Mysteel年费 |

### 10.2 跳过时的脚本规范

```python
# 在脚本中打印明确跳过原因
print("[跳过] 无免费数据源（付费订阅:隆众资讯）")
# auto模式下直接 return，不写入任何数据
if '--auto' in sys.argv:
    return
```

---

## 十一、新品种开发流程

### 11.1 优先级判断

```
P0: 期货交易所直接有数据的品种（RU/CU/I/AL/RB/JM/M/TA/AU/AG/BR/NR等）
    → futures_main_sina + futures_inventory_em + get_shfe_rank_table 覆盖

P1: 宏观/汇率相关（USDCNY/DXY/美债收益率）
    → FRED CSV + 新浪财经

P2: 需要行业付费数据的品种
    → Mysteel/SMM/隆众
```

### 11.2 开发检查清单

- [ ] 脚本在 `--auto` 模式下运行成功
- [ ] 数据正确写入 `pit_data.db`
- [ ] `run_all.py` 包含新脚本且顺序正确
- [ ] 批量运行全部成功（9/9 或 7/7）
- [ ] obs_date 动态传入，无硬编码日期
- [ ] raw_value 数值型，无字符串
- [ ] emoji 替换为 [OK]/[WARN]/[ERR]
- [ ] 历史数据回填（2023-01-01 至今）

---

## 十二、项目结构规范

```
D:\futures_v6\macro_engine\
├── crawlers\
│   ├── {品种}\              # 每个品种一个目录
│   │   ├── run_all.py      # 采集入口
│   │   ├── {品种}_抓取xxx.py
│   │   └── {品种}_计算xxx.py
│   ├── common\              # 公共模块
│   │   ├── db_utils.py
│   │   ├── io_win.py       # Windows编码修复（必须 import）
│   │   ├── market_data.py  # 统一行情获取
│   │   ├── web_utils.py    # HTTP请求封装
│   │   └── check_health.py # 数据质量检查
│   └── logs\               # 运行时日志
├── config\
│   └── factors\{品种}\     # YAML配置（引擎用）
├── research\reports\{品种} # 研究报告
├── pit_data.db             # SQLite数据库
└── ARCHITECTURE.md         # 本文档
```

---

## 附录：常用命令参考

```bash
# 数据库查询
python crawlers/common/check_db.py

# 检查因子覆盖
python crawlers/check_factors.py

# 验证数据库
python crawlers/verify_db.py

# 查看 cron 任务状态
openclaw cron list

# 触发 cron 任务
openclaw cron run <job_id>
```

---

*本文档是个人经验沉淀，随项目演进持续更新。*
*最后更新：2026-05-01 by 程序员mimo 🕷️*
