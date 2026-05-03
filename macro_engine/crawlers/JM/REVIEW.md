# JM 因子采集脚本复查报告

**复查时间**: 2026-05-02 09:40 GMT+8
**工作目录**: `D:\futures_v6\macro_engine\crawlers\JM\`
**执行命令**: `python JM_run_all.py --auto`

---

## 一、运行结果

```
结果: 成功=4 失败=0 跳过=14
  自动化: 4/5
  手动兜底: 0/13 (DB回补)
```

| 脚本 | 运行结果 | 写入DB |
|------|---------|--------|
| JM_抓取焦煤期货持仓量.py | ✅ 成功 | ✅ JM_POS_OI |
| JM_计算焦煤月差.py | ✅ 成功 | ✅ JM_SPD_CONTRACT |
| JM_计算焦煤期现基差.py | ⚠️ 跳过 | ❌ JM_SPD_BASIS无现货源 |
| JM_计算焦煤动力煤比价.py | ✅ 成功 | ✅ JM_SPD_ZC |
| JM_抓取焦煤进口量.py | ⚠️ 跳过 | ❌ L1-L3均未获取到数据 |
| 14个付费stub脚本 | ⏸️ 跳过 | ❌ 付费数据源不可用 |

**DB现状**（2026-05-02最新）：

| factor_code | raw_value | source | confidence |
|-------------|-----------|--------|-------------|
| JM_POS_OI | 428448.0 | akshare | 1.0 |
| JM_SPD_CONTRACT | -207.5 | akshare | 1.0 |
| JM_SPD_ZC | 1.3974 | akshare | 0.9 |

**注意**: `JM_SPD_BASIS` 无数据——期货价可取，但所有层级的现货价均失败（L1汾渭/L2 Mysteel付费，L3隆众待实现，L4无DB历史）。

---

## 二、逐脚本范式检查

### 2.1 ✅ JM_run_all.py（总控脚本）

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ✅ | 头部有功能说明 |
| try-except | ✅ | `except Exception as e`（非bare） |
| timeout | ✅ | `subprocess.run(timeout=120)` |
| 魔法数字 | ✅ | 120秒超时常量，无硬编码 |
| 类型注解 | ⚠️ | 函数无类型注解（但参数简单可接受） |
| 日志 | ✅ | INFO/ERROR级别日志 |
| 输出路径 | N/A | 不直接输出CSV，写DB |
| 硬编码中文文件名 | ✅ | 无 |
| 中断/恢复 | ✅ | 逐脚本独立try-except |

**评价**: 结构清晰，分类合理（auto_scripts / manual_scripts）。

---

### 2.2 ✅ JM_抓取焦煤期货持仓量.py

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ✅ | 有Header，含因子说明 |
| try-except | ⚠️ | L2层`except:`为bare except；L1/L3/L4正常 |
| timeout | ⚠️ | L1 AKShare无timeout；L3有timeout=10 |
| 魔法数字 | ✅ | 1000000定义为合理范围上限 |
| 类型注解 | ✅ | 有部分类型注解 |
| 日志 | ✅ | L1-L4每层都有日志 |
| 输出路径 | ✅ | 写入DB，无CSV输出需求 |
| 硬编码中文文件名 | ✅ | 无 |
| 中断/恢复 | N/A | L4回补机制 |

**问题**:
1. L2层`except:`为bare except，应改为`except Exception:`
2. L1层AKShare调用无超时保护

---

### 2.3 ⚠️ JM_抓取焦煤进口量.py

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ✅ | 有Header |
| try-except | ⚠️ | 主逻辑`except:`为bare except |
| timeout | ✅ | L1有timeout=15 |
| 魔法数字 | ✅ | 无硬编码 |
| 类型注解 | ⚠️ | `main()`有注解，其他无 |
| 日志 | ⚠️ | 有print但无ERROR级别 |
| 输出路径 | ✅ | 写入DB |
| 硬编码中文文件名 | ✅ | 无 |

**严重问题**:
1. `fetch_from_customs_gov()`只请求页面，**未解析任何数据**，函数形同虚设
2. `fetch_from_stats()`为空函数，直接pass
3. 四层漏斗中L1/L2实际都返回None，整条链路无效
4. bare except需修复
5. **无合理值校验**

---

### 2.4 ⚠️ JM_计算焦煤期现基差.py

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ✅ | 有Header |
| try-except | ✅ | 各函数有try-except（非bare） |
| timeout | ✅ | AKShare无timeout但合理 |
| 魔法数字 | ✅ | 无硬编码 |
| 类型注解 | ❌ | 无类型注解 |
| 日志 | ✅ | 各分支有日志 |
| 输出路径 | ✅ | 写入DB |
| 硬编码中文文件名 | ✅ | 无 |

**问题**:
1. L1汾渭/L2 Mysteel打印信息后直接pass，无实际爬取逻辑
2. L3隆众TODO未实现
3. **无现货价时L4回补基差值而非现货价，逻辑有误**（基差=现货-期货，用历史基差回补没有意义）
4. 函数无类型注解

---

### 2.5 ⚠️ JM_计算焦煤月差.py

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ✅ | 有Header |
| try-except | ⚠️ | `fetch_contract_settle()`中有bare `except:` |
| timeout | ⚠️ | L1 AKShare无timeout；L2有timeout=10 |
| 魔法数字 | ✅ | 无硬编码 |
| 类型注解 | ⚠️ | `main()`有注解，其他无 |
| 日志 | ✅ | 日志完善 |
| 输出路径 | ✅ | 写入DB |
| 硬编码中文文件名 | ✅ | 无 |

**问题**:
1. `fetch_contract_settle()`中有bare `except: pass`，应加Exception类型
2. L1 AKShare无超时保护

---

### 2.6 ⚠️ JM_计算焦煤动力煤比价.py

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ✅ | 有Header |
| try-except | ⚠️ | `fetch_zc_price()`中有bare `except:` |
| timeout | ⚠️ | L1无timeout |
| 魔法数字 | ✅ | 无硬编码 |
| 类型注解 | ⚠️ | `main()`有注解，其他无 |
| 日志 | ✅ | 日志完善 |
| 输出路径 | ✅ | 写入DB |
| 硬编码中文文件名 | ✅ | 无 |

**问题**:
1. 动力煤L1无timeout
2. bare `except: pass`需修复

---

### 2.7 ⏸️ 14个付费stub脚本（统一问题）

以下脚本结构完全相同，均为L4 DB回补+手动输入stub：

| 脚本 | 因子代码 | 付费来源 |
|------|---------|---------|
| JM_三大口岸库存.py | JM_INV_THREE_PORTS | Mysteel |
| JM_澳煤进口盈亏.py | JM_COST_AU_PROFIT | 普氏 |
| JM_焦企产能利用率.py | JM_DEMAND_COKING_RATE | Mysteel |
| JM_焦化利润.py | JM_COST_COKING_PROFIT | Mysteel |
| JM_焦化厂炼焦煤库存.py | JM_INV_COKING_PLANT | Mysteel |
| JM_甘其毛都口岸库存.py | JM_INV_GQMD | 汾渭 |
| JM_甘其毛都通关车数.py | JM_SUPPLY_GQMD_CARS | 汾渭 |
| JM_矿山开工率.py | JM_SUPPLY_MINE_RATE | Mysteel |
| JM_精煤产量.py | JM_SUPPLY_WASHED_OUTPUT | 统计局 |
| JM_蒙煤口岸成本.py | JM_COST_MONGOLIA | 汾渭 |
| JM_蒙煤山西煤价差.py | JM_SPD_MG_SX | 汾渭 |
| JM_钢厂炼焦煤库存.py | JM_INV_STEEL_PLANT | Mysteel |
| JM_铁水产量.py | JM_DEMAND_HOT_METAL | Mysteel |
| JM_批次2_手动输入.py | 多个因子 | 混合付费 |

**共同问题**：

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ⚠️ | Header存在但"尝试过的数据源及结果"和"解决方案"均为"需补充" |
| try-except | ✅ | 无网络请求，无异常风险 |
| timeout | N/A | 无网络请求 |
| 魔法数字 | ✅ | 无硬编码 |
| 类型注解 | ❌ | `fetch_value()`均无类型注解 |
| 日志 | ⚠️ | 有print但无ERROR级别 |
| 输出路径 | ✅ | 写入DB |
| 硬编码中文文件名 | ✅ | 无 |

**评价**: stub状态合理，但Header需完善（补充尝试过的数据源、失败原因、解决方案）。

---

### 2.8 ✅ JM_批次2_手动输入.py

| 检查项 | 状态 | 备注 |
|--------|------|------|
| docstring | ⚠️ | 有Header，但"尝试过的数据源及结果"和"解决方案"均为"需补充" |
| try-except | ✅ | `try/except ValueError`非bare |
| timeout | N/A | 无网络请求 |
| 魔法数字 | ✅ | bounds定义在FACTORS常量中 |
| 类型注解 | ✅ | `main()`有类型注解 |
| 日志 | ✅ | 完善print日志 |
| 输出路径 | ✅ | 写入DB |
| 硬编码中文文件名 | ✅ | 无 |

**评价**: 逻辑完整，交互式录入+合理性校验+越界确认均已实现。

---

## 三、问题汇总

### 3.1 优先级P0（必须修复）

| # | 脚本 | 问题 | 影响 |
|---|------|------|------|
| 1 | JM_抓取焦煤进口量.py | `fetch_from_customs_gov()`只请求不解析，数据永远为None | 因子长期无数据 |
| 2 | JM_抓取焦煤期货持仓量.py | L2层bare except | 异常静默吞掉 |
| 3 | JM_计算焦煤月差.py | `fetch_contract_settle()`中bare except | 异常静默吞掉 |
| 4 | JM_计算焦煤动力煤比价.py | `fetch_zc_price()`中bare except | 异常静默吞掉 |

### 3.2 优先级P1（应修复）

| # | 脚本 | 问题 | 影响 |
|---|------|------|------|
| 5 | 多个脚本 | 函数无类型注解 | 可维护性差 |
| 6 | 14个stub脚本 | Header"尝试过的数据源及结果"和"解决方案"均未填写 | 不可追溯 |
| 7 | JM_计算焦煤期现基差.py | L1汾渭/L2 Mysteel打印信息后直接pass，无实际爬取 | 无免费现货价 |
| 8 | JM_计算焦煤期现基差.py | L4用历史基差回补而非真实现货价，逻辑有误 | 数据无物理意义 |

### 3.3 优先级P2（建议修复）

| # | 脚本 | 问题 | 影响 |
|---|------|------|------|
| 9 | JM_抓取焦煤期货持仓量.py | L1 AKShare无timeout | 网络卡死无保护 |
| 10 | JM_计算焦煤月差.py | L1 AKShare无timeout | 同上 |
| 11 | JM_计算焦煤动力煤比价.py | L1无timeout | 同上 |
| 12 | 所有脚本 | 日志为print而非logging模块 | 日志级别不分明 |

---

## 四、CSV输出说明

**发现**: JM脚本数据写入`pit_data.db`（`pit_factor_observations`表），**不输出CSV文件**到`D:\futures_v6\macro_engine\output\`。output目录中无JM相关CSV，说明JM的输出规范与output目录无关，而是直接写DB。这是符合设计的（db_utils.py的save_to_db直接写入DB）。

---

## 五、README.md 更新建议

当前README.md格式基本符合要求，建议补充以下内容：

1. **运行状态更新**: 标注JM_SPD_BASIS当前状态为⚠️（无现货价）
2. **因子表格补充**: 标注JM_IMPORT当前状态为⚠️（海关数据未解析）
3. **最后更新时间**: 改为2026-05-02

---

## 六、总体评价

| 维度 | 评分 | 说明 |
|------|------|------|
| 可运行性 | 8/10 | 4/5个自动化脚本可运行，1个(JM_SPD_BASIS)跳过合理 |
| 数据质量 | 6/10 | 仅3个因子有数据，JM_IMPORT链路不通 |
| 代码规范 | 6/10 | 多处bare except、无类型注解 |
| 付费stub | 7/10 | 结构一致，Header待完善 |
| 文档完整 | 5/10 | Header"需补充"项过多 |

**核心问题**: JM_IMPORT海关解析函数形同虚设，需实际实现；bare except需全部修复；JM_SPD_BASIS的L4回补逻辑有误（回补基差值而非现货价）。

---
_复查时间: 2026-05-02 | 复查人: mimo subagent_
