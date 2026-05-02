# Pandera Schema 检查报告
**时间**: 2026-04-27 13:42 GMT+8
**工具**: pandera 0.31.1

======================================================================

## 检查文件列表 (41 个)

## 检查结果汇总
| 指标 | 数值 |
|------|------|
| 检查文件数 | 41 |
| PASS | 9 |
| FAIL | 32 |
| WARN | 0 |
| SKIP | 0 |
| 通过率 | 9/41 = 22.0% |

## 详细结果
| 品种 | 文件 | 行数 | 状态 | 问题 |
|------|------|------|------|------|
| AG | AG_fut_close.csv | 1523 | [PASS] |  |
| AL | AL_fut_close.csv | 1523 | [PASS] |  |
| AO | AO_fut_close.csv | 690 | [FAIL] | 1个失败: schema_context column           check  check_number  failure_cas |
| AU | AU_SGE_SHFE_spread.csv | 1199 | [FAIL] | 1个失败: column failure_case index  schema_context               check ch |
| AU | AU_fut_close.csv | 1523 | [PASS] |  |
| BR | BR_fut_close.csv | 663 | [FAIL] | 2个失败: schema_context column           check  check_number  failure_cas |
| CU | CU_fut_close.csv | 1523 | [PASS] |  |
| CU | LME_copper_cash_3m_spread.csv | 1590 | [FAIL] | 1个失败: column failure_case index  schema_context               check ch |
| EC | EC_fut_close.csv | 648 | [FAIL] | 2个失败: schema_context column           check  check_number  failure_cas |
| I | I_fut_close.csv | 3043 | [FAIL] | 200个失败: schema_context column           check  check_number  failure_c |
| JM | JM01_futures_ohlcv_2026-04-18.csv | 1295 | [FAIL] | 3个失败: schema_context column           check  check_number  failure_cas |
| JM | JM02_futures_spread_2026-04-18.csv | 382 | [FAIL] | 1个失败: column failure_case index  schema_context               check ch |
| JM | JM03_futures_basis_2026-04-18.csv | 241 | [FAIL] | 246个失败:  schema_context column               check check_number failur |
| JM | JM04_futures_hold_volume_2026-04-18.csv | 1295 | [FAIL] | 4个失败: column failure_case index  schema_context               check ch |
| JM | JM_fut_close.csv | 3175 | [FAIL] | 200个失败: schema_context column           check  check_number  failure_c |
| LC | LC_fut_close.csv | 668 | [FAIL] | 1个失败: schema_context column           check  check_number  failure_cas |
| LH | LH_fut_close.csv | 1281 | [FAIL] | 2个失败: schema_context column           check  check_number  failure_cas |
| M | M_fut_close.csv | 5185 | [FAIL] | 1589个失败: schema_context column           check  check_number  failure_ |
| NI | LME_nickel_cash_3m_spread.csv | 1585 | [FAIL] | 1个失败: column failure_case index  schema_context               check ch |
| NI | NI_fut_close.csv | 1522 | [PASS] |  |
| NR | NR_fut_close.csv | 1624 | [FAIL] | 3个失败: schema_context column           check  check_number  failure_cas |
| P | P_fut_close.csv | 4496 | [FAIL] | 899个失败: schema_context column           check  check_number  failure_c |
| PB | PB_LME_3M.csv | 4 | [FAIL] | 4个失败: column failure_case index  schema_context               check ch |
| PB | PB_fut_close.csv | 3664 | [FAIL] | 29个失败: schema_context column           check  check_number  failure_ca |
| RB | RB_fut_close.csv | 4146 | [FAIL] | 326个失败: schema_context column           check  check_number  failure_c |
| RU | RU_fut_close.csv | 5180 | [FAIL] | 1371个失败: schema_context column           check  check_number  failure_ |
| SA | SA_fut_close.csv | 1546 | [PASS] |  |
| SC | SC_fut_close.csv | 1960 | [FAIL] | 5个失败: schema_context column           check  check_number  failure_cas |
| SHARED | AU_AG_ratio_corrected.csv | 1523 | [PASS] |  |
| SHARED | AU_AG_ratio_v2.csv | 1523 | [PASS] |  |
| SHARED | Brent_crude.csv | 1638 | [FAIL] | 5个失败: column failure_case index  schema_context               check ch |
| SHARED | CN_10Y_bond_yield.csv | 246 | [FAIL] | 5个失败: column failure_case index  schema_context               check ch |
| SHARED | CN_10Y_bond_yield_v2.csv | 477 | [FAIL] | 5个失败: column failure_case index  schema_context               check ch |
| SHARED | CN_10Y_bond_yield_v3.csv | 6067 | [FAIL] | 5个失败: column failure_case index  schema_context               check ch |
| SHARED | CN_US_bond_yield_full.csv | 5674 | [FAIL] | 5个失败: column failure_case index  schema_context               check ch |
| SHARED | USD_CNY_spot.csv | 1723 | [FAIL] | 5个失败: column failure_case index  schema_context               check ch |
| SN | SN_LME_3M.csv | 4 | [FAIL] | 4个失败: column failure_case index  schema_context               check ch |
| SN | SN_fut_close.csv | 2693 | [FAIL] | 6个失败: schema_context column           check  check_number  failure_cas |
| TA | TA_fut_close.csv | 4700 | [FAIL] | 922个失败: schema_context column           check  check_number  failure_c |
| ZN | ZN_LME_3M.csv | 4 | [FAIL] | 4个失败: column failure_case index  schema_context               check ch |
| ZN | ZN_fut_close.csv | 1523 | [PASS] |  |

## FAIL 文件详细错误
**AO / AO_fut_close.csv**
  错误: 1个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0    309
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open    high     low   close  volume   hold  settle
0  2023-06-19  2730.0  2766.0  2680.0  2721.0   91505  11188  2713.0
1  2023-06-20  2713.0  2747.0  2712.0  2731.0   62189  10400  2733.0
2  2023-06-21  2726.0  2742.0  2715.0  2738.0   51494   7871  2731.0

**AU / AU_SGE_SHFE_spread.csv**
  错误: 1个失败: column failure_case index  schema_context               check check_number |   None         diff  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'close_sge', 'close_fut', 'sge_fut_spread']
  前3行:
         date  close_sge  close_fut  sge_fut_spread
0  2020-01-02     346.75     346.24            0.51
1  2020-01-06     351.42     358.34           -6.92
2  2020-01-07     357.41     354.94            2.47

**BR / BR_fut_close.csv**
  错误: 2个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0     21 |         Column  close greater_than(0)             0           0.0    282
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date     open     high      low    close  volume   hold   settle
0  2023-07-28  10750.0  10880.0  10560.0  10755.0   82745  15177  10720.0
1  2023-07-31  10790.0  11105.0  10765.0  10985.0   98875  26887  10965.0
2  2023-08-01  10990.0  11045.0  10855.0  10970.0   28220  32618  10955.0

**CU / LME_copper_cash_3m_spread.csv**
  错误: 1个失败: column failure_case index  schema_context               check check_number |   None         diff  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's']
  前3行:
         date    open    high     low   close  volume  position    s
0  2020-01-02  6188.5  6233.0  6161.0  6207.0   14304         0  0.0
1  2020-01-03  6206.0  6209.0  6088.5  6136.5   18427         0  0.0
2  2020-01-06  6124.0  6162.0  6100.5  6143.0   14694         0  0.0

**EC / EC_fut_close.csv**
  错误: 2个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      6 |         Column  close greater_than(0)             0           0.0    267
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date   open   high    low  close  volume   hold  settle
0  2023-08-18  770.0  932.9  770.0  916.3  343882  12099   895.0
1  2023-08-21  918.0  950.0  894.1  903.2  268074  14428   916.7
2  2023-08-22  895.4  957.0  885.0  895.1  332138  15913   923.4

**I / I_fut_close.csv**
  错误: 200个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0     66 |         Column  close greater_than(0)             0           0.0   1584
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date   open   high    low  close  volume   hold  settle
0  2013-10-18  978.0  984.0  962.0  977.0  300818  65042   975.0
1  2013-10-21  976.0  977.0  960.0  969.0   95432  68130   967.0
2  2013-10-22  963.0  966.0  948.0  948.0   91296  76004   956.0

**JM / JM01_futures_ohlcv_2026-04-18.csv**
  错误: 3个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0     89 |         Column  close greater_than(0)             0           0.0    256
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle', 'contract', 'variety']
  前3行:
         date    open    high     low   close  volume  hold  settle contract variety
0  2024-05-20  1777.5  1815.0  1769.0  1810.0      17    11  1796.5   JM2505      JM
1  2024-05-21  1811.5  1811.5  1790.0  1790.0       5    15  1796.5   JM2505      JM
2  2024-05-22  1825.5  1863.5  1821.0  1847.0      21    18  1841.5   JM2505      JM

**JM / JM02_futures_spread_2026-04-18.csv**
  错误: 1个失败: column failure_case index  schema_context               check check_number |   None         diff  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'JM2505_settle', 'JM2505_close', 'JM2509_settle', 'JM2509_close', 'JM2506_settle', 'JM2506_close', 'JM2512_settle', 'JM2512_close', 'spread_01', 'spread_03', 'spread_05']
  前3行:
         date  JM2505_settle  JM2505_close  JM2509_settle  JM2509_close  JM2506_settle  JM2506_close  JM2512_settle  JM2512_close  spread_01  spread_03  spread_05
0  2024-05-20         1796.5        1810.0            NaN           NaN            NaN           NaN            NaN           NaN        NaN        NaN        NaN
1  2024-05-21         1796.5        1790.0            NaN           NaN            NaN           NaN            NaN           NaN        NaN        NaN        NaN
2  2024-05-22         1841.5        1847.0            NaN           NaN            NaN           NaN            NaN           NaN        NaN        NaN        NaN

**JM / JM03_futures_basis_2026-04-18.csv**
  错误: 246个失败:  schema_context column               check check_number failure_case index | DataFrameSchema   None column_in_dataframe         None       volume  None | DataFrameSchema   None column_in_dataframe         None          low  None
  列名: ['date', 'futures_settle', 'futures_close', 'spot_price', 'spot_source', 'basis', 'basis_rate', 'data_status']
  前3行:
         date  futures_settle  futures_close  spot_price spot_source  basis  basis_rate   data_status
0  2024-05-20          1796.5         1810.0         NaN     missing    NaN         NaN  futures_only
1  2024-05-21          1796.5         1790.0         NaN     missing    NaN         NaN  futures_only
2  2024-05-22          1841.5         1847.0         NaN     missing    NaN         NaN  futures_only

**JM / JM04_futures_hold_volume_2026-04-18.csv**
  错误: 4个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'contract', 'hold', 'hold_change', 'volume']
  前3行:
         date contract  hold  hold_change  volume
0  2024-05-20   JM2505    11          NaN      17
1  2024-05-21   JM2505    15          4.0       5
2  2024-05-22   JM2505    18          3.0      21

**JM / JM_fut_close.csv**
  错误: 200个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0    201 |         Column  close greater_than(0)             0           0.0   1716
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open    high     low   close  volume    hold  settle
0  2013-03-22  1280.0  1304.0  1257.0  1267.0  845512   96086  1276.0
1  2013-03-25  1276.0  1286.0  1251.0  1258.0  722022  139712  1266.0
2  2013-03-26  1255.0  1276.0  1249.0  1272.0  835326  141544  1265.0

**LC / LC_fut_close.csv**
  错误: 1个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0    287
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date      open      high       low     close  volume  hold    settle
0  2023-07-21  238900.0  238900.0  214150.0  215100.0   59519  5854  220700.0
1  2023-07-24  214500.0  214700.0  209000.0  211400.0   40662  7680  211150.0
2  2023-07-25  211000.0  225900.0  211000.0  225900.0   61787  9213  222050.0

**LH / LH_fut_close.csv**
  错误: 2个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0    237 |         Column  close greater_than(0)             0           0.0    900
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date     open     high      low    close  volume   hold   settle
0  2021-01-08  29500.0  30680.0  26385.0  26805.0   91045  14988  28290.0
1  2021-01-11  26225.0  26720.0  26030.0  26030.0   23026  17600  26260.0
2  2021-01-12  25760.0  26210.0  25205.0  25560.0   39402  17194  25795.0

**M / M_fut_close.csv**
  错误: 1589个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      0 |         Column  close greater_than(0)             0           0.0   1068
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open    high     low   close  volume   hold  settle
0  2005-01-04  2150.0  2155.0  2142.0  2150.0   58792  63364     0.0
1  2005-01-05  2131.0  2154.0  2127.0  2154.0   71172  62704     0.0
2  2005-01-06  2152.0  2168.0  2146.0  2167.0   66174  63948     0.0

**NI / LME_nickel_cash_3m_spread.csv**
  错误: 1个失败: column failure_case index  schema_context               check check_number |   None         diff  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's']
  前3行:
         date     open     high      low    close  volume  position    s
0  2020-01-02  14130.0  14265.0  14040.0  14225.0    5690         0  0.0
1  2020-01-03  14250.0  14280.0  13740.0  13770.0    8022         0  0.0
2  2020-01-06  13750.0  13860.0  13625.0  13805.0    6594         0  0.0

**NR / NR_fut_close.csv**
  错误: 3个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0    580 |         Column  close greater_than(0)             0           0.0    982
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open     high     low   close  volume   hold  settle
0  2019-08-12  9805.0  10175.0  9720.0  9820.0   87618  19456  9865.0
1  2019-08-13  9780.0   9980.0  9775.0  9855.0   18956  17864  9855.0
2  2019-08-14  9840.0  10220.0  9785.0  9995.0   37116  23014  9965.0

**P / P_fut_close.csv**
  错误: 899个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      0 |         Column  close greater_than(0)             0           0.0    727
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open    high     low   close  volume  hold  settle
0  2007-10-29  8350.0  8424.0  8350.0  8424.0    2098  1652     0.0
1  2007-10-30  8700.0  8700.0  8550.0  8572.0   18646  4286     0.0
2  2007-10-31  8502.0  8554.0  8500.0  8516.0    5142  3774     0.0

**PB / PB_LME_3M.csv**
  错误: 4个失败: column failure_case index  schema_context               check check_number |   None         open  None DataFrameSchema column_in_dataframe         None |   None         high  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'symbol', 'latest', 'yesterday_settle', 'spread_diff']
  前3行:
         date symbol  latest  yesterday_settle  spread_diff
0  2026-04-20    PBD  1963.2            1962.0         -1.2
1  2026-04-19    PBD  1963.2            1962.0         -1.2
2  2026-04-19    PBD  1963.2            1962.0         -1.2

**PB / PB_fut_close.csv**
  错误: 29个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0    263 |         Column  close greater_than(0)             0           0.0    751
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date     open     high      low    close  volume  hold   settle
0  2011-03-24  19230.0  19570.0  18830.0  18935.0   73440  9696  19095.0
1  2011-03-25  18935.0  19135.0  18860.0  18950.0   24858  8494  18995.0
2  2011-03-28  18900.0  19035.0  18500.0  18605.0   16960  8262  18775.0

**RB / RB_fut_close.csv**
  错误: 326个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      0 |         Column  close greater_than(0)             0           0.0    204
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open    high     low   close  volume   hold  settle
0  2009-03-27  3550.0  3663.0  3513.0  3561.0  354590  45548     0.0
1  2009-03-30  3550.0  3580.0  3528.0  3544.0  145168  48380     0.0
2  2009-03-31  3538.0  3566.0  3531.0  3549.0   70592  44714     0.0

**RU / RU_fut_close.csv**
  错误: 1371个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      0 |         Column  close greater_than(0)             0           0.0    911
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date     open     high      low    close  volume  hold  settle
0  2005-01-04  12040.0  12090.0  11945.0  12025.0    3856  9330     0.0
1  2005-01-05  12000.0  12055.0  11965.0  12045.0    2698  9690     0.0
2  2005-01-06  12050.0  12100.0  12025.0  12085.0    2188  9498     0.0

**SC / SC_fut_close.csv**
  错误: 5个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      0 |         Column  close greater_than(0)             0           0.0    266
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date   open   high    low  close  volume    hold  settle
0  2018-03-26  440.0  447.1  426.3  429.9   40656  311400     0.0
1  2018-03-27  429.9  431.7  412.6  424.0   40602    3936   426.4
2  2018-03-28  429.0  429.2  406.5  410.4   67198    6074   414.1

**SHARED / Brent_crude.csv**
  错误: 5个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'wti_spot_usd_bbl']
  前3行:
         date  wti_spot_usd_bbl
0  2020-01-02             61.17
1  2020-01-03             63.00
2  2020-01-06             63.27

**SHARED / CN_10Y_bond_yield.csv**
  错误: 5个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'cn_10y_yield']
  前3行:
         date  cn_10y_yield
0  2020-02-04        2.8551
1  2020-02-05        2.8440
2  2020-02-06        2.8392

**SHARED / CN_10Y_bond_yield_v2.csv**
  错误: 5个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['DATE', 'DSWP10']
  前3行:
         DATE  DSWP10
0  2015-01-01     NaN
1  2015-01-02    2.23
2  2015-01-05    2.17

**SHARED / CN_10Y_bond_yield_v3.csv**
  错误: 5个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'cn_10y_yield']
  前3行:
         date  cn_10y_yield
0  2002-01-04        3.2096
1  2002-01-07        3.2003
2  2002-01-08        3.5225

**SHARED / CN_US_bond_yield_full.csv**
  错误: 5个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'cn_10y', 'cn_2y', 'cn_5y', 'us_10y', 'us_2y']
  前3行:
         date  cn_10y   cn_2y   cn_5y  us_10y  us_2y
0  2002-01-04  3.2096  2.6563  2.8674    5.18   3.19
1  2002-01-07  3.2003  2.6697  2.8728    5.09   3.08
2  2002-01-08  3.5225  2.1578  2.7890    5.10   3.07

**SHARED / USD_CNY_spot.csv**
  错误: 5个失败: column failure_case index  schema_context               check check_number |   None        close  None DataFrameSchema column_in_dataframe         None |   None         open  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'usd_cny', 'boc_banknote_buy', 'boc_cash_buy', 'boc_sell', 'pbc_mid']
  前3行:
         date  usd_cny  boc_banknote_buy  boc_cash_buy  boc_sell  pbc_mid
0  2020-01-01   6.9762            694.99        689.34    697.94      NaN
1  2020-01-02   6.9614            695.09        689.44    698.04   696.14
2  2020-01-03   6.9681            695.29        689.63    698.24   696.81

**SN / SN_LME_3M.csv**
  错误: 4个失败: column failure_case index  schema_context               check check_number |   None         open  None DataFrameSchema column_in_dataframe         None |   None         high  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'symbol', 'latest', 'yesterday_settle', 'spread_diff']
  前3行:
         date symbol    latest  yesterday_settle  spread_diff
0  2026-04-20    SND  50050.85           50695.0       644.15
1  2026-04-19    SND  50050.85           50695.0       644.15
2  2026-04-19    SND  50050.85           50695.0       644.15

**SN / SN_fut_close.csv**
  错误: 6个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0     64 |         Column  close greater_than(0)             0           0.0    114
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date      open      high       low     close  volume   hold    settle
0  2015-03-27   16025.0   16060.0   15880.0   15905.0   35290  75124   15970.0
1  2015-03-30  119270.0  119530.0  115600.0  118080.0    2464    834  117721.0
2  2015-03-31  117650.0  119800.0  115960.0  118160.0    4522   1176  117790.0

**TA / TA_fut_close.csv**
  错误: 922个失败: schema_context column           check  check_number  failure_case  index |         Column  close greater_than(0)             0           0.0      0 |         Column  close greater_than(0)             0           0.0    605
  列名: ['date', 'open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
  前3行:
         date    open    high     low   close  volume  hold  settle
0  2006-12-19  8860.0  8958.0  8806.0  8906.0   49070  7488     0.0
1  2006-12-20  8944.0  8970.0  8906.0  8958.0   25586  8882     0.0
2  2006-12-21  8940.0  8948.0  8884.0  8912.0   19414  8080     0.0

**ZN / ZN_LME_3M.csv**
  错误: 4个失败: column failure_case index  schema_context               check check_number |   None         open  None DataFrameSchema column_in_dataframe         None |   None         high  None DataFrameSchema column_in_dataframe         None
  列名: ['date', 'symbol', 'latest', 'yesterday_settle', 'spread_diff']
  前3行:
         date symbol    latest  yesterday_settle  spread_diff
0  2026-04-20    ZSD  3452.265            3446.0       -6.265
1  2026-04-19    ZSD  3450.800            3446.0       -4.800
2  2026-04-19    ZSD  3451.000            3446.0       -5.000


======================================================================
检查完成
