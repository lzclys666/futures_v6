# 因子走势监控系统升级方案
## 从"展示工具"到"决策辅助系统"的完整规划文档

**文档版本**：v1.0  
**创建日期**：2026-04-23（周四）16:50 GMT+8  
**作者**：因子分析师 YIYI（agent-ded0d6a7）  
**状态**：已评审 · 永久存档 · 作为后续迭代基准线  
**存放路径**：`D:\futures_v6\macro_engine\research\reports\Factor_Decision_Support_System_Upgrade_Plan_20260423.md`  
**配套文档**：
- `D:\futures_v6\macro_engine\research\reports\Factor_Registry_P1_P4_20260420.md`（因子注册表）
- `D:\futures_v6\macro_engine\research\reports\IC_validation_Phase4_20260420.md`（IC验证报告）
- `D:\futures_v6\macro_engine\research\reports\IC_validation_Phase1_20260420.md`（Phase1验证报告）

---

## 一、项目背景与目标

### 1.1 为什么需要升级

2026-04-20 完成 Phase 1~4 因子 IC 验证后，系统已有能力输出核心因子的历史走势和统计指标（IC/IR/t统计量）。但**当前系统的定位是"展示工具"**——研究员需要自己解读图表、自己判断信号是否有效、自己决定是否使用。

这存在三个核心问题：

| 问题 | 现状 | 风险 |
|------|------|------|
| **信号质量依赖人工判断** | IC 曲线掉下来了，但不知道是暂时波动还是永久失效 | 误判导致错误交易决策 |
| **单一指标无法支撑决策** | 只看 IC 均值，金银比 IC=-0.297 但胜率仅3.7%——到底该信还是不该信？ | 用错误的逻辑指导交易 |
| **被动发现失效** | 因子失效后，在图表上看到了，才知道坏了 | 已经产生了亏损才知道报警 |

**升级目标**：让系统从"告诉我数据是什么"→"告诉我该怎么办"。

### 1.2 升级的核心定义

```
"决策辅助系统" = "展示工具" + 智能预警 + 多维评分 + 自动化输出
```

三个关键转变：
1. **从被动展示 → 主动预警**：IC 还没崩就提前告警，不是事后看到才报警
2. **从单一 IC → 多维信号评分**：综合 IC_mean/stability/decay/breadth/regime_fit 判断信号强弱
3. **从图表 → 行动建议**：输出"建议做多/做空/观望/降权"，而不是只展示数字

### 1.3 既有资产盘点

升级基于以下已验证资产：

**P1 核心因子（可直接入系统）：**

| 因子代码 | 因子描述 | 目标品种 | 持有期 | IC | IR | 评级 |
|----------|----------|----------|--------|-----|-----|------|
| P1-A | 金银比（SGE Au / SGE Ag修正） | AG 白银 | 10日 | -0.297 | -1.688 | 🟢 核心 |
| P2-A | CU LME 升贴水差分 | CU 沪铜 | 5日 | +0.361 | +1.947 | 🟢 核心 |
| P2-B | NI LME 升贴水差分 | NI 沪镍 | 5日 | +0.314 | +1.602 | 🟢 核心 |
| P4-A | USD/CNY 日变化量 | AU/AG/CU | 5日 | -0.15~-0.19 | -1.0~-1.3 | 🟢 核心 |
| P4-B | CN10Y 国债收益率变化 | CU 沪铜 | 5日 | +0.050 | ~0.23 | 🟡 辅助 |
| P4-C | CN 10Y-2Y 曲线利差 | AU 黄金 | 5日 | +0.023 | +0.199 | 🟠 边缘 |
| P4-D | US 10Y-2Y 曲线利差 | AG 白银 | 5日 | +0.028 | +0.201 | 🟠 边缘 |
| P3-A | CU 前20会员净持仓变化 | CU 沪铜 | 1日 | — | IR=6.17(反转) | ⚠️ 待验证 |

**数据文件清单：**

| 因子 | 数据文件路径 | 状态 |
|------|------------|------|
| 金银比 | `data/crawlers/_shared/daily/AU_AG_ratio_corrected.csv` | ✅ 可用，45KB |
| CU LME 升贴水差分 | `data/crawlers/CU/daily/LME_copper_cash_3m_spread.csv` | ✅ 可用，83KB |
| NI LME 升贴水差分 | `data/crawlers/NI/daily/LME_nickel_cash_3m_spread.csv` | ✅ 可用，87KB |
| USD/CNY 即期汇率 | `data/crawlers/_shared/daily/USD_CNY_spot.csv` | ✅ 可用，85KB |
| CN/US 国债收益率 | `data/crawlers/_shared/daily/CN_US_bond_yield_full.csv` | ✅ 可用，240KB |
| WTI 原油 | `data/crawlers/_shared/daily/Brent_crude.csv` | ✅ 可用，29KB |
| CU 沪铜收盘价 | `data/crawlers/CU/daily/CU_fut_close.csv` | ✅ 可用，100KB |
| NI 沪镍收盘价 | `data/crawlers/NI/daily/NI_fut_close.csv` | ✅ 可用，107KB |

**配套因子注册表**：完整因子信息见 `Factor_Registry_P1_P4_20260420.md`

---

## 二、系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                 │
│   ① Dashboard（Plotly Dash，核心交互界面）                        │
│   ② PDF 周报（每周一自动生成，通过邮件推送）                      │
│   ③ 信号看板（多品种信号状态总览，5分钟刷新）                     │
│   ④ 告警通知（钉钉/微信/邮件，IC预警触发）                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                      信号计算层（每日 17:00 Cron 触发）           │
│                                                                  │
│   compute_factors_daily.py                                       │
│   ├── 增量更新因子原始值                                         │
│   ├── 计算 forward returns（5/10/20日）                         │
│   ├── 计算滚动 IC/IR（20/60/120日窗口）                         │
│   ├── 计算综合信号评分（0~100）                                  │
│   ├── 拥挤度检测（Skewness/Kurtosis）                           │
│   ├── 失效预测（IC趋势预警）                                     │
│   └── 输出：因子快照 JSON + 更新 Parquet 数据文件                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                      数据持久层                                    │
│                                                                  │
│   Parquet 格式（替代 CSV，性能提升 10~50x）                       │
│   ├── 按年份分区：factors/2020.parquet, 2021.parquet, ...        │
│   ├── 按品种分区：factors/CU/, factors/AG/, ...                  │
│   ├── 信号评分历史：scores.parquet                                │
│   └── 告警日志：alerts.parquet（每日追加）                        │
│                                                                  │
│   SQLite（结构化元数据）                                          │
│   ├── 因子注册表（名称/品种/参数/状态）                           │
│   ├── 告警记录（时间/因子/类型/级别/处理状态）                    │
│   └── 私人标注（日期/分类/内容/创建时间）                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                      数据源层                                     │
│                                                                  │
│   交易所 API（上期所/LME/SHFE 官方结算价）     → 主力源          │
│   AKShare（Tushare 备用）                    → 备用源           │
│   行业网站（Mysteel/SMM/隆众）                 → 兜底源           │
│   PIT 数据库（Point-in-Time 合规数据）         → 历史回测专用     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
D:\futures_v6\macro_engine\
├── research\
│   ├── reports\
│   │   ├── Factor_Decision_Support_System_Upgrade_Plan_20260423.md  ← 本文档
│   │   ├── Factor_Registry_P1_P4_20260420.md                        ← 因子注册表
│   │   └── IC_validation_*.md                                       ← IC验证报告
│   └── notebooks\                                                   ← Jupyter研究
│       ├── factor_ic_analysis.ipynb
│       └── signal_scoring.ipynb
├── data\
│   └── crawlers\
│       ├── _shared\daily\
│       │   ├── AU_AG_ratio_corrected.csv       ← 金银比原始数据
│       │   ├── USD_CNY_spot.csv                 ← 汇率原始数据
│       │   └── CN_US_bond_yield_full.csv       ← 国债收益率
│       ├── CU\daily\
│       │   ├── CU_fut_close.csv                 ← 价格数据
│       │   └── LME_copper_cash_3m_spread.csv   ← LME升贴水
│       └── NI\daily\
│           ├── NI_fut_close.csv
│           └── LME_nickel_cash_3m_spread.csv
├── factor_engine\                                 ← 因子引擎（新目录）
│   ├── __init__.py
│   ├── compute_factors_daily.py                  ← 每日因子计算主脚本
│   ├── factor_calculator.py                      ← 因子计算核心类
│   ├── signal_scorer.py                          ← 多维信号评分
│   ├── alert_engine.py                           ← 失效预警引擎
│   ├── crowding_detector.py                      ← 拥挤度检测
│   ├── regime_detector.py                        ← Regime自动检测
│   ├── data_quality.py                           ← 数据质量校验
│   ├── schema_validator.py                       ← pandera Schema校验
│   └── utils.py                                  ← 工具函数
├── dashboard\                                    ← Dashboard（新目录）
│   ├── app.py                                   ← Plotly Dash 主应用
│   ├── components\                              ← 页面组件
│   │   ├── factor_chart.py                       ← 因子历史曲线
│   │   ├── ic_chart.py                           ← IC曲线图
│   │   ├── ir_chart.py                           ← IR曲线图
│   │   ├── signal_board.py                       ← 信号看板
│   │   ├── distribution_chart.py                 ← 条件分布图
│   │   └── heatmap.py                            ← IC热力图
│   ├── callbacks.py                             ← Dash回调函数
│   └── assets\                                  ← CSS/图片
├── reports\                                     ← 自动报告输出
│   ├── weekly\                                  ← PDF周报
│   └── alerts\                                  ← 告警记录
└── database\
    ├── factors.parquet                          ← Parquet主数据
    ├── alerts.db                               ← SQLite告警库
    └── annotations.db                          ← SQLite标注库
```

---

## 三、统计方法论（增强规格）

### 3.1 IC/IR 计算标准（强化版）

#### 3.1.1 核心指标定义

**原方案问题**：只用 IC 均值作为唯一判断标准，容易被极端值（Stubborn Sample）误导。

**强化方案**：用**5维指标矩阵**综合评估信号质量：

| 指标 | 计算方式 | 抗极端值 | 说明 |
|------|---------|---------|------|
| **IC_mean** | 60日滚动窗口，Pearson相关系数均值 | ❌ 否 | 原始预测能力，但需结合IC_std |
| **IC_median** | 60日滚动窗口，IC序列中位数 | ✅ 是 | 核心指标，不受极端值影响 |
| **IC_std** | 60日滚动窗口，IC标准差 | — | 稳定性指标，越小越好 |
| **IR** | IC_mean / IC_std | ✅ 是 | 信息比率，综合稳定性 |
| **t_stat** | IC_mean × √N / IC_std | ✅ 是 | 显著性检验 |
| **win_rate** | IC同向交易日占比 | — | 方向稳定性（低IR高胜率信号有价值） |

**IC 计算伪代码**：
```python
def compute_rolling_ic(factor_series, return_series, window=60):
    """
    factor_series: 因子Z-score序列（对齐到交易日历）
    return_series:  forward return序列（与因子同日期对齐）
    window: 滚动窗口天数
    """
    ic_list = []
    for i in range(window, len(factor_series)):
        fac_window = factor_series.iloc[i-window:i]
        ret_window = return_series.iloc[i-window:i]
        # 去除NaN
        mask = fac_window.notna() & ret_window.notna()
        if mask.sum() < 20:
            ic_list.append(np.nan)
            continue
        ic = pearsonr(fac_window[mask], ret_window[mask])[0]
        ic_list.append(ic)
    return pd.Series(ic_list, index=factor_series.index[window:])
```

#### 3.1.2 Bootstrap 置信区间（新增，P0级）

**为什么需要**：IC 点估计=+0.05，但 95% CI=[-0.02, +0.12] ——说明信号不稳定，不应该贸然使用。

```python
def compute_ic_bootstrap_ci(factor_series, return_series, window=60,
                             n_bootstrap=1000, confidence=0.95):
    alpha = 1 - confidence
    ic_samples = []

    for _ in range(n_bootstrap):
        # 有放回重采样
        idx = np.random.choice(len(factor_series),
                                size=len(factor_series),
                                replace=True)
        fac_sample = factor_series.iloc[idx].reset_index(drop=True)
        ret_sample = return_series.iloc[idx].reset_index(drop=True)

        # 截取有效长度
        min_len = min(len(fac_sample), len(ret_sample))
        fac_sample = fac_sample[:min_len]
        ret_sample = ret_sample[:min_len]

        # 计算该次采样的IC均值
        ic = pearsonr(fac_sample, ret_sample)[0]
        ic_samples.append(ic)

    ci_lower = np.percentile(ic_samples, alpha/2 * 100)
    ci_upper = np.percentile(ic_samples, (1-alpha/2) * 100)

    return {
        'ic_mean': np.mean(ic_samples),
        'ic_median': np.median(ic_samples),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'cross_zero': ci_lower < 0 < ci_upper
    }
```

**判断规则**：
- `cross_zero = True` → 信号不稳定，降权处理，通知研究员
- `ci_upper < 0` → 强负向信号，考虑反向使用
- `ci_lower > 0` → 强正向信号，可以加仓

#### 3.1.3 多重检验校正（新增）

```python
from statsmodels.stats.multitest import multipletests

def adjust_pvalues(p_values, method='fdr_bh'):
    """
    方法：FDR Benjamini-Hochberg（发现最多信号，允许一定假阳性）
    备选：Bonferroni（最严格，防止家族误差膨胀）
    """
    reject, p_corrected, _, _ = multipletests(p_values, method=method)
    return p_corrected, reject

# 使用
p_values = [0.001, 0.03, 0.08, 0.12, 0.45]
p_corrected, significant = adjust_pvalues(p_values, 'fdr_bh')
# significant = [True, True, False, False, False]
```

### 3.2 信号综合评分（0~100分制）

#### 3.2.1 评分公式

```
Score = w1 × IC_norm + w2 × Stability + w3 × Decay + w4 × Breadth + w5 × RegimeFit

其中：
  IC_norm    = min(100, |IC_median| / 0.10 × 100)        （40%权重）
  Stability  = max(0, 100 - (IC_std / |IC_mean|) × 100) （20%权重）
  Decay      = decay_score(optimal_hold, actual_hold)     （15%权重）
  Breadth    = cross_symbol_effectiveness_score            （15%权重）
  RegimeFit  = current_regime_ic / historical_avg_ic       （10%权重）
```

#### 3.2.2 评分等级与应用

| 评分区间 | 等级 | 含义 | 建议操作 |
|----------|------|------|---------|
| **80~100** | 🟢 强信号 | IC稳定、跨品种有效、当前Regime匹配 | 权重 20%+，可作为核心信号 |
| **60~79** | 🟡 标准信号 | 信号有效但不完美 | 权重 10~20%，辅助判断 |
| **40~59** | 🟠 边缘信号 | IC不稳定或单向性强 | 权重 < 5%，谨慎使用 |
| **20~39** | 🔴 弱信号 | 信号质量差 | 权重 0~2%，观察为主 |
| **0~19** | ⚫ 无效信号 | IC接近零或负向 | 建议剔除，等待重建 |

#### 3.2.3 各维度详细计算

**Stability（稳定性，0~100）**：
```
Stability = max(0, 100 - CV × 100)
其中 CV = IC_std / |IC_mean|（变异系数）

解读：
  CV < 0.3 → Stability > 70 → 信号稳定
  CV = 0.5 → Stability = 50 → 信号中等波动
  CV > 1.0 → Stability < 0 → 信号不稳定，封顶0
```

**Decay（衰减速度，0~100）**：
```
Decay = 100 - |optimal_hold - actual_hold| / optimal_hold × 100

解读：
  |optimal - actual| = 0 → Decay = 100 → 当前持有期最优
  |optimal - actual| = 50% → Decay = 50 → 有优化空间
```

**Breadth（跨品种有效性，0~100）**：
```
Breadth = (有效品种数 / 总品种数) × 100

有效品种定义：该因子的 IC_median > 0.02 且 Bootstrap CI 不跨零

解读：
  金银比只对 AG 有效（1/9）→ Breadth = 11
  USD_diff 对 AU/AG/CU 有效（3/9）→ Breadth = 33
  LME差分 对 CU/NI 有效（2/9）→ Breadth = 22
```

**RegimeFit（当前Regime匹配度，0~100）**：
```
RegimeFit = IC_current_regime / IC_all_regimes_mean × 100

解读：
  RegimeFit > 80 → 当前市场环境适合该因子，全力使用
  RegimeFit < 50 → 当前市场环境不匹配，降权
  RegimeFit < 20 → Regime失效，关闭信号
```

---

## 四、功能模块详细规格

### 4.1 模块一：因子历史曲线图（Chart 1）⭐ P0

**功能**：展示因子原始值 + 品种价格的双轴叠加走势

**规格**：

```
图表类型：Plotly Dash + candlestick / line chart
时间范围：2020-01-01 ~ 今日（默认），支持缩放
X轴：日期（交易日历，非自然日）
左Y轴：因子原始值（标准化/未标准化可切换）
右Y轴：品种期货价格

标注层：
  ├── 均值线（灰色虚线）
  ├── ±1σ 通道带（浅蓝色填充）
  ├── ±2σ 通道带（更浅蓝色填充）
  ├── 宏观事件竖线（COVID爆发/封控/美联储加息等，可点击查看详情）
  └── 最新值标注（右下角数字标签）

交互：
  ├── Hover：显示日期 + 因子值 + 价格 + IC当日值
  ├── 缩放：滑轮缩放 + 框选放大
  ├── 范围选择器：1M / 3M / 6M / YTD / 1Y / 3Y / All
  └── 私人标注：右键"添加标注"，弹出文本框

输出：
  静态图：PNG，1920×1080，用于PDF报告
  动态：实时Dash页面
```

**宏观事件标注清单（预设）**：

| 日期 | 事件 | 影响 |
|------|------|------|
| 2020-01-20 | COVID疫情爆发 | 全球需求骤降，商品普跌 |
| 2020-03-15 | 美联储降息至0 | 流动性宽松，黄金大涨 |
| 2020-04-20 | WTI原油期货负值 | 流动性危机，极端事件 |
| 2022-03-16 | 美联储加息25bp | 紧缩周期开启，铜价压力 |
| 2022-04-01 | 上海封控 | 铜需求崩塌，CN10Y→CU失效 |
| 2022-11-11 | 防疫新十条 | 放开预期，商品反弹 |
| 2023-03-10 | SVB银行倒闭 | 避险情绪，黄金上涨 |
| 2024-09-24 | 中国降准降息 | 宽松周期，商品利好 |
| 2025-01-20 | 特朗普关税2.0 | 贸易战，铜镍需求预期下降 |

### 4.2 模块二：滚动 IC 曲线图（Chart 2）⭐ P0

**功能**：展示滚动 IC 时间序列，判断信号稳定性

**规格**：

```
图表类型：Plotly Scatter + 填充区域
X轴：日期
Y轴：IC 值（-1 ~ +1，零线居中）

多曲线：
  ├── IC_20日（细线，敏感）
  ├── IC_60日（中线，核心）
  └── IC_120日（粗线，长期趋势）

阈值线：
  ├── IC = 0（零线，黑色虚线）
  ├── IC = +0.05（弱有效阈值，绿色虚线）
  ├── IC = -0.05（弱有效阈值，红色虚线）
  └── IC = ±0.10（强有效阈值，绿色/红色粗线）

显著性标注：
  ├── 当 IC_60 > 0.10 时，K线标绿色
  ├── 当 IC_60 < -0.10 时，K线标红色
  └── 当 Bootstrap CI 跨零时，K线标灰色+虚线边框

事件竖线：同 Chart 1
```

### 4.3 模块三：滚动 IR 曲线图（Chart 3）⭐ P0

**规格**：

```
图表类型：Plotly Scatter
X轴：日期
Y轴：IR 值（无界限，但常见范围 -3 ~ +3）

颜色规则（60日滚动IR）：
  ├── IR > +0.5 → 绿色（信号有效）
  ├── IR +0.3~+0.5 → 浅绿色（边缘有效）
  ├── IR -0.3~+0.3 → 灰色（信号不稳定）
  ├── IR -0.5~-0.3 → 浅红色（边缘反向）
  └── IR < -0.5 → 深红色（信号反转，可能反向用）

趋势箭头：
  ├── IR 20日均线较前20日上升 → 绿色↑
  ├── IR 20日均线较前20日下降 → 红色↓
  └── 变化 < 5% → 灰色→
```

### 4.4 模块四：因子信号 → 收益率条件分布图（Chart 4）⭐ P1

**功能**：直观展示"因子分位数 → 未来收益率"的映射关系

**规格**：

```
图表类型：Seaborn violin plot + strip plot
X轴：因子分位数（Q1 / Q2 / Q3 / Q4 / Q5）
Y轴：持有期收益率（%）

多子图：
  ├── 5日持有期
  ├── 10日持有期
  └── 20日持有期

解读：
  Q1（左）收益率 < Q5（右）收益率 → 信号方向正确
  Q1 vs Q5 分布无重叠 → 信号区分度极高
  分布窄 → 信号稳定；分布宽 → 信号波动大

统计标注：
  每组标注均值（μ）和标准差（σ）
  均值差异 t-test p-value 标注在图上
```

### 4.5 模块五：IC 衰减曲线图（Chart 5）⭐ P1

**功能**：展示 IC 随持有期衰减的速度，找到最优持有期

**规格**：

```
图表类型：Plotly Line chart
X轴：持有期（1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 60 日）
Y轴：IC 均值（60日滚动窗口）

多曲线：
  ├── IC_60日（主曲线，核心）
  ├── IC_20日（辅曲线，敏感）
  └── IC_120日（辅曲线，长期）

标注：
  ├── 最优持有期（IC峰值处）→ 大号星标
  ├── 半衰期（IC衰减到峰值一半的持有期）→ 虚线
  └── 衰减率（每增加1日持有期IC下降多少）

解读：
  衰减慢（曲线平坦）→ 信号持续有效，可以长持
  衰减快（曲线陡峭）→ 信号短促，必须及时平仓
```

### 4.6 模块六：多因子 IC 热力图（Chart 6）⭐ P1

**功能**：一张图展示所有因子 × 所有品种的 IC 矩阵

**规格**：

```
图表类型：Plotly Heatmap（diverging colormap）
X轴：品种（AU / AG / CU / NI / ZN / AL / PB / RU / RB / I / JM）
Y轴：因子代码（P1-A金银比 / P2-A LME Cu / P2-B LME Ni / P4-A USD / P4-B CN10Y 等）

颜色：
  IC > +0.10 → 深绿
  IC +0.05~+0.10 → 浅绿
  IC 0~+0.05 → 淡绿
  IC = 0 → 白色
  IC -0.05~0 → 淡红
  IC -0.10~-0.05 → 浅红
  IC < -0.10 → 深红

单元格标注：显示具体 IC 值（保留3位小数）
点击单元格 → 跳转该因子→该品种的详细分析页面

交互：
  ├── Hover 显示：因子描述 / 品种名称 / IC / IR / 胜率 / 评分
  └── 筛选：只显示某类因子（宏观/期限结构/资金结构）
```

### 4.7 模块七：因子拥挤度监控（Chart 7）⭐ P2

**规格**：

```
图表类型：Plotly Gauge + time series

Gauge 仪表盘（综合拥挤度，0~100）：
  ├── 0~40 → 绿色（无拥挤）
  ├── 40~60 → 黄色（轻度拥挤，观察）
  ├── 60~80 → 橙色（中度拥挤，降权）
  └── 80~100 → 红色（严重拥挤，关闭信号）

子指标（雷达图）：
  ├── Skewness（偏度）→ 正常范围 -1 ~ +1
  ├── Kurtosis（峰度）→ 正常范围 < 5
  ├── 因子间相关性最大值 → 正常 < 0.7
  ├── 持仓集中度变化率 → 正常 < 20%/月
  └── 因子收益离散度 → 越小越拥挤
```

### 4.8 模块八：信号看板（Dashboard 主页）⭐ P0

**功能**：多品种信号状态总览，一眼看全局

**布局**：

```
┌──────────────────────────────────────────────────────────────────────┐
│  因子信号监控看板          最后更新：2026-04-23 16:45    🔄 5分钟自动 │
├──────────────────────────────────────────────────────────────────────┤
│  [时间范围选择]  1W | 1M | 3M | YTD | 1Y | 3Y | All  [刷新] [导出]  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  品种   │ 核心因子     │ IC(60日) │ IR(60日) │ 评分 │ 趋势 │ 信号   │
│  ───────┼──────────────┼──────────┼──────────┼──────┼──────┼───────  │
│  CU 沪铜│ LME差分 P2-A │  +0.361  │  +1.947  │  92  │  ↑   │ 🟢 做多  │
│  NI 沪镍│ LME差分 P2-B │  +0.314  │  +1.602  │  85  │  →   │ 🟢 做多  │
│  AG 白银│ 金银比 P1-A  │  -0.297  │  -1.688  │  88  │  ↓   │ 🟡 观望  │
│  AU 黄金│ USD_diff P4A │  -0.146  │  -1.051  │  75  │  ↓   │ 🟡 低配  │
│  ZN 沪锌│ 无有效因子   │    —     │    —     │  —   │  —   │ 🔴 空仓  │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  ⚠️ 告警栏                                                              │
│  [2026-04-23 15:30] CN10Y_diff→CU：IC连续5日下降，当前0.038，预警阈值0.05│
│  [2026-04-23 09:15] 金银比：Bootstrap CI 跨零（-0.01~+0.08），信号不稳 │
└──────────────────────────────────────────────────────────────────────┘
```

**信号状态定义**：

| 信号 | 条件 | 操作建议 |
|------|------|---------|
| 🟢 做多 | 评分≥70 + IC>0 + 方向向上 | 正常配置，权重≥15% |
| 🟢 做空 | 评分≥70 + IC<0 + 方向向下 | 正常配置，权重≥15% |
| 🟡 观望 | 评分50~69 或 IC方向不稳 | 降低权重，观察3日 |
| 🔴 空仓 | 评分<50 或 IC跨零 或 拥挤度>80 | 权重=0，等待信号重建 |

---

## 五、数据质量校验规格

### 5.1 Schema 校验（pandera）

```python
import pandera as pa
from pandera import Column, Check, DataFrameSchema

FactorSchema = DataFrameSchema({
    "date": Column(pa.DateTime, nullable=False, unique=True),
    "factor_value": Column(pa.Float, nullable=False),
    "factor_zscore": Column(pa.Float, nullable=True),
    "ic_60d": Column(pa.Float, nullable=True),
    "ir_60d": Column(pa.Float, nullable=True),
    "signal_score": Column(pa.Int, nullable=True, checks=Check.in_range(0, 100)),
})

# 各因子的物理约束
GoldSilverRatioSchema = FactorSchema.extend({
    "factor_value": Column(pa.Float, checks=Check.in_range(20, 200)),
    # 金银比物理上不可能 < 20 或 > 200
})

USDCNYDiffSchema = FactorSchema.extend({
    "factor_value": Column(pa.Float, checks=Check.in_range(-0.05, 0.05)),
    # USD/CNY 日变化不可能超过 5%（极端情况）
})

LMESpreadDiffSchema = FactorSchema.extend({
    "factor_value": Column(pa.Float, checks=Check.in_range(-500, 500)),
    # LME升贴水差分单位USD/T，正常范围 -300~+300
})
```

### 5.2 每日数据质量检查清单

```python
def daily_data_quality_check(factor_name, df):
    alerts = []

    # 1. 缺失值检查
    if df["factor_value"].isna().sum() > 0:
        alerts.append(f"WARNING: {df['factor_value'].isna().sum()} NaN values found")

    # 2. 极端跳跃检查（> 5σ）
    daily_change = df["factor_value"].diff().abs()
    threshold = daily_change.mean() + 5 * daily_change.std()
    if daily_change.max() > threshold:
        alerts.append(f"ALERT: Extreme jump detected: {daily_change.idxmax()}")

    # 3. 连续不更新检查（> 3个交易日）
    if df["factor_value"].tail(3).notna().sum() == 0:
        alerts.append(f"CRITICAL: No update for 3 consecutive trading days")

    # 4. Schema 校验
    try:
        schema = get_schema(factor_name)
        schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        alerts.append(f"DATA_QUALITY_FAIL: {e}")

    # 5. 与备用源差异检查（如果多数据源）
    if has_backup_source(factor_name):
        diff = abs(df["factor_value"] - df["backup_value"])
        if diff.mean() > 0.01:  # 1%以上差异
            alerts.append(f"WARNING: Source差异大，均值={diff.mean():.4f}")

    return alerts
```

### 5.3 PIT 合规性冒烟测试

```python
def pit_smoke_test(factor_name, n_samples=100):
    """
    随机抽取 n_samples 个日期，验证因子值 <= 对应日期的 snapshot
    即：确保没有用未来数据计算历史因子值
    """
    from your_pit_db import PitDataService

    dates = random.sample(all_dates, n_samples)
    violations = []

    for date in dates:
        factor_value_on_date = compute_factor(factor_name, date)
        snapshot_value = PitDataService.get_snapshot(factor_name, date)

        if factor_value_on_date != snapshot_value:
            violations.append({
                "date": date,
                "factor_value": factor_value_on_date,
                "snapshot": snapshot_value
            })

    if violations:
        print(f"PIT VIOLATION: {len(violations)} / {n_samples} samples failed")
        return False
    else:
        print(f"PIT OK: All {n_samples} samples passed")
        return True
```

---

## 六、失效预测与告警规格

### 6.1 失效预测模型

**核心思想**：在 IC 真正崩掉之前，市场上会有一些"前兆"——IC 的短期均线开始下行、资金开始拥挤、因子偏度开始极端化。

**预警触发条件（满足任一即预警）**：

| 预警级别 | 条件 | 含义 |
|----------|------|------|
| ⚠️ 黄色预警 | IC_20日均线跌破 IC_60日均线 | 短期动能转弱，可能趋势反转 |
| ⚠️ 黄色预警 | IC 连续 10 个交易日下降 | 持续性减弱，不是正常波动 |
| ⚠️ 黄色预警 | IC_60日均值较前60日下降 > 30% | 信号系统性弱化 |
| 🔴 红色预警 | IC_60日均线 < 0（转负） | 信号彻底失效 |
| 🔴 红色预警 | Bootstrap CI 跨零（95% CI） | 统计上已不显著 |
| 🔴 红色预警 | 拥挤度 > 80 | 太多人用，信号踩踏 |
.2 告警消息格式（续）

```json
{
  "alert_id": "ALERT-20260423-001",
  "timestamp": "2026-04-23 16:30:00",
  "severity": "YELLOW",
  "factor": "CN10Y_diff",
  "target": "CU",
  "symbol": "CU",
  "ic_60d_current": 0.038,
  "ic_60d_previous": 0.052,
  "threshold": 0.050,
  "trigger": "IC连续5日下降，跌破预警阈值0.05",
  "recommendation": "建议降低该因子权重至5%，观察3个交易日",
  "expected_recovery": "如果CN PMI回升至50以上，可恢复权重",
  "auto_action": "已自动降权（需人工确认）"
}
```

### 6.3 告警路由规则

```
告警级别 × 时间 → 路由方式

┌─────────────┬──────────────────┬────────────────────────────────────┐
│ 告警级别     │ 路由渠道          │ 响应要求                             │
├─────────────┼──────────────────┼────────────────────────────────────┤
│ 信息（蓝）   │ 日志记录          │ 自动处理，无需人工                    │
│ 观察（黄）   │ 钉钉/微信群       │ 研究员4小时内确认                     │
│ 警告（橙）   │ 钉钉/微信 + 邮件  │ 研究员2小时内确认                     │
│ 严重（红）   │ 电话 + 钉钉 + 邮件 │ 研究员30分钟内确认，否则升级          │
└─────────────┴──────────────────┴────────────────────────────────────┘

升级机制：
  研究员30分钟内未确认 → 升级给项目负责人
  研究员60分钟内未确认 → 升级给风控总监
  紧急情况 → 直接电话呼叫
```

---

## 七、Regime 自动检测（HMM）

### 7.1 为什么需要自动 Regime 检测

当前方案依赖人工标注宏观事件（COVID爆发/封控等），存在两个问题：
1. **人工标注滞后**：事件发生才知道，不知道什么时候开始"不正常"
2. **过于粗糙**：封控3个月期间市场也在动态变化，不能简单用"封控期=失效"来概括

**解决方案：Hidden Markov Model (HMM)** — 让数据自己告诉我们什么时候Regime变了。

### 7.2 HMM Regime 检测规格

```python
import numpy as np
from hmmlearn import hmm

class RegimeDetector:
    """
    用 HMM 自动检测市场 Regime
    观测变量：VIX + IC_median_diff + CN10Y_diff（三个维度）
    隐状态：Regime 1(正常) / Regime 2(危机) / Regime 3(政策刺激)
    """

    def __init__(self, n_regimes=3):
        self.n_regimes = n_regimes
        self.model = None
        self.regime_names = {
            0: "正常宏观期",
            1: "危机/高波动期",
            2: "政策刺激/宽松期"
        }

    def fit(self, features_df):
        """
        features_df: DataFrame，columns=['vix', 'ic_diff', 'cn10y_diff']
                     至少需要 2 年数据（500+ 样本）
        """
        X = features_df[['vix', 'ic_diff', 'cn10y_diff']].values

        # 标准化
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # 训练 HMM
        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type='full',
            n_iter=1000,
            random_state=42
        )
        self.model.fit(X_scaled)

        # 预测隐状态
        self.hidden_states = self.model.predict(X_scaled)

        # 给每个隐状态贴标签（根据特征均值判断）
        self._label_regimes(features_df)

        return self

    def _label_regimes(self, features_df):
        """
        根据每个 Regime 的特征均值，判断它代表什么宏观状态
        """
        for regime_id in range(self.n_regimes):
            mask = self.hidden_states == regime_id
            regime_features = features_df[mask].mean()

            # 简单规则判断
            if regime_features['vix'] > 25:
                label = "危机/高波动期"
            elif regime_features['cn10y_diff'] > 0.05:
                label = "政策刺激/宽松期"
            else:
                label = "正常宏观期"

            self.regime_names[regime_id] = label

    def get_current_regime(self):
        """返回当前 Regime ID 和名称"""
        current_state = self.hidden_states[-1]
        return current_state, self.regime_names[current_state]
```

### 7.3 Regime-conditional IC 计算

```python
def compute_regime_ic(factor_series, return_series, regime_labels, target_regime):
    """
    只计算特定 Regime 下的 IC，避免用全样本掩盖结构性差异
    """
    mask = regime_labels == target_regime
    fac_regime = factor_series[mask]
    ret_regime = return_series[mask]

    if len(fac_regime) < 30:
        return np.nan

    # 计算 Regime 内的 IC
    ic = pearsonr(fac_regime, ret_regime)[0]
    return ic

# 示例：计算金银比在"危机期"的 IC
crisis_ic = compute_regime_ic(gold_silver_ratio, ag_forward_return,
                                regimes, target_regime=1)
normal_ic = compute_regime_ic(gold_silver_ratio, ag_forward_return,
                                regimes, target_regime=0)

print(f"危机期 IC: {crisis_ic:.4f}, 正常期 IC: {normal_ic:.4f}")
```

### 7.4 各因子 Regime 匹配表（待填充）

| 因子 | Regime 1（正常期）IC | Regime 2（危机期）IC | Regime 3（宽松期）IC | 最优 Regime |
|------|---------------------|---------------------|---------------------|------------|
| P1-A 金银比→AG | 待测 | 待测 | 待测 | — |
| P2-A LME差分→CU | 待测 | 待测 | 待测 | — |
| P4-A USD_diff→AU | 待测 | 待测 | 待测 | — |
| P4-B CN10Y→CU | 待测 | 待测 | 待测 | — |

> 注：表格在 HMM 模型训练后填充，作为因子使用的重要参考。

---

## 八、动态持有期优化规格

### 8.1 最优持有期搜索

```python
def find_optimal_hold_period(factor_series, return_series,
                               hold_range=range(1, 61)):
    """
    对每个持有期计算 IC，选择 IC 均值最高的持有期作为最优持有期
    """
    results = []

    for hold in hold_range:
        fwd_return = compute_forward_return(price_series, hold)
        ic_series = compute_rolling_ic(factor_series, fwd_return, window=60)
        ic_mean = ic_series.mean()
        ic_median = ic_series.median()
        results.append({
            'hold': hold,
            'ic_mean': ic_mean,
            'ic_median': ic_median
        })

    results_df = pd.DataFrame(results)

    # 最优持有期 = IC 中位数最高的持有期（抗极端值）
    optimal_hold = results_df.loc[
        results_df['ic_median'].abs().idxmax(), 'hold'
    ]

    # 半衰期 = IC 衰减到峰值一半的持有期
    peak_ic = results_df['ic_median'].abs().max()
    half_ic = peak_ic / 2
    half_life_row = results_df[
        results_df['ic_median'].abs() <= half_ic
    ].iloc[0] if len(results_df[
        results_df['ic_median'].abs() <= half_ic
    ]) > 0 else results_df.iloc[-1]
    half_life = half_life_row['hold']

    return {
        'optimal_hold': optimal_hold,
        'peak_ic': peak_ic,
        'half_life': half_life,
        'ic_decay_curve': results_df
    }
```

### 8.2 波动率调整持有期

```python
def adjust_hold_by_volatility(base_hold, current_vix, historical_vix_median=18):
    """
    高波动环境（VIX>25）→ 缩短持有期（信号更快失效）
    低波动环境（VIX<15）→ 延长持有期（信号持续性好）
    """
    vol_ratio = current_vix / historical_vix_median

    if vol_ratio > 1.4:  # 高波动
        adjusted_hold = int(base_hold * 0.7)  # 缩短30%
        reason = f"VIX={current_vix:.1f}偏高，缩短持有期"
    elif vol_ratio < 0.8:  # 低波动
        adjusted_hold = int(base_hold * 1.3)  # 延长30%
        reason = f"VIX={current_vix:.1f}偏低，延长持有期"
    else:
        adjusted_hold = base_hold
        reason = "VIX正常，使用基准持有期"

    return max(1, adjusted_hold), reason
```

---

## 九、拥挤度检测规格

### 9.1 拥挤度指标计算

```python
def compute_crowding_score(factor_returns_df):
    """
    factor_returns_df: DataFrame
        index=日期
        columns=[金银比_return, LME差分_return, USD_diff_return, ...]

    返回：综合拥挤度分数（0~100）
    """
    scores = {}

    # 1. 因子偏度（Skewness）
    # Skewness < -1 或 > +1 表示极端拥挤
    for col in factor_returns_df.columns:
        skew = factor_returns_df[col].skew()
        if abs(skew) > 1.5:
            skew_score = 100
        elif abs(skew) > 1.0:
            skew_score = 75
        elif abs(skew) > 0.5:
            skew_score = 50
        else:
            skew_score = 25
        scores[f'{col}_skew'] = skew_score

    # 2. 因子峰度（Kurtosis）
    # Kurtosis > 5 表示肥尾极端
    for col in factor_returns_df.columns:
        kurt = factor_returns_df[col].kurtosis()
        if kurt > 8:
            kurt_score = 100
        elif kurt > 5:
            kurt_score = 75
        elif kurt > 3:
            kurt_score = 50
        else:
            kurt_score = 25
        scores[f'{col}_kurt'] = kurt_score

    # 3. 因子间相关性矩阵最大特征根占比
    # 如果第一主成分解释 > 50% 方差，说明因子高度共线性（系统性拥挤）
    corr_matrix = factor_returns_df.corr()
    eigenvalues = np.linalg.eigvalsh(corr_matrix)
    eigenvalues = eigenvalues[::-1]  # 降序
    first_component_var = eigenvalues[0] / eigenvalues.sum()
    corr_score = min(100, first_component_var * 200)  # 0.5->100分

    # 4. 综合拥挤度（加权平均）
    weights = {
        'skew': 0.3,
        'kurt': 0.3,
        'corr': 0.4
    }

    all_skew_scores = [v for k, v in scores.items() if 'skew' in k]
    all_kurt_scores = [v for k, v in scores.items() if 'kurt' in k]

    crowding_score = (
        np.mean(all_skew_scores) * weights['skew'] +
        np.mean(all_kurt_scores) * weights['kurt'] +
        corr_score * weights['corr']
    )

    return {
        'overall_crowding': crowding_score,
        'skew_scores': scores,
        'corr_matrix': corr_matrix,
        'first_component_var': first_component_var,
        'status': get_crowding_status(crowding_score)
    }

def get_crowding_status(score):
    if score < 40:
        return "🟢 正常"
    elif score < 60:
        return "🟡 轻度拥挤，观察"
    elif score < 80:
        return "🟠 中度拥挤，建议降权"
    else:
        return "🔴 严重拥挤，建议关闭信号"
```

---

## 十、实施路线图

### 10.1 开发阶段划分

```
Phase 0（第1~2周）：数据基础设施
  ├── 数据质量 Schema 校验（pandera）
  ├── Parquet 替代 CSV 数据管道
  ├── PIT 冒烟测试框架
  └── 每日数据更新 Cron 配置

Phase 1（第3~4周）：核心计算引擎
  ├── 因子 IC/IR 滚动计算（含 Bootstrap CI）
  ├── 多维信号评分（5维评分体系）
  ├── 失效预测引擎（IC趋势预警）
  └── Regime Detector（HMM 初版）

Phase 2（第5~6周）：可视化 Dashboard
  ├── Plotly Dash 单因子历史曲线（Chart 1~3）
  ├── 因子信号看板（Chart 8）
  ├── IC 热力图（Chart 6）
  └── 宏观事件标注交互

Phase 3（第7~8周）：高级功能
  ├── 因子→收益率条件分布图（Chart 4）
  ├── IC 衰减曲线（Chart 5）
  ├── 拥挤度监控（Chart 7）
  ├── 动态持有期优化
  └── 私人标注系统

Phase 4（第9~10周）：自动化与输出
  ├── PDF 周报自动生成
  ├── 钉钉/微信告警推送
  ├── Dashboard 权限管理
  └── 全量回测报告输出
```

### 10.2 工时估算汇总

| Phase | 模块 | 工时 | 累计工时 |
|-------|------|------|---------|
| Phase 0 | 数据基础设施 | 16h | 16h |
| Phase 1 | 核心计算引擎 | 24h | 40h |
| Phase 2 | 可视化 Dashboard | 24h | 64h |
| Phase 3 | 高级功能 | 20h | 84h |
| Phase 4 | 自动化与输出 | 12h | **96h** |

> 总计：**约 96 小时**（约 12 个工作日）
> 说明：按 mimo（程序员 agent-d4f65f0e）开发估算，不含需求确认和测试时间。

### 10.3 里程碑定义

| 里程碑 | 完成标准 | 预期时间 |
|--------|---------|---------|
| **M0 数据就绪** | Parquet 数据管道打通，所有 P1 因子数据可用 | Week 2 |
| **M1 核心上线** | IC/IR 滚动计算 + 信号评分 + Dashboard 基本功能 | Week 4 |
| **M2 完整功能** | 所有 8 个 Chart 上线，告警推送可用 | Week 8 |
| **M3 自动化运行** | PDF 周报自动生成，系统 7×24h 运行 | Week 10 |

---

## 十一、技术选型汇总

| 技术层 | 选型 | 备选 | 决策原因 |
|--------|------|------|---------|
| 可视化框架 | **Plotly Dash** | Streamlit / ECharts | 交互能力强，多图联动原生支持，Python 原生 |
| 数据格式 | **Parquet** | CSV / HDF5 | 列式压缩，类型安全，查询快10~50x |
| 统计校验 | **pandera** | Great Expectations | 与 pandas 原生集成，API 友好 |
| 时间序列分析 | **statsmodels** | Prophet / Kats | 假设检验、HMM、ARIMA 原生支持 |
| HMM 模型 | **hmmlearn** | pomegranate | Gaussian HMM 成熟稳定 |
| 时区处理 | **pytz** | zoneinfo | Windows 兼容性更好 |
| 数据库（告警/标注） | **SQLite** | PostgreSQL | 轻量，无需额外部署 |
| 报告生成 | **ReportLab** | WeasyPrint / pdfkit | Python 原生，支持中文字体 |
| Cron 调度 | Windows Task Scheduler | APScheduler | 服务器稳定运行 |
| 告警推送 | 钉钉自定义机器人 | 微信 / 飞书 | 技术成熟，API 简单 |

---

## 十二、风险与缓解措施

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LME 数据断供（制裁/禁运） | 中 | 高 | 提前储备离线数据；SMM 作为备用源 |
| AKShare 接口变动（API Breaking Change） | 中 | 中 | 版本固定；增加集成测试 |
| Dashboard 性能问题（大数据量） | 低 | 中 | Parquet 按年份分区；图表采样降采样 |
| 过多告警导致狼来了效应 | 高 | 中 | 告警阈值从严；告警聚合（同类合并） |
| Regime 模型过拟合 | 中 | 中 | 用2018~2022数据训练，2023~2024数据验证 |
| 研究员不信任系统评分 | 高 | 高 | 透明化评分逻辑；输出每维度详细得分；先手动对照3个月再自动 |

---

## 十三、附录

### 13.1 数据文件完整清单

```
D:\futures_v6\macro_engine\data\crawlers\
├── _shared\daily\
│   ├── AU_AG_ratio_corrected.csv        # 金银比（修正版，含CNY/kg→CNY/g换算）
│   ├── USD_CNY_spot.csv                 # USD/CNY即期汇率
│   ├── CN_US_bond_yield_full.csv        # 中美国债收益率全量（2002~2026）
│   ├── Brent_crude.csv                  # 布伦特原油现货
│   └── WTI_crude.csv                   # WTI原油（备用）
├── CU\daily\
│   ├── CU_fut_close.csv                 # SHFE沪铜主力合约收盘价
│   └── LME_copper_cash_3m_spread.csv   # LME铜现货-3M升贴水
├── NI\daily\
│   ├── NI_fut_close.csv                # SHFE沪镍主力合约收盘价
│   └── LME_nickel_cash_3m_spread.csv   # LME镍现货-3M升贴水
└── AG\daily\
    └── AG_fut_close.csv                 # SHFE沪银主力合约收盘价（待补充）
```

### 13.2 因子注册表快速索引（截至 2026-04-20）

完整因子信息见：`D:\futures_v6\macro_engine\research\reports\Factor_Registry_P1_P4_20260420.md`

核心快速索引：

| 因子代码 | 描述 | 品种 | 持有期 | IC | IR | 评分 | 状态 |
|----------|------|------|--------|-----|-----|------|------|
| P1-A | 金银比 | AG | 10日 | -0.297 | -1.688 | 88 | 🟢 上线 |
| P2-A | CU LME升贴水差分 | CU | 5日 | +0.361 | +1.947 | 92 | 🟢 上线 |
| P2-B | NI LME升贴水差分 | NI | 5日 | +0.314 | +1.602 | 85 | 🟢 上线 |
| P4-A | USD_CNY_diff | AU/AG/CU | 5日 | -0.15~-0.19 | -1.0~-1.3 | 75 | 🟢 上线 |
| P4-B | CN10Y_diff→CU | CU | 5日 | +0.050 | ~0.23 | 60 | 🟡 辅助 |
| P3-A | CU净持仓变化 | CU | 1日 | — | IR=6.17 | 50 | ⚠️ 待验证 |

### 13.3 文档变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2026-04-23 | v1.0 | 初版创建，包含完整架构设计 | YIYI |

### 13.4 相关文档索引

```
本项目相关文档：
  [1] Factor_Registry_P1_P4_20260420.md          ← 因子注册表
  [2] IC_validation_Phase1_20260420.md            ← Phase1 IC验证
  [3] IC_validation_Phase4_20260420.md            ← Phase4 IC验证
  [4] IC_validation_Phase2_Phase3_20260420.md     ← Phase2/3 IC验证
  [5] CU_NI_LME_Spread_Fix_20260420.md            ← LME差分数据修正
  [6] Factor_Decision_Support_System_Upgrade_Plan_20260423.md ← 本文档（第一部分）
  [7] Factor_Decision_Support_System_Upgrade_Plan_20260423_Part2.md ← 本文档（第二部分）

数据相关：
  [8] D:\futures_v6\macro_engine\data\crawlers\README.md ← 数据源说明（待创建）

开发相关：
  [9] D:\futures_v6\macro_engine\factor_engine\README.md  ← 因子引擎开发说明（待创建）
  [10] D:\futures_v6\macro_engine\dashboard\README.md    ← Dashboard使用说明（待创建）
```

---

## 十四、一页总览（决策者速读）

```
┌─────────────────────────────────────────────────────────────────┐
│              因子监控系统升级项目 · 一页总览                      │
├─────────────────────────────────────────────────────────────────┤
│  目标：让因子系统从"展示工具"升级为"决策辅助系统"               │
│                                                                  │
│  核心价值：                                                     │
│    1. 主动预警（IC还没崩就报警，不等事后发现）                   │
│    2. 多维评分（综合 IC/稳定性/衰减/跨品种/Regime 5个维度）     │
│    3. 行动建议（直接输出"做多/做空/观望/降权"，不是只展示数字） │
│                                                                  │
│  数据基础：5个P1核心因子，2020~2026历史数据已就绪               │
│                                                                  │
│  技术投入：约96小时（10周，分4个Phase）                          │
│                                                                  │
│  里程碑：                                                       │
│    Week 2 → 数据基础设施就绪（M0）                              │
│    Week 4 → 核心计算+Dashboard上线（M1）                       │
│    Week 8 → 全部8个Chart+告警可用（M2）                        │
│    Week 10 → PDF周报+7×24h自动运行（M3）                       │
│                                                                  │
│  关键风险：告警疲劳（狼来了效应）→ 从严阈值+告警聚合缓解        │
│                                                                  │
│  下一步行动：mimo（程序员）开始 Phase 0 数据基础设施开发        │
└─────────────────────────────────────────────────────────────────┘
```

---

*本文档由因子分析师 YIYI 创建并永久存档*
*如有疑问或更新需求，请联系因子分析师或在本文档目录下新建讨论笔记*
*最后更新：2026-04-23 16:55 GMT+8*
