# 因子数据就绪审计报告

> **生成时间**: 2026-04-27 12:13  
> **审计范围**: 22品种 × 配置因子  
> **数据路径**: `D:\futures_v6\macro_engine\data\crawlers`  

---

## 一、总体统计

| 指标 | 数值 | 占比 |
|------|------|------|
| **总因子数** | 293 | 100% |
| **数据完整 (OK)** | 195 | 66.6% |
| **数据缺失 (MISSING_DATA)** | 91 | 31.1% |
| **数据不足 (INSUFFICIENT_DATA)** | 2 | 0.7% |
| **缺失率高 (HIGH_MISSING)** | 5 | 1.7% |
| **无配置 (NO_CONFIG)** | 0 | 0.0% |
| **配置错误 (CONFIG_ERROR)** | 0 | 0.0% |

**核心因子完整度**: 66.6%  
**目标**: ≥ 70%  
**状态**: ❌ 未达标

---

## 二、分品种完整度

| 品种 | 配置因子数 | 数据完整数 | 完整度 |
|------|-----------|-----------|--------|
| AG | 12.0 | 12.0 | ✅ 100.0% |
| AL | 8.0 | 8.0 | ✅ 100.0% |
| AO | 3.0 | 3.0 | ✅ 100.0% |
| AU | 11.0 | 11.0 | ✅ 100.0% |
| BR | 12.0 | 12.0 | ✅ 100.0% |
| CU | 11.0 | 11.0 | ✅ 100.0% |
| EC | 2.0 | 2.0 | ✅ 100.0% |
| I | 5.0 | 5.0 | ✅ 100.0% |
| NR | 18.0 | 18.0 | ✅ 100.0% |
| NI | 8.0 | 8.0 | ✅ 100.0% |
| M | 12.0 | 12.0 | ✅ 100.0% |
| LH | 2.0 | 2.0 | ✅ 100.0% |
| LC | 2.0 | 2.0 | ✅ 100.0% |
| SN | 3.0 | 3.0 | ✅ 100.0% |
| RU | 12.0 | 12.0 | ✅ 100.0% |
| SA | 18.0 | 18.0 | ✅ 100.0% |
| SC | 2.0 | 2.0 | ✅ 100.0% |
| ZN | 3.0 | 3.0 | ✅ 100.0% |
| P | 6.0 | 6.0 | ✅ 100.0% |
| PB | 17.0 | 17.0 | ✅ 100.0% |
| RB | 7.0 | 7.0 | ✅ 100.0% |
| TA | 10.0 | 10.0 | ✅ 100.0% |
| JM | 18.0 | 11.0 | 🟡 61.1% |
| BU | 15.0 | 0.0 | ❌ 0.0% |
| EG | 10.0 | 0.0 | ❌ 0.0% |
| J | 17.0 | 0.0 | ❌ 0.0% |
| HC | 18.0 | 0.0 | ❌ 0.0% |
| PP | 15.0 | 0.0 | ❌ 0.0% |
| Y | 16.0 | 0.0 | ❌ 0.0% |

---

## 三、数据缺失详情

### 3.1 数据文件缺失的因子

| 品种 | 因子代码 | 因子名称 | 期望数据文件 |
|------|---------|---------|------------|
| BU | BU_BU_FUT_CLOSE | 沥青期货收盘价 | daily/BU_fut_close.csv |
| BU | BU_BU_FX_USDCNY | 美元兑人民币汇率 | 未映射 |
| BU | BU_BU_MACRO_CCI | 消费者信心指数 | 未映射 |
| BU | BU_BU_MACRO_HIGHWAY | 全国高速公路整车流量 | 未映射 |
| BU | BU_BU_POS_NET | 沥青期货净持仓 | 未映射 |
| BU | BU_BU_SPD_BASIS | 沥青期现基差 | daily/BU_fut_close.csv |
| BU | BU_BU_SPD_BU_BRENT | 沥青与布伦特原油价差 | 未映射 |
| BU | BU_BU_SPT_EAST_CHINA | 华东沥青市场价格 | 未映射 |
| BU | BU_BU_STK_INVENTORY | 全国沥青总库存 | 未映射 |
| BU | BU_BU_STK_PETROCHEM | 石化企业沥青库存 | 未映射 |
| BU | BU_BU_STK_PORT | 港口沥青库存 | 未映射 |
| BU | BU_BU_STK_REFINERY | 炼厂沥青库存 | 未映射 |
| BU | BU_BU_STK_REFINE_RATE | 炼厂沥青开工率 | 未映射 |
| BU | BU_BU_STK_SOCIAL | 沥青社会库存 | 未映射 |
| BU | BU_BU_STK_WARRANT | 沥青期货仓单 | 未映射 |
| EG | EG_EG_POS_NET | 乙二醇期货净持仓 | 未映射 |
| EG | EG_EG_SPD_BASIS | 乙二醇期现基差 | daily/EG_fut_close.csv |
| EG | EG_EG_SPT_NAPTHA | 石脑油裂解价差 | 未映射 |
| EG | EG_EG_STK_COAL_RATE | 煤制乙二醇开工率 | 未映射 |
| EG | EG_EG_STK_PLANT_RATE | 乙二醇装置开工率 | 未映射 |
| EG | EG_EG_STK_POLYESTER | 聚酯企业乙二醇库存 | 未映射 |
| EG | EG_EG_STK_PORT | 华东乙二醇港口库存 | 未映射 |
| EG | EG_FUT_CLOSE | EG乙二醇期货收盘价 | daily/EG_fut_close.csv |
| EG | EG_FUT_OI | EG乙二醇期货持仓量 | daily/EG_fut_close.csv |
| EG | EG_STK_WARRANT | EG乙二醇工厂库存 | 未映射 |
| HC | HC_FUT_CLOSE | HC热轧卷板期货收盘价 | daily/HC_fut_close.csv |
| HC | HC_FUT_OI | HC热轧卷板期货持仓量 | daily/HC_fut_close.csv |
| HC | HC_HC_MACRO_AUTO_OUTPUT | 汽车产量 | 未映射 |
| HC | HC_HC_MACRO_PMI_MFG | 制造业PMI | 未映射 |
| HC | HC_HC_POS_NET | 热卷期货净持仓 | 未映射 |
| HC | HC_HC_PROD_CAPACITY | 热卷产能利用率 | 未映射 |
| HC | HC_HC_PROD_OUTPUT | 热卷产量 | 未映射 |
| HC | HC_HC_SPD_BASIS | 热卷期现基差 | daily/HC_fut_close.csv |
| HC | HC_HC_SPD_HC_CC | 热卷期货合约间价差 | 未映射 |
| HC | HC_HC_SPD_HC_RB | 热卷-螺纹钢跨品种价差 | 未映射 |
| HC | HC_HC_SPD_NEAR_FAR | 热卷期货近远月价差 | 未映射 |
| HC | HC_HC_SPT_MYSTEEEL | 我的钢铁网热卷现货价格 | 未映射 |
| HC | HC_HC_STK_INVENTORY | 热卷社会库存 | 未映射 |
| HC | HC_HC_STK_OUTPUT_WEEKLY | 钢厂热卷库存周度 | 未映射 |
| HC | HC_HC_STK_PLANT | 钢厂热卷库存 | 未映射 |
| HC | HC_HC_STK_SOCIAL | 热卷社会库存总量 | 未映射 |
| HC | HC_HC_STK_TRADE | 贸易商热卷库存 | 未映射 |
| HC | HC_HC_STK_WARRANT | 热卷仓单库存 | 未映射 |
| J | J_J_FOB_EXPORT | 焦炭出口FOB价 | 未映射 |
| J | J_J_POS_NET | 焦炭期货净持仓 | 未映射 |
| J | J_J_PROD_OUTPUT | 焦炭产量 | 未映射 |
| J | J_J_SPD_BASIS | 焦炭期现基差 | daily/J_fut_close.csv |
| J | J_J_SPD_J_JM | 焦炭与焦煤价差 | 未映射 |
| J | J_J_SPD_NEAR_FAR | 焦炭期货近远月价差 | 未映射 |
| J | J_J_SPT_CCI | CCI焦炭价格指数 | 未映射 |
| J | J_J_SPT_MYSTEEEL | 我的钢铁网焦炭现货价格 | 未映射 |
| J | J_J_STK_COKE_RATE | 焦化企业开工率 | 未映射 |
| J | J_J_STK_MINE | 煤矿焦煤库存 | 未映射 |
| J | J_J_STK_PORT | 港口焦炭库存 | 未映射 |
| J | J_J_STK_SEPARATE | 独立焦企焦炭库存 | 未映射 |
| J | J_J_STK_STEEL_DAYS | 钢厂焦炭可用天数 | 未映射 |
| J | J_J_STK_TOTAL | 焦炭社会总库存 | 未映射 |
| J | J_J_STK_TRADE | 贸易商焦炭库存 | 未映射 |
| J | J_J_STK_WARRANT | 焦炭期货仓单 | 未映射 |
| J | J_J_TOT_DISPATCH | 焦炭总调出量 | 未映射 |
| PP | PP_FUT_CLOSE | PP聚丙烯期货收盘价 | daily/PP_fut_close.csv |
| PP | PP_FUT_OI | PP聚丙烯期货持仓量 | daily/PP_fut_close.csv |
| PP | PP_PP_POS_NET | 聚丙烯期货净持仓 | 未映射 |
| PP | PP_PP_PROD_OUTPUT | 聚丙烯产量 | 未映射 |
| PP | PP_PP_SPD_BASIS | 聚丙烯期现基差 | daily/PP_fut_close.csv |
| PP | PP_PP_SPD_LAM_Copoly | 拉丝-共聚价差 | 未映射 |
| PP | PP_PP_SPD_LLDPE_PP | 线型低密度聚乙烯-聚丙烯价差 | 未映射 |
| PP | PP_PP_SPT_CFR_CHINA | CFR中国丙烯到岸价格 | 未映射 |
| PP | PP_PP_STK_BAG_RATE | 聚丙烯袋装比例 | 未映射 |
| PP | PP_PP_STK_INVENTORY | 聚丙烯社会库存 | 未映射 |
| PP | PP_PP_STK_PLANT | 聚丙烯石化库存 | 未映射 |
| PP | PP_PP_STK_PLANT_RATE | 聚丙烯装置开工率 | 未映射 |
| PP | PP_PP_STK_POLYMER | 高分子库存 | 未映射 |
| PP | PP_PP_STK_PORT | 聚丙烯港口库存 | 未映射 |
| PP | PP_PP_STK_WARRANT | 聚丙烯仓单库存 | 未映射 |
| Y | Y_FUT_CLOSE | Y棕榈油期货收盘价 | daily/Y_fut_close.csv |
| Y | Y_FUT_OI | Y棕榈油期货持仓量 | daily/Y_fut_close.csv |
| Y | Y_Y_COST_CNF | 进口大豆CNF价 | 未映射 |
| Y | Y_Y_FUT_CBOT_OIL | CBOT豆油期货收盘价 | 未映射 |
| Y | Y_Y_FUT_CBOT_SOY | CBOT大豆期货收盘价 | 未映射 |
| Y | Y_Y_FUT_CBOT_SOY_MEAL | CBOT豆粕主力合约 | 未映射 |
| Y | Y_Y_FUT_CBOT_SOY_OIL | CBOT豆油主力合约 | 未映射 |
| Y | Y_Y_INV_LAND | 进口大豆港口库存 | 未映射 |
| Y | Y_Y_INV_MALAYS | 马来西亚棕榈油库存 | 未映射 |
| Y | Y_Y_INV_PACIFIC | 太平洋大豆到港量 | 未映射 |
| Y | Y_Y_POS_NET | 豆油期货净持仓 | 未映射 |
| Y | Y_Y_SPD_BASIS | 豆油期现基差 | daily/Y_fut_close.csv |
| Y | Y_Y_SPD_PALM_OIL | 豆油与棕榈油价差 | 未映射 |
| Y | Y_Y_STK_COMMERCIAL | 豆油商业库存 | 未映射 |
| Y | Y_Y_STK_INVENTORY | 豆油商业库存 | 未映射 |
| Y | Y_Y_STK_WARRANT | 豆油期货仓单 | 未映射 |

### 3.2 数据量不足的因子

| 品种 | 因子代码 | 数据行数 | 日期范围 |
|------|---------|---------|---------|
| JM | JM_INV_GQMD | 1 | N/A |
| JM | JM_SUPPLY_GQMD_CARS | 1 | N/A |

---

## 四、数据文件映射待确认

以下因子尚未建立数据文件映射关系，需要人工确认：

| 品种 | 因子代码 | 因子名称 |
|------|---------|---------|
| BU | BU_BU_FX_USDCNY | 美元兑人民币汇率 |
| BU | BU_BU_MACRO_CCI | 消费者信心指数 |
| BU | BU_BU_MACRO_HIGHWAY | 全国高速公路整车流量 |
| BU | BU_BU_POS_NET | 沥青期货净持仓 |
| BU | BU_BU_SPD_BU_BRENT | 沥青与布伦特原油价差 |
| BU | BU_BU_SPT_EAST_CHINA | 华东沥青市场价格 |
| BU | BU_BU_STK_INVENTORY | 全国沥青总库存 |
| BU | BU_BU_STK_PETROCHEM | 石化企业沥青库存 |
| BU | BU_BU_STK_PORT | 港口沥青库存 |
| BU | BU_BU_STK_REFINERY | 炼厂沥青库存 |
| BU | BU_BU_STK_REFINE_RATE | 炼厂沥青开工率 |
| BU | BU_BU_STK_SOCIAL | 沥青社会库存 |
| BU | BU_BU_STK_WARRANT | 沥青期货仓单 |
| EG | EG_EG_POS_NET | 乙二醇期货净持仓 |
| EG | EG_EG_SPT_NAPTHA | 石脑油裂解价差 |
| EG | EG_EG_STK_COAL_RATE | 煤制乙二醇开工率 |
| EG | EG_EG_STK_PLANT_RATE | 乙二醇装置开工率 |
| EG | EG_EG_STK_POLYESTER | 聚酯企业乙二醇库存 |
| EG | EG_EG_STK_PORT | 华东乙二醇港口库存 |
| EG | EG_STK_WARRANT | EG乙二醇工厂库存 |
| HC | HC_HC_MACRO_AUTO_OUTPUT | 汽车产量 |
| HC | HC_HC_MACRO_PMI_MFG | 制造业PMI |
| HC | HC_HC_POS_NET | 热卷期货净持仓 |
| HC | HC_HC_PROD_CAPACITY | 热卷产能利用率 |
| HC | HC_HC_PROD_OUTPUT | 热卷产量 |
| HC | HC_HC_SPD_HC_CC | 热卷期货合约间价差 |
| HC | HC_HC_SPD_HC_RB | 热卷-螺纹钢跨品种价差 |
| HC | HC_HC_SPD_NEAR_FAR | 热卷期货近远月价差 |
| HC | HC_HC_SPT_MYSTEEEL | 我的钢铁网热卷现货价格 |
| HC | HC_HC_STK_INVENTORY | 热卷社会库存 |
| HC | HC_HC_STK_OUTPUT_WEEKLY | 钢厂热卷库存周度 |
| HC | HC_HC_STK_PLANT | 钢厂热卷库存 |
| HC | HC_HC_STK_SOCIAL | 热卷社会库存总量 |
| HC | HC_HC_STK_TRADE | 贸易商热卷库存 |
| HC | HC_HC_STK_WARRANT | 热卷仓单库存 |
| J | J_J_FOB_EXPORT | 焦炭出口FOB价 |
| J | J_J_POS_NET | 焦炭期货净持仓 |
| J | J_J_PROD_OUTPUT | 焦炭产量 |
| J | J_J_SPD_J_JM | 焦炭与焦煤价差 |
| J | J_J_SPD_NEAR_FAR | 焦炭期货近远月价差 |
| J | J_J_SPT_CCI | CCI焦炭价格指数 |
| J | J_J_SPT_MYSTEEEL | 我的钢铁网焦炭现货价格 |
| J | J_J_STK_COKE_RATE | 焦化企业开工率 |
| J | J_J_STK_MINE | 煤矿焦煤库存 |
| J | J_J_STK_PORT | 港口焦炭库存 |
| J | J_J_STK_SEPARATE | 独立焦企焦炭库存 |
| J | J_J_STK_STEEL_DAYS | 钢厂焦炭可用天数 |
| J | J_J_STK_TOTAL | 焦炭社会总库存 |
| J | J_J_STK_TRADE | 贸易商焦炭库存 |
| J | J_J_STK_WARRANT | 焦炭期货仓单 |
| J | J_J_TOT_DISPATCH | 焦炭总调出量 |
| PP | PP_PP_POS_NET | 聚丙烯期货净持仓 |
| PP | PP_PP_PROD_OUTPUT | 聚丙烯产量 |
| PP | PP_PP_SPD_LAM_Copoly | 拉丝-共聚价差 |
| PP | PP_PP_SPD_LLDPE_PP | 线型低密度聚乙烯-聚丙烯价差 |
| PP | PP_PP_SPT_CFR_CHINA | CFR中国丙烯到岸价格 |
| PP | PP_PP_STK_BAG_RATE | 聚丙烯袋装比例 |
| PP | PP_PP_STK_INVENTORY | 聚丙烯社会库存 |
| PP | PP_PP_STK_PLANT | 聚丙烯石化库存 |
| PP | PP_PP_STK_PLANT_RATE | 聚丙烯装置开工率 |
| PP | PP_PP_STK_POLYMER | 高分子库存 |
| PP | PP_PP_STK_PORT | 聚丙烯港口库存 |
| PP | PP_PP_STK_WARRANT | 聚丙烯仓单库存 |
| Y | Y_Y_COST_CNF | 进口大豆CNF价 |
| Y | Y_Y_FUT_CBOT_OIL | CBOT豆油期货收盘价 |
| Y | Y_Y_FUT_CBOT_SOY | CBOT大豆期货收盘价 |
| Y | Y_Y_FUT_CBOT_SOY_MEAL | CBOT豆粕主力合约 |
| Y | Y_Y_FUT_CBOT_SOY_OIL | CBOT豆油主力合约 |
| Y | Y_Y_INV_LAND | 进口大豆港口库存 |
| Y | Y_Y_INV_MALAYS | 马来西亚棕榈油库存 |
| Y | Y_Y_INV_PACIFIC | 太平洋大豆到港量 |
| Y | Y_Y_POS_NET | 豆油期货净持仓 |
| Y | Y_Y_SPD_PALM_OIL | 豆油与棕榈油价差 |
| Y | Y_Y_STK_COMMERCIAL | 豆油商业库存 |
| Y | Y_Y_STK_INVENTORY | 豆油商业库存 |
| Y | Y_Y_STK_WARRANT | 豆油期货仓单 |

---

## 五、下一步行动

1. **立即修复**: 补充数据文件缺失的因子（91个）
2. **短期修复**: 增加数据量不足的因子历史数据（2个）
3. **映射完善**: 确认未映射因子的数据文件路径（76个）
4. **质量提升**: 降低高缺失率因子的缺失比例（5个）

---

*报告生成时间: 2026-04-27 12:13:31*
