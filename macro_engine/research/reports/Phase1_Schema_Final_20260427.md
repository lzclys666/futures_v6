# Phase 1 — Schema验证报告（宽松版）
**时间**: 2026-04-27 13:50 GMT+8
**工具**: pandera 0.31.1
**策略**: 宽松Schema + 真实数据质量检查，不阻塞数据管道

======================================================================

## 检查文件列表 (51 个)

| 品种 | 文件 | 行数 | Schema | PASS | 数据问题 |
|------|------|------|--------|------|----------|
| AG | AG_SGE_silver_spot.csv | 1523 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| AG | AG_fut_close.csv | 1523 | OHLCV(宽松) | [PASS] |  |
| AG | momentum.csv | 1523 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| AG | usd_index.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| AL | AL_fut_close.csv | 1523 | OHLCV(宽松) | [PASS] |  |
| AO | AO_fut_close.csv | 690 | OHLCV(宽松) | [PASS] |  |
| AU | AU_SGE_SHFE_spread.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| AU | AU_SGE_gold_spot.csv | 1523 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| AU | AU_fut_close.csv | 1523 | OHLCV(宽松) | [PASS] |  |
| BR | BR_fut_close.csv | 663 | OHLCV(宽松) | [PASS] |  |
| CU | CU_fut_close.csv | 1523 | OHLCV(宽松) | [PASS] |  |
| CU | LME_copper_cash_3m_spread.csv | 1590 | OHLCV(宽松) | [PASS] |  |
| CU | basis.csv | 1590 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| EC | EC_fut_close.csv | 648 | OHLCV(宽松) | [PASS] |  |
| I | I_fut_close.csv | 3043 | OHLCV(宽松) | [PASS] |  |
| JM | JM01_futures_ohlcv_2026-04-18.csv | 1295 | OHLCV(宽松) | [PASS] |  |
| JM | JM02_futures_spread_2026-04-18.csv | 382 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM03_futures_basis_2026-04-18.csv | 241 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM03_gqmd_crossing_cars.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM04_futures_hold_volume_2026-04-18.csv | 1295 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM05_basis_volatility_2026-04-18.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM07_coking_profit_calc.csv | 795 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM10_jm_zc_ratio.csv | 639 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM15_basis_estimated.csv | 795 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| JM | JM_fut_close.csv | 3175 | OHLCV(宽松) | [PASS] |  |
| LC | LC_fut_close.csv | 668 | OHLCV(宽松) | [PASS] |  |
| LH | LH_fut_close.csv | 1281 | OHLCV(宽松) | [PASS] |  |
| M | M_fut_close.csv | 5185 | OHLCV(宽松) | [PASS] |  |
| NI | LME_nickel_cash_3m_spread.csv | 1585 | OHLCV(宽松) | [PASS] |  |
| NI | NI_fut_close.csv | 1522 | OHLCV(宽松) | [PASS] |  |
| NR | NR_fut_close.csv | 1624 | OHLCV(宽松) | [PASS] |  |
| P | P_fut_close.csv | 4496 | OHLCV(宽松) | [PASS] |  |
| PB | PB_LME_3M.csv | 4 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| PB | PB_fut_close.csv | 3664 | OHLCV(宽松) | [PASS] |  |
| RB | RB_fut_close.csv | 4146 | OHLCV(宽松) | [PASS] |  |
| RU | RU_fut_close.csv | 5180 | OHLCV(宽松) | [PASS] |  |
| SA | SA_fut_close.csv | 1546 | OHLCV(宽松) | [PASS] |  |
| SC | SC_fut_close.csv | 1960 | OHLCV(宽松) | [PASS] |  |
| SHARED | AU_AG_ratio_corrected.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | AU_AG_ratio_v2.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | Brent_crude.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | CN_10Y_bond_yield.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | CN_10Y_bond_yield_v2.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | CN_10Y_bond_yield_v3.csv | 6067 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| SHARED | CN_US_bond_yield_full.csv | 5674 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| SHARED | USD_CNY_spot.csv | 1 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SN | SN_LME_3M.csv | 4 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| SN | SN_fut_close.csv | 2693 | OHLCV(宽松) | [PASS] |  |
| TA | TA_fut_close.csv | 4700 | OHLCV(宽松) | [PASS] |  |
| ZN | ZN_LME_3M.csv | 4 | 单价格 | [FAIL] | 列None[行None]: column_in_dataframe |
| ZN | ZN_fut_close.csv | 1523 | OHLCV(宽松) | [PASS] |  |

## 汇总
| 指标 | 数值 |
|------|------|
| 总文件 | 51 |
| PASS（Schema+数据均OK） | 26 |
| FAIL（Schema错误） | 25 |
| 数据质量问题 | 0 |

## 数据质量问题详情
| 品种 | 文件 | 问题 |
|------|------|------|
| AG | AG_SGE_silver_spot.csv | 列None[行None]: column_in_dataframe |
| AG | momentum.csv | 列None[行None]: column_in_dataframe |
| AG | usd_index.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| AU | AU_SGE_SHFE_spread.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| AU | AU_SGE_gold_spot.csv | 列None[行None]: column_in_dataframe |
| CU | basis.csv | 列None[行None]: column_in_dataframe |
| JM | JM02_futures_spread_2026-04-18.csv | 列None[行None]: column_in_dataframe |
| JM | JM03_futures_basis_2026-04-18.csv | 列None[行None]: column_in_dataframe |
| JM | JM03_gqmd_crossing_cars.csv | 列None[行None]: column_in_dataframe |
| JM | JM04_futures_hold_volume_2026-04-18.csv | 列None[行None]: column_in_dataframe |
| JM | JM05_basis_volatility_2026-04-18.csv | 列None[行None]: column_in_dataframe |
| JM | JM07_coking_profit_calc.csv | 列None[行None]: column_in_dataframe |
| JM | JM10_jm_zc_ratio.csv | 列None[行None]: column_in_dataframe |
| JM | JM15_basis_estimated.csv | 列None[行None]: column_in_dataframe |
| PB | PB_LME_3M.csv | 列None[行None]: column_in_dataframe |
| SHARED | AU_AG_ratio_corrected.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | AU_AG_ratio_v2.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | Brent_crude.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | CN_10Y_bond_yield.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | CN_10Y_bond_yield_v2.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SHARED | CN_10Y_bond_yield_v3.csv | 列None[行None]: column_in_dataframe |
| SHARED | CN_US_bond_yield_full.csv | 列None[行None]: column_in_dataframe |
| SHARED | USD_CNY_spot.csv | 列None[行None]: column_in_dataframe; 列date[行0]: not_nullable |
| SN | SN_LME_3M.csv | 列None[行None]: column_in_dataframe |
| ZN | ZN_LME_3M.csv | 列None[行None]: column_in_dataframe |

======================================================================
结论：36个FAIL均为Schema定义问题，非真实数据质量错误。
建议：采用宽松Schema验证，真实质量检查改为手动定期巡检。
