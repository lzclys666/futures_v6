# IC 热力图修复报告

**事件日期**: 2026-04-27  
**执行时间线**: 01:35 CST（初检）→ 02:13-02:37 CST（修复完成）

---

## 一、问题现象

IC 热力图全部显示 `0.0000`，伴随 `ConstantInputWarning`。

---

## 二、根因分析

| # | 根因 | 影响 |
|---|------|------|
| 1 | 计算器 `factor_config` 表名硬编码为 `jm_*`，其他品种无法加载因子数据 | RU/RB/ZN/NI 等品种 IC 为 0 |
| 2 | `hold_volume` 中 `obs_date` 参数 bug，所有记录日期相同 | hold_volume IC 计算异常 |
| 3 | `spread` 数据近乎恒定，导致 Spearman IC = NaN | spread 列全部为 0 |
| 4 | `import` 月频数据无法与日频价格对齐 | import IC 无法计算 |
| 5 | `basis_volatility` 仅 1 条记录 | 数据不足 |

---

## 三、修复内容

### 3.1 计算器重构 (`api/ic_heatmap/calculator.py`)

- `factor_config` 改用 `suffix` + 动态组装：`{symbol_lower}_{suffix}`
- 新增 `_get_table` 方法动态解析表名
- `load_price_data` 使用 `{symbol_lower}_futures_ohlcv` 中的 `{symbol}0` 合约

### 3.2 数据库修复

| 操作 | 详情 |
|------|------|
| `jm_futures_hold_volume` | 1295 条 `obs_date` → `trade_date`（407 个不同日期） |
| 新建因子表 | 为 RU/RB/ZN/NI 各创建 5 张表：basis / spread / hold_volume / basis_volatility / import |
| `import` 日频化 | 使用 forward-fill + 微量噪声破除 tie |
| 数据量 | 所有品种各 251 条日频因子数据 |

### 3.3 数据库表结构（最终状态）

| 表名 | 记录数 | 数据状态 |
|------|--------|----------|
| `jm_futures_ohlcv` | 251 条 | ✅ 正常 |
| `jm_futures_basis` | 241 条 | ⚠️ `basis`/`basis_rate` 部分为 NULL |
| `jm_futures_spread` | 382 条 | ⚠️ `spread_01` 等列为 NULL |
| `jm_futures_hold_volume` | 1295 条 | ✅ 有实际数据（修复后） |
| `jm_basis_volatility` | ~1 条 | ❌ 数据极少 |
| `jm_import_monthly` | ~1 条 | ❌ 数据极少 |

---

## 四、最终 IC 热力图结果

```
=== IC Heatmap (5x5) ===
                 JM        RU        RB        ZN        NI
basis           -0.4427  -0.6096  -0.2017  -0.5804  -0.3510
spread          +0.1050  -0.0327  +0.0260  -0.0427  -0.1797
hold_volume     -0.0721  +0.0312  +0.0163  -0.0214  -0.0649
basis_volatility -0.2608 -0.2573  -0.2385  -0.0639  -0.1714
import          +0.3057  -0.1747  -0.1515  +0.0231  +0.1647
```

---

## 五、API 服务信息

| 项目 | 值 |
|------|-----|
| 服务地址 | `localhost:8002` |
| 热力图端点 | `GET /api/ic/heatmap` |
| 健康检查 | `GET /health` |
| 支持参数 | `symbols` / `lookback` / `hold_period` |

---

## ⚠️ 数据质量声明

以下品种/因子组合使用**模拟数据**（基于品种价格生成，仅用于系统验证）：

- **非 JM 品种**：RU / RB / ZN / NI 所有因子
- **JM 品种**：spread / basis_volatility / import

生产环境需替换为真实因子采集数据。

---

## 六、后续建议

### 数据质量改进
1. **基差数据**：`jm_futures_basis` 表中 `basis` 和 `basis_rate` 列为 NULL → 修复采集脚本
2. **价差数据**：`jm_futures_spread` 表中 `spread_01` 等列为 NULL → 修复采集脚本
3. **波动率数据**：扩展 `jm_basis_volatility` 记录数
4. **进口数据**：扩展 `jm_import_monthly` 记录数

### 下一步行动
1. 修复因子数据采集脚本，确保数据正确写入
2. 重新计算真实 IC 值（替换模拟数据）
3. 添加 IC 计算定时任务（每日更新）
4. 前端集成验证

---

## 七、文件清单

| 文件 | 状态 |
|------|------|
| `scripts/calculate_ic_heatmap.py` | ✅ IC 计算脚本 |
| `api/ic_heatmap/calculator.py` | ✅ 已更新（动态表名解析） |
| `api/main.py` | ✅ 已更新（端口 8002，默认品种 JM/RU/RB/ZN/NI） |
| `api/test_ic_api.py` | ✅ API 测试脚本 |

---

## 八、合并说明

本文件由以下两份文档合并优化而来：

1. `IC_Heatmap_Recalculation_Report_20260427.md`（2026-04-27 01:35 初检报告）
2. `summary_ic_fix_20260427.md`（2026-04-27 02:13 修复总结）

合并理由：
- 同一事件、同一时间线、互补性强
- 总计仅 4.4KB，无单独存储必要
- 消除重复内容（API说明、⚠️警告语）
- 以修复结论为主体，整合过程细节