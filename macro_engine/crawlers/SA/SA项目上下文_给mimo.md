# 纯碱（SA）数据采集项目 — 上下文摘要（因子分析师 → 程序员mimo）

## 一、项目背景
期货智能交易系统需要纯碱（SA）的基本面因子数据。因子分析师已制定三梯队采集计划，当前完成第一梯队。

## 二、AKShare 接口验证结果（全部可用）

1. `ak.futures_zh_daily_sina(symbol="SA0")` — SA主力连续日线，无需日期参数返回全量，列: date/open/high/low/close/volume/hold/settle
2. `ak.get_futures_daily(start_date, end_date, market="CZCE")` — 全合约日线识别次主力，需日期范围YYYYMMDD，列: symbol/date/open/high/low/close/volume/open_interest/turnover/settle/pre_settle/variety
3. `ak.get_rank_table_czce(date)` — 持仓排名前20席位，日期YYYYMMDD，返回dict，key含SA609等，列: rank/vol_party_name/vol/vol_chg/long_party_name/long_open_interest/long_open_interest_chg/short_party_name/short_open_interest/short_open_interest_chg/symbol/variety
4. `ak.futures_warehouse_receipt_czce(date)` — 仓单日报，日期YYYYMMDD，返回dict，key="SA"，DataFrame列序: 仓库代码(0)/仓库简称(1)/地区等级(2)/注册仓单(3)/注册增减(4)/有效预报(5)/升贴水(6)

已确认不可用: futures_zh_daily_sina("SA1")、futures_hist_em、futures_spot_price_daily

## 三、已写代码（3个爬虫 + 2个bug已修）

文件位置: D:\futures_macro_engine\crawlers\SA\

- SA_抓取期货日线.py (10KB) — 主力SA0 + 次主力（从全合约取持仓第2）
- SA_抓取持仓排名.py (7KB) — 前5合计多/空/净持仓，已修复千分位逗号bug
- SA_抓取仓单数据.py (8KB) — 注册仓单(周频)+有效预报(日频)，已修复列索引bug

参考模板: D:\futures_macro_engine\crawlers\AG\ 目录下有 AG（白银）爬虫模板
通用工具: D:\futures_macro_engine\crawlers\common\db_utils.py 提供 ensure_table/save_to_db/get_pit_dates

### Bug修复记录
1. 仓单列名编码: 中文列名在Windows GBK下乱码 -> 改用 iloc[:, idx] 列索引
2. 持仓千分位逗号: 值如"39,171"导致pd.to_numeric返回NaN -> 加 .str.replace(',', '')

## 四、因子命名与数据规范

- sa_futures_daily_close (日频, obs_date=交易日周一=上周五, 阈值1000~5000)
- sa_futures_daily_hold (日频, 同上, 阈值>0)
- sa_futures_sub_daily_close (日频, 同上, 阈值1000~5000)
- sa_positions_long5 (日频, 同上, 阈值>0)
- sa_positions_short5 (日频, 同上, 阈值>0)
- sa_positions_net5 (日频, 同上, 无限制)
- sa_inventory_w (周频, obs_date=上周五, 阈值>=0)
- sa_warrant_daily (日频, obs_date=交易日, 阈值>=0)

## 五、4/16实测数据（已写入 pit_data.db）

- SA主力收盘: 1241.0
- SA主力持仓: 839,622
- 多头前5: 152,021 / 空头前5: 291,755 / 净持仓: -139,734
- 注册仓单: 13,398 / 有效预报: 1,808

## 六、待办事项

### 优先级1: 完成第一阶段
- 编写 SA_run_all.py 统一调度脚本（按顺序执行3个爬虫）
- 配置 cron 定时任务（交易日15:30自动运行）
- 日志输出到 D:\futures_macro_engine\crawlers\SA\logs\

### 优先级2: 第二梯队数据
- 现货报价（华北沙河重碱送到价、华东重碱送到价）- 需要爬网页
- 上下游价格（纯碱-原盐价差、纯碱-玻璃比价）
- 开工率（纯碱行业周度开工率）
- 产能数据（月度）

### 优先级3: 第三梯队
- 宏观数据（房地产新开工、汽车产量等）
- 海外数据（美国纯碱出口FOB价）
