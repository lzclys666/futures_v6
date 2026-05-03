# 因子采集规范执行计划书
> 制定日期：2026-05-03 | 范围：SPEC_REVIEW_SYNTHESIS.md 全部修复任务
> 状态：**终稿，待执行**

---

## 执行前提：关键发现修正

**E3 根本不存在（实地验证）**：
- `db_utils.py` 第 26 行：`PRIMARY KEY (factor_code, symbol, pub_date, obs_date)` 已是 **4列 PK**
- E3 从阻塞清单移除，E1 成为唯一需要处理的 PK/UPSERT 问题

**E1 的真实问题**：不是"PK 定义错误"，而是 **`INSERT OR REPLACE` 会用 L4 回补数据（source_confidence=0.5）覆盖 L1 原始数据（source_confidence=1.0）**。

---

## 任务依赖关系图（DAG）

```
[E5 L1脚本sys.path] ─────────────────┐
                                     ▼
[F1 PIT验证SQL] ─────────────────────┐
                                     ▼
[E4 AST解析检查] ────────────────────┐
                                     ▼
[E1 UPSERT语义澄清] ─────────────────────────────────────────────────────┐
                                     │                                    │
[D2 compute_ic_heatmap.py] ◄─────────┘                                    │
                                     │                                    │
[F2 IC方法论spec] ───────────────────┤                                    │
                                     │                                    ▼
[F3 expected_range修订] ──────────────┤                                    │
                                     │                              [阶段三]
[F4 健康度评分重设计] ───────────────┤                                    │
                                     │                                    │
[A3 CFTC窗口修订] ───────────────────┤                                    │
                                     │                                    ▼
[A6 记录数门槛提至60] ───────────────┘                              [阶段三]
                                     │
[A1 target_symbol字段] ──────────► [前端IC热图更新]
                                     │
[A2 豁免规则] ───────────────────────┤
                                     │
[A7 重试逻辑] ───────────────────────┤ ◄── [db_utils.py]
                                     │
[A8 L5降级链null写入] ───────────────┘

[A10 ic_heatmap调度关系] ────────────► [run_all cron定义]
```

---

## 联动影响分析（修复前必读）

| 修复项 | 影响的文件和组件 | 联动修改 |
|--------|----------------|---------|
| **E1** save_l4_fallback 语义 | `db_utils.py`、`save_l4_fallback` 调用方 | L4 回补不再以今日 pub_date 写入，而是保留原始 pub_date；或增加 source_confidence 不降低保护 |
| **D2** compute_ic_heatmap.py | `scripts/compute_ic_heatmap.py`（新建）、`api/macro_scoring_engine.py`（调用方）、`frontend`（IC 热图展示） | 需要同步修改 engine 调用逻辑和前端展示 |
| **F1** PIT 验证 SQL | `scripts/check_factors_l3.py`（新建）、`pit_data.db` | 每日定时运行，发现前视偏差自动告警 |
| **A1** ic_heatmap 加 target_symbol | `pit_data.db`（ALTER TABLE）、`compute_ic_heatmap.py`、`frontend` IC 热图 | ic_heatmap API 返回值变化，前端需同步改 |
| **A8** L5 降级链 null 写入 | `db_utils.py`、`save_to_db` 所有调用方 | 因子获取失败时需显式写入 source_confidence=0.0 的 NULL 行 |
| **A7** 重试逻辑扩展 | `db_utils.py` | save_to_db 增加对 OperationalError:not locked / DatabaseError / 磁盘满的处理 |

---

## 执行批次（5 批次）

---

### 批次 1：立即执行（今天，P0 先决条件）

**目标**：清除所有阻塞项，建立验证基础设施，为阶段三铺路。

| 任务 | 编号 | 操作 | 文件 | 联动修改 | 负责 |
|------|------|------|------|---------|------|
| E1 | B1-1 | 修复 `save_l4_fallback` 的 source_confidence 覆盖问题：L4 回补时，如果原始 source_confidence >= 0.5，不降低；或使用单独的回补表 | `crawlers/common/db_utils.py` | save_l4_fallback 所有调用方 | deep |
| E1 | B1-2 | 更新 `FACTOR_COLLECTION_SPEC_v1.md` 第 2.3 节：明确"允许 INSERT OR REPLACE，以 factor_code+symbol+pub_date+obs_date 为去重键，L4 回补保留原始 source_confidence" | `FACTOR_COLLECTION_SPEC_v1.md` | — | PM |
| E5 | B1-3 | 修复 L1 import 验证脚本：移除 `os.path.join(CRAWLERS, os.path.basename(root))`，只插入 `CRAWLERS` | `tools/run_verification.py` 或新建 `scripts/check_factors_l1_import.py` | — | mimo |
| F1 | B1-4 | 新建 PIT 完整性验证脚本 `scripts/check_pit_integrity.py`：执行 obs_date > pub_date 检测、幸存者偏差检测、交易日历对齐检测 | `scripts/check_pit_integrity.py`（新建） | 每日 cron 告警配置 | deep |
| E4 | B1-5 | 修复 fetch_url 解包检查：用 AST 解析替代正则，抽样 20 个文件验证 | `scripts/check_fetch_unpack.py`（新建） | — | mimo |
| D2 | B1-6 | 新建 `scripts/compute_ic_heatmap.py`：计算 60 日滚动 IC、IC_sign_stability、IC_IR，更新 ic_heatmap 表 | `scripts/compute_ic_heatmap.py`（新建） | `macro_scoring_engine.py`（调用方，如需要）、前端 IC 展示组件 | YIYI |

**B1 验收标准**：
- [ ] B1-1：REPLACE 后 source_confidence 不降低（写 UT 验证）
- [ ] B1-2：SPEC.md 更新后 grep 0 个"禁止 upsert"
- [ ] B1-3：L1 import 验证假性失败率 < 1%
- [ ] B1-4：PIT 检查脚本运行成功，输出 3 类问题的清单
- [ ] B1-5：AST 检查 20 个文件，0 个误报
- [ ] B1-6：compute_ic_heatmap.py 语法正确，对 RU/AU/CU/AG/RB 5 个品种计算出 IC 值

---

### 批次 2：Spec 修订（今天，B1 完成后并行）

**目标**：更新所有规范文档，建立正确的量化标准。

| 任务 | 编号 | 操作 | 文件 | 负责 |
|------|------|------|------|------|
| F2 | B2-1 | 更新 L4 IC 方法论：IC 窗口 ≥60 日、胜率定义为 |IC|>0.01 的交易日占比、IC_sign_stability≥60%、IC_FDR_corrected_p<0.05 | `FACTOR_COLLECTION_SPEC_v1.md` L4 章节 | PM |
| F3 | B2-2 | 修订 expected_range 合规：99%→99.5%、增加历史分位数自验证、高频因子 3σ 检测 | `FACTOR_COLLECTION_SPEC_v1.md` | PM |
| F4 | B2-3 | 重设计健康度评分函数：基于 IC 质量加权因子数、expected_range 0.5% 收紧、增加 PIT 观测比例维度 | `FACTOR_COLLECTION_SPEC_v1.md` | YIYI |
| A3 | B2-4 | CFTC 因子：IC 窗口改为 12 周滚动、IR 阈值降至 0.3 | `FACTOR_COLLECTION_SPEC_v1.md` 豁免规则 | YIYI |
| A6 | B2-5 | 记录数门槛：≥30→≥60（最低）、推荐 120、月度豁免 12 | `FACTOR_COLLECTION_SPEC_v1.md` | PM |
| D4 | B2-6 | 更新验收方案 L4/L5：P0≥90%/P1≥80%/P2≥70% 分档门槛 | `因子采集健康度验收方案_20260503.md` L4/L5 | PM |

**B2 验收标准**：
- [ ] SPEC.md grep 0 个"IC_rolling_20d"
- [ ] SPEC.md grep 0 个"99%"（改为 99.5%）
- [ ] health_score 函数有 IC 质量加权逻辑（代码或注释描述）
- [ ] 验收方案 grep 0 个"100%"成功率要求

---

### 批次 3：Schema + 联动修改（明天，P0 先决条件完成后再启动）

**目标**：修改数据库 schema，更新所有联动组件。

| 任务 | 编号 | 操作 | 文件 | 联动修改 | 负责 |
|------|------|------|------|---------|------|
| A1 | B3-1 | ic_heatmap 表加 `target_symbol TEXT` 列 | `pit_data.db`（ALTER TABLE） | — | deep |
| A1 | B3-2 | 更新 `compute_ic_heatmap.py`：写入 target_symbol（用于宏观因子跨品种 IC） | `scripts/compute_ic_heatmap.py` | — | YIYI |
| A1 | B3-3 | 更新 ic_heatmap API 返回值（如果 macro_api_server.py 有相关端点） | `api/` 相关文件 | 前端 IC 热图组件 | deep |
| A1 | B3-4 | 前端 IC 热图组件增加 target_symbol 展示 | `frontend/` IC 热图组件 | — | Lucy |
| A1 | B3-5 | 更新 `因子采集健康度验收方案_20260503.md` L3 ic_heatmap 覆盖要求：≥20 个品种 | `因子采集健康度验收方案_20260503.md` | — | PM |

**B3 验收标准**：
- [ ] ic_heatmap 表 DESCRIBE 有 target_symbol 列
- [ ] compute_ic_heatmap.py 运行时无 target_symbol 相关错误
- [ ] 前端 IC 热图显示 target_symbol 标签（如 AU_DXY→target=AG）

---

### 批次 4：db_utils + 豁免规则（本周）

**目标**：完善异常处理和数据豁免体系。

| 任务 | 编号 | 操作 | 文件 | 联动修改 | 负责 |
|------|------|------|------|---------|------|
| A7 | B4-1 | 扩展 save_to_db 重试逻辑：增加对 `OperationalError:not locked`、`DatabaseError`、`磁盘满`、`权限错误`的区分处理 | `crawlers/common/db_utils.py` | — | deep |
| A8 | B4-2 | 实现 L5 降级链 null 写入路径：`save_to_db(factor_code, ..., raw_value=NULL, source_confidence=0.0)` | `crawlers/common/db_utils.py` | 需要在爬虫脚本中显式调用 | mimo |
| A8 | B4-3 | 抽样 5 个爬虫脚本实现 null 写入路径示例（AG/CU/RU/AU/J 各一） | `crawlers/AG/AG_抓取TIPS.py` 等 | — | mimo |
| A2 | B4-4 | 增加月度/季度数据豁免规则：CPI/PPI/PMI/GDP/USDA_obs_date 对齐规则 | `FACTOR_COLLECTION_SPEC_v1.md` 豁免规则章节 | — | YIYI |
| A4 | B4-5 | 明确"上线"定义锚定到 DB `first_obs_date`，更新豁免规则 | `FACTOR_COLLECTION_SPEC_v1.md` | — | PM |

**B4 验收标准**：
- [ ] db_utils.py 有 3 种以上错误类型的区分处理
- [ ] B4-2 实现后，null 写入有 `[DB] 因子 {factor} NULL 占位写入` 日志
- [ ] 豁免规则包含 CPI/PPI/PMI/GDP/USDA

---

### 批次 5：调度 + 最终验收（本周）

**目标**：定义 ic_heatmap 与 run_all 的调度关系，完成全量验收。

| 任务 | 编号 | 操作 | 文件 | 联动修改 | 负责 |
|------|------|------|------|---------|------|
| A10 | B5-1 | 定义 ic_heatmap 每日计算与 run_all 的依赖链：run_all 成功 → 触发 compute_ic_heatmap | `scripts/run_all_with_ic.sh` 或 Windows schtasks 配置 | — | deep |
| A10 | B5-2 | 更新 `因子采集健康度验收方案_20260503.md` 增加 A10 调度依赖说明 | `因子采集健康度验收方案_20260503.md` | — | PM |
| — | B5-3 | 运行全量 L0-L6 验收（见合并架构），生成最终验收报告 | 全部组件 | — | PM |
| — | B5-4 | 合并 SPEC.md + 验收方案 + 执行计划 → 统一文档 `FACTOR_GOVERNANCE.md` | `FACTOR_GOVERNANCE.md`（新建） | — | PM |

**B5 验收标准**：
- [ ] run_all 执行后 ic_heatmap 有增量更新
- [ ] L0-L6 全量验收通过
- [ ] `FACTOR_GOVERNANCE.md` 包含所有规范和验收标准

---

## 风险与回滚预案

| 风险 | 概率 | 影响 | 预案 |
|------|------|------|------|
| B3-1 ALTER TABLE ic_heatmap 导致现有数据损坏 | 低 | 高 | 回滚：备份原 db 文件；如失败则重建 target_symbol 字段从 compute_ic_heatmap 增量回填 |
| B1-1 save_l4_fallback 修改破坏 L4 回补逻辑 | 中 | 高 | 回滚：`git checkout`；并行运行 B1-1 regression test（对比修改前后 L4 回补行为） |
| B1-6 compute_ic_heatmap.py 计算错误导致错误 IC 值进入打分 | 高 | 高 | 隔离：计算结果先写入影子表 `ic_heatmap_staging`，人工确认后再 swap 到正式表 |
| B3-4 前端 target_symbol 改动破坏现有 IC 热图 | 中 | 中 | Feature Flag：前端增加 `USE_TARGET_SYMBOL=false` 开关，灰度切流 |
| B4-1 save_to_db 重试逻辑引入死循环 | 低 | 高 | 增加最大重试时间（当前 3×2s=6s，总耗时上限 30s）|

---

## 验收报告模板（L0-L6 全量）

```markdown
# 因子采集健康度验收报告 — {日期}

## 批次执行状态
| 批次 | 任务数 | 完成数 | 状态 |
|------|--------|--------|------|
| B1 立即执行 | 6 | X/6 | ✅/🔴 |
| B2 Spec修订 | 6 | X/6 | ✅/🔴 |
| B3 Schema+联动 | 5 | X/5 | ✅ |
| B4 db_utils+豁免 | 5 | X/5 | ✅/🔴 |
| B5 调度+最终验收 | 4 | X/4 | ✅ |

## L0-L6 验收结果
| 层级 | 检查项 | 结果 | 详情 |
|------|--------|------|------|
| L0 | requests.get 残留=0 | ✅/🔴 | X 个残留 |
| L0 | .py.old 残留=0 | ✅/🔴 | X 个残留 |
| L1 | py_compile 315/315 | ✅/🔴 | X FAIL |
| L1 | import ≥95% | ✅/🔴 | X FAIL |
| L1 | fetch_url AST解包检查 | ✅/🔴 | X 误报 |
| L2 | P0 品种×5 运行 | ✅/🔴 | X FAIL |
| L2 | P1 品种×10 运行 | ✅/🔴 | X FAIL |
| L3 | PIT 完整性 | ✅/🔴 | X 问题 |
| L3 | ic_heatmap 覆盖≥20品种 | ✅/🔴 | X 品种 |
| L4 | compute_ic_heatmap 60d IC | ✅/🔴 | X 因子 |
| L4 | IC IR 三档分层 | ✅/🔴 | X 不健康 |
| L5 | run_all P0≥90%/P1≥80% | ✅/🔴 | X 品种不达标 |
| L6 | 降级链 3/3 通过 | ✅/🔴 | X 链路失败 |

## 遗留问题
| # | 严重度 | 问题 | 负责人 | 计划 |
|---|--------|------|--------|------|
| 1 | 🔴 | ... | ... | ... |
```

---

## 快速启动命令

```powershell
# 批次1验证
cd D:\futures_v6\macro_engine
python scripts/check_pit_integrity.py
python scripts/check_fetch_unpack.py
python scripts/compute_ic_heatmap.py --dry-run

# 批次3验证
sqlite3 pit_data.db "ALTER TABLE ic_heatmap ADD COLUMN target_symbol TEXT"

# 全量L0-L1
python -m py_compile crawlers/**/[a-z]*.py 2>&1 | Select-String "Error" | Measure-Object
```
