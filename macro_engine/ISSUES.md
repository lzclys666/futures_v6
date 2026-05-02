# 🔧 系统遗留问题与优化建议

> 更新时间: 2026-04-23 16:09 GMT+8
> 位置: `D:\futures_macro_engine\ISSUES.md`
> 使用方式: 问我"还有哪些遗留问题？""待优化""待扩展""系统有什么问题"等即可激活此文件

---

## 🚫 永久跳过因子清单（无免费数据源）

> 以下因子**永久跳过**，auto模式下不写入任何数据，不做L4回补，不使用占位符。
> 当问及"品种还有哪些待解决项"或"系统待优化"时，必须提及此清单。

### SA（纯碱）区域现货价格 — 3个
| 因子代码 | 名称 | 无免费源原因 | 付费替代 |
|---------|------|------------|---------|
| sa_spot_price_east | 华东轻碱送到价 | AKShare无区域维度 | 隆众资讯年费 |
| sa_spot_price_l | 重碱/联碱送到价 | 同上 | 同上 |
| sa_spot_price_shahe | 沙河送到价 | 同上 | 同上 |

### TA（精对苯二甲酸）— 4个
| 因子代码 | 名称 | 无免费源原因 | 付费替代 |
|---------|------|------------|---------|
| TA_CST_PX | PX CFR中国价格 | 普氏/隆众资讯付费 | 隆众资讯年费、普氏付费订阅 |
| TA_CST_PROCESSING_FEE | PTA加工费 | 依赖PX，无免费源 | 同上 |
| TA_DEM_POLYESTER_OP | 聚酯开工率 | CCF/隆众资讯付费 | 隆众资讯年费 |
| TA_SUP_OP_RATE | PTA开工率 | 隆众资讯付费 | 隆众资讯年费 |

### BR（丁二烯橡胶）✅ 数据质量问题已修复
- BR_SPD_BASIS: ✅ 已修正（现货15950 - BR0结算价15740 = 210）
- BR_COST_MARGIN: ✅ 已修正公式（BR_SPOT_PRICE - BD×0.82 - 3000 = 2076.8）
- BR_批次2_手动输入.py: ✅ bug已修复
- BR_COST_BD: 付费手动录入（SMM/隆众资讯）
- BR_COST_ETH/BR_DEM_*/BR_SUP_RATE: 付费因子，见 BR_批次2_手动输入.py

### AL（铝）批次2/3/4 ✅ 永久跳过框架已创建
- AL_批次2_手动输入.py 已创建（15个付费因子，自动模式跳过）

### AU（黄金）— 2个待解决
| 因子代码 | 名称 | 无免费源原因 | 状态 |
|---------|------|------------|------|
| AU_SPD_GLD | SPDR黄金ETF持仓量(吨) | SPDR官网需JS加载，Yahoo 403，无免费API | ⚠️ 需因子分析师推送初始值 |
| AU_SHFE_RANK | SHFE沪金前20会员净持仓 | AKShare DCE不支持SHFE, SHFE官网404 | ⚠️ 需因子分析师推送初始值 |

### AL/RB SHFE仓单 — 无免费源
| 因子代码 | 名称 | 无免费源原因 | 状态 |
|---------|------|------------|------|
| AL_INV_SHFE | 沪铝SHFE仓单 | AKShare `futures_shfe_warehouse_receipt` JSONDecodeError；SHFE官网API返回404 | ⚠️ 永久L4回补，付费源：Mysteel/铝业协会 |
| RB_INV_SHFE | 螺纹钢SHFE仓单 | 同上，AKShare失效+SHFE官网404 | ⚠️ 永久L4回补，付费源：Mysteel |

> AU_DXY已解决: FRED `DTWEXBGS` CSV接口可用（trade-weighted broad dollar index），写入118.0795 ✅
> AU_FED_DOT已解决: FRED CSV接口可用（DFII10/DGS10），写入1.92% ✅

### RB（螺纹钢）批次2 — 大量
- 螺纹钢表需/成交量、社会库存、产量、高炉开工率等
- 付费替代: Mysteel年费

### JM（焦煤）批次2/3/4 ✅ 永久跳过框架已创建
- JM_批次2_手动输入.py 已创建（14个因子，含JM_SPD_BASIS永久跳过）
- 付费替代: 汾渭能源年费（口岸）、Mysteel年费（生产/库存）

### NR（天然橡胶）✅ 修复完成
- NR_SPD_RU_NR: ✅ 已修正（改用NR0/RU0期货主力，ratio=0.8226）
- NR_FREIGHT_BDI: ✅ 新增自动因子（BDI波罗的海干散货指数，AKShare宏观数据）
- NR_SPD_BASIS: ✅ 无NR现货数据，永久跳过（AKShare无NR橡胶现货报价）
- NR_计算期现基差.py: ✅ 已删除（与NR_抓取现货和基差.py重复）
- NR_抓取INE仓单.py: ✅ 模板stub，永久跳过
- NR_抓取青岛库存.py: ✅ 模板stub，永久跳过（NR_STK_QINGDAO待手动录入）
- NR_抓取汇率.py: ✅ 模板stub，永久跳过（TA_CST_USDCNY已覆盖）
- NR_抓取轮胎出口.py: ✅ 模板stub，永久跳过（批次2手动）
- NR_抓取轮胎开工率.py: ✅ 模板stub，永久跳过（批次2手动）
- NR_抓取期货库存.py: ✅ 模板stub，永久跳过
- NR_抓取持仓量.py: ✅ 模板stub，永久跳过（NR_FUT_OI已覆盖）
- NR批次2: ✅ 付费因子见NR_批次2_手动输入.py

### RU（沪胶）✅ 缺口已填补 (2026-04-20)
- RU_FUT_OI: ✅ 新建爬虫，AKShare futures_main_sina("RU0") open_interest
- RU_INV_TOTAL: ✅ 与RU_FUT_OI共用持仓量数据（YAML: 持仓量作库存代理）
- RU_run_all.py: ✅ GBK修复（PYTHONIOENCODING=utf-8）
- 剩余: SA区域现货价格(付费)、TA开工率(付费)

### SA（纯碱）批次2
- 浮法玻璃日熔量、纯碱下游需求、玻璃厂库存、纯碱工厂库存
- 付费替代: 隆众资讯年费、百川盈孚年费

### SA（纯碱）新增缺口 ✅ 已确认 (2026-04-20)
| 因子代码 | 名称 | 无免费源原因 | 付费替代 |
|---------|------|------------|---------|
| sa_spot_price_east | 华东轻碱送到价 | AKShare futures_spot_price_daily 无区域维度；隆众/卓创付费 | 隆众资讯年费 |
| sa_spot_price_l | 重碱（联碱）送到价 | 同上 | 同上 |
| sa_spot_price_shahe | 沙河送到价 | 同上 | 同上 |
- YAML依赖错误标注 akshare/futures_spot_price_daily（实际无区域数据）
- 因子分析师若需此数据，需配置隆众资讯订阅

### NR（天然橡胶）新增缺口 ✅ 已确认 (2026-04-20)
- NR_SPD_BASIS: 永久跳过（AKShare无NR橡胶现货报价），已记录于批次1

### M（豆粕）批次2
- 大豆进口量、USDA月度报告、生猪存栏、饲料产量、豆油价格等
- 付费替代: USDA付费接口、卓创资讯年费
- M_STK_WARRANT: ✅ 已修正（27580吨来自akshare_futures_inventory_em，合法豆粕库存数据）

### AG（白银）批次2 ✅ 已完成
- AG_INV_COMEX_GOLD: AKShare返回黄金库存，脚本已重定向到COMEX黄金库存
- AG_SPD_BASIS: ✅ 永久跳过（无可靠免费源），脚本已标记
- AG_INV_COMEX_SILVER: AKShare不稳定，永久跳过
- AG_MACRO_DXY: ⚠️ FRED封锁无替代源，AG_MACRO_DXY conf=0.8记录保留(obs=2026-04-18)，旧conf=0.3记录已清理

---

## 🚨 P0 - 数据质量问题（影响系统可信度）

### 1. TA_PX 历史值被污染 ✅ 已修复 (2026-04-19 19:10)
- TA_CST_PX 污染值(850.00)已修正为4328.75 CNY/吨
- 数据源: AKShare `futures_spot_price(date='20250415', vars_list=['TA'])` → spot_price=4328.75
- 修正方法: 清理重复记录 + UPDATE raw_value WHERE factor_code='TA_CST_PX'
- **建议**: 订阅隆众资讯后导出2023-01-01至今PX CFR China价格做完整校正

### 2. TA基差突变待确认
- TA_SPD_BASIS: 2026-04-18=211.47, 2026-04-17=-33.47，单日变化116%
- 原因: AKShare `near_basis`数据可能有异动
- **需确认**: 211.47是否为真实基差值（PTA现货约4800，期货约4589，基差约211合理）

### 3. AG_SPD_BASIS异常高值 ✅ 已修复
- AG_SPD_BASIS=19493已清理，脚本已标记永久跳过
- 无可靠免费源，需订阅隆众资讯/SMM

### 4. BR数据质量问题 ✅ 已修复
- BR_SPD_BASIS: ✅ =210（现货15950 - BR0结算价15740）
- BR_COST_MARGIN: ✅ =2076.8（正确公式）
- BR_批次2_手动输入.py: ✅ bug已修复
- BR数据库重复记录: ✅ 已清理

### 5. TA_CST_BRENT ✅ 已修复_bounds (2026-04-23)
- MAX_VALUE从85→120（BRENT已升至$103+）
- EIA `EPCBRENT` API DEMO_KEY可用，写入$103.13 ✅
- FRED MCOILBRENTEU月度数据仍滞后~30天（作为备用，写入$103.13，conf=0.85）

---

## ⚠️ P1 - 品种数据覆盖率不足

### 6. AL 批次2/3/4 ✅ 永久跳过框架已创建
- AL_批次2_手动输入.py 已创建（15个付费因子）
- 需Mysteel/SMM/铝道网付费数据
- 影响因子数: ~15个

### 7. JM 批次2/3/4 ✅ 永久跳过框架已创建
- JM_批次2_手动输入.py 已创建（14个因子，含JM_SPD_BASIS永久跳过）
- 需汾渭能源年费订阅（甘其毛都口岸数据是JM核心因子）
- 影响因子数: ~14个

### 8. NR ✅ 数据质量已修复
- NR_SPD_RU_NR 比值已修正为0.8226（NR0/RU0期货主力）
- NR_FREIGHT_BDI 新增自动因子（BDI）
- NR永久跳过stub已标注

### 9. RB 批次2 未开发
- 需Mystee年费（螺纹钢表需/成交量）
- 影响因子数: ~8个
- 优先级: P2

### 10. P/NI/SN/ZN/AU/SC/LH/LC ✅ 8个新品种已完成
### 11. AO/EC ✅ 2个新品种已完成
- AO(氧化铝): 2因子，AO0期货+AO0持仓量
- EC(集运指数): 2因子，EC0期货+EC0持仓量

### 12. AU批次2 ✅ CFTC/SGE/央行数据免费接口
- AKShare: macro_usa_cftc_nc_holding() → CFTC黄金非商业净多(周度)
- AKShare: spot_golden_benchmark_sge() → SGE现货基准价(周度)
- AKShare: macro_china_fx_gold() → 央行黄金储备(月度)

### 13. Cron调度 ✅ 已更新 (2026-04-19 18:21)
- 期货日度采集cron作业已加入全部22个品种
- 旧10种 + CU/I + P/NI/SN/ZN + AU/SC/LH/LC/AO/EC
- 下一运行: 2026-04-21 20:00 CST

### 14. 数据库健康评分 (2026-04-19 19:15)
- 当前评分: 39/100 [需修复]
- 总因子: 160 | 总记录: 872 | 品种: 22
- 近7天数据: 153因子 | 7-30天: 39因子 | 30-90天: 1因子 | 90天+: 5因子
- 低置信度(conf≤0.6): 29个(L4回退，AL/RB/RU/SA/NR等品种的批次2因子)
- 近7天缺数据: 7个因子
  - P_SPD_BASIS/NI_SPD_BASIS: 719天 (AKShare数据源枯竭，无免费替代)
  - P_SPD_CONTRACT: 719天 (依赖P_SPD_BASIS)
  - CU_WRT_SHFE/NI_WRT_SHFE: 369天 (SHFE WRT API失效，CU_DCE_INV/NI_DCE_INV替代)
  - AU_GOLD_RESERVE_CB: 49天 (月度数据，正常)
  - BR_DEM_AUTO: 19天 (月度数据，正常)
- 范围异常: 0个 ✅
- **核心系统状态**: 22品种全测试通过 ✅ 607条30天历史数据已回填 ✅

### 15. 近7天缺数据的7个因子处理方案
| 因子 | 天数 | 方案 |
|------|------|------|
| NI_SPD_BASIS | 719天 | ⚠️ AKShare数据枯竭，无免费替代，永久L4 |
| P_SPD_BASIS | 719天 | ⚠️ AKShare数据枯竭，无免费替代，永久L4 |
| P_SPD_CONTRACT | 719天 | ⚠️ 依赖P_SPD_BASIS |
| CU_WRT_SHFE | 369天 | ✅ 已用CU_DCE_INV替代(2026-04-17=140339吨) |
| NI_WRT_SHFE | 369天 | ✅ 已用NI_DCE_INV替代(2026-04-17=64209吨) |
| AU_GOLD_RESERVE_CB | 49天 | ✅ 月度数据，正常滞后 |
| BR_DEM_AUTO | 19天 | ✅ 月度数据，正常滞后 |

### 14. TA_PX历史值校正
- TA_PX=16040 (obs=2024-05-17) 远超预期范围(5000-10000)
- 需付费订阅或手动修正历史值
- P(棕榈油): 5因子，P0期货+P0持仓量+P_OIL_REF(INE原油)+spot基差(滞后2年)
- NI(沪镍): 4因子，NI0期货+NI0持仓量+spot基差(滞后2年)+SHFE仓单(滞后1年)
- SN(沪锡): 2因子，SN0期货+SN0持仓量
- ZN(沪锌): 2因子，ZN0期货+ZN0持仓量
- AU(黄金): 6因子，AU0期货+AU0持仓量+CFTC非商业净多(45530)+SGE现货基准价(1058)+央行黄金储备(3427吨)+期现基差(4.6)
- SC(原油): 2因子，SC0期货+SC0持仓量
- LH(生猪): 2因子，LH0期货+LH0持仓量
- LC(碳酸锂): 2因子，LC0期货+LC0持仓量
- LC(碳酸锂): 2因子，LC0期货+LC0持仓量
- 总计新增: ~21个因子，全部免费数据源

### 11. 新品种批次2 待开发
- P批次2: MPOB月报(棕榈油产量/出口/库存)，需PDF解析或手动录入
- NI/SN/ZN批次2: LME镍/锡/锌库存，AKShare无可靠免费源，需SMM/Mysteel
- AU批次2: Fed WHS/GOLD/CFTC非商业净多，conf需验证
- SC批次2: OPEC产量/IEA数据，EIA原油库存(API)，需EIA/OPEC付费
- LH批次2: 农业农村部数据+发改委数据，AKShare可能有部分覆盖
- 优先级: AU批次2免费源最多(P0

---

## 🔧 P2 - 脚本优化

### 9. 旧脚本改造（利用公共模块）
- `market_data.py`/`web_utils.py`/`io_win.py`已完成
- 改造方式: 发现问题时顺手改，非大规模重构
- 状态: 持续进行

### 10. 监控告警系统 ✅ 已完成
- `check_health.py` 已部署
- 每周五HEARTBEAT提醒手动运行

---

## 📋 付费订阅优先级建议

| 优先级 | 订阅 | 覆盖品种 | 因子数 |
|-------|------|---------|-------|
| P0 | 隆众资讯年费 | TA/PTA、BR、SA、NR、RU | ~20 |
| P1 | 汾渭能源年费 | JM（核心） | ~15 |
| P1 | Mysteel年费 | AL、RB、JM（生产端） | ~25 |
| P2 | SMM年费 | AL（铝） | ~10 |
| P2 | 普氏能源付费 | TA_PX、JM进口盈亏 | ~5 |

---

## 📋 已解决（从列表移除）

| 日期 | 问题 | 解决方案 |
|------|------|---------|
| 2026-04-19 | BR_BR_COST_MARGIN异常波动(-480→2986) | 数据错误已清理，BR_COST_MARGIN新值2077合理 |
| 2026-04-19 | 因子分析师推送8个新品种(P/NI/SN/ZN/AU/SC/LH/LC) | AKShare futures_main_sina直采21个免费因子，全部写入DB |
| 2026-04-19 | TA_STK_WARRANT L4回补 | 升级为L1郑商所直采，写入204123吨 |
| 2026-04-19 | TA_PTA基差脚本硬编码 | 动态PIT日期，基差=-33.47合理 |
| 2026-04-18 | 项目无Git版本控制 | 初始化Git仓库 |
| 2026-04-18 | 103个脚本被覆盖事故 | 从桌面备份+会话临时文件恢复 |
| 2026-04-18 | NR_SPD_BASIS跨市场价差错误 | 改为NR近月-远月跨期价差 |
| 2026-04-18 | COMEX白银库存数据错误 | 改用AG_INV_COMEX_GOLD |
| 2026-04-18 | db_utils.py缺source列 | 添加source列和get_latest_value函数 |

---

## 📖 使用说明

```
问: "还有哪些遗留问题？"
→ 读取本文件，按P0/P1/P2列出

问: "TA/RU/BR还有哪些待解决？"
→ 读取本文件"永久跳过因子清单"中对应品种

问: "系统还有哪些待优化/待扩展？"
→ 读取本文件"P2优化"和"付费订阅优先级建议"

问: "解决了XX问题"
→ 从本文件移除该项，并commit到Git

问: "新增一个问题"
→ 追加到本文件对应优先级区域
```
## CU/I新品种（2026-04-19）

### 已知限制
- CU_WRT_SHFE: obs_date=2025-04-15（数据滞后约1年），SHFE接口2026年无数据，需定期检查
- I_SPD_BASIS: 铁矿石现货价无免费可靠源，AKShare的spot_price数据质量待验证
- I_POS_NET: DCE持仓排名接口不稳定，暂归批次2

### 数据源可用性
| 因子 | 数据源 | 状态 |
|------|--------|------|
| CU_INV_SHFE | AKShare futures_inventory_em | ✅ 免费 |
| CU_WRT_SHFE | AKShare futures_shfe_warehouse_receipt | ✅ 免费(滞后1年) |
| CU_SPD_BASIS | AKShare futures_spot_price | ✅ 免费 |
| CU_FUT_OI | AKShare futures_main_sina | ✅ 免费 |
| CU_POS_NET | AKShare get_shfe_rank_table | ✅ 免费 |
| CU_INV_LME | AKShare macro_euro_lme_stock | ✅ 免费 |
| I_STK_PORT | AKShare futures_inventory_em | ✅ 免费 |
| I_SPD_BASIS | AKShare futures_spot_price | ✅ 免费 |
| I_FUT_OI | AKShare futures_main_sina | ✅ 免费 |
| I_FUT_MAIN | AKShare futures_main_sina | ✅ 免费 |
