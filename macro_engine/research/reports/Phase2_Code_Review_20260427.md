# Phase 2 代码审查报告
**审查时间**: 2026-04-27 15:30 GMT+8
**审查人**: 因子分析师YIYI
**文件**: `D:\futures_v6\macro_engine\research\phase2_statistical_modules.py`

---

## 一、模块清单与评级

| 模块 | 代码行数 | 功能正确性 | 集成状态 | 生产就绪 |
|------|---------|-----------|---------|---------|
| RollingICCalculator | ~100 | 🔴 有Bug | ❌ 未集成 | 否 |
| BootstrapAnalyzer | ~50 | 🟡 逻辑OK但缺固定种子 | ❌ 未集成 | 否 |
| HMMRegimeDetector | ~100 | 🟠 用错库+硬编码 | ❌ 未集成 | 否 |
| FactorDecayAnalyzer | ~40 | 🟢 正确 | ❌ 未集成 | 否 |

---

## 二、BUG #1（致命）：RollingICCalculator.compute_rolling_ic 位置偏移

### 问题描述

```python
aligned = pd.DataFrame({'factor': df['close'], 'return': df['return_5d']}).dropna()
rolling_ic = aligned['factor'].rolling(window=60).apply(spearman_corr)
```

`dropna()` 删除了因子序列前5行（NaN来自pct_change(5)），导致 `aligned` 比原始 `df` 少5行、且索引位置偏移。

### 实测数据（AG期货close数据）

| 指标 | 值 |
|------|-----|
| df长度 | 1523 |
| aligned长度 | 1518（差5） |
| aligned.iloc[0] 对应 | df.iloc[5]（而非df.iloc[0]）|
| **后果** | 滚动窗口系统性地偏移5个位置 |

### 影响

- 参考实现：窗口`[i-60:i]` → 对应日期`[date[i-60]:date[i-1]]`
- Phase2：窗口`aligned[i-60:i]` → 对应日期`[df_date[i-55]:df_date[i+4]]`
- **最大IC偏差**: 0.084（参考0.310 vs Phase2 0.395）
- **平均IC偏差**: 0.023
- IC序列相关性: 0.991（高度相关但不相等）

### 修复方案

**方案A（推荐）**：不在dropna后的DataFrame上做rolling，改在原始数据上操作：
```python
def compute_rolling_ic(self, factor_series, forward_return):
    df = pd.DataFrame({'factor': factor_series, 'return': forward_return})
    # rolling时每窗口单独dropna，不全局dropna
    def spearman_corr(window):
        win_df = df.iloc[window.start:window.stop].dropna()
        if len(win_df) < self.min_periods:
            return np.nan
        ic, _ = spearmanr(win_df['factor'].values, win_df['return'].values)
        return ic
    
    index = df.index
    result = pd.Series(index=index, dtype=float)
    for i in range(self.window, len(df)):
        win_range = range(i - self.window, i)
        result.iloc[i] = spearman_corr(range(win_range.start, win_range.stop))
    return result.dropna()
```

**方案B**：接受dropna偏移，在aligned上正确使用label-based访问：
```python
# dropna后rolling.apply的x是Series，其index是DatetimeIndex
# 用label访问确保对齐
def spearman_corr(x):
    y = aligned.loc[x.index, 'return']  # label-based，恒正确
    ...
```

---

## 三、BUG #2（高危）：HMMRegimeDetector 使用错误的库

### 问题描述

```python
from sklearn.mixture import GaussianMixture  # ❌ 错误

model = GaussianMixture(
    n_components=self.n_regimes,
    random_state=self.random_state,
    covariance_type='full'
)
```

**sklearn.mixture.GaussianMixture** 是高斯混合模型，用于聚类/密度估计。**不是真正的隐马尔可夫模型（HMM）**。

### 后果

| 问题 | 影响 |
|------|------|
| 不建模状态转移概率 | 无法得到 P(今天状态 \| 昨天状态) |
| 不建模观测概率 | 假设观测在给定状态下独立同分布 |
| 无未来状态推断 | 无法做真正的状态预测 |
| 标注不连续 | 可能连续两帧状态剧烈跳动 |

### 正确做法

使用 `hmmlearn` 库的 HMM：
```python
from hmmlearn import hmm
import numpy as np

# 离散化收益率和波动率作为观测
X = np.column_stack([returns.values, volatility.values])

# 训练HMM
model = hmm.GaussianHMM(
    n_components=n_regimes,
    covariance_type='full',
    n_iter=100,
    random_state=random_state
)
model.fit(X[:-1])  # 训练集（最后一个点用于预测）
```

### 补充：n_regimes 硬编码问题

当前硬编码 `n_regimes=3`，没有自动选择机制。应该使用 BIC/AIC 准则或交叉验证：
```python
def select_best_n_regimes(self, returns_series, max_regimes=5):
    """用BIC选择最优状态数"""
    best_bic = np.inf
    best_n = 2
    for n in range(2, max_regimes + 1):
        model = GaussianMixture(n_components=n, covariance_type='full')
        model.fit(X)
        bic = model.bic(X)
        if bic < best_bic:
            best_bic = bic
            best_n = n
    return best_n
```

---

## 四、BUG #3（中危）：BootstrapAnalyzer 缺固定随机种子

```python
def __init__(self, n_bootstrap=1000, confidence=0.95):
    # 没有 random_state 参数！
    self.n_bootstrap = n_bootstrap
    self.confidence = confidence
```

每次运行结果不同，无法复现。建议：
```python
def __init__(self, n_bootstrap=1000, confidence=0.95, random_state=42):
    self.n_bootstrap = n_bootstrap
    self.confidence = confidence
    self.random_state = random_state

def compute_ic_ci(self, factor_series, forward_return):
    np.random.seed(self.random_state)  # 固定随机种子
    ...
```

---

## 五、缺失清单

### 5.1 与生产系统集成（阻塞）

| 缺失项 | 当前状态 | 期望状态 |
|--------|---------|---------|
| PIT数据库接口 | 只读CSV | `PitDataService.get_snapshot()` 集成 |
| 生产IC服务 | 独立实现于 `core/analysis/ic_heatmap_service.py` | Phase2模块应被生产服务调用或替换 |
| 模型持久化 | 无 | `save_model()` / `load_model()` |
| 配置管理 | 硬编码参数 | YAML/JSON配置 |

### 5.2 核心功能缺失

| 缺失项 | 影响 |
|--------|------|
| 单元测试 | 无法验证正确性回归 |
| IC热力图（多因子×多品种） | 只支持单因子-单品种 |
| IC序列持久化 | 每次重新计算，无缓存 |
| 滚动IR计算 | 只有单序列IR，无多因子组合IR |
| 前瞻偏差检验 | 无 |
| 多重检验校正 | 无（FDR、Bonferroni等） |

### 5.3 数据接口缺失

| 缺失项 | 说明 |
|--------|------|
| 因子列表输入 | 需指定要计算的因子code列表 |
| 品种列表输入 | 需指定要计算的品种列表 |
| 日期范围控制 | 需指定 start_date / end_date |
| 持仓期参数 | 需支持1/5/10/20日等多种forward_period |

---

## 六、与生产系统对比

| 维度 | Phase2研究代码 | 生产服务 `ic_heatmap_service.py` |
|------|--------------|----------------------------------|
| 数据源 | CSV文件 | PIT数据库 |
| IC计算 | 有偏移bug | 正确（测试过） |
| 热力图 | 无 | 有（多因子×多品种矩阵） |
| 集成状态 | 孤立 | 已集成 |
| 统计模块 | Bootstrap/HMM/Decay | 无 |

**结论**：Phase 2 代码是孤立的原型研究实现，生产系统使用独立开发的 `ic_heatmap_service.py`。两者代码不共享，Phase 2 未被生产系统调用。

---

## 七、修复优先级

| 优先级 | BUG/缺失 | 工时估算 |
|--------|---------|---------|
| P0 | RollingICCalculator位置偏移bug | 2小时 |
| P0 | 单元测试覆盖 | 4小时 |
| P1 | HMM改用hmmlearn | 3小时 |
| P1 | 集成PIT数据库接口 | 4小时 |
| P1 | Bootstrap固定随机种子 | 30分钟 |
| P2 | 模型持久化（pickle/joblib） | 2小时 |
| P2 | n_regimes自动选择 | 2小时 |
| P3 | IC热力图扩展 | 6小时 |
| P3 | 多重检验校正 | 3小时 |

**总工时**: ~27小时

---

## 八、审查结论

Phase 2 代码是**孤立的研究原型**，存在1个致命bug和多个设计缺陷，**未集成到生产系统**。

核心问题：
1. 🔴 `compute_rolling_ic` 的 iloc 偏移导致 IC 系统性错误（最大0.084偏差）
2. 🔴 与生产系统（`ic_heatmap_service.py`）完全隔离，代码不共享
3. 🟠 `HMMRegimeDetector` 使用 GMM 而非真正的 HMM
4. 🟡 Bootstrap缺随机种子，结果不可复现

**建议**：Phase 2 代码不能直接用于生产，需修复bug后重新评估是否复用生产服务的IC计算逻辑。
