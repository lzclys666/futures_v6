# Phase 1 — Pandera Schema 修复报告
**时间**: 2026-04-27 13:46 GMT+8
**工具**: pandera 0.31.1

======================================================================

## Phase 1 修复：专用Schema验证
检查文件数: 51

| 品种 | 文件 | Schema类型 | 行数 | 状态 | 问题 |
|------|------|-----------|------|------|------|
| AG | AG_SGE_silver_spot.csv | 宽松 | 1523 | [PASS] |  |
| AG | AG_fut_close.csv | OHLCV | 1523 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| AG | momentum.csv | 宽松 | 1523 | [PASS] |  |
| AG | usd_index.csv | 宏观价格 | 1723 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| AL | AL_fut_close.csv | OHLCV | 1523 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| AO | AO_fut_close.csv | OHLCV | 690 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| AU | AU_SGE_SHFE_spread.csv | 金银价差 | 1199 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| AU | AU_SGE_gold_spot.csv | 宽松 | 1523 | [PASS] |  |
| AU | AU_fut_close.csv | OHLCV | 1523 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| BR | BR_fut_close.csv | OHLCV | 663 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| CU | CU_fut_close.csv | OHLCV | 1523 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| CU | LME_copper_cash_3m_spread.csv | 价差 | 1590 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| CU | basis.csv | 宽松 | 1590 | [PASS] |  |
| EC | EC_fut_close.csv | OHLCV | 648 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| I | I_fut_close.csv | OHLCV | 3043 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| JM | JM01_futures_ohlcv_2026-04-18.csv | OHLCV | 1295 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| JM | JM02_futures_spread_2026-04-18.csv | 金银价差 | 382 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| JM | JM03_futures_basis_2026-04-18.csv | 宽松 | 241 | [PASS] |  |
| JM | JM03_gqmd_crossing_cars.csv | 宽松 | 1 | [PASS] |  |
| JM | JM04_futures_hold_volume_2026-04-18.csv | 宽松 | 1295 | [PASS] |  |
| JM | JM05_basis_volatility_2026-04-18.csv | 宽松 | 1 | [PASS] |  |
| JM | JM07_coking_profit_calc.csv | 宽松 | 795 | [PASS] |  |
| JM | JM10_jm_zc_ratio.csv | 比价 | 639 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| JM | JM15_basis_estimated.csv | 宽松 | 795 | [PASS] |  |
| JM | JM_fut_close.csv | OHLCV | 3175 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| LC | LC_fut_close.csv | OHLCV | 668 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| LH | LH_fut_close.csv | OHLCV | 1281 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| M | M_fut_close.csv | OHLCV | 5185 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| NI | LME_nickel_cash_3m_spread.csv | 价差 | 1585 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| NI | NI_fut_close.csv | OHLCV | 1522 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| NR | NR_fut_close.csv | OHLCV | 1624 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| P | P_fut_close.csv | OHLCV | 4496 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| PB | PB_LME_3M.csv | LME_3M | 4 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| PB | PB_fut_close.csv | OHLCV | 3664 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| RB | RB_fut_close.csv | OHLCV | 4146 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| RU | RU_fut_close.csv | OHLCV | 5180 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| SA | SA_fut_close.csv | OHLCV | 1546 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| SC | SC_fut_close.csv | OHLCV | 1960 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| SHARED | AU_AG_ratio_corrected.csv | 金银比 | 1523 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| SHARED | AU_AG_ratio_v2.csv | 金银比 | 1523 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| SHARED | Brent_crude.csv | 宏观价格 | 1638 | [FAIL] | 1个失败: schema_context column           check  check_number  f |
| SHARED | CN_10Y_bond_yield.csv | 宏观价格 | 246 | [PASS] |  |
| SHARED | CN_10Y_bond_yield_v2.csv | 宏观价格 | 477 | [PASS] |  |
| SHARED | CN_10Y_bond_yield_v3.csv | 宏观价格 | 6067 | [PASS] |  |
| SHARED | CN_US_bond_yield_full.csv | 宏观价格 | 5674 | [PASS] |  |
| SHARED | USD_CNY_spot.csv | 宏观价格 | 1723 | [PASS] |  |
| SN | SN_LME_3M.csv | LME_3M | 4 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| SN | SN_fut_close.csv | OHLCV | 2693 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| TA | TA_fut_close.csv | OHLCV | 4700 | [FAIL] | 1个失败: column failure_case index  schema_context              |
| ZN | ZN_LME_3M.csv | LME_3M | 4 | [FAIL] | 2个失败: column failure_case index  schema_context              |
| ZN | ZN_fut_close.csv | OHLCV | 1523 | [FAIL] | 2个失败: column failure_case index  schema_context              |

## 汇总
| 指标 | 数值 |
|------|------|
| 总文件数 | 51 |
| PASS | 15 |
| FAIL | 36 |
| WARN | 0 |
| SKIP | 0 |
| 通过率 | 15/51 = 29.4% |

## 真实数据问题：close/price=0 的文件
| 品种 | 文件 | close=0行数 | null行数 |
|------|------|-----------|--------|
| — | 无 | 0 | 0 |

## FAIL文件详情（Schema不匹配）
**AG / AG_fut_close.csv**
  Schema类型: OHLCV
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold']
  前2行:
         date         open         high          low        close  volume    hold
0  2020-01-01  3511.014198  3568.829830  3527.439234  3527.938411  173631  178331
1  2020-01-02  3515.834642  3534.234132  3501.381993  3522.389929  400053  149280

**AG / usd_index.csv**
  Schema类型: 宏观价格
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'value']
  前2行:
         date   value
0  2020-01-01  6.9762
1  2020-01-02  6.9614

**AL / AL_fut_close.csv**
  Schema类型: OHLCV
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold']
  前2行:
         date     open     high      low    close  volume    hold
0  2020-01-02  14080.0  14145.0  14060.0  14090.0   38578  115942
1  2020-01-03  14075.0  14090.0  13960.0  14085.0   70834  110425

**AO / AO_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume   hold  settle
0  2023-06-19  2730.0  2766.0  2680.0  2721.0   91505  11188  2713.0
1  2023-06-20  2713.0  2747.0  2712.0  2731.0   62189  10400  2733.0

**AU / AU_SGE_SHFE_spread.csv**
  Schema类型: 金银价差
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'close_sge', 'close_fut', 'sge_fut_spread']
  前2行:
         date  close_sge  close_fut  sge_fut_spread
0  2020-01-02     346.75     346.24            0.51
1  2020-01-06     351.42     358.34           -6.92

**AU / AU_fut_close.csv**
  Schema类型: OHLCV
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold']
  前2行:
         date    open    high     low   close  volume    hold
0  2020-01-02  346.00  346.58  345.44  346.24   41087  129725
1  2020-01-03  346.82  351.96  346.58  351.16  144392  140774

**BR / BR_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date     open     high      low    close  volume   hold   settle
0  2023-07-28  10750.0  10880.0  10560.0  10755.0   82745  15177  10720.0
1  2023-07-31  10790.0  11105.0  10765.0  10985.0   98875  26887  10965.0

**CU / CU_fut_close.csv**
  Schema类型: OHLCV
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold']
  前2行:
         date     open     high      low    close  volume    hold
0  2020-01-02  49120.0  49340.0  49120.0  49230.0   42747  110353
1  2020-01-03  49130.0  49130.0  48750.0  48780.0   80835   98739

**CU / LME_copper_cash_3m_spread.csv**
  Schema类型: 价差
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's']
  前2行:
         date    open    high     low   close  volume  position    s
0  2020-01-02  6188.5  6233.0  6161.0  6207.0   14304         0  0.0
1  2020-01-03  6206.0  6209.0  6088.5  6136.5   18427         0  0.0

**EC / EC_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date   open   high    low  close  volume   hold  settle
0  2023-08-18  770.0  932.9  770.0  916.3  343882  12099   895.0
1  2023-08-21  918.0  950.0  894.1  903.2  268074  14428   916.7

**I / I_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date   open   high    low  close  volume   hold  settle
0  2013-10-18  978.0  984.0  962.0  977.0  300818  65042   975.0
1  2013-10-21  976.0  977.0  960.0  969.0   95432  68130   967.0

**JM / JM01_futures_ohlcv_2026-04-18.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle', 'contract', 'variety']
  前2行:
         date    open    high     low   close  volume  hold  settle contract variety
0  2024-05-20  1777.5  1815.0  1769.0  1810.0      17    11  1796.5   JM2505      JM
1  2024-05-21  1811.5  1811.5  1790.0  1790.0       5    15  1796.5   JM2505      JM

**JM / JM02_futures_spread_2026-04-18.csv**
  Schema类型: 金银价差
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'JM2505_settle', 'JM2505_close', 'JM2509_settle', 'JM2509_close', 'JM2506_settle', 'JM2506_close', 'JM2512_settle', 'JM2512_close', 'spread_01', 'spread_03', 'spread_05']
  前2行:
         date  JM2505_settle  JM2505_close  JM2509_settle  JM2509_close  JM2506_settle  JM2506_close  JM2512_settle  JM2512_close  spread_01  spread_03  spread_05
0  2024-05-20         1796.5        1810.0            NaN           NaN            NaN           NaN            NaN           NaN        NaN        NaN        NaN
1  2024-05-21         1796.5        1790.0            NaN           NaN            NaN           NaN            NaN           NaN        NaN        NaN        NaN

**JM / JM10_jm_zc_ratio.csv**
  Schema类型: 比价
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['日期', 'JM_close', 'ZC_close', 'ratio']
  前2行:
           日期  JM_close  ZC_close     ratio
0  2020-01-02    1176.5     556.6  2.113726
1  2020-01-03    1178.5     552.2  2.134191

**JM / JM_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume    hold  settle
0  2013-03-22  1280.0  1304.0  1257.0  1267.0  845512   96086  1276.0
1  2013-03-25  1276.0  1286.0  1251.0  1258.0  722022  139712  1266.0

**LC / LC_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date      open      high       low     close  volume  hold    settle
0  2023-07-21  238900.0  238900.0  214150.0  215100.0   59519  5854  220700.0
1  2023-07-24  214500.0  214700.0  209000.0  211400.0   40662  7680  211150.0

**LH / LH_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date     open     high      low    close  volume   hold   settle
0  2021-01-08  29500.0  30680.0  26385.0  26805.0   91045  14988  28290.0
1  2021-01-11  26225.0  26720.0  26030.0  26030.0   23026  17600  26260.0

**M / M_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume   hold  settle
0  2005-01-04  2150.0  2155.0  2142.0  2150.0   58792  63364     0.0
1  2005-01-05  2131.0  2154.0  2127.0  2154.0   71172  62704     0.0

**NI / LME_nickel_cash_3m_spread.csv**
  Schema类型: 价差
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's']
  前2行:
         date     open     high      low    close  volume  position    s
0  2020-01-02  14130.0  14265.0  14040.0  14225.0    5690         0  0.0
1  2020-01-03  14250.0  14280.0  13740.0  13770.0    8022         0  0.0

**NI / NI_fut_close.csv**
  Schema类型: OHLCV
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold']
  前2行:
         date      open      high       low     close  volume    hold
0  2020-01-02  111490.0  112050.0  109820.0  111310.0  451446  141670
1  2020-01-03  111650.0  111900.0  107680.0  107800.0  832788  157883

**NR / NR_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open     high     low   close  volume   hold  settle
0  2019-08-12  9805.0  10175.0  9720.0  9820.0   87618  19456  9865.0
1  2019-08-13  9780.0   9980.0  9775.0  9855.0   18956  17864  9855.0

**P / P_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume  hold  settle
0  2007-10-29  8350.0  8424.0  8350.0  8424.0    2098  1652     0.0
1  2007-10-30  8700.0  8700.0  8550.0  8572.0   18646  4286     0.0

**PB / PB_LME_3M.csv**
  Schema类型: LME_3M
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'symbol', 'latest', 'yesterday_settle', 'spread_diff']
  前2行:
         date symbol  latest  yesterday_settle  spread_diff
0  2026-04-20    PBD  1963.2            1962.0         -1.2
1  2026-04-19    PBD  1963.2            1962.0         -1.2

**PB / PB_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date     open     high      low    close  volume  hold   settle
0  2011-03-24  19230.0  19570.0  18830.0  18935.0   73440  9696  19095.0
1  2011-03-25  18935.0  19135.0  18860.0  18950.0   24858  8494  18995.0

**RB / RB_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume   hold  settle
0  2009-03-27  3550.0  3663.0  3513.0  3561.0  354590  45548     0.0
1  2009-03-30  3550.0  3580.0  3528.0  3544.0  145168  48380     0.0

**RU / RU_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date     open     high      low    close  volume  hold  settle
0  2005-01-04  12040.0  12090.0  11945.0  12025.0    3856  9330     0.0
1  2005-01-05  12000.0  12055.0  11965.0  12045.0    2698  9690     0.0

**SA / SA_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume   hold  settle
0  2019-12-06  1580.0  1585.0  1546.0  1561.0  318030  38922  1566.0
1  2019-12-09  1564.0  1591.0  1556.0  1572.0  167478  31568  1571.0

**SC / SC_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date   open   high    low  close  volume    hold  settle
0  2018-03-26  440.0  447.1  426.3  429.9   40656  311400     0.0
1  2018-03-27  429.9  431.7  412.6  424.0   40602    3936   426.4

**SHARED / AU_AG_ratio_corrected.csv**
  Schema类型: 金银比
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'au_ag_ratio_corrected']
  前2行:
         date  au_ag_ratio_corrected
0  2020-01-01              79.578383
1  2020-01-02              79.239031

**SHARED / AU_AG_ratio_v2.csv**
  Schema类型: 金银比
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'au_ag_ratio_g_per_g']
  前2行:
         date  au_ag_ratio_g_per_g
0  2020-01-01            79.578383
1  2020-01-02            79.239031

**SHARED / Brent_crude.csv**
  Schema类型: 宏观价格
  错误: 1个失败: schema_context column           check  check_number  failure_case  index        
  列名: ['date', 'wti_spot_usd_bbl']
  前2行:
         date  wti_spot_usd_bbl
0  2020-01-02             61.17
1  2020-01-03             63.00

**SN / SN_LME_3M.csv**
  Schema类型: LME_3M
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'symbol', 'latest', 'yesterday_settle', 'spread_diff']
  前2行:
         date symbol    latest  yesterday_settle  spread_diff
0  2026-04-20    SND  50050.85           50695.0       644.15
1  2026-04-19    SND  50050.85           50695.0       644.15

**SN / SN_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date      open      high       low     close  volume   hold    settle
0  2015-03-27   16025.0   16060.0   15880.0   15905.0   35290  75124   15970.0
1  2015-03-30  119270.0  119530.0  115600.0  118080.0    2464    834  117721.0

**TA / TA_fut_close.csv**
  Schema类型: OHLCV
  错误: 1个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前2行:
         date    open    high     low   close  volume  hold  settle
0  2006-12-19  8860.0  8958.0  8806.0  8906.0   49070  7488     0.0
1  2006-12-20  8944.0  8970.0  8906.0  8958.0   25586  8882     0.0

**ZN / ZN_LME_3M.csv**
  Schema类型: LME_3M
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'symbol', 'latest', 'yesterday_settle', 'spread_diff']
  前2行:
         date symbol    latest  yesterday_settle  spread_diff
0  2026-04-20    ZSD  3452.265            3446.0       -6.265
1  2026-04-19    ZSD  3450.800            3446.0       -4.800

**ZN / ZN_fut_close.csv**
  Schema类型: OHLCV
  错误: 2个失败: column failure_case index  schema_context               check check_number   Non
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold']
  前2行:
         date     open     high      low    close  volume   hold
0  2020-01-02  17900.0  18000.0  17855.0  17880.0   66720  75962
1  2020-01-03  17945.0  17985.0  17730.0  17755.0   97431  74212

======================================================================
Phase 1 修复检查完成
