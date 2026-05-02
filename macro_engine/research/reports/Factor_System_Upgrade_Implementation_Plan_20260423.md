# 因子系统升级改造详细实施计划

> **文档版本**：v1.1（已对齐技术架构V6.0）  
> **制定日期**：2026-04-23  
> **制定人**：因子分析师 YIYI  
> **状态**：待执行  
> **存放路径**：`D:\futures_v6\macro_engine\research\reports\Factor_System_Upgrade_Implementation_Plan_20260423.md`

---

## 一、目标与范围

### 1.1 升级目标

将因子走势监控系统从"展示工具"升级为"决策辅助系统"，具体达成：

| 维度 | 现状 | 目标 |
|------|------|------|
| 统计方法 | IC 均值，点估计 | IC 中位数 + Bootstrap 95% CI + HMM Regime |
| 可视化 | 因子走势单图 | 三图联动 + 热力图 + 动态动画 |
| 数据质量 | 基础校验 | pandera Schema + PIT 冒烟测试 + Parquet |
| 信号输出 | 方向判断 | 多维评分（0~100）+ 拥挤度 + 动态持有期 |
| 实用功能 | 无 | 失效预警 + 私人标注 + 多品种看板 |

### 1.2 升级范围

**纳入升级的品种**（共22个）：
```
贵金属：  AU / AG
有色金属：CU / AL / ZN / NI / PB / SN
黑色系：  RB / HC / I / J / JM
化工：   TA / EG / PP / BU / FU / SA
农产品：  M / Y / P
软商品：  RU / NR / BR / LC / LH
```

**升级覆盖的因子**（已验证 Phase 1~4）：

| 阶段 | 因子数 | 代表因子 |
|------|--------|---------|
| Phase 1（共用） | ~10 | 金银比、USD/CNY变化量、CN10Y变化量 |
| Phase 2（LME系） | ~5 | LME铜升贴水差分、LME镍升贴水差分 |
| Phase 3（品种特有） | ~20 | CU TC/冶炼利润、RU 轮胎开工率等 |
| Phase 4（宏观） | ~5 | WTI/布伦特原油、中美利差 |

### 1.3 不纳入范围

- 因子库以外的全新品种开发
- 回测引擎重写（仅升级监控展示层面）
- 实盘交易接口对接

---

## 二、当前系统状态评估

### 2.1 已具备的能力

```
✅ 22个品种的基础爬虫交付文档（dataloader + 备用源 + 告警规则）
✅ Phase 1~4 因子 IC/IR 实证验证（部分品种）
✅ 4个品种的前端展示（需确认具体品种和完成度）
✅ 金银比、LME升贴水、USD/CNY、CN10Y、布伦特原油数据管道
✅ AKShare 数据采集基础设施
```

### 2.2 存在的短板

```
⚠️ 数据就绪状态未经系统性审计（历史完整性、实时管道存活率）
⚠️ 18个品种前端展示尚未完成
⚠️ pandera / PIT 数据校验体系未建立
⚠️ 因子 IC Bootstrap CI / HMM Regime 模块未开发
⚠️ 拥挤度监控 / 动态持有期 / 失效预警等模块未开发
⚠️ 多因子 IC 热力图未开发
```

---

## 三、实施路线图

```
整体工期：约 5 周（工作日）
关键里程碑：
  Week 1  → 数据就绪审计完成 ✅
  Week 2  → 数据管道修复 + 基础框架搭建 ✅
  Week 3  → 统计模块（Bootstrap CI / HMM）✅
  Week 4  → 信号系统 + 可视化升级 ✅
  Week 5  → 全品种推广 + 调优 ✅
```

---

## 四、详细实施步骤

---

### 【Phase 0】数据就绪审计  ▶ Week 1

> **目标**：摸清数据家底，建立"可升级因子清单"和"待修复数据清单"

#### Step 0.1：因子数据文件审计

**执行时间**：Day 1~2

**操作**：对每个核心因子文件执行以下检查脚本

```python
# audit_factor_data.py — 因子数据完整性审计
import pandas as pd
import numpy as np
from pathlib import Path

DATA_ROOT = Path(r'D:\futures_v6\macro_engine\data')

factors = {
    '金银比':          DATA_ROOT / 'crawlers/_shared/daily/AU_AG_ratio_corrected.csv',
    'USD_CNY现货':     DATA_ROOT / 'crawlers/_shared/daily/USD_CNY_spot_daily.csv',
    'CN10Y国债':       DATA_ROOT / 'crawlers/_shared/daily/CN_US_bond_yield_full.csv',
    'LME铜升贴水':     DATA_ROOT / 'crawlers/LME/copper/LME_copper_spot3m_spread.csv',
    'LME镍升贴水':     DATA_ROOT / 'crawlers/LME/nickel/LME_nickel_spot3m_spread.csv',
    '布伦特原油':       DATA_ROOT / 'crawlers/_shared/daily/Brent_crude.csv',
    'CU_AL比价':       DATA_ROOT / 'crawlers/shared/daily/CU_AL_ratio.csv',
}

results = []
for name, path in factors.items():
    if not path.exists():
        results.append({'因子': name, '状态': 'FILE_MISSING', '有效行数': 0, '时间覆盖': 'N/A', '最近更新': 'N/A'})
        continue
    df = pd.read_csv(path, parse_dates=['date'] if 'date' in pd.read_csv(path, nrows=1).columns else [0])
    col_date = df.columns[0]
    df[col_date] = pd.to_datetime(df[col_date])
    df = df.dropna()
    n_rows = len(df)
    date_range = f"{df[col_date].min().date()} ~ {df[col_date].max().date()}"
    days_span = (df[col_date].max() - df[col_date].min()).days
    expected = days_span  # 粗略期望天数
    completeness = n_rows / days_span * 100 if days_span > 0 else 0
    results.append({
        '因子': name,
        '状态': 'OK' if completeness > 85 else 'LOW_COMPLETENESS',
        '有效行数': n_rows,
        '时间覆盖': date_range,
        '最近更新': df[col_date].max().date(),
        '完整度%': round(completeness, 1)
    })

df_result = pd.DataFrame(results)
print(df_result.to_string())
df_result.to_csv('D:/futures_v6/macro_engine/research/reports/audit_factor_data_20260423.csv', index=False)
```

**判断标准**：

| 完整度 | 状态 | 行动 |
|--------|------|------|
| ≥ 90% | 🟢 OK | 可直接进入升级 |
| 70%~90% | 🟡 需补充 | 制定补采计划 |
| < 70% | 🔴 不可用 | 降级为观察因子或搁置 |

**交付物**：`audit_factor_data_20260423.csv` — 每个因子的完整度报告

---

#### Step 0.2：品种价格数据审计

**执行时间**：Day 2~3

**操作**：验证 AKShare 能否稳定获取 22 个品种的期货日线数据

```python
# audit_price_data.py — 品种价格数据审计
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

symbols = {
    'AU': 'au0', 'AG': 'ag0', 'CU': 'cu0', 'AL': 'al0',
    'ZN': 'zn0', 'NI': 'ni0', 'PB': 'pb0', 'SN': 'sn0',
    'RB': 'rb0', 'HC': 'hc0', 'I':  'i0',
    'J':  'j0',  'JM': 'jm0',
    'M':  'm0',  'Y':  'y0',  'P':  'p0',
    'TA': 'ta0', 'EG': 'eg0', 'PP': 'pp0',
    'BU': 'bu0', 'FU': 'fu0', 'SA': 'sa0',
    'RU': 'ru0', 'NR': 'nr0', 'BR': 'br0',
    'LC': 'lc0', 'LH': 'lh0',
    'SC': 'sc0', 'AO': 'ao0',
}

results = []
for name, symbol in symbols.items():
    try:
        df = ak.futures_zh_daily_sina(symbol=symbol)
        n = len(df)
        latest = df['date'].max() if 'date' in df.columns else 'N/A'
        results.append({'品种': name, '合约': symbol, '状态': 'OK', '行数': n, '最新日期': str(latest)})
    except Exception as e:
        results.append({'品种': name, '合约': symbol, '状态': f'ERROR: {e}', '行数': 0, '最新日期': 'N/A'})

df_result = pd.DataFrame(results)
print(df_result.to_string())
df_result.to_csv('D:/futures_v6/macro_engine/research/reports/audit_price_data_20260423.csv', index=False)
```

**判断标准**：

| 状态 | 行动 |
|------|------|
| 最新日期 ≤ 3交易日前 | 🟢 OK |
| 最新日期 4~10交易日前 | 🟡 需补采 |
| ERROR 或 最新日期 > 10交易日前 | 🔴 需修复采集管道 |

**交付物**：`audit_price_data_20260423.csv`

---

#### Step 0.3：实时数据管道健康检查

**执行时间**：Day 3~4

**检查项**：

| 管道任务 | 检查方式 | 正常指标 |
|---------|---------|---------|
| LME ZN/PB/SN 每日采集 | 查 `D:\futures_v6\macro_engine\data\crawlers\LME\{metal}\` 最新文件 | 文件日期 = 最近交易日 |
| AKShare 宏观数据采集 | 查 `D:\futures_v6\macro_engine\data\crawlers\_shared\daily\` USD_CNY / CN10Y | 文件日期 = 最近交易日 |
| Brent 原油采集 | 查 `D:\futures_v6\macro_engine\data\crawlers\_shared\daily\Brent_crude.csv` | 最新日期 ≤ 2交易日前 |

**Cron 任务清单**（需验证存活）：

```bash
# 验证 cron 任务是否存活
openclaw cron list
```

| 任务名 | 频率 | 上次执行 | 状态 |
|--------|------|---------|------|
| `OpenClaw_LME_ZN_PB_SN` | 周一至五 17:05 | ? | 待确认 |
| `OpenClaw_Macro_Daily` | 周一至五 17:30 | ? | 待确认 |

---

#### Step 0.4：IC 窗口长度评估

**执行时间**：Day 4~5

**目的**：确认每个因子有多少个有效 IC 计算窗口，决定可上线哪些统计模块

```python
# assess_ic_window.py
import pandas as pd
import numpy as np
from scipy import stats

DATA_ROOT = r'D:\futures_v6\macro_engine\data'
REPORTS   = r'D:\futures_v6\macro_engine\research\reports'

# 定义因子文件路径（取 Step 0.1 结果）
# 定义品种合约（取 Step 0.2 结果）

def assess_ic_window(factor_path, price_symbol, hold=5):
    """
    评估某因子对某品种的 IC 时间序列有效长度
    返回：IC序列长度、IC>0.02比例、建议持有期
    """
    fac = pd.read_csv(factor_path, parse_dates=[0], index_col=0)
    # ... 获取 price ...
    ic_series = compute_rolling_ic(fac, price, window=60, hold=hold)
    ic_valid = ic_series.dropna()
    return {
        'IC序列长度': len(ic_valid),
        'IC>0.02比例': (ic_valid.abs() > 0.02).mean(),
        'IR': ic_valid.mean() / ic_valid.std() * np.sqrt(252/hold) if ic_valid.std() > 0 else 0,
        '可做Bootstrap': len(ic_valid) >= 120,
        '可做HMM': len(ic_valid) >= 240,
    }

# 矩阵输出：因子 x 品种
```

**判断标准**：

| 指标 | 🟢 可用 | 🟡 观察 | 🔴 不可用 |
|------|--------|--------|---------|
| IC序列长度 | ≥ 240天 | 60~239天 | < 60天 |
| IC>0.02比例 | ≥ 50% | 30%~50% | < 30% |

---

#### Step 0.5：数据就绪审计报告输出

**执行时间**：Day 5（本周最后一天）

**交付物**：`Factor_Data_Readiness_Report_20260423.md`

```
# 因子数据就绪审计报告 — 2026-04-23

## 审计结论总览

| 因子 | 状态 | IC序列长度 | 可做Bootstrap | 可做HMM | 可升级模块 |
|------|------|-----------|--------------|--------|-----------|
| 金银比 | 🟢 | 500+ | ✅ | ✅ | 全部 |
| USD/CNY | 🟢 | 500+ | ✅ | ✅ | 全部 |
| CN10Y | 🟢 | 500+ | ✅ | ✅ | 全部 |
| LME铜升贴水 | 🟢 | 300+ | ✅ | ✅ | 全部 |
| LME镍升贴水 | 🟢 | 300+ | ✅ | ✅ | 全部 |
| 布伦特原油 | 🟢 | 400+ | ✅ | ✅ | 全部 |
| WTI原油 | 🔴 | 0 | ❌ | ❌ | 搁置（Brent已覆盖）|
| ... | | | | | |

## 待修复数据清单
（列出有完整性问题的文件 + 修复方案）

## 可升级因子清单
（按IC序列长度排序，用于后续实施优先级）

## 风险项
（数据不足可能导致某些统计模块无法上线）
```

---

### 【Phase 1】数据管道修复与基础框架  ▶ Week 2

> **前置条件**：Phase 0 审计完成

#### Step 1.1：修复缺失/损坏数据

| 问题类型 | 修复方案 | 负责 |
|---------|---------|------|
| 历史数据缺失 | 从 AKShare / 交易所补采 | mimo |
| 实时管道中断 | 检查 cron 日志，修复采集脚本 | mimo |
| 字段名不一致 | 统一字段命名规范 | mimo |

#### Step 1.2：建立 pandera Schema 校验

**目标**：在数据入库时自动校验，发现异常立即告警

```python
# schemas.py — 因子数据 Schema 定义示例
import pandera as pa
from pandera import Column, Check, DataFrameSchema

FactorSchema = DataFrameSchema({
    'date':        Column(pa.DateTime, nullable=False, unique=True),
    'factor_value': Column(pa.Float64, nullable=False,
                           Check.greater_than(-100), Check.less_than(1000)),
    'source':      Column(pa.String, nullable=False),
})

PriceSchema = DataFrameSchema({
    'date':   Column(pa.DateTime, nullable=False, unique=True),
    'open':   Column(pa.Float64, Check.greater_than(0)),
    'high':   Column(pa.Float64, Check.greater_than_or_equal_to(pa.Column('open'))),
    'low':    Column(pa.Float64, Check.less_than_or_equal_to(pa.Column('high'))),
    'close':  Column(pa.Float64, Check.greater_than(0)),
    'volume': Column(pa.Float64, Check.greater_than_or_equal_to(0)),
})
```

**校验时机**：
- 采集脚本执行后 → 立即校验
- 数据加载进分析流程前 → 二次校验
- 异常数据 → 隔离到 `quarantine/` 目录 + 告警

#### Step 1.3：建立 PIT 冒烟测试

**目标**：确保因子数据在任意历史时点都可获取（无未来数据泄漏）

```python
# pit_smoke_test.py
def test_pit_no_future_leakage(factor_df, as_of_date):
    """
    取 as_of_date 的快照，确保快照中最大日期 <= as_of_date
    """
    snapshot = PitDataService.get_snapshot(factor_df, as_of_date)
    assert snapshot['date'].max() <= as_of_date, \
        f"PIT violation: snapshot contains future data as of {as_of_date}"
```

**执行频率**：每日 cron 任务随机抽取 10 个历史时点做冒烟测试

#### Step 1.4：CSV → Parquet 迁移（双写模式，兼容现有VNpy策略）

**迁移策略**：

| 阶段 | CSV | Parquet | 说明 |
|------|-----|---------|------|
| Phase 1-2 | ✅ 写入+读取 | ✅ 写入（归档） | VNpy策略继续读CSV，API层读CSV |
| Phase 3 | ✅ 写入+读取 | ✅ 写入+API读取 | API层切换Parquet，VNpy仍读CSV |
| Phase 4+ | ⚠️ 仅VNpy读取 | ✅ 主存储 | 确认VNpy侧无问题后退役CSV写入 |

**原则**：CSV是宏观层与VNpy执行层的唯一共享边界（架构V6.0约定），
迁移期间必须保持双写，避免破坏现有数据流。

---

### 【Phase 2】统计模块开发  ▶ Week 3

> **目标**：在数据就绪的因子上实现 Bootstrap CI 和 HMM Regime

#### Step 2.1：滚动 IC/IR 模块（60日窗口 + t 检验）

**核心逻辑**：

```python
def compute_rolling_ic_with_stats(factor_series, price_series, window=60, holds=[1, 5, 10, 20]):
    """
    对每个持有期计算：
    1. 滚动IC序列（60日窗口，Pearson相关）
    2. IC均值 + IC中位数
    3. t统计量（检验IC是否显著异于0）
    4. Bootstrap 95% CI
    """
    results = {}
    for hold in holds:
        fwd_ret = compute_forward_returns(price_series, hold)
        aligned = align_factor_return(factor_series, fwd_ret)
        ic_raw = rolling_correlation(aligned['factor'], aligned['return'], window=window)
        ic_series = ic_raw.dropna()
        
        # 核心统计量
        ic_mean  = ic_series.mean()
        ic_median = ic_series.median()
        ic_std   = ic_series.std()
        t_stat   = ic_mean / (ic_std / np.sqrt(len(ic_series))) if ic_std > 0 else 0
        p_value  = 2 * (1 - stats.t.cdf(abs(t_stat), df=len(ic_series)-1))
        
        # Bootstrap 95% CI
        bootstrap_ci = bootstrap_ci(ic_series, n_bootstrap=1000, ci=0.95)
        
        results[hold] = {
            'icMean':   ic_mean,
            'icMedian': ic_median,
            'icStd':    ic_std,
            'tStat':    t_stat,
            'pValue':   p_value,
            'ciLower':  bootstrap_ci[0],
            'ciUpper':  bootstrap_ci[1],
            'ir':        ic_mean / ic_std * np.sqrt(252/hold) if ic_std > 0 else 0,
            'winRate':  (ic_series > 0).mean(),
            'nObs':     len(ic_series),
        }
    return results
```

**输出格式**：

```json
{
  "factor": "金银比",
  "target": "AG",
  "window": 60,
  "as_of": "2026-04-23",
  "holds": {
    "1":  { "icMean": -0.130, "icMedian": -0.118, "tStat": -8.5, "pValue": 0.000, "ciLower": -0.155, "ciUpper": -0.105, "ir": -1.20, "winRate": 0.93 },
    "5":  { "icMean": -0.297, "icMedian": -0.281, "tStat": -12.1, "pValue": 0.000, "ciLower": -0.341, "ciUpper": -0.253, "ir": -1.82, "winRate": 0.95 },
    "10": { "icMean": -0.402, "icMedian": -0.389, "tStat": -61.0, "pValue": 0.000, "ciLower": -0.418, "ciUpper": -0.386, "ir": -1.82, "winRate": 0.97 }
  },
  "regime": "NORMAL"  // 或 "HIGH_VOL" / "TREND" 等
}
```

#### Step 2.2：HMM Regime 检测

**数据说明**：HMM Regime检测使用品种自身价格的波动率/趋势特征，不依赖外部VIX指数。模块

**逻辑**：

```python
import hmmlearn.hmm as hmm

def detect_regime(ic_series, n_states=3):
    """
    用 Gaussian HMM 将 IC 序列分为 3 个regime：
    - REGIME 0: IC 低迷（均值 < 0 or 绝对值小）→ 因子失效
    - REGIME 1: IC 正常（均值中等）→ 正常交易
    - REGIME 2: IC 强势（均值大且稳定）→ 增仓信号
    
    也可扩展到 2regime（有效/失效）或 4regime（加入波动率维度）
    """
    X = ic_series.values.reshape(-1, 1)
    model = GaussianHMM(n_components=n_states, covariance_type='full', n_iter=1000)
    model.fit(X)
    states = model.predict(X)
    
    # 解释每个 state 的含义
    state_means = {s: ic_series[states == s].mean() for s in range(n_states)}
    sorted_states = sorted(state_means, key=state_means.get)
    
    regime_map = {
        sorted_states[0]: 'REGIME_WEAK',   # IC最低 → 失效
        sorted_states[1]: 'REGIME_NORMAL',  # IC中等 → 正常
        sorted_states[2]: 'REGIME_STRONG',  # IC最高 → 强势
    }
    regime_labels = [regime_map[s] for s in states]
    return regime_labels, state_means
```

**Regime 判定规则**（供信号系统使用）：

| Regime | IC特征 | 建议操作 |
|--------|--------|---------|
| REGIME_STRONG | IC均值 > 0.08，IR > 0.5 | 正常仓位，可考虑加仓 |
| REGIME_NORMAL | IC均值 0.02~0.08，IR 0.3~0.5 | 正常交易 |
| REGIME_WEAK | IC均值 < 0.02 或 IR < 0.3 | 降仓或观望 |
| REGIME_REVERSE | IC均值 < -0.02（方向反转） | 检查逻辑，慎重复 |**

#### Step 2.3：多因子 IC 热力图模块

**目标**：一目了然看到多因子对多品种的 IC 矩阵

```python
def generate_ic_heatmap(factors_dict, symbols_list, hold=5):
    """
    factors_dict: {因子名: 因子文件路径}
    symbols_list: [品种代码列表]
    
    输出：IC热力图矩阵 + IR热力图矩阵
    """
    ic_matrix = pd.DataFrame(index=list(factors_dict.keys()),
                              columns=symbols_list, dtype=float)
    ir_matrix = pd.DataFrame(index=list(factors_dict.keys()),
                              columns=symbols_list, dtype=float)
    
    for fname, fpath in factors_dict.items():
        for sym in symbols_list:
            stats = compute_rolling_ic_with_stats(load_factor(fpath), load_price(sym), hold=hold)
            ic_matrix.loc[fname, sym] = stats[hold]['ic_mean']
            ir_matrix.loc[fname, sym] = stats[hold]['ir']
    
    return ic_matrix, ir_matrix
```

---

### 【Phase 3】信号系统开发  ▶ Week 3~4

#### Step 3.1：多维信号评分（0~100）

**评分体系**：

```python
def signal_score(factor, target, as_of_date) -> dict:
    """
    综合评分（0~100），维度：
    1. IC强度（25分）：IC均值相对历史分位数
    2. IC稳定性（25分）：IR值
    3. Regime状态（25分）：HMM判定的Regime
    4. 趋势一致性（25分）：因子方向与历史方向对比
    """
    stats = get_ic_stats(factor, target)  # Step 2.1 结果
    regime = detect_regime(...)            # Step 2.2 结果
    
    # IC强度分
    ic_percentile = stats['ic_percentile']  # 相对自身历史的分位
    ic_score = min(25, ic_percentile / 100 * 25)
    
    # IC稳定性分（IR）
    ir_score = min(25, max(0, (stats['ir'] - 0.3) / 0.7 * 25)) if stats['ir'] > 0.3 else 0
    
    # Regime分
    regime_scores = {'REGIME_STRONG': 25, 'REGIME_NORMAL': 15, 'REGIME_WEAK': 5}
    regime_score = regime_scores.get(regime, 0)
    
    # 趋势一致性（因子当期方向是否与近20日均值方向一致）
    trend_score = 25 if check_trend_alignment(factor, target) else 0
    
    total = ic_score + ir_score + regime_score + trend_score
    
    return {
        '总分': round(total, 1),
        'IC强度分': round(ic_score, 1),
        '稳定性分': round(ir_score, 1),
        'Regime分': round(regime_score, 1),
        '趋势分':   round(trend_score, 1),
        '信号方向': '做多' if stats['ic_mean'] < 0 else '做空',  # 视因子极性
        '建议持有期': optimize_holding_period(factor, target),
        'Regime': regime,
        '更新时间': as_of_date,
    }
```

**评分阈值**：

| 总分 | 信号等级 | 操作建议 |
|------|---------|---------|
| 80~100 | 🟢 强 | 正常仓位，可适度增仓 |
| 60~79 | 🟡 中等 | 正常交易，谨慎增仓 |
| 40~59 | 🟠 偏弱 | 降仓观察 |
| 0~39 | 🔴 弱/失效 | 止损或清仓 |

#### Step 3.2：因子拥挤度监控

**计算逻辑**：

```python
def factor_crowding_score(factor, target, window=20) -> float:
    """
    衡量该因子当前是否被过度拥挤使用
    方法：滚动IC的波动率是否异常升高（拥挤 → IC波动加大）
    也可引入：持仓集中度数据、成交持仓比等
    """
    ic_std_20 = rolling_std(factor_ic_series, window=20).iloc[-1]
    ic_std_hist_mean = rolling_std(factor_ic_series, window=20).mean()
    ic_std_hist_std  = rolling_std(factor_ic_series, window=20).std()
    
    z_score = (ic_std_20 - ic_std_hist_mean) / ic_std_hist_std
    crowding = min(100, max(0, 50 + z_score * 25))  # 归一化到 0~100
    
    return {
        '拥挤度': round(crowding, 1),
        'z_score': round(z_score, 2),
        '状态': '拥挤' if crowding > 70 else '正常',
    }
```

**告警规则**：

| 拥挤度 | 状态 | 行动 |
|--------|------|------|
| < 60 | 🟢 正常 | 无需操作 |
| 60~80 | 🟡 偏拥挤 | 降低该因子权重 |
| > 80 | 🔴 极度拥挤 | 暂停使用该因子，切换备用因子 |

#### Step 3.3：动态持有期优化

**逻辑**：选择 IC 最稳定的持有期作为推荐持有期

```python
def optimize_holding_period(factor, target) -> dict:
    """
    对比 1/5/10/20 日持有期的 IR，选择最优
    但需注意：持有期越长，IC可能越高但延迟越大
    """
    results = compute_rolling_ic_with_stats(factor, target, holds=[1, 5, 10, 20])
    
    best_hold = max(results, key=lambda h: results[h]['ir'])
    return {
        '推荐持有期': best_hold,
        '各持有期IR': {h: round(results[h]['ir'], 3) for h in results},
        '说明': f'IR最优持有期={best_hold}日（IR={results[best_hold]["ir"]:.3f}）'
    }
```

---

### 【Phase 4】可视化升级  ▶ Week 4

#### Step 4.1：三图联动 Dashboard

**技术选型**：Plotly Dash 或 ECharts + Flask/FastAPI

**三个图表**：

```
┌─────────────────────────────────────────────────────────┐
│  因子：金银比  →  品种：AG白银                          │
│  信号状态：🟢 REGIME_STRONG  总分：87/100              │
├──────────────────┬──────────────────┬───────────────────┤
│  图1: 因子走势   │  图2: 滚动IC    │  图3: 滚动IR       │
│  （带均线）      │  （60日窗口）   │  （60日窗口）      │
│                  │  + Bootstrap CI │  + t统计量         │
├──────────────────┴──────────────────┴───────────────────┤
│  辅助信息栏：Regime状态 | 拥挤度 | 动态持有期 | 信号方向  │
└─────────────────────────────────────────────────────────┘
```

**Plotly Dash 实现框架**：

```python
# dashboard/app.py
from dash import Dash, html, dcc, callback, Output, Input
import plotly.graph_objects as go
from plotly.subplots import make_subplots

app = Dash(__name__)

app.layout = html.Div([
    html.H1('因子决策支持系统'),
    
    # 因子/品种选择器
    html.Div([
        dcc.Dropdown(id='factor-selector', options=[...], value='金银比'),
        dcc.Dropdown(id='symbol-selector',  options=[...], value='AG'),
        dcc.DatePickerSingle(id='date-picker', date=today),
    ]),
    
    # 三图联动区
    dcc.Graph(id='factor-chart'),      # 图1
    dcc.Graph(id='ic-chart'),         # 图2
    dcc.Graph(id='ir-chart'),         # 图3
    
    # 信号健康度仪表盘
    html.Div(id='signal-dashboard'),
    
    # Regime 说明
    html.Div(id='regime-explanation'),
])

@callback(
    Output('factor-chart', 'figure'),
    Output('ic-chart', 'figure'),
    Output('ir-chart', 'figure'),
    Output('signal-dashboard', 'children'),
    Input('factor-selector', 'value'),
    Input('symbol-selector', 'value'),
    Input('date-picker', 'date'),
)
def update_charts(factor_name, symbol, date):
    stats = signal_score(factor_name, symbol, date)  # Step 3.1
    ic_series, ir_series = load_ic_ir_series(factor_name, symbol)
    
    fig_ic = go.Figure()
    fig_ic.add_trace(go.Scatter(x=ic_series.date, y=ic_series.ic,
                                 mode='lines', name='IC(60d)'))
    fig_ic.add_shape(type='line', x0=ic_series.date.min(), y0=0,
                     x1=ic_series.date.max(), y1=0,
                     line=dict(color='gray', dash='dash')))
    # Bootstrap CI 区间
    fig_ic.add_trace(go.Scatter(x=ci_dates, y=ci_upper, fill='tonexty',
                                 mode='lines', fillcolor='rgba(0,176,246,0.1)',
                                 line=dict(color='rgba(0,176,246,0.1)'), name='95% CI'))
    
    # 信号仪表盘HTML
    dashboard = html.Div([
        html.Span(f"总分: {stats['总分']}", style={'fontSize': '24px'}),
        html.Span(f"Regime: {stats['Regime']}", style={'fontSize': '18px'}),
        html.Span(f"推荐持有期: {stats['建议持有期']}", style={'fontSize': '16px'}),
    ])
    
    return fig_fac, fig_ic, fig_ir, dashboard
```

#### Step 4.2：多因子 IC 热力图（按品种分组）

```python
def render_ic_heatmap(ic_matrix, ir_matrix):
    import plotly.figure_factory as ff
    
    fig = ff.create_annotated_heatmap(
        z=ic_matrix.values,
        x=list(ic_matrix.columns),
        y=list(ic_matrix.index),
        annotation_text=ic_matrix.applymap(lambda x: f'{x:.3f}' if not pd.isna(x) else '').values,
        colorscale='RdBu', zmid=0,
        showscale=True,
    )
    fig.update_layout(title=f'因子 IC 热力图（持有期={hold}日）— {date}')
    return fig
```

#### Step 4.3：因子失效预警

**触发条件**（任一即触发）：

| 条件 | 说明 |
|------|------|
| IC滚动均值 < 0.01 持续 20日 | 因子基本失效 |
| IC趋势背离：因子与价格方向背离 > 15日 | 逻辑可能已变 |
| Regime 进入 REGIME_REVERSE | 方向反转 |
| 拥挤度 > 85 | 过度拥挤 |

**预警通知**：

```python
def check_failure_signals(factor, target) -> list:
    signals = []
    ic_series = load_ic_series(factor, target)
    
    if ic_series.tail(20).mean() < 0.01:
        signals.append({'level': 'WARNING', 'msg': f'{factor} IC均值持续低于0.01'})
    
    if detect_regime_reversal(ic_series):
        signals.append({'level': 'CRITICAL', 'msg': f'{factor}→{target} 方向反转！'})
    
    if factor_crowding_score(factor, target) > 85:
        signals.append({'level': 'ALERT', 'msg': f'{factor} 拥挤度超标'})
    
    return signals
```

---

### 【Phase 5】私人标注与知识库  ▶ Week 4（穿插）

#### Step 5.1：私人标注系统

**功能**：研究员可对任意日期的因子信号添加文字备注

```python
# annotations.db — SQLite 存储
CREATE TABLE factor_annotations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    factor     TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    date       DATE NOT NULL,
    note       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags       TEXT,  -- JSON array: ["宏观事件","数据异常","季节性"]
);

-- 查询某因子的所有标注
SELECT * FROM factor_annotations
WHERE factor=? AND symbol=? AND date BETWEEN ? AND ?
ORDER BY date DESC;
```

**Dashboard 集成**：在因子走势图的对应日期添加"📝"标记，悬停显示备注内容

#### Step 5.2：失效事件知识库

```python
# knowledge

---

#### Step 5.2：失效事件知识库

**目的**：将因子失效事件系统化记录，形成团队共享知识

```python
# knowledge_base.db
CREATE TABLE factor_incidents (
    id            INTEGER PRIMARY KEY,
    factor        TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    onset_date    DATE NOT NULL,
    recovery_date DATE,
    ic_before     FLOAT,
    ic_during     FLOAT,
    ic_after      FLOAT,
    root_cause    TEXT,
    notes         TEXT,
    created_by     TEXT
);
```

**典型失效模式**：

| 失效模式 | 特征 | 应对 |
|---------|------|------|
| 宏观事件打断 | CN10Y在封控期方向反转 | 加生效条件（Regime判断）|
| 数据源变更 | 字段定义/单位变化 | pandera校验捕获 |
| 市场结构变化 | 某品种产业链重构 | 因子退役/替换 |
| 季节性失效 | 某些品种有强季节性 | 季节性调整因子 |

---

### 【Phase 6】多品种组合信号看板  ▶ Week 5

#### Step 6.1：品种分组与信号汇总

**分组逻辑**：

```
贵金属组（跨品种联动强）：
  AU <-> AG（金银比因子）
  
有色金属组（宏观敏感）：
  CU / AL / ZN / NI / PB / SN
  
黑色系组（国内需求驱动）：
  RB / HC / I / J / JM
  
化工组（原油链路）：
  TA / EG / PP / BU / FU / SA / SC
  
农产品组（外盘联动）：
  M / Y / P / RU / NR / BR / LC / LH
```

**汇总看板显示**：

| 品种 | 推荐因子 | 信号总分 | 方向 | Regime | 持有期 | 更新时刻 |
|------|---------|---------|------|--------|--------|---------|
| AG | 金银比 | 87/100 | 做空 | REGIME_STRONG | 10日 | 2026-04-23 16:30 |
| CU | LME铜升贴水 | 72/100 | 做多 | REGIME_NORMAL | 5日 | 2026-04-23 16:30 |
| ... | | | | | | |

#### Step 6.2：板块联动信号

**逻辑**：当同一板块内多个品种同时出现相同方向信号时，板块趋势可信度更高

```python
def sector_signal_score(sector_factors):
    all_scores = [v['总分'] for v in sector_factors.values()]
    avg_score = mean(all_scores)
    alignment = count_same_direction(sector_factors) / len(sector_factors)
    return {
        '板块均值': round(avg_score, 1),
        '方向一致率': round(alignment, 2),
        '板块信号': '强' if avg_score > 70 and alignment > 0.7 else '弱',
        '建议': '顺势交易' if alignment > 0.7 else '谨慎观望',
    }
```

---

### 【Phase 7】全品种推广与优化  ▶ Week 5 尾

#### Step 7.1：未覆盖品种补全

**优先级排序**（按数据就绪程度）：

```
第一梯队（数据就绪，直接部署）：
 金银比系：AU、AG
 LME系：CU、NI（已验证数据）
 宏观系：USD/CNY、CN10Y（通用因子）
 
第二梯队（需少量数据修复）：
 有色系：AL、ZN、PB、SN
 黑色系：RB、HC、I、J、JM（数据管道已有）
 
第三梯队（需专项数据修复）：
 化工系：TA、EG、PP、BU、FU（部分因子数据不足）
 农产品系：M、Y、P、RU、NR（品种特有因子待验证）
```

#### Step 7.2：持续优化机制

**月度review**：

| 时间 | 内容 |
|------|------|
| 每月1日 | 跑全品种 IC 热力图，更新因子有效性矩阵 |
| 每月第一个周五 | 复盘上月失效事件，更新知识库 |
| 每月15日 | 检查数据管道健康度，更新采集脚本 |
| 每季度 | 评估是否有新因子可加入注册表 |

---

## 五、质量门控（Quality Gates）

每个 Phase 结束后必须通过质量门控才能进入下一阶段。

### Gate 0：数据就绪审计（Week 1 末）

```
[ ] 所有核心因子数据完整度 >= 70%
[ ] AKShare 22品种价格数据可正常获取
[ ] 实时数据管道 cron 任务存活
[ ] IC 序列长度满足最低要求（>= 60天）
[ ] 无未来数据泄漏（PIT 冒烟测试通过）
```

**Gate Owner**：因子分析师 YIYI  
**如有项未通过**：Block Phase 1，直到修复完成

---

### Gate 1：数据管道验收（Week 2 末）

```
[ ] pandera Schema 在所有因子数据上校验通过
[ ] 异常数据能被自动隔离到 quarantine/ 目录
[ ] Parquet 归档正常（若选择迁移）
[ ] PIT 冒烟测试连续7天全部通过
```

**Gate Owner**：mimo + YIYI 联合验收

---

### Gate 2：统计模块验收（Week 3 末）

```
[ ] Bootstrap 95% CI 在所有因子上可计算
[ ] HMM Regime 在所有因子上可判定（>= 240天数据）
[ ] 多因子 IC 热力图可正常渲染
[ ] IC/IR 数值与历史记录对比误差 < 1%
[ ] 回归测试：Phase 1 核心因子的已知 IC/IR 不发生显著漂移
```

**Gate Owner**：YIYI

---

### Gate 3：信号系统验收（Week 4 末）

```
[ ] 信号评分在所有因子上可计算（0~100）
[ ] 拥挤度监控在所有因子上可计算
[ ] 动态持有期推荐逻辑正确
[ ] 失效预警在模拟数据上可触发
[ ] Dashboard 三图联动响应 < 2秒
```

**Gate Owner**：YIYI + 前端负责人

---

### Gate 4：全品种上线（Week 5 末）

```
[ ] 22个品种全部接入信号看板
[ ] 月度review 机制已建立
[ ] 私人标注系统正常运行
[ ] 知识库积累 >= 5 条失效记录（可选，有则更好）
[ ] 文档完整（操作手册 + 故障排查指南）
```

**Gate Owner**：YIYI + 项目经理

---

## 六、风险登记册

| # | 风险描述 | 概率 | 影响 | 应对措施 |
|---|---------|------|------|---------|
| R1 | 某些因子历史数据缺失严重，无法做 Bootstrap/HMM | 中 | 高 | 降级为观察因子；优先处理数据缺失最严重的品种 |
| R2 | AKShare 数据不稳定（接口变更/限流） | 中 | 高 | 建立备用源（Tushare/交易所直采） |
| R3 | HMM Regime 判定不稳定，切换频繁 | 中 | 中 | 增加 Regime 切换的平滑逻辑（需要N天确认期） |
| R4 | 22品种全部接入后 Dashboard 响应变慢 | 低 | 中 | 预计算+缓存；按需加载非活跃品种 |
| R5 | 因子拥挤度数据不足（无持仓数据） | 高 | 中 | 用IC波动率代替；逐步引入持仓数据 |
| R6 | mimo 人力瓶颈（采集+数据修复+开发并行） | 中 | 高 | 优先级排序；部分工作并行化 |
| R7 | 升级改动了现有因子逻辑，导致历史验证结果不兼容 | 低 | 高 | 回归测试；因子逻辑变更走评审流程 |
| R8 | Plotly Dash 部署复杂，维护成本高 | 低 | 低 | 先用单文件原型验证；确有需要再上框架 |

---

## 七、依赖关系图

```
Week 1 (Phase 0)
  数据就绪审计
  |- 因子数据审计
  |- 品种价格数据审计
  |- 实时管道健康检查
  |- IC窗口评估
         |
         v
Week 2 (Phase 1)  <- Gate 0 通过后
  数据管道修复
  |- 缺失数据补采（mimo）
  |- pandera Schema（mimo + YIYI）
  |- PIT冒烟测试（YIYI）
  |- CSV -> Parquet迁移（如有必要，mimo）
         |
         v
Week 3 (Phase 2)  <- Gate 1 通过后
  统计模块开发
  |- 滚动IC/IR + t检验（YIYI）
  |- Bootstrap 95% CI（YIYI）
  |- HMM Regime检测（YIYI）
         |
         v
Week 4 (Phase 3+4)  <- Gate 2 通过后
  信号系统 + 可视化
  |- 多维信号评分（YIYI）
  |- 拥挤度监控（YIYI）
  |- 动态持有期优化（YIYI）
  |- 失效预警（YIYI）
  |- 三图联动Dashboard（前端+mimo）
  |- IC热力图（前端+mimo）
  |- 私人标注 + 知识库（mimo）
         |
         v
Week 5 (Phase 5+6+7)  <- Gate 3 通过后
  多品种推广
  |- 品种分组信号看板（前端）
  |- 未覆盖品种补全（mimo）
  |- 持续优化机制建立（YIYI）
  |- 月度review 排期（PM）
         |
         v
Gate 4 全品种上线
```

---

## 八、工时估算

| 模块 | 工作内容 | 工时估算 | 负责人 |
|------|---------|---------|--------|
| Phase 0 | 数据审计 | 8h | YIYI |
| Phase 1 | 数据管道修复 | 16h | mimo |
| Phase 2 | 统计模块（Bootstrap CI / HMM） | 16h | YIYI |
| Phase 3 | 信号系统（评分/拥挤度/持有期/预警） | 20h | YIYI |
| Phase 4 | 可视化（Dashboard三图联动/热力图） | 24h | 前端 + mimo |
| Phase 5 | 私人标注 + 知识库 | 8h | mimo |
| Phase 6 | 多品种看板 | 12h | 前端 |
| Phase 7 | 全品种推广 + 优化机制 | 8h | YIYI + mimo |
| **合计** | | **~112h（约14工作日）** | |

> 注：若前端资源有限，Phase 4 可分为 MVP（最小可行产品，用 ECharts 快速出原型）和完整版（Plotly Dash）两期交付。

---

## 九、附录

### 附录A：实施检查清单（Checklist）

```
Phase 0 - 数据就绪审计
  [ ] audit_factor_data.py 执行完毕
  [ ] audit_price_data.py 执行完毕
  [ ] LME cron 任务存活确认
  [ ] AKShare 宏观数据 cron 任务存活确认
  [ ] IC窗口评估完成，输出可升级因子清单
  [ ] Gate 0 通过（YIYI 签字）

Phase 1 - 数据管道修复
  [ ] 缺失数据补采完成
  [ ] pandera Schema 定义完成并通过全部因子数据校验
  [ ] PIT冒烟测试连续7天全部通过
  [ ] Gate 1 通过（YIYI + mimo 联合签字）

Phase 2 - 统计模块
  [ ] 滚动IC/IR模块测试通过
  [ ] Bootstrap 95% CI模块测试通过
  [ ] HMM Regime检测模块测试通过
  [ ] IC热力图渲染正常
  [ ] 回归测试：已知IC/IR不漂移
  [ ] Gate 2 通过

Phase 3 - 信号系统
  [ ] 多维评分在所有因子上可计算
  [ ] 拥挤度监控可工作
  [ ] 动态持有期逻辑正确
  [ ] 失效预警模拟触发成功
  [ ] Gate 3 通过

Phase 4 - 可视化
  [ ] 三图联动Dashboard MVP上线
  [ ] IC热力图上线
  [ ] 响应时间 < 2秒（22品种全开）
  [ ] 私人标注功能可用
  [ ] 知识库有内容

Phase 5-7 - 全品种推广
  [ ] 22品种全部接入看板
  [ ] 月度review机制建立
  [ ] 操作手册编写完成
  [ ] Gate 4 通过
```

### 附录B：关键文件路径索引

| 文件 | 路径 |
|------|------|
| 升级方案原文 | D:utures_v6\macro_engine
esearch
eports\Factor_Decision_Support_System_Upgrade_Plan_20260423.md |
| 本实施计划 | D:utures_v6\macro_engine
esearch
eports\Factor_System_Upgrade_Implementation_Plan_20260423.md |
| 数据就绪审计报告 | D:utures_v6\macro_engine
esearch
eportsudit_factor_data_20260423.csv |
| 品种价格审计报告 | D:utures_v6\macro_engine
esearch
eportsudit_price_data_20260423.csv |
| Dashboard代码 | D:utures_v6\macro_engine\dashboard\ |
| 因子引擎代码 | D:utures_v6\macro_engineactor_engine\ |
| 采集脚本 | D:utures_v6\macro_engine\crawlers\ |
| 因子数据 | D:utures_v6\macro_engine\data\crawlers\_shared\daily\ |
| LME数据 | D:utures_v6\macro_engine\data\crawlers\LME\ |
| 标注数据库 | D:utures_v6\macro_engine\knowledgennotations.db |
| 知识库 | D:utures_v6\macro_engine\knowledge\knowledge_base.db |

### 附录C：技术栈清单

| 用途 | 技术选型 | 备注 |
|------|---------|------|
| 统计分析 | Python 3.10+ / pandas / scipy / statsmodels | 核心计算 |
| HMM模型 | hmmlearn | Regime检测 |
| 数据校验 | pandera | Schema校验 |
| 数据存储 | Parquet + SQLite | 历史+标注 |
| 可视化 | Plotly Dash（或ECharts MVP） | Dashboard |
| 实时数据 | AKShare | 主力采集 |
| 后备数据 | Tushare / 交易所直采 | 降级方案 |
| 定时任务 | OpenClaw cron | 调度 |
| 代码管理 | Git | 版本控制 |

---

*本文档为因子系统升级改造的永久实施依据，每次重大变更后更新版本号。*
*当前版本：v1.0（2026-04-23）*
*下次审查日期：Phase 0 完成后（约2026-04-28）*


---

### 附录D：情绪因子扩展方案（Phase 5+，暂不实施）

> **状态**：规划中  
> **优先级**：P3（现有因子系统稳定运行后再评估）  
> **负责人**：因子分析师 YIYI  
> **预计启动时间**：Phase 4 完成后视情况决定

---

#### D.1 情绪因子的三类来源

| 类型 | 数据源 | 可靠性 | 实现难度 | 适用品种 |
|------|--------|--------|----------|---------|
| **衍生品隐含** | 期权IV / 期限结构 / COT持仓 | 高 | 低 | 全品种 |
| **行为数据** | Google搜索量 / 资金流 / 换手率 | 中高 | 中 | 全品种 |
| **文本情绪** | 新闻NLP / 社交媒体 / 券商研报 | 中 | 高 | 全品种 |

**落地顺序**：衍生品隐含 → 行为数据 → 文本情绪

---

#### D.2 衍生品隐含情绪（优先实现）

##### D.2.1 期权隐含波动率溢价（IV Premium）

**核心逻辑**：
- IV溢价 = 隐含波动率 - 历史波动率
- 正值 → 市场对未来波动定价偏高 → 可能过度恐慌
- 负值 → 市场低估未来波动 → 可能过度自满

**实现代码框架**：

```python
def compute_iv_premium(symbol, as_of_date):
    iv = get_option_iv(symbol, as_of_date, 'ATM 1M')
    hv = get_realized_vol(symbol, as_of_date, window=20)
    iv_premium = iv - hv
    iv_premium_z = (iv_premium - history.mean()) / history.std()
    return {
        'factor_value': iv_premium,
        'z_score': iv_premium_z,
        'signal': 'panic' if iv_premium_z > 1.5 else 'complacent' if iv_premium_z < -1.5 else 'neutral',
    }
```

**数据源**：

| 品种 | 来源 | 成本 |
|------|------|------|
| AU/AG/CU/AL/ZN/NI/RB/I/J/M | 上期所/大商所/郑商所期权 | 免费（AKShare部分覆盖）|
| 原油/CBOT品种 | CME Group | 付费或爬虫 |
| LME品种 | LME Options | 付费 |

**信号逻辑**：
- IV溢价 > 1.5σ → 过度恐慌 → 可能是反向信号
- IV溢价 < -1.5σ → 过度自满 → 风险预警

##### D.2.2 期权偏度（IV Skew）

**核心逻辑**：
- IV偏度 = OTM Put IV - OTM Call IV
- 正偏度 → 市场对下跌风险定价更高 → 恐慌
- 负偏度 → 市场对上涨期待更高 → 贪婪

**适用性**：有活跃期权市场的品种（AU/AG/CU/IO/M/C/P等）

##### D.2.3 COT持仓情绪（扩展现有因子）

```python
def compute_cot_sentiment(symbol, as_of_date):
    cot = get_cot_report(symbol, as_of_date)
    speculative_net = cot['noncommercial_long'] - cot['noncommercial_short']
    commercial_net = cot['commercial_long'] - cot['commercial_short']
    sentiment = (speculative_net - commercial_net) / cot['open_interest']
    percentile = historical_percentile(sentiment)
    return {
        'factor_value': sentiment,
        'percentile': percentile,
        'signal': 'long_crowded' if percentile > 90 else 'short_crowded' if percentile < 10 else 'neutral',
    }
```

---

#### D.3 行为数据情绪

##### D.3.1 Google Trends 搜索热度

**核心逻辑**：搜索热度飙升 → 市场关注度提高 → 趋势加速或反转信号

**实现框架**：

```python
import pytrends
from pytrends.request import TrendReq

def compute_search_trend(keyword, as_of_date):
    pytrends = TrendReq(hl='zh-CN', tz=480)
    pytrends.build_payload([keyword], timeframe='today 3-m')
    df = pytrends.interest_over_time()
    latest = df[keyword].iloc[-1]
    baseline = df[keyword].iloc[-8:-1].mean()
    surge = (latest - baseline) / baseline if baseline > 0 else 0
    return {
        'factor_value': surge,
        'signal': 'surge' if surge > 0.5 else 'decline' if surge < -0.3 else 'normal',
    }
```

**关键词配置**：

| 品种 | 关键词 | 语言 |
|------|--------|------|
| AU 黄金 | 黄金价格 / gold price | 中/英 |
| CU 铜 | 铜价 / copper price | 中/英 |
| I 铁矿石 | 铁矿石价格 | 中 |
| M 豆粕 | 豆粕价格 | 中 |

**更新频率**：周度

##### D.3.2 ETF资金流

**适用品种**：黄金ETF、有色金属ETF、豆粕ETF等有对应ETF的品种

---

#### D.4 文本情绪因子（高投入，后期评估）

##### D.4.1 新闻情绪分析

**数据源**：

| 来源 | 覆盖范围 | 成本 |
|------|---------|------|
| 新浪财经/东方财富 | 国内财经新闻 | 免费（爬虫）|
| Reuters/Bloomberg | 国际财经新闻 | 付费 |
| 行业网站（SMM/我的钢铁网）| 行业新闻 | 部分免费 |

**实现方案**：

```python
from snownlp import SnowNLP

def compute_news_sentiment(symbol, as_of_date, window=7):
    news = fetch_news(symbol, days=window)
    sentiments = []
    for article in news:
        s = SnowNLP(article['title'] + article['content'])
        sentiments.append(s.sentiments)
    avg = sum(sentiments) / len(sentiments) if sentiments else 0.5
    return {
        'factor_value': avg - 0.5,
        'n_news': len(sentiments),
        'signal': 'bullish' if avg > 0.6 else 'bearish' if avg < 0.4 else 'neutral',
    }
```

**方案对比**：

| 方案 | 开发成本 | 运行成本 | 准确性 |
|------|---------|---------|--------|
| SnowNLP | 低 | 免费 | 中 |
| 微调BERT | 中 | 低 | 高 |
| GPT-4 API | 低 | 高（约0.02元/条）| 最高 |

##### D.4.2 社交媒体情绪

**警告**：社交媒体噪音极高，对商品期货价值有限（散户主导，信号弱）

---

#### D.5 Factor Registry 扩展定义（复用现有 factor_meta.json）
> **注意**：不新建独立的 `factor_registry.yaml`，而是扩展现有的 `macro_engine/factor_meta.json`，
> 与 `config/factors/*.yaml` 保持兼容。

```yaml
factors:
  iv_premium_AU:
    name: "黄金IV溢价"
    phase: 5
    category: "sentiment"
    subcategory: "derivative_implied"
    unit: "vol_diff"
    direction: "inverse"
    applicable_symbols: [AU]
    data_source:
      primary:
        type: "shfe_option"
        function: "option_iv_atm"
        underlying: "AU"
        term: "1M"
    data_path: "crawlers/sentiment/AU_iv_premium.csv"
    tags: ["情绪", "期权", "波动率"]
    status: "planned"

  google_trend_AU:
    name: "黄金搜索热度"
    phase: 5
    category: "sentiment"
    subcategory: "behavioral"
    unit: "ratio_change"
    direction: "mixed"
    applicable_symbols: [AU]
    data_source:
      primary:
        type: "pytrends"
        keyword: "黄金价格"
    data_path: "crawlers/sentiment/AU_google_trend.csv"
    update_frequency: "weekly"
    tags: ["情绪", "搜索", "行为数据"]
    status: "planned"

  news_sentiment_AU:
    name: "黄金新闻情绪"
    phase: 5
    category: "sentiment"
    subcategory: "text"
    unit: "sentiment_score"
    direction: "mixed"
    applicable_symbols: [AU]
    data_source:
      primary:
        type: "crawler"
        sources: ["sina_finance", "eastmoney"]
    data_path: "crawlers/sentiment/AU_news_sentiment.csv"
    update_frequency: "daily"
    tags: ["情绪", "新闻", "NLP"]
    status: "planned"
```

---

#### D.6 落地优先级

| 优先级 | 因子 | 理由 | 预估周期 |
|--------|------|------|---------|
| P0 | IV溢价（有期权品种）| 数据可靠、逻辑清晰 | 1周 |
| P0 | IV偏度（有期权品种）| 捕捉尾部风险定价 | 1周 |
| P1 | COT情绪扩展 | 数据已有，逻辑简单 | 2天 |
| P1 | Google Trends | 免费、可靠 | 3天 |
| P2 | ETF资金流 | 需接入新数据源 | 1周 |
| P3 | 新闻情绪 | 需爬虫+NLP管道 | 2~3周 |
| P4 | 社交情绪 | 噪音高、信号弱 | 评估后决定 |

---

#### D.7 情绪因子的特殊风险

| 风险 | 说明 | 应对措施 |
|------|------|---------|
| 情绪反转不总是发生 | 高恐慌不等于即将上涨 | +Regime条件判断 |
| 数据滞后 | Google Trends周度更新 | 做辅助信号，非主信号 |
| 过度拟合 | 历史规律可能是幸存者偏差 | 样本外验证+持续监控IC |
| 文本歧义 | "暴跌"是利空还是利空出尽？ | 需更复杂NLP（事件抽取）|

---

#### D.8 启动条件

情绪因子纳入实施需满足以下条件：

```
[ ] 现有Phase 1~4因子决策系统稳定运行 >= 3个月
[ ] 信号评分→行动建议闭环验证有效
[ ] 因子Registry机制成熟，可快速纳入新因子
[ ] 有充足的样本外数据用于情绪因子IC验证
[ ] 团队有带宽投入爬虫/NLP管道开发
```

---

*本附录为情绪因子扩展的规划文档，具体实施时间视Phase 1~4运行效果决定。*
*文档版本：v1.0（2026-04-23）*
