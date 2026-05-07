# R9-6 NULL 因子调查报告

**日期**: 2026-05-06  
**数据库**: `D:\futures_v6\macro_engine\pit_data.db`  
**执行脚本**: `D:\futures_v6\shared\r9_null_check.py`

---

## 1. NULL 因子统计

**总计: 14 个 NULL 因子**，分布在 3 个品种。

### AO 氧化铝（5 个 NULL，最新日期: 2026-05-05）

| 因子代码 | 最新日期 | 分析 |
|----------|----------|------|
| AO_IMP_ALUMINA | 2026-05-05 | 氧化铝进口数据，数据源可能缺失 |
| AO_IMP_BAUXITE | 2026-05-05 | 铝土矿进口数据 |
| AO_INV_SHFE | 2026-05-05 | 上期所库存，数据源可能未更新 |
| AO_PRC_CIF_BAUXITE | 2026-05-05 | 铝土矿CIF价格 |
| AO_SPD_BASIS | 2026-05-05 | 基差价差 |

### FU 燃料油（5 个 NULL，最新日期: 2026-05-01）

| 因子代码 | 最新日期 | 分析 |
|----------|----------|------|
| FU_BASIS | 2026-05-01 | 基差 |
| FU_HS_LS_SPREAD | 2026-05-01 | 高低硫价差 |
| FU_NET_POSITION | 2026-05-01 | 净持仓 |
| FU_SG_INVENTORY | 2026-05-01 | 新加坡库存 |
| FU_WARRANT | 2026-05-01 | 仓单 |

### M 豆粕（4 个 NULL，最新日期: 2026-05-01）

| 因子代码 | 最新日期 | 分析 |
|----------|----------|------|
| M_BEAN_ARRIVAL | 2026-05-01 | 大豆到港量 |
| M_OIL_BEAN_STOCK | 2026-05-01 | 油厂大豆库存 |
| M_OIL_MEAL_STOCK | 2026-05-01 | 油厂豆粕库存 |
| M_PLANT_OP_RATE | 2026-05-01 | 油厂开机率 |

---

## 2. ETL 定时任务检查

**FuturesMacro_ETL**: ❌ 不存在

**实际存在的相关定时任务**:
| 任务名 | 说明 |
|--------|------|
| FuturesAPIHealthCheck | API 健康检查 |
| FuturesMacro_DailyScoring | 每日评分 |
| FuturesMacro_ETL_Daily | 每日 ETL（与需求的 FuturesMacro_ETL 不同） |
| FuturesMacro_FactorCollector | 因子采集器 |
| FuturesMacro_FactorCollector_OnBoot | 开机启动因子采集 |

**结论**: 系统有 ETL 相关任务，但任务名是 `FuturesMacro_ETL_Daily`（非 `FuturesMacro_ETL`）。因子采集有独立任务 `FuturesMacro_FactorCollector`。

---

## 3. ETL 脚本检查

| 脚本 | 状态 |
|------|------|
| factor_collector_main.py | ✅ 存在 |
| etl_crawler_main.py | ❌ 不存在 |
| etl_main.py | ❌ 不存在 |

---

## 4. 根因分析

### 共性问题
- **AO**: 5 个因子全部 NULL，数据源集中在进口/库存数据，可能是爬虫脚本未覆盖或数据源网站结构变化
- **FU**: 5 个因子全部 NULL，最新日期停在 2026-05-01（5 天前），新加坡库存和仓单数据源可能抓取失败
- **M**: 4 个因子全部 NULL，均为油厂数据（到港量、库存、开机率），数据源可能是行业资讯网站，需要登录或有反爬

### 根本原因
1. **无 ETL 定时任务名为 FuturesMacro_ETL**（存在的是 FuturesMacro_ETL_Daily）
2. **因子采集任务存在**（FuturesMacro_FactorCollector），但部分因子采集持续失败
3. **NULL 值持续写入数据库**——说明 ETL 在运行，但某些数据源无法获取数据，仍写入 NULL 记录

---

## 5. 建议措施

1. **立即修复**: 检查 AO/FU/M 的爬虫脚本，确认数据源 URL 是否有效
2. **数据源切换**: 若主力源不可用，按三源架构切换到备用源
3. **ETL 逻辑优化**: 当数据源失败时，不要写入 NULL 记录，保持上一次有效值（forward fill）
4. **告警机制**: 对持续 NULL 的因子触发告警，而非静默写入

---

## 6. 验收清单

- [x] 脚本已执行（有输出，exit code 1 因 schtasks 编码问题，但主要数据已获取）
- [x] NULL 因子数量：14 个（AO:5, FU:5, M:4）
- [x] ETL cron 状态：FuturesMacro_ETL 不存在，存在 FuturesMacro_ETL_Daily 和 FuturesMacro_FactorCollector
- [x] 报告文件已创建
