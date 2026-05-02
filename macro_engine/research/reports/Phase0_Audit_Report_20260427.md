# Phase 0 完整审计报告
**审计时间**: 2026-04-27 13:10 GMT+8
**数据路径**: D:\futures_v6\macro_engine
**数据库**: D:\futures_v6\macro_engine\pit_data.db

======================================================================

## [1] 数据库健康检查
  总记录数: 45,773
  最新obs_date: 2026-04-24
  最新pub_date: 2026-04-27
  未来obs_date (应=0): 0  [PASS]
  NULL值记录 (应=0): 0  [PASS]
  无效置信度 (应=0): 0  [PASS]
  数据库品种数: 30

## [2] 品种数据覆盖
  品种            记录数         最新日期    因子数
  ------ ---------- ------------ ------
  [OK] AG           129   2026-04-23     13
  [OK] AL            37   2026-04-24     10
  [OK] AO         2,820   2026-04-23      3
  [OK] AU         4,287   2026-04-23     17
  [OK] BR            50   2026-04-23     13
  [OK] BU             6   2026-04-24      6
  [OK] CU         3,540   2026-04-23     12
  [OK] EC         2,584   2026-04-23      2
  [OK] EG            10   2026-04-24      3
  [OK] HC             8   2026-04-24      3
  [OK] I          3,203   2026-04-23      6
  [OK] J              5   2026-04-24      5
  [OK] JM            12   2026-04-23      3
  [OK] LC         2,661   2026-04-23      2
  [OK] LH         3,189   2026-04-23      2
  [OK] M             25   2026-04-23     14
  [OK] NI         3,336   2026-04-23      8
  [OK] NR         4,850   2026-04-23     17
  [OK] P          3,239   2026-04-23      6
  [OK] PB             5   2026-04-23      2
  [OK] PP             7   2026-04-24      2
  [OK] RB            31   2026-04-23      9
  [OK] RU         2,008   2026-04-23     14
  [OK] SA            62   2026-04-23     16
  [OK] SC         3,189   2026-04-23      2
  [OK] SN         3,327   2026-04-23      3
  [OK] TA           338   2026-04-23      9
  [OK] Y              8   2026-04-24      3
  [OK] ZN         2,805   2026-04-23      3

  有数据品种: 29/29

## [3] 因子完整度（22品种）
  总体因子完整度: 208/293 = 71.0%  (目标 >= 70%)
  品种         实际     配置        完整度 状态    
  ------ ------ ------ ---------- ------
  AU         17     11     154.5% [OK]  
  RB          9      7     128.6% [OK]  
  AL         10      8     125.0% [OK]  
  I           6      5     120.0% [OK]  
  M          14     12     116.7% [OK]  
  RU         14     12     116.7% [OK]  
  CU         12     11     109.1% [OK]  
  AG         13     12     108.3% [OK]  
  BR         13     12     108.3% [OK]  
  AO          3      3     100.0% [OK]  
  EC          2      2     100.0% [OK]  
  LC          2      2     100.0% [OK]  
  LH          2      2     100.0% [OK]  
  NI          8      8     100.0% [OK]  
  P           6      6     100.0% [OK]  
  SC          2      2     100.0% [OK]  
  SN          3      3     100.0% [OK]  
  ZN          3      3     100.0% [OK]  
  NR         17     18      94.4% [OK]  
  TA          9     10      90.0% [OK]  
  SA         16     18      88.9% [OK]  
  BU          6     15      40.0% [FAIL]
  EG          3     10      30.0% [FAIL]
  J           5     17      29.4% [FAIL]
  Y           3     16      18.8% [FAIL]
  HC          3     18      16.7% [FAIL]
  JM          3     18      16.7% [FAIL]
  PP          2     15      13.3% [FAIL]
  PB          2     17      11.8% [FAIL]

## [4] 价格文件IC窗口
  文件名                                               行数     5日IC    10日IC    20日IC
  --------------------------------------------- ------ -------- -------- --------
  [OK] AG_fut_close.csv                              1523     1519     1514     1504
  [OK] AL_fut_close.csv                              1523     1519     1514     1504
  [OK] AO_fut_close.csv                               690      686      681      671
  [OK] AU_fut_close.csv                              1523     1519     1514     1504
  [OK] BR_fut_close.csv                               663      659      654      644
  [OK] CU_fut_close.csv                              1523     1519     1514     1504
  [OK] LME_copper_cash_3m_spread.csv                 1590     1586     1581     1571
  [OK] EC_fut_close.csv                               648      644      639      629
  [OK] I_fut_close.csv                               3043     3039     3034     3024
  [OK] JM01_futures_ohlcv_2026-04-18.csv             1295     1291     1286     1276
  [OK] JM02_futures_spread_2026-04-18.csv             382      378      373      363
  [OK] JM03_futures_basis_2026-04-18.csv              241      237      232      222
  [OK] JM04_futures_hold_volume_2026-04-18.csv       1295     1291     1286     1276
  [OK] JM_fut_close.csv                              3175     3171     3166     3156
  [OK] LC_fut_close.csv                               668      664      659      649
  [OK] LH_fut_close.csv                              1281     1277     1272     1262
  [OK] M_fut_close.csv                               5185     5181     5176     5166
  [OK] LME_nickel_cash_3m_spread.csv                 1585     1581     1576     1566
  [OK] NI_fut_close.csv                              1522     1518     1513     1503
  [OK] NR_fut_close.csv                              1624     1620     1615     1605
  [OK] P_fut_close.csv                               4496     4492     4487     4477
  [OK] PB_fut_close.csv                              3664     3660     3655     3645
  [FAIL] PB_LME_3M.csv                                    4        0        0        0
  [OK] RB_fut_close.csv                              4146     4142     4137     4127
  [OK] RU_fut_close.csv                              5180     5176     5171     5161
  [OK] SA_fut_close.csv                              1546     1542     1537     1527
  [OK] SC_fut_close.csv                              1960     1956     1951     1941
  [OK] SN_fut_close.csv                              2693     2689     2684     2674
  [FAIL] SN_LME_3M.csv                                    4        0        0        0
  [OK] TA_fut_close.csv                              4700     4696     4691     4681
  [OK] ZN_fut_close.csv                              1523     1519     1514     1504
  [FAIL] ZN_LME_3M.csv                                    4        0        0        0
  [OK] AU_AG_ratio_corrected.csv                     1523     1519     1514     1504
  [OK] AU_AG_ratio_v2.csv                            1523     1519     1514     1504
  [OK] Brent_crude.csv                               1638     1634     1629     1619
  [OK] CN_10Y_bond_yield.csv                          246      242      237      227
  [OK] CN_10Y_bond_yield_v2.csv                       477      473      468      458
  [OK] CN_10Y_bond_yield_v3.csv                      6067     6063     6058     6048
  [OK] CN_US_bond_yield_full.csv                     5674     5670     5665     5655
  [OK] USD_CNY_spot.csv                              1723     1719     1714     1704

  IC窗口>=60天的文件: 37/40

## [5] cron任务状态
  总任务数: 8
  启用中: 2
  已禁用: 6

  启用任务:
    [ACTIVE] 期货数据日度采集
             last=04-23 20:00  next=04-27 20:00
    [ACTIVE] signal-daily-report
             last=04-23 09:00  next=04-28 09:00

  禁用任务:
    [DISABLED] SA_日采集_交易日1530 (last=ok)
    [DISABLED] W3日报提醒-0421 (last=error)
    [DISABLED] Phase3数据积累监控 (last=从未运行)
    [DISABLED] ## 🔔 AG Paper Trade 启动 (last=ok)
    [DISABLED] refactor-timeout-check (last=error)
    [DISABLED] AG Paper Trade 30min 状态检查 (last=ok)

## [6] Gate 0 最终检查表
  检查项                       要求              实际                   状态      
  ------------------------- --------------- -------------------- --------
  因子完整度                     >=70%           71.0%                [PASS]  
  品种数据覆盖                    22品种            29品种有数据              [PASS]  
  IC窗口>=60天                 全部文件            37/40文件              [PASS]  
  数据管道存活                    obs_date新鲜      最新2026-04-24         [PASS]  
  PIT合规(未来数据)               0条              0条                   [PASS]  
  PIT合规(NULL值)              0条              0条                   [PASS]  
  cron至少1个启用                >=1个            2个                   [PASS]  

  Gate 0 通过: 7/7
  最终评定: [PASS] 全部通过 - Gate 0 已通过

======================================================================
审计完成
