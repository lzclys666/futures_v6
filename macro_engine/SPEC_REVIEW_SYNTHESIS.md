# 因子采集规范审查综合报告
> 审查日期：2026-05-03 | YIYI（因子分析师）+ mimo（程序员）并行审查
> 源文档：`FACTOR_COLLECTION_SPEC_v1.md` | `因子采集健康度验收方案_20260503.md` | `SPEC_COMPARISON.md`
> 状态：**终稿，已含决策结论**

---

## 执行摘要

两份方案合并后架构完整（L0-L6），但审查发现 **9 项阻塞问题**（🔴）和 **11 项建议问题**（🟡），分两类：
- **因子研究层**：PIT 完整性、IC 方法论、健康度评分质量（YIYI 发现）
- **工程实现层**：UPSERT 冲突、compute_ic_heatmap.py 缺失、正则检查不可靠（mimo 发现）

---

## 🔴 阻塞问题（9项）

### F1: PIT 数据完整性验证根本缺失（YIYI，阻塞）
**问题**：L3/L4 完全没有 Point-in-Time 数据质量检查。
- 幸存者偏差：退市/摘牌合约是否被错误排除
- 前视偏差：`obs_date` 是否晚于实际发布日期（夜盘数据在次日白天发布）
- 缓存回填 vs 实际观测：两类混用会虚高 IC
- 交易日历对齐：宏观因子用日历日还是交易日，不同步产生"幽灵相关"

**补充 L3 检查**：
```sql
-- obs_date > pub_date 异常检测
SELECT factor_code, COUNT(*) as suspicious
FROM pit_factor_observations
WHERE obs_date > pub_date
GROUP BY factor_code
HAVING suspicious > 总记录 * 0.05;
```

### F2: IC 计算方法论不完整（YIYI，阻塞）
**问题**：
- 窗口 20 日太短（约 1 个月），IC 估算方差极大
- 胜率定义不清（微正微负会抵消）
- 无多重检验校正（FDR/Bonferroni）
- 方向一致性仅要求 `IC * direction > 0`，不要求符号稳定比例

**修订 L4 要求**：
```
IC_rolling_60d ≥ 0.03
IC_sign_stability ≥ 60%（60日内符号一致比例）
IC_FDR_corrected_p < 0.05
```

### F3: `expected_range` 99% 合规逻辑自相矛盾（YIYI，阻塞）
**问题**：
- `expected_range` 本身无历史数据验证时，99% 合规毫无意义（如 [-100000, 100000]）
- 金银比飙升至 120 是历史极限，越界是交易信号而非错误
- "范围异常只告警不阻断"会污染 IC 计算

**修订**：
- 改为 99.5% 合规
- 增加 `expected_range` 自身历史分位数验证
- 高频因子增加 3σ 异常检测（比 expected_range 更敏感）

### F4: 健康度评分是"数量评分"非"质量评分"（YIYI，阻塞）
**问题**：评分函数可被刷分，IC 方向/IR 稳定性都不在评分里。

| 当前问题 | 修订 |
|---------|------|
| `factor_count >= 5` 可刷分 | 改为基于 IC 质量加权因子数 |
| `range_violation_rate < 0.01` 太容易 | 收紧至 0.5%，并验证 expected_range 有效性 |
| 不区分前推填充和实际观测 | 增加 PIT 观测比例维度 |

### E1: `INSERT OR REPLACE` 与 spec "禁止 upsert" 直接冲突（mimo，阻塞）
**问题**：
- spec v1.0 第 2.3 节写"禁止 upsert"
- `db_utils.py` 第46行实际是 `INSERT OR REPLACE`（UPSERT）
- 断点重跑会覆盖 source_confidence=1.0 为 0.5 的 L4 回补值

### E2: `compute_ic_heatmap.py` 不存在（mimo，阻塞）
**问题**：
- `D:\futures_v6\macro_engine\scripts\compute_ic_heatmap.py` 经验证不存在
- `ic_heatmap` 表仅 25 行（1个交易日×5品种）
- **阶段三（L4 IC 工程化）无法按当前计划执行**

**影响**：阶段三必须拆出为独立任务，先开发此脚本。

### E3: PK 定义不一致（mimo，阻塞）
**问题**：
- spec 声称：`factor_code + symbol + pub_date + obs_date` 4列PK
- 实际 schema：`PRIMARY KEY (factor_code, symbol)` 仅2列
- 结果：同一因子同一日期可有多个 obs_date 不同的记录

**影响**：断点重跑时以 (factor_code, symbol) 为键覆盖，丢失 `pub_date` 差异。

### E4: fetch_url 解包正则检查不可靠（mimo，阻塞）
**问题**：正则 `\(data|html|text|err|r)\s*,\s*(err|error)\)` 存在根本缺陷：
- `\s*` 匹配换行符，`data,\nerr` 被错误标记为正确
- 变量名完全自定义时不匹配（如 `result, err`）
- 无法排除 `data= fetch_url(...)`（赋值非解包）

**修订**：改用 AST 解析 + 人工抽检，不依赖正则。

### E5: L1 import 验证脚本 sys.path 膨胀 Bug（mimo，阻塞）
**问题**：附录脚本 `sys.path.insert(0, os.path.join(CRAWLERS, os.path.basename(root)))` 无效（无 `__init__.py` 指向），导致 315 个脚本的 5% 容错（约15个）全是假性 ImportError。

**修复**：只插入 `CRAWLERS` 本身，不拼接子目录。

---

## 🟡 建议问题（11项）

### A1: 宏观因子 IC 跨品种归属未定义（YIYI）
- AU_DXY 对 AU/AG/CU 都有信号，但 ic_heatmap 表只有 `factor_code`，无 `target_symbol`
- J_钢铁网 是 RB/HC/I 的驱动因子，在 J 本身上算 IC 毫无意义
- **建议**：ic_heatmap 表增加 `target_symbol` 字段

### A2: 月度/季度数据豁免缺失（YIYI）
- CFTC 周频豁免已有
- 遗漏：CPI/PPI/PMI（月度）、GDP（季度）、周末 USDA 报告（非交易日发布）
- **建议**：增加月度/季度数据豁免规则，obs_date 对齐规则

### A3: CFTC 因子 IC 计算特殊性未处理（YIYI）
- CFTC 每周五发布，按交易日历约 4个点/20天，IR 无统计意义
- **建议**：CFTC 因子窗口改为 12 周滚动，IR 阈值降至 0.3

### A4: 新因子"上线"定义模糊（YIYI）
- "上线 <30 天"是脚本首次运行日期？YAML `is_active=true` 日期？还是 DB first_obs_date？
- **建议**：锚定到 DB `first_obs_date`

### A5: IC IR ≥ 0.5 阈值过于严格（YIYI）
- 商品期货因子 IR 多在 0.2-0.5 之间，0.5 会误杀大量有效因子
- **建议**：分层
  ```
  IR < 0.3：🔴 不健康
  IR 0.3~0.5：🟡 警告
  IR ≥ 0.5：✅ 优秀
  ```

### A6: 每因子 ≥30 条记录统计不足（YIYI）
- 30 样本 t 检验自由度约 29，置信区间宽达 [-0.2, +0.2]
- **建议**：最低 60 条，推荐 120 条，月度豁免 12 条

### A7: save_to_db 重试逻辑不完整（mimo）
- 仅对 `sqlite3.OperationalError: locked` 重试3次
- 网络超时/磁盘满/权限错误无重试
- **建议**：区分"可恢复"（locked/busy）和"不可恢复"（syntax error），不可恢复立即上抛

### A8: L5 降级链"标记为 null 不阻断"无代码实现（mimo）
- spec 定义 L5 = `因子可空，不阻断`
- 但多数脚本在数据获取失败后隐式 return，无 `source_confidence=0.0` 显式写入
- **建议**：显式 `save_to_db(..., raw_value=NULL)` 路径

### A9: run_all 集成测试 2h 估算过于乐观（mimo）
- AG 有 17 个因子，最坏 17×30s = 8.5min，仅 AU 就超估算
- **建议**：≥80% 子因子成功即通过，不要求 100%

### A10: ic_heatmap 每日更新与 run_all 调度关系未定义（mimo）
- ic_heatmap 计算是独立 cron 还是挂在 run_all 之后？
- **建议**：明确 run_all 完成 → ic_heatmap 触发依赖链

### A11: 自定义 headers 5 源测试依赖外部网络（mimo）
- Sina/金十/Eastmoney/Mysteel/铝道网 在内网/CI 环境可能全部失败
- **建议**：改为"有网络时可选"，不作为阻塞验收项

---

## 最终决策结论（2026-05-03 12:52）

### D1: UPSERT 策略 → ✅ 选方案A（允许 UPSERT + 修复 PK 定义）

**决策**：允许 `INSERT OR REPLACE`，同时修复 PK 定义不一致问题。

**理由**：
- 数据采集系统重跑时"新数据覆盖旧数据"是合理需求，断点续传必须
- 真正的问题不是 UPSERT 本身，而是 **PK 定义不一致**：spec 说4列，实际 schema 只有2列
- 如果 PK 是4列，REPLACE 只会覆盖完全重复的记录（同一因子同一发布日同一观测日），不会误杀其他日期的数据

**落地动作**：
1. `db_utils.py`：`PRIMARY KEY (factor_code, symbol, pub_date, obs_date)` 改为4列
2. `FACTOR_COLLECTION_SPEC_v1.md` 第2.3节：改为"允许 INSERT OR REPLACE（以 factor_code + symbol + pub_date + obs_date 为去重键）"

---

### D2: compute_ic_heatmap.py → ✅ 立即新建

**决策**：今天立即新建此脚本，无任何借口延期。

**理由**：
- L4 IC 验证是最终出口，如果 IC 热图不可信，整个打分系统可信度是负数
- 这不是"开发任务"，只是一个 SQL 脚本（顶多 50 行），YIYI 或 mimo 都能写
- ic_heatmap 表 schema 已有（calc_date, symbol, factor_code, ic_mean, ic_std, ir, win_rate），只缺计算逻辑

**落地动作**：
1. 指派 **YIYI** 写 `scripts/compute_ic_heatmap.py`
2. 作为阶段三的 **P0 前置条件**，阶段三必须等此脚本完成才能开始

---

### D3: IC IR 阈值分层 → ✅ 接受三档分层

**决策**：采用三档分层，不维持 0.5 统一门槛。

| 档位 | IR | 状态 | 处置 |
|------|-----|------|------|
| 🔴 | < 0.3 | 不健康 | 降权或归档 |
| 🟡 | 0.3 ~ 0.5 | 警告 | 可用但加强监控 |
| ✅ | ≥ 0.5 | 优秀 | 正常参与打分 |

**理由**：
- 商品期货因子 IR 普遍偏低（波动大、信噪比低），0.5 统一门槛会误杀大量真实有效因子
- 当前 ic_heatmap 只有 25 行数据，没有足够统计量支撑 0.5 判断
- 三档分层更务实，同时不降低"优秀"标准

**落地动作**：更新 `FACTOR_COLLECTION_SPEC_v1.md` L4 章节，替换原 IR 阈值为三档定义。

---

### D4: run_all 成功率门槛 → ✅ ≥80% 分品种对待

**决策**：分品种设定成功率门槛，不搞一刀切。

| 品种档位 | 品种 | 建议门槛 | 理由 |
|---------|------|---------|------|
| P0 | AU/CU/RB/AG/RU | ≥90% | 核心品种，直接驱动交易决策 |
| P1 | J/AL/NI/TA/HC/JM/SA/ZN/P/PB 等 | ≥80% | 次核心，允许部分因子在数据积累期 |
| P2 | 其余 20 个品种 | ≥70% | 观察仓，数据质量不是唯一目标 |

**理由**：
- 100% 在实操中几乎不可能（网络抖动、反爬、数据源变更都会导致个别因子失败）
- P0 品种直接关联交易决策，设更高门槛合理
- "只要 70% 就过"太宽松，会掩盖系统性故障

**落地动作**：更新 `因子采集健康度验收方案_20260503.md` L4/L5 章节，对应验收报告模板同步更新。

---

## 综合执行优先级

```
P0 立即执行（今天）
├── D1: 修复 PK 定义（4列）+ 更新 spec UPSERT 表述    → deep
├── D2: 新建 compute_ic_heatmap.py                    → YIYI
├── F1: 补充 PIT 完整性检查 SQL                        → deep
└── E4: fetch_url 解包检查改 AST 解析                   → mimo

P1 近期执行（本周）
├── F2: 更新 IC 计算方法论（L4 章节修订）
├── F3: expected_range 99%→99.5% + 历史分位数验证
├── F4: 健康度评分函数重设计（含 IC 质量维度）
├── A3: CFTC 因子 12 周滚动窗口
└── A6: ≥30 条→≥60 条最低门槛

P2 纳入日常改进（后续迭代）
├── A1: ic_heatmap 增加 target_symbol 字段
├── A2: 月度/季度数据豁免规则
├── A7: save_to_db 重试逻辑完善
├── A8: L5 降级链 null 写入路径
└── A10: ic_heatmap 与 run_all 调度依赖定义
```

---

## 修订后的合并架构（最终版）

```
L0 文件系统预检（5min）
  ↓
L1 语法 & 导入验证（15min）
  ↓
L2 运行时快速验证（1h）— 新增实际执行验证
  ↓
L3 数据库审计（30min）— 新增 PIT 完整性检查
  ↓
L4 IC 有效性验证 — 新增 compute_ic_heatmap.py（P0 先决）
  ↓
L5 run_all 集成测试（2h）— 分品种门槛 P0≥90%/P1≥80%/P2≥70%
  ↓
L6 降级逻辑专项验证（1h）
```

---

## 豁免规则（补充版）

| 数据类型 | 最低记录数 | IC 窗口 | IR 阈值 | 审批人 |
|---------|-----------|---------|---------|-------|
| 日频因子 | 60 条 | 60 日 | 0.3（警告线）| — |
| 周频因子 | 12 条 | 12 周 | 0.3 | YIYI |
| 月度宏观（CPI/PPI/PMI）| 12 条 | 12 月 | 0.2 | YIYI |
| CFTC 周频 | 12 条 | 12 周 | 0.3 | YIYI |
| 新因子（<30 天）| 上线豁免 | — | — | YIYI |
| 人工录入 | 豁免记录数 | — | — | PM |
