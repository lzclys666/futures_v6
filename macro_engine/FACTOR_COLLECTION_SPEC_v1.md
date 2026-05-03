# 因子采集规范与验收方案 v1.0
> 范围：31 品种目录，296 因子脚本，1 数据库 (pit_data.db)
> 制定日期：2026-05-03 | 状态：草稿，待用户确认

---

## 一、现状摸底

### 1.1 资产清单

| 资产 | 数量 | 备注 |
|------|------|------|
| 品种目录（crawlers/） | 31 个 | AG/AL/AU/BU/CU/J/JM/NR/RB/RU/TA/ZN 等 |
| 因子脚本（*.py） | 315 个 | 排除 `__init__.py`、`run_all.py`、`run_collect.py` |
| 因子 YAML 元数据文件 | 293 个 | `config/factors/{SYMBOL}/{FACTOR_CODE}.yaml` |
| 数据库表（pit_data.db） | 7+ 张 | `pit_factor_observations`、`ic_heatmap`、`factor_metadata` 等 |
| 因子代码（DB 中有数据） | 239 个 | `pit_factor_observations` 中不同 factor_code |
| ic_heatmap 记录 | 25 行 | 仅 1 个交易日（2026-04-27），仅 5 个品种 |

### 1.2 当前数据健康度

```
✅ 基础覆盖：34 个品种均有数据（AG/AU/CU/RU 等）
⚠️  数据深度：
    - ic_heatmap 仅 1 天（JM/NI/RB/RU/ZN 各 5 因子）
    - 部分品种数据极少：EG(16行)、BU(18行)、Y(12行)、HC(12行)、PB(9行)、PP(11行)
    - 部分品种历史极长：CU/RU(2020年起)、AU/NI/NR(2023年起)
⚠️  YAML-DB 一致性：
    - YAML 有但 DB 无：116 个因子（BU 批量缺失）
    - DB 有但 YAML 无：62 个因子（AG/AU 等缺失元数据）
🔴 ic_heatmap：陈旧（仅 2026-04-27），每日增量更新机制未启用
🔴 factor_metadata 表：仅 19 行（应为 239 行），大部分因子无元数据记录
```

---

## 二、因子采集规范（采集员守则）

### 2.1 脚本命名规范

```
{SYMBOL}_{操作类型}_{标的/指标}.py

操作类型：
  抓取  — 原始数据从外部来源获取（requests/fetch_url）
  计算  — 派生指标从内部数据计算（价差/比值/收益率）
  输入  — 人工录入数据（手动输入/CSV 导入）

示例：
  RU_抓取仓单.py        ✅
  AG_计算沪银COMEX比价.py  ✅
  RU_抓取现货和基差.py   ✅
  NR_手动输入.py        ✅
  run_all.py            ❌（批处理脚本，不算因子）
  __init__.py           ❌
```

**规则：**
- 一个脚本对应一个因子代码（factor_code）
- 脚本名中的 `{SYMBOL}` 必须与 YAML 元数据的 `symbol` 完全一致
- `计算` 类脚本需在 YAML 中注明 `dependencies`（依赖的父因子）

### 2.2 YAML 元数据规范

每个因子必须在 `config/factors/{SYMBOL}/{FACTOR_CODE}.yaml` 有对应文件。

**必需字段：**

```yaml
factor_code: AG_COST_USDCNY          # 全大写下划线，与脚本名和DB字段一致
factor_name: 美元成本                # 中文名称（可读）
symbol: AG                           # 品种代码（与目录名一致）
category: free_data                  # free_data | derived | paid_data（三选一）
direction: 1                        # 1=正相关，-1=负相关，0=中性
frequency: daily                     # daily | weekly | monthly
norm_method: zscore                  # zscore | mad | minmax | none
is_active: true                      # true=参与打分，false=归档
data_source: AKShare                 # AKShare | Sina | Eastmoney | CFTC | 交易所 | Manual
source_confidence: 0.85              # 0.0~1.0，数据源可信度
expected_range: [-100000.0, 100000.0] # 数值合法区间（用于异常检测）
logic_category: FX                  # 逻辑分类：FX | IND | POS | SPOT | MACRO | CST | DEM | SUP | INDICATOR
description: 美元兑人民币汇率...      # 因子逻辑说明（≥10字）
```

**可选字段：**

```yaml
dependencies: [AG_FUT_CLOSE, AG_FUT_OI]  # 派生因子依赖的父因子列表
base_weight: 0.06    # IC驱动权重（0.01~0.2）
max_weight: 0.1      # 上限
norm_window: 252     # 标准化窗口（默认252）
detrend_method: none # 去趋势方法
econ_category: CST   # 经济周期分类
```

**禁止事项：**
- `expected_range` 禁止使用字符串格式 `['-100000-200000']`，必须用 `[-100000.0, 200000.0]`
- `category` 禁止使用旧三值体系（`price_data`/`indicator_data`/`macro_data`）
- YAML 文件名不得包含下划线 `_` 以外的分隔符

### 2.3 数据库写入规范

**目标表：** `pit_factor_observations`

```sql
INSERT INTO pit_factor_observations 
    (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
VALUES 
    ('AG_COST_USDCNY', 'AG', '2026-05-02', '2026-05-02', 7.2456, 'AKShare', 0.85);
```

**规则：**
- `factor_code`：必须与 YAML 文件名（不含 `.yaml`）完全一致
- `pub_date`：数据发布日期（爬虫运行日），格式 `YYYY-MM-DD`
- `obs_date`：数据对应实际观测日（部分品种晚于 pub_date）
- `raw_value`：原始数值（不标准化）
- `source`：数据来源（字符串，不可为 NULL）
- `source_confidence`：0.0~1.0，不可为 NULL
- **允许 INSERT OR REPLACE**（以 `factor_code + symbol + pub_date + obs_date` 为去重键，断点续传用）
  - 保护机制：`save_to_db` 会在 REPLACE 前检查已有记录的 source_confidence，若 ≥ 当前值则保留原值（不覆盖高置信度数据）
  - L1 原始数据（source_confidence=1.0）不会被 L4 回补数据（0.5）覆盖
  - L4 回补时保留原始 pub_date 和 obs_date，不以今日日期覆盖历史

### 2.4 错误处理规范

```python
def collect_AG_COST_USDCNY():
    url = "https://api.example.com/usd_cny"
    text, err = fetch_url(url, timeout=15)
    if err:
        # 网络错误 → 记录错误日志，不写入数据库，继续下一个
        log_error(f"AG_COST_USDCNY fetch failed: {err}")
        return  # ❌ 不 raise，不中断
    if not text:
        log_error("AG_COST_USDCNY empty response")
        return
    try:
        value = float(text)
    except (ValueError, TypeError):
        log_error(f"AG_COST_USDCNY parse failed: {text[:100]}")
        return

    # 范围检查（与 YAML expected_range 对照）
    if not (-100000.0 <= value <= 100000.0):
        log_warn(f"AG_COST_USDCNY out of range: {value}")
        # 告警但不阻断（可能今日行情特殊）
    
    save_to_db(...)
```

**三条铁律：**
1. **网络错误不 raise**：记录后继续，不中断采集流
2. **解析错误不 raise**：记录后跳过该因子，不写脏数据
3. **范围异常只告警不阻断**：记录 warning，但仍然写入（供人工复核）

### 2.5 采集频率规范

| 频率 | 执行时间（CST） | 触发方式 |
|------|----------------|----------|
| 日频 | 每日 08:30 之前 | Windows schtasks |
| 周频 | 每周一 08:30 | schtasks |
| 月频 | 每月 1 日 09:00 | schtasks |
| 实时 | 交易时段按需 | CTP 回调触发 |

---

## 三、最终验收方案

### 3.1 验收架构：四层验证

```
┌─────────────────────────────────────────────────────────┐
│  L4 IC验证   ic_heatmap 表每日更新，覆盖全部品种           │
│              IC > 0.05 才是有效因子                      │
├─────────────────────────────────────────────────────────┤
│  L3 数据验证  pit_factor_observations 完整性               │
│              每个因子 ≥60 条记录（统计显著最低要求）         │
├─────────────────────────────────────────────────────────┤
│  L2 元数据验证 YAML 文件完整且与 DB 一一对应               │
│              293 YAML ←→ 239 DB factor_code              │
├─────────────────────────────────────────────────────────┤
│  L1 脚本验证  py_compile + fetch_url 迁移 + 基础功能      │
│              315 脚本全部语法正确，可正常执行               │
└─────────────────────────────────────────────────────────┘
```

### 3.2 L1：脚本验收（自动化）

**执行方式：** Python 脚本一次性扫描

```python
# L1 验收清单（每个因子脚本必须通过）
checklist_l1 = {
    "语法正确": compile(script_path, 'exec'),           # py_compile 通过
    "导入 fetch_url": 'fetch_url' in content,           # 已迁移到 web_utils
    "无裸 requests.get": 'requests.get' not in content, # 不使用 requests 直接
    "save_to_db 调用": 'save_to_db' in content,         # 必须有数据库写入
    "无 hardcoded 凭据": 'luzc' not in content.lower(),  # 无明文凭据
}
```

**验收标准：**
- 315 个脚本 100% 通过 L1 检查
- 0 个 `requests.get` 残留（已完成迁移至 `fetch_url`）

### 3.3 L2：元数据验收（半自动化）

**执行方式：** Python 脚本扫描 YAML + DB 对照

```python
# L2 验收清单
checklist_l2 = {
    "YAML 文件数": 293,                                 # 与 DB factor_code 匹配
    "YAML 必需字段": ['factor_code','symbol','direction','category','is_active'],
    "category 三值枚举": set(categories) ⊆ {'free_data','derived','paid_data'},
    "expected_range 格式": all(isinstance(r, list) and len(r)==2 for r in ranges),
    "YAML ↔ DB 一致性": YAML_factor_codes == DB_factor_codes,  # 差集为空
    "direction 取值": all(d in {1, -1, 0} for d in directions),
}
```

**YAML-DB 对齐问题处理策略：**

| 情况 | 处理方式 |
|------|---------|
| YAML 有，DB 无（116 个）| 优先补充采集脚本执行；无脚本的标注为「待开发」|
| DB 有，YAML 无（62 个）| 补充 YAML 元数据文件（从 `factor_metadata` 反推）|
| YAML 命名与 DB 不一致 | 以 YAML 文件名为准，DB 刷写一致（如有冲突用户决定）|

**目标：** YAML factor_code 集合 = DB factor_code 集合，差集为空

### 3.4 L3：数据完整性验收（自动化）

**执行方式：** SQLite 查询 + Python 分析

```python
# L3 验收清单
checklist_l3 = {
    # 每个品种 ≥1 个有效因子（active=true in YAML）
    "品种因子覆盖": 每个 symbol 至少 1 个 is_active=true 的因子
    
    # 每个因子 ≥60 条记录（统计显著性门槛：60条≈3个月，252条≈1年）
    "因子记录数": 所有 factor_code 的 COUNT(*) ≥ 60（部分周频/月频宏观因子可申请豁免，见豁免规则）
    
    # 数据时效：每个 active 因子最近 5 个交易日内有数据
    "数据时效": MAX(pub_date) >= TODAY - 5d
    
    # 无连续超过 7 天的数据断层
    "数据连续性": 无连续 7 天无数据记录（允许节假日除外）
    
    # 数值合理性：99.5% 数据在 expected_range 内（收紧0.5pp）
    # 金银比等历史极值越界时仅告警，不阻断（可能反映真实宏观异动）
    # 高频因子额外增加 3σ 异常检测（比 expected_range 更敏感）
    "范围合规": 各因子 99.5% 数据 ∈ expected_range（宽松阈值）
    # expected_range 本身应经历史数据验证覆盖率 ≈ 99.5%，否则仅供参考
}
```

**品种健康度评分（质量导向，重构版）：**

```python
def health_score(symbol):
    """
    质量导向评分：基于 IC 有效因子数，不只是数量
    """
    factors = get_factors(symbol)
    if not factors:
        return 0
    
    score = 0
    
    # 维度1：IC 有效因子数（质量加权，替代简单的 factor_count）
    # IC 优秀(IR≥0.5)权重=2，IC 警告(0.3≤IR<0.5)权重=1，其他=0
    ic_weighted = sum(
        2 if f.ir >= 0.5 else (1 if f.ir >= 0.3 else 0)
        for f in factors if hasattr(f, 'ir')
    )
    score += min(30, ic_weighted * 5)  # 最高30分
    
    # 维度2：数据深度（60条起计，120条满分）
    avg_records = sum(f.record_count for f in factors) / len(factors)
    score += 30 if avg_records >= 120 else (15 if avg_records >= 60 else 0)
    
    # 维度3：时效性
    latest = max(f.latest_date for f in factors)
    score += 20 if latest >= today - 5 else (10 if latest >= today - 20 else 0)
    
    # 维度4：范围合规（收紧至 0.5%）+ expected_range 有效性
    range_violation_rate = sum(f.range_violations / f.total for f in factors) / len(factors)
    score += 20 if range_violation_rate < 0.005 else (10 if range_violation_rate < 0.02 else 0)
    
    # 维度5：PIT 观测比例（新增）
    # 实际观测（source_confidence=1.0）占比应 > 70%
    pit_ratio = sum(f.pit_observed_count / f.total for f in factors) / len(factors)
    score += 10 if pit_ratio >= 0.7 else (5 if pit_ratio >= 0.5 else 0)
    
    # 维度6：IC 方向一致性（新增）
    # 60 日内符号一致率应 ≥ 60%
    direction_aligned = sum(
        1 for f in factors
        if hasattr(f, 'sign_stability') and f.sign_stability >= 0.6
        and f.ic_value * f.direction > 0
    )
    score += 10 if direction_aligned >= len(factors) * 0.6 else 0
    
    return score  # ≥80 分健康 / 60-80 警告 / <60 不健康
```

### 3.5 L4：IC 有效性验收（自动化）

**执行方式：** Python 脚本每日增量计算

```python
# L4 验收清单
checklist_l4 = {
    # ic_heatmap 每日有更新（最后 calc_date = TODAY）
    "ic_heatmap 时效": MAX(calc_date) >= TODAY
    
    # 每个 active 因子 IC ≠ 0（有效预测能力）
    "IC 非零": 所有因子 |IC| > 0.01（宽松阈值，初筛）
    
    # IC 方向与 YAML direction 一致（符号检验）
    "IC 方向一致性": IC * direction > 0
    
    # IC 三档分层（IR=IC均值/IC标准差）
    # 🔴 <0.3 不健康 / 🟡 0.3~0.5 警告 / ✅ ≥0.5 优秀
    "IC IR 三档": (IR < 0.3, "不健康"), (0.3 <= IR < 0.5, "警告"), (IR >= 0.5, "优秀")
    
    # IC 滚动窗口 ≥60 日（替代原 20 日，减少方差）
    "IC 窗口": 滚动 60 个交易日 IC 值计算均值/IR
    
    # IC 方向一致性：60 日内符号一致率 ≥ 60%
    "IC 方向一致性": IC_sign_stability ≥ 60%（且 IC * direction > 0）
    
    # IC 胜率：|IC| > 0.01 的交易日占比 ≥ 55%（微正微负不计入）
    "IC 胜率": COUNT(IC > 0.01) / COUNT(|IC| > 0) ≥ 55%
    
    # 多重检验校正（Bonferroni）：18+ 因子同时检验时 FDR < 5%
    "IC FDR校正": IC_FDR_corrected_p < 0.05
}
```

**IC 热图计算问题（2026-05-03 修复中）：**
- 旧脚本 `scripts/calculate_ic_heatmap.py` 只能处理 JM/RB/RU/ZN/NI 5 个品种，数据来自品种专属 OHLCV 表（如 `jm_futures_ohlcv`），非通用
- 新脚本 `scripts/compute_ic_heatmap.py`（B1-6）基于 `pit_factor_observations` 表统一计算，覆盖全部 34 个品种
- 修复后：ic_heatmap 每日更新，覆盖全部品种，IC 窗口 60 日

**IC IR 三档分层（商品期货专用）：**

| 档位 | IR 范围 | 状态 | 处置 |
|------|---------|------|------|
| 🔴 | < 0.3 | 不健康 | 降权或归档 |
| 🟡 | 0.3 ~ 0.5 | 警告 | 可用但加强监控 |
| ✅ | ≥ 0.5 | 优秀 | 正常参与打分 |

**特殊豁免**：CFTC 周频因子 IR 阈值降至 0.3（样本稀疏）；月度宏观因子 IR 阈值降至 0.2。

---

## 四、分阶段执行计划

### 阶段一：基线验证（L1 + L2）— 立即执行

| 步骤 | 操作 | 负责 | 验收标准 |
|------|------|---------|
| 1.1 | 运行 `py_compile` 扫描 368 个脚本 | PM 执行 | 0 个 SyntaxError |
| 1.2 | 运行 L1 import 验证（sys.path 修复后）| PM 执行 | 假性 ImportError < 3 个 |
| 1.3 | 运行 AST fetch_url 解包检查（B1-5）| mimo 执行 | 误报率 < 5% |
| 1.4 | 修复 db_utils.py source_confidence 保护（B1-1）| deep 执行 | regression test 通过 |
| 1.5 | 新建 PIT 完整性检查脚本（B1-4）| deep 执行 | 输出 3 类问题清单 |

**验收门槛：** L1 100% 通过，L2 字段完整率 100%，差异清单 100% 有处理方案。

### 阶段二：数据健康修复（L3）— 1 周

| 步骤 | 操作 | 负责 | 验收标准 |
|------|------|------|---------|
| 2.1 | 修复 ic_heatmap 每日计算脚本 | deep | ic_heatmap 每日更新 |
| 2.2 | 数据断层修复（≥60 天因子补录）| mimo | 低记录因子（<60 条）降至 0 |
| 2.3 | 新品种初始化（EG/BU/Y 等）| mimo | EG/BU/Y/HC/PB/PP ≥60 条/品种 |
| 2.4 | 品种健康度评分 | PM | ≥80 分品种 ≥25 个 |

**验收门槛：** 全 34 品种健康度 ≥60 分，≥80 分品种 ≥20 个。

### 阶段三：IC 工程化（L4）— 2 周

| 步骤 | 操作 | 负责 | 验收标准 |
|------|------|------|---------|
| 3.1 | 部署 `compute_ic_heatmap.py` 每日 cron | deep | ic_heatmap 每日增量写入 |
| 3.2 | IC 方向一致性自动告警 | YIYI | IC 符号与 direction 不符 → 告警 |
| 3.3 | IC IR < 0.5 因子自动降权 | YIYI | 低质量因子 base_weight 归零 |
| 3.4 | IC 胜率可视化看板 | Lucy | 前端展示 IC 热图 |

**验收门槛：** ic_heatmap 覆盖全 34 品种，IC 更新无断层 ≥10 个交易日。

---

## 五、验收交付物清单

| 交付物 | 文件路径 | 说明 |
|--------|---------|------|
| L1 扫描脚本 | `scripts/check_factors_l1.py` | py_compile + fetch_url + save_to_db |
| L2 扫描脚本 | `scripts/check_factors_l2.py` | YAML schema + DB 对照 |
| L3 健康度脚本 | `scripts/check_factors_l3.py` | 数据完整性 + 时效性 |
| L4 IC 计算脚本 | `scripts/compute_ic_heatmap.py` | 每日 IC 热图增量计算 |
| YAML 元数据模板 | `config/factors/_templates.yaml` | 新因子创建模板 |
| 验收报告 | `FACTOR_ACCEPTANCE_REPORT.md` | 四层验收结果 |

---

## 六、豁免申请规则

以下情况可申请豁免（需 YIYI 批准）：

1. **宏观因子豁免**：
   - **CFTC 持仓**：每周五发布，IC 窗口 12 周滚动，IR 阈值降至 0.3
   - **CPI/PPI**：obs_date=每月第二个工作日，pub_date 滞后最多 5 个工作日，IC 窗口 12 周滚动
   - **PMI**：obs_date=每月最后工作日，pub_date 滞后最多 3 个工作日，IC 窗口 12 周滚动
   - **GDP**：obs_date=季度末（3/31、6/30、9/30、12/31），pub_date 滞后最多 10 个工作日，IC 窗口 4 季度滚动
   - **USDA 报告**：obs_date=报告发布日期，pub_date 无滞后（=obs_date），IC 窗口 26 周滚动
   - 月度宏观因子（记录数 <60 但方向明确）：豁免门槛 12 条，IR 阈值降至 0.2
2. **新因子豁免**：上线 <30 天的因子，历史不足不扣健康分
3. **特殊数据源豁免**：人工输入数据源（NR_手动输入.py），source_confidence 可设为 0.5

豁免申请格式：
```yaml
# 在因子 YAML 中添加
waiver:
  reason: "CFTC 每周五发布，交易日历不足"
  approved_by: YIYI
  approved_date: "2026-05-10"
```
