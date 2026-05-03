# 因子数据治理总纲

> **合并日期**: 2026-05-03
> **来源**: FACTOR_COLLECTION_SPEC_v1.md + 因子采集健康度验收方案_20260503.md + SPEC_EXECUTION_PLAN.md

---

## 一、文档结构

| 来源文件 | 内容 | 路径 |
|----------|------|------|
| `FACTOR_COLLECTION_SPEC_v1.md` | 因子采集规格说明（PIT 规则、豁免逻辑、质量标准） | `macro_engine/FACTOR_COLLECTION_SPEC_v1.md` |
| `因子采集健康度验收方案_20260503.md` | L0-L6 验收方案（5 小时全量验收） | `macro_engine/因子采集健康度验收方案_20260503.md` |
| `SPEC_EXECUTION_PLAN.md` | B1-B5 分批次修复执行计划 | `macro_engine/SPEC_EXECUTION_PLAN.md` |

---

## 二、调度架构

```
FactorCollector (每日 15:30 CST)
    └─ run_factor_collector.bat
        └─ 因子采集脚本
            └─ compute_ic_heatmap.py  ✅ B5-1.2 已追加
                └─ ic_heatmap 表更新

DailyScoring (工作日 14:30 CST)
    └─ daily_scoring.py
        └─ macro_scoring_engine.py
            └─ CSV 信号输出
```

---

## 三、验收状态（L0-L6）

### L0 文件系统预检
- ✅ requests.get 残留：**0**
- ✅ .py.old 残留：**0**
- ✅ 总文件：**368 个**

### L1 语法 & 导入验证
- ✅ Python 语法错误：**0**（333 个实际脚本全部通过）
- ✅ Import 错误：**0**
- ℹ️ 排除文件：`phase3_v2_collect_report.py`（实为 markdown 报告）

### L2 运行时快速验证
- ⏳ 手动：P0 品种 ×5 运行（AU/CU/RB/AG/RU）
- ⏳ 手动：P1 品种 ×10 运行

### L3 数据库审计
- ✅ 前视偏差（obs_date > pub_date）：**0 条**
- ⚠️ ic_heatmap 覆盖：**18 品种**（目标 ≥20）
- ⚠️ 数据量不足（<60 行）：**9 品种**

| 品种 | 行数 | 状态 |
|------|------|------|
| FU | 2 | 🔴 |
| PB | 11 | 🔴 |
| PP | 13 | 🔴 |
| HC | 14 | 🔴 |
| Y | 14 | 🔴 |
| EG | 19 | 🔴 |
| J | 20 | 🔴 |
| BU | 24 | 🔴 |
| M | 39 | 🔴 |

### L4 run_all 集成测试
- ⏳ 手动：P0 品种 ×5 全链路
- ⏳ 手动：P1 品种 ×10 全链路

### L5 降级链验证
- ⏳ 手动：模拟 L1 失败 → L2/L3/L4 回补验证

### L6 ic_heatmap 调度验证
- ✅ B5-1.1：FactorCollector 15:30，DailyScoring 14:30
- ✅ B5-1.2：`compute_ic_heatmap.py` 已追加到 FactorCollector 链路
- ✅ B5-1.3：ic_heatmap 写入验证（73 行/次）

---

## 四、B 批次执行状态

| 批次 | 任务数 | 完成 | 状态 |
|------|--------|------|------|
| B1 代码审查工具 | 6 | 6 | ✅ 全部完成 |
| B2 SPEC 修订 | 6 | 6 | ✅ 全部完成 |
| B3 Schema + 联动 | 5 | 4/5 | ⚠️ B3-4 取消（API 不走 ic_heatmap） |
| B4 db_utils + 豁免 | 5 | 5 | ✅ 全部完成 |
| B5 调度 + 最终验收 | 4 | 3/4 | 🔄 B5-3/B5-4 进行中 |

**B4 详细**：
- ✅ B4-1：db_utils.py 重试逻辑扩展（6 种错误类型）
- ✅ B4-2：null 写入路径实现
- ✅ B4-3：5 个爬虫脚本 null 写入示例（AG/CU/RU/AU/J）
- ✅ B4-4：月度/季度豁免规则合并到 SPEC.md

**B5 详细**：
- ✅ B5-1.1：定时任务确认（15:30/14:30）
- ✅ B5-1.2：compute_ic_heatmap.py 追加到 FactorCollector
- ✅ B5-1.3：ic_heatmap 增量验证（73 行写入）
- ⏳ B5-2：验收方案调度章节（已更新框架）
- ⏳ B5-3：L0-L6 全量验收（L2/L4/L5 手动）
- ⏳ B5-4：本文档合并

---

## 五、豁免规则摘要

详见 `FACTOR_COLLECTION_SPEC_v1.md` 第六章。

| 数据类型 | obs_date | pub_date 滞后 | IC 窗口 |
|----------|----------|-------------|---------|
| CPI/PPI | 每月第二个工作日 | 5 工作日 | 12 周 |
| PMI | 每月最后工作日 | 3 工作日 | 12 周 |
| GDP | 季度末 | 10 工作日 | 4 季度 |
| USDA | 报告发布日期 | 0 | 26 周 |
| CFTC | 每周五 | 0 | 12 周 |

---

## 六、IC 健康度阈值

| IR 范围 | 评级 | 处置 |
|---------|------|------|
| ≥ 0.5 | 优秀 | 正常参与打分 |
| 0.3 - 0.5 | 警告 | 正常参与打分，记录 |
| < 0.3 | 不健康 | 标记并告警 |

---

## 七、快速验收命令

```powershell
# L0 文件系统
python C:\Users\Administrator\.qclaw\workspace-agent-63961edb\_check_l0.py

# L1 语法检查
python C:\Users\Administrator\.qclaw\workspace-agent-63961edb\_check_l1.py

# L3 数据库审计
python D:\futures_v6\macro_engine\scripts\check_pit_integrity.py

# L3 ic_heatmap 验证
python D:\futures_v6\macro_engine\scripts\compute_ic_heatmap.py

# schtasks 验证
schtasks /query /fo LIST /v | findstr "FuturesMacro"
```
