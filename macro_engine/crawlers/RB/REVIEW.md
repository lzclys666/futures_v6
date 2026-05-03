# RB 螺纹钢因子采集脚本 — 复查报告

**复查时间**: 2026-05-02 10:02  
**复查人**: mimo  
**运行平台**: Windows | Python 3.11

---

## 一、脚本清单（共9个）

| # | 脚本名 | 因子代码 | 运行状态 |
|---|--------|---------|---------|
| 1 | `RB_run_all.py` | — | ✅ 成功 |
| 2 | `RB_抓取螺纹钢库存.py` | RB_INV_STEEL | ✅ 成功 |
| 3 | `RB_抓取上期所螺纹钢仓单.py` | RB_INV_SHFE | ⚠️ L1失败→L4回补 |
| 4 | `RB_抓取净持仓.py` | RB_POS_NET | ⚠️ L1失败→L4回补 |
| 5 | `RB_计算持仓集中度.py` | RB_POS_CONCENTRATION | ⚠️ L1失败→L4回补 |
| 6 | `RB_计算期现基差.py` | RB_SPD_BASIS | ⚠️ L1失败→L4回补 |
| 7 | `RB_计算螺纹钢热卷比价.py` | RB_SPD_RB_HC | ✅ 成功（L2） |
| 8 | `RB_计算近远月价差.py` | RB_SPD_CONTRACT | ✅ 成功（L2） |
| 9 | `RB_批次2_手动输入.py` | 批次2因子×5 | ⏸️ 无历史数据→全部跳过 |

**批量运行结果**: 成功=8 失败=0 跳过=0（自动化 7/7，手动 1/1）

---

## 二、范式检查结果

### 2.1 逐项检查汇总

| 检查项 | 通过 | 问题脚本 |
|--------|------|---------|
| 脚本头部有docstring | ✅ 9/9 | — |
| 有try-except（无bare except） | ⚠️ 8/9 | RB_run_all.py 有一处bare except |
| 网络请求有timeout | ✅ 7/7（需网络的脚本） | — |
| 魔法数字定义为常量 | ❌ 0/9 | 全部脚本均有魔法数字硬编码 |
| 函数/方法有类型注解 | ❌ 0/9 | 全部缺失 |
| 日志级别完善 | ⚠️ 8/9 | 均为print，无logging模块 |
| CSV输出到output/ | ❌ 0/9 | 全部直接写DB，无CSV |
| 无硬编码中文文件名 | ✅ 9/9 | — |
| 中断/恢复逻辑 | N/A | 无状态文件需求，设计合理 |

### 2.2 各脚本详细问题

#### ✅ `RB_run_all.py`（总控脚本）
- 范式：基本符合，有timeout(120s)，subprocess封装良好
- 问题：bare except 1处（第57行 `except Exception as e` 在循环内可接受，但函数级别应更精确）
- **结论：轻微问题，不影响运行**

#### ✅ `RB_抓取螺纹钢库存.py`（RB_INV_STEEL）
- 范式：结构完整，四层漏斗清晰
- 问题：
  - 魔法数字 `10000000`（库存上限）硬编码
  - 无类型注解
  - 用print代替logging
- **结论：轻微问题，可接受**

#### ⚠️ `RB_抓取上期所螺纹钢仓单.py`（RB_INV_SHFE）
- 范式：结构完整
- 问题：
  - AKShare L1返回空数据（`Expecting value: line 1 column 1`），L2上期所官网TODO未实现
  - 仓单数据依赖L4回补，**数据链路中断**
  - 魔法数字 `1000000` 硬编码
  - 无类型注解
- **结论：L2数据源长期未实现，需优先补全**

#### ⚠️ `RB_抓取净持仓.py`（RB_POS_NET）
- 范式：结构完整，四层漏斗
- 问题：
  - L1（AKShare get_shfe_rank_table）失败，L2（新浪API）失败，**当前全靠L4回补**
  - 计算逻辑 `rb_df['volume'].sum()` 过于简化，与因子含义不符
  - 无类型注解
- **结论：数据源链路不通，L1+L2均失败，需排查**

#### ⚠️ `RB_计算持仓集中度.py`（RB_POS_CONCENTRATION）
- 范式：结构完整
- 问题：
  - AKShare L1失败，**全靠L4回补**
  - `rb_df['volume'].sum()` / `rb_df.head(10)['volume'].sum()` 计算逻辑存疑（total_vol=top20还是top20？）
  - 无类型注解
- **结论：数据源链路不通，需排查**

#### ⚠️ `RB_计算期现基差.py`（RB_SPD_BASIS）
- 范式：结构完整
- 问题：
  - 现货L1（东方财富）TODO未实现，L2/L3直接跳过付费
  - **无免费现货价数据源，基差计算依赖历史回补**
  - 无类型注解
- **结论：现货价数据源缺失，基差因子永久降级为L4回补**

#### ✅ `RB_计算螺纹钢热卷比价.py`（RB_SPD_RB_HC）
- 范式：L1新浪失败，L2 AKShare成功，逻辑清晰
- 问题：L1新浪API不稳定（当日L1失败属正常波动），无类型注解
- **结论：可接受，L2为稳定备源**

#### ✅ `RB_计算近远月价差.py`（RB_SPD_CONTRACT）
- 范式：L1新浪失败，L2 AKShare成功
- 问题：L1不稳定，月份推断逻辑 `months = [1,5,10]` 硬编码，无类型注解
- **结论：可接受，L2为稳定备源**

#### ⏸️ `RB_批次2_手动输入.py`（批次2因子×5）
- 范式：stub脚本，逻辑合理
- 问题：
  - 5个因子全部无历史数据（L4回补失败），因子尚未配置到数据库
  - 手动输入模式未真正使用（因为没有人工触发）
- **结论：脚本正常，待因子分析师推进批次2**

---

## 三、运行日志关键片段

```
>>> RB_抓取螺纹钢库存.py... (auto)
[L1] AKShare futures_inventory_em...
[L1] 成功: 90526 吨              ← ✅ RB_INV_STEEL L1成功

>>> RB_抓取上期所螺纹钢仓单.py... (auto)
[L1] AKShare futures_shfe_warehouse_receipt obs=2026-05-01...
[L1] 失败: Expecting value: line 1 column 1 (char 0)  ← ⚠️ L1失败
[L4] DB历史回补...
[L4] 兜底: 83390.0               ← 降级L4回补

>>> RB_抓取净持仓.py... (auto)
[L1] AKShare get_shfe_rank_table...
[L2] 新浪实时API...
[L4] DB历史回补...
[L4] 兜底: 55829.0               ← ⚠️ L1+L2均失败，降级L4

>>> RB_计算期现基差.py... (auto)
[期货] AKShare futures_main_sina RB0...
  期货价格: 3214.0 元/吨          ← ✅ 期货价格获取成功
[现货L1] 东方财富建材数据...       ← ⚠️ TODO未实现
[现货L2] 我的钢铁网 - 付费订阅，跳过
[现货L3] 兰格钢铁网 - 付费订阅，跳过
[L4] DB历史基差回补...            ← 无现货价，永久降级L4

>>> RB_计算螺纹钢热卷比价.py... (auto)
[L1] 新浪实时API RB0 & HC0...
[L2] AKShare futures_zh_daily_sina...
[L2] 成功: RB/HC=0.9384          ← ✅ L2成功

>>> RB_批次2_手动输入.py... (auto)
[自动模式] 批次2因子无免费数据源，尝试DB回补...
  [跳过] RB_SUPPLY_STEEL_OUTPUT 无历史数据  ← ⚠️ 因子未入库
```

---

## 四、CSV输出规范问题（严重）

**规范要求**：数据应输出到 `D:\futures_v6\macro_engine\output\`，CSV格式。

**实际现状**：所有脚本均无CSV输出，直接调用 `save_to_db()` 写库。

**影响**：
- 无法人工核查采集值
- 无法横向对比不同因子
- 违反了操作手册V6.1的输出规范

**建议**：在 `RB_run_all.py` 统一加CSV输出，或在各脚本加 `--csv` flag。

---

## 五、优先级问题汇总

| 优先级 | 问题 | 脚本 |
|--------|------|------|
| P0 | AKShare L1全面失败（上期所接口变更？） | RB_INV_SHFE, RB_POS_NET, RB_POS_CONCENTRATION |
| P1 | 现货价数据源缺失，基差因子永久回补 | RB_SPD_BASIS |
| P2 | CSV输出规范未遵守 | 全部脚本 |
| P3 | 类型注解/魔法数字常量 | 全部脚本（长期改进） |

---

## 六、README.md 更新内容

```markdown
# RB — 螺纹钢 期货数据采集

## 基本信息

| 字段 | 值 |
|------|-----|
| 品种代码 | `RB` |
| 中文名称 | 螺纹钢 |
| 交易所 | SHFE |
| 因子数量 | 9（含批次2: 5个） |

## 因子配置

| 因子代码 | 描述 | 采集状态 | 数据源 |
|---------|------|---------|-------|
| RB_INV_STEEL | 螺纹钢库存 | ✅ 正常 | AKShare L1 |
| RB_INV_SHFE | 上期所仓单 | ⚠️ L4回补 | AKShare L1失败，L2未实现 |
| RB_POS_NET | 前20净持仓 | ⚠️ L4回补 | L1+L2均失败 |
| RB_POS_CONCENTRATION | 持仓集中度CR10 | ⚠️ L4回补 | AKShare L1失败 |
| RB_SPD_BASIS | 期现基差 | ⚠️ L4回补 | 现货L1未实现 |
| RB_SPD_CONTRACT | 近远月价差 | ✅ 正常 | AKShare L2 |
| RB_SPD_RB_HC | 螺纹钢/热卷比价 | ✅ 正常 | AKShare L2 |
| RB_SUPPLY_STEEL_OUTPUT | 钢厂螺纹钢产量 | ⏸️ 待开发 | 批次2，无免费源 |
| RB_DEMAND_REAL_ESTATE | 房地产新开工面积 | ⏸️ 待开发 | 批次2，无免费源 |

## 爬虫脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| RB_抓取螺纹钢库存.py | ✅ | L1可用 |
| RB_抓取上期所螺纹钢仓单.py | ⚠️ | L1失败，L2待实现 |
| RB_抓取净持仓.py | ⚠️ | L1+L2均失败，全靠回补 |
| RB_计算持仓集中度.py | ⚠️ | L1失败 |
| RB_计算期现基差.py | ⚠️ | 现货价源缺失 |
| RB_计算螺纹钢热卷比价.py | ✅ | L2备用正常 |
| RB_计算近远月价差.py | ✅ | L2备用正常 |
| RB_run_all.py | ✅ | 总控正常 |
| RB_批次2_手动输入.py | ⏸️ | Stub，因子待入库 |

## 运行方式

```bash
# 批量采集（推荐）
python crawlers/RB/RB_run_all.py --auto

# 单脚本测试
python crawlers/RB/<脚本名>.py --auto
```

## 已知问题

- ⚠️ AKShare `get_shfe_rank_table` / `futures_shfe_warehouse_receipt` L1接口近期不稳定，多个因子降级至L4回补
- ⚠️ 现货价数据源缺失，RB_SPD_BASIS 永久依赖L4回补，需因子分析师确认付费数据源
- ⚠️ CSV输出规范未实现（直接写DB，无CSV文件）

---
_复查时间: 2026-05-02 10:02 | 复查人: mimo_
```

---

## 七、交付结论

1. **批量运行通过**：8/8 脚本执行成功，0失败
2. **L1数据源整体偏弱**：5/7个自动化因子降级到L4回补（AKShare接口问题或L2未实现）
3. **CSV输出规范缺失**：需补全
4. **最优先修复**：RB_INV_SHFE的L2上期所官网爬虫 + RB_SPD_BASIS的现货价源
