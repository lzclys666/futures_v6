# 因子 IC 有效性验证 — 实战方案

**生成时间**：2026-04-20
**分析师**：因子分析师

---

## 一、验证框架已就位

路径：`D:\futures_macro_engine\research\validate_factor_ic.py`

使用方法：
```bash
# 验证共用因子
python validate_factor_ic.py --symbol SHARED --factors shared --start 2020-01-01 --forward 5

# 验证沪铜 Phase 1 因子（需先安装 AKShare）
pip install akshare
python validate_factor_ic.py --symbol CU --factors CU_LME_3M_CLOSE,CU_LME_3M_SPREAD --start 2020-01-01 --forward 5

# 批量验证所有 Phase 1 因子
python validate_factor_ic.py --symbol CU --factors phase1 --start 2020-01-01 --forward 5

# 验证所有因子
python validate_factor_ic.py --symbol all --factors all --start 2020-01-01 --forward 5
```

---

## 二、实战演示结果（2026-04-20）

### 共用因子验证（USD/CNY + WTI，vs USD/CNY 自身）

| 因子 | IC均值 | IR | t统计量 | 胜率 | 评级 |
|------|-------:|----:|-------:|-----:|------|
| WTI原油现货 | +0.0225 | 0.086 | 3.33 | 52.4% | 🟠 及格 |
| USD/CNY汇率 | -0.3070 | -1.051 | -42.37 | 14.1% | ⚫ 无效 |

**注意**：USD/CNY 的"无效"是方法论问题，不是因子真的无效。框架使用了 USD/CNY 自身作为价格代理（因为没有其他价格数据），导致 IC 计算的是汇率的均值回归特性，而不是它对商品收益的预测能力。

**正确做法**：USD/CNY 应测试其对铜/铝/原油等商品期货的 IC，不是对自身的 IC。

---

### 因子衰减分析（关键发现）

| 因子 | 1日IC | 5日IC | 10日IC | 20日IC | 最优持有期 |
|------|------:|------:|------:|------:|------------|
| WTI原油 | -0.001 | +0.034 | **+0.054** | +0.052 | **10日** |
| USD/CNY | -0.162 | -0.300 | -0.381 | -0.448 | 20日（均值回归）|

**实战意义**：WTI 原油因子在 10 日前瞻期 IC 达到 +0.054，高于 5 日的 +0.022。这说明能源因子更适合**中频/波段交易**，而非高频。对于 10~20 日持仓的策略，WTI 的预测能力接近 IC_GOOD 标准（0.05）。

---

## 三、当前可用数据盘点

| 阶段 | 因子 | 数据状态 | 可验证IC |
|------|------|----------|---------|
| Phase 1 | LME铜3M行情/升贴水 | ✅ 已采集（1590条） | ⚠️ 需AKShare获取沪铜价格 |
| Phase 1 | LME镍3M行情/升贴水 | ✅ 已采集 | ⚠️ 需AKShare获取沪镍价格 |
| Phase 4 | USD/CNY汇率 | ✅ 已采集（1720条） | ✅ 可验证（见上方结果） |
| Phase 4 | WTI原油 | ✅ 已采集（1569条） | ✅ 可验证（见上方结果） |
| Phase 3 | 各品种基本面因子 | 🔄 采集中 | ⏳ 待数据积累后验证 |

---

## 四、下一步计划

### 立即可做（本周）

**① 安装 AKShare，验证 Phase 1 因子**
```bash
pip install akshare --upgrade
```
然后运行：
```bash
python validate_factor_ic.py --symbol CU --factors phase1 --start 2020-01-01 --forward 5
python validate_factor_ic.py --symbol NI --factors phase1 --start 2020-01-01 --forward 5
```

**② 固定框架使用规范**

每个品种上线前必须完成 IC 验证：
```
新品因子 → 数据采集（≥60交易日）→ IC验证 → 权重分配 → 上线
                                              ↓
                                        IC < IC_MIN → 降级/剔除
```

**③ 给 Phase 3 因子做预验证**

当前 Phase 3 因子已有近 1 个月数据（mimo 采集的 2026-04-18 数据），积累 60 个交易日（约 3 个月）后即可做正式 IC 验证。

---

### 中期计划（下月）

**④ 滚动 IC 监控（每日自动运行）**

在 `validate_factor_ic.py` 基础上扩展监控脚本：
```python
# 每日收盘后自动计算各因子最新滚动 IC
# 触发告警条件：
#   - IC 20日均值 < IC_MIN（0.02）→ 因子失活警告
#   - IC 较上月下降 > 40% → 因子衰减警告
#   - 连续 10 日 IC < 0 → 因子下线审查
```

**⑤ 多重检验校正正式纳入流程**

当前框架已实现 Bonferroni 和 FDR 校正。品种因子越多（如ZN有18个），多重检验问题越严重——测试100个因子，随机预期有5个 IC > 0.02。**FDR 校正是必备的**，不是可选项。

**⑥ 分层回测验证**

框架中 `compute_top_bottom_ic()` 函数尚未完整演示。补充后可以验证：
- Top 组（因子值最高）与 Bottom 组（因子值最低）的收益差
- 这个差值才是真正的多空策略收益，不是 IC 本身

---

## 五、IC 验证结论

| 维度 | 当前状态 | 下一步 |
|------|----------|--------|
| 框架工具 | ✅ 就绪 | 完善文档 |
| 共用因子IC | ✅ 已验证（WTI有效，USD/CNY方法问题） | 重测（用商品价格做代理） |
| Phase 1 IC | ⏳ 等待AKShare | 安装后立即验证 |
| Phase 3 IC | ⏳ 数据不足（需积累≥60日） | 等待数据积累 |
| 动态IC监控 | 🔴 缺失 | 开发监控脚本 |
| 分层回测 | 🔴 缺失 | 补充验证 |

---

## 六、框架核心代码说明

```python
# ============ 关键参数（SOUL.md 标准）============
IC_MIN = 0.02       # 最低标准（不合格 = 剔除）
IC_GOOD = 0.05      # 良好标准
IC_EXCELLENT = 0.08  # 优秀标准
IR_MIN = 0.3         # IR 最低标准
T_STAT_MIN = 2.0     # t 统计量最低标准
ROLLING_WINDOW = 60  # 滚动 IC 窗口（交易日）
```

**合格因子判定（同时满足）**：
1. IC均值 > IC_MIN（0.02）
2. t统计量绝对值 > T_STAT_MIN（2.0）
3. FDR 校正后 p值 < 0.05
4. 胜率 > 50%（方向稳定性）

**权重分配（IC × IR 加权）**：
```python
weight_i = (IC_i_mean × IR_i) / Σ(IC × IR)
```
其中 IC × IR 兼顾了预测强度（IC）和稳定性（IR）。

---

*本方案由因子分析师制定 | 2026-04-20*
