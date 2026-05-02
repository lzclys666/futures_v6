**期货智能交易系统 V6.0**

基于 VNpy 二次开发架构文档

版本：V6.0-20260423\
基于：VNpy 4.3.0 + CTA Strategy\
范围：全系统能力清单 + 二次开发记录 + 实施路线\
状态：持续更新

# 目录

1.  第一章 文档说明与阅读指南

2.  第二章 VNpy 4.3.0 内置能力清单

3.  第三章 当前系统架构（全路径）

4.  第四章 二次开发模块详解

5.  第五章 待开发模块（蓝图对照）

6.  第六章 功能对照总表：VNpy / 已开发 / 待开发

7.  第七章 接口规格与数据流

8.  第八章 命名规范

9.  第九章 部署与运维

# 第一章 文档说明与阅读指南

## 1.1 文档目的

本文档是「期货智能交易系统 V6.0」的全系统架构说明，核心原则是：**VNpy
已有的能力直接复用，二次开发聚焦于宏观信号层和上层业务逻辑。**

- 本文档回答以下问题：

- VNpy 原生提供了哪些功能，我们不需要重新开发？

- 我们已经二次开发了哪些模块，它们与 VNpy 的边界在哪里？

- 还有哪些功能是蓝图规划但尚未实现的？

- 完整系统的各层职责如何划分？

## 1.2 文档范围

  --------------------------------------------------------------------------
  **包含**                               **不包含**
  -------------------------------------- -----------------------------------
  VNpy 4.3.0 内置能力清单                完整用户使用说明书（见用户手册）

  已实现的宏观信号引擎（macro_engine）   CTP 柜台协议细节（见 VNpy 文档）

  已实现的 VNpy 策略（multi_factor /     详细代码实现（见源码注释）
  macro_demo）                           

  待开发模块的接口规格                   回测引擎内部算法（见 VNpy
                                         回测文档）

  部署运维指南                           历史数据整理流程（见 data/
                                         目录说明）
  --------------------------------------------------------------------------

## 1.3 关键原则

- **不重造轮子：**VNpy 已实现的 OrderManager / PositionManager /
  RiskEngine / EventEngine / 回测引擎直接使用

- **CSV 作为共享边界：**宏观打分引擎输出 CSV，VNpy 策略读取
  CSV，两层独立进程解耦

- **FastAPI 仅负责宏观层：**不把交易执行层塞进 FastAPI；交易执行统一走
  VNpy CTA Engine

- **数据质量优先：**因子 IC 验证 \> 代码量；数据有问题时宁愿输出 NEUTRAL

- **稳定优先于功能：**未充分验证的功能不上线；API 网关只提供只读查询

## 1.4 术语对照

  ------------------------------------------------------------------------------------------------------------------------
  **术语**                            **定义**
  ----------------------------------- ------------------------------------------------------------------------------------
  VNpy 原生                           指 VNpy 4.3.0 源码自带的功能，未经二次开发

  二次开发                            我们在 VNpy 基础上新增或扩展的模块（macro_engine / strategies / event_bus.py）

  待开发                              蓝图规划但尚未实现的模块，通常缺少关键依赖或待优先级排序

  宏观层                              宏观打分引擎（macro_scoring_engine.py + daily_scoring.py），独立于 VNpy 进程运行

  执行层                              VNpy CTA Strategy Engine，负责从信号到订单的全流程

  边界文件                            macro_engine/output/{SYMBOL}\_macro_daily_YYYYMMDD.csv，即宏观层与执行层的唯一接口
  ------------------------------------------------------------------------------------------------------------------------

# 第二章 VNpy 4.3.0 内置能力清单

## 2.1 已安装组件

当前环境已安装以下 VNpy 组件，均为官方维护，无需二次开发：

  ---------------------------------------------------------------------------
  **组件**                    **版本**                **说明**
  --------------------------- ----------------------- -----------------------
  vnpy==4.3.0                                         核心框架（MainEngine /
                                                      EventEngine / Gateway /
                                                      数据对象）

  vnpy-ctp==6.7.11.4                                  CTP 7.x
                                                      柜台直连接口，支持
                                                      SimNow 模拟盘和实盘

  vnpy-ctastrategy==1.4.1                             CTA 策略引擎（内置
                                                      CtaTemplate / CtaEngine
                                                      / 回测调度）

  vnpy-ctabacktester==1.3.0                           回测模块（事件驱动 +
                                                      Walk-Forward +
                                                      参数优化）

  vnpy-datamanager==1.2.0                             历史数据管理器（K
                                                      线存储 / 导出 / 维护）

  vnpy-chart==0.0.5                                   K 线图表渲染（PyQt5
                                                      集成）

  vnpy-akshare==1.0.0                                 AKShare
                                                      数据适配器（历史行情 /
                                                      财务数据）

  vnpy-sqlite==1.1.3                                  SQLite 数据库引擎（K
                                                      线持久化）
  ---------------------------------------------------------------------------

## 2.2 VNpy 原生能力对照表（可直接使用）

**以下能力由 VNpy 提供，本项目不重复开发：**

  -----------------------------------------------------------------------------------------------------------------------------------------------------
  **能力分类**      **VNpy类/函数**                              **接口说明**                                                      **本项目使用方式**
  ----------------- -------------------------------------------- ----------------------------------------------------------------- --------------------
  事件引擎          EventEngine                                  全局事件总线，驱动所有模块通信（Trader/Strategy/Gateway事件）     直接继承/调用

  主引擎            MainEngine                                   整合 Gateway / App / Engine 的核心容器，支持 add_gateway /        直接继承/调用
                                                                 add_app                                                           

  CTA策略基类       CtaTemplate                                  策略模板，提供 buy/sell/short/cover/send_order 等方法，已实现     直接继承/调用
                                                                 on_bar/on_tick/on_init/on_start/on_stop                           

  CTA引擎           CtaEngine                                    策略生命周期管理（加载/初始化/启动/停止/参数同步/sync_data）      直接继承/调用

  回测引擎          BacktestingEngine                            事件驱动回测，run_backtesting / calculate_statistics /            直接继承/调用
                                                                 run_optimization                                                  

  K线生成器         BarGenerator                                 Tick→1min/5min/15min/\...K线聚合，支持自定义on_bar回调            直接继承/调用

  数组管理器        ArrayManager                                 K线序列存储与指标计算（支持talib直接传入）                        直接继承/调用

  网关基类          BaseGateway                                  柜台接口抽象，已实现的：CTPGateway（vnpy-ctp）                    直接继承/调用

  行情订阅          subscribe / TickData                         Tick级实时行情，含5档行情/最新价/成交量/持仓量                    直接继承/调用

  订单管理          OrderData / TradeData                        订单生命周期（SUBMITTING→SUBMITTED→TRADING→ALLTRADED/REJECTED）   直接继承/调用

  持仓管理          PositionData                                 按方向（Long/Short）实时维护持仓，支持净持仓模式（net=True）      直接继承/调用

  账户管理          AccountData                                  实时权益/可用资金/冻结资金/保证金                                 直接继承/调用

  止损单            StopOrder / send_stop_order                  本地STOP单/止盈止损单，支持服务器条件单（CTP柜台支持时）          直接继承/调用

  数据管理App       DataManagerApp                               K线数据导入/导出/清理，PyQt5图形界面                              直接继承/调用

  回测App           CtaBacktesterApp                             Walk-Forward / GA / Grid参数优化，图形化回测界面                  直接继承/调用

  日志引擎          LogEngine / write_log                        策略级写日志，支持文件+控制台输出，email告警                      直接继承/调用

  常量枚举          Direction/Offset/Status/OrderType/Exchange   所有枚举值，统一风格，避免字符串硬编码                            直接继承/调用

  配置管理          load_json / save_json                        策略参数/账户配置的持久化读写                                     直接继承/调用

  网关连接监控      Gateway连接状态事件                          网关断开/重连自动发布事件，触发 DataAdapterChain 降级逻辑         直接继承/调用
  -----------------------------------------------------------------------------------------------------------------------------------------------------

## 2.3 CtaTemplate 核心方法（已内置）

**所有策略均继承 CtaTemplate，自动获得以下能力：**

- **下单：**buy(price, volume) / sell(price, volume) / short(price,
  volume) / cover(price, volume)

- **信号止损：**send_order(direction, offset, price, volume) +
  on_stop_order(stop_order)

- **K线管理：**BarGenerator 自动聚合Tick → BarData，触发 on_bar(bar:
  BarData)

- **指标数组：**ArrayManager(size=100) 存储历史K线，支持talib直接传入

- **策略生命周期：**on_init → on_start → on_bar循环 → on_stop

- **参数同步：**get_parameters() /
  update_setting()，自动持久化到JSON，重启恢复

- **日志：**write_log(msg) → LogEngine → 文件/控制台/email

- **事件通知：**put_event() → 通知UI刷新策略状态

- **数据加载：**load_bar(days, interval) 从数据库加载历史K线到
  ArrayManager

- **邮件告警：**send_email(msg) → EmailEngine → SMTP → 邮箱

- **策略同步：**sync_data() 将策略变量持久化，重启后恢复运行状态

## 2.4 MainEngine 架构（已内置）

MainEngine 是 VNpy 的核心容器，负责管理所有 Gateway 和 App：

- add_gateway(GatewayClass) → 网关实例，支持同时连接多个柜台

- add_app(AppClass) → App实例，注册到引擎树，自动创建对应的 Engine

- init_engines() → 初始化所有已注册的引擎

- get_gateway(name) → 获取指定网关实例

- get_all_gateway_names() → 获取所有已注册网关名称

- get_all_apps() → 获取所有已注册 App

# 第三章 当前系统架构（全路径）

## 3.1 整体架构图

当前系统采用三层分离架构（宏观打分层 + API层 +
VNpy执行层），三层独立运行，任一层故障不影响其他层：

┌─────────────────────────────────────────────────────────────────────────────┐

│ 用户浏览器（localhost:5173） │

│ 宏观信号看板 │ 持仓面板 │ 风控监控 │ 回测中心（预留） │

└────────────────────────────┬────────────────────────────────────────────────┘

│ HTTP REST + WebSocket

┌─────────────────────────────┴────────────────────────────────────────────────┐

│ FastAPI 宏观层（进程2，端口8000） D:\\futures_v6\\api\\ │

│
┌──────────────────────────────────────────────────────────────────────┐
│

│ │ macro_api_server.py │ │

│ │ macro_scoring_engine.py │ │

│ │ GET /api/macro/signal/all GET /api/macro/signal/{sym} │ │

│ │ WS /ws/macro_updates（规划中） │ │

│
└──────────────────────────────────────────────────────────────────────┘
│

│ ↑ 读 CSV │

│
┌───────────────────────────┴──────────────────────────────────────────┐
│

│ │ macro_engine\\ D:\\futures_v6\\macro_engine\\ │ │

│ │ crawlers\\ │ core\\pipeline\\ │ core\\scoring\\ │ output\\ │ │

│ │ 日终定时 14:30 ──→ Pipeline ──→ CSV ──→ VNpy读取 │ │

│
└───────────────────────────────────────────────────────────────────────┘
│

└────────────────────────────┬────────────────────────────────────────────────┘

│ CSV文件 D:\\futures_v6\\macro_engine\\output\\

┌─────────────────────────────┴────────────────────────────────────────────────┐

│ VNpy 执行层（进程1，主入口 D:\\futures_v6\\run.py） │

│
┌──────────────────────────────────────────────────────────────────────┐
│

│ │ MainEngine │ │

│ │ ├─ CtpGateway（SimNow 模拟盘 / 实盘CTP） │ │

│ │ ├─ CtaStrategyApp（CtaEngine → 策略实例） │ │

│ │ ├─ CtaBacktesterApp（回测界面入口） │ │

│ │ ├─ DataManagerApp（K线数据管理界面） │ │

│ │ └─ RiskManagerApp（未安装，自写 MacroRiskApp 替代） │ │

│ │ │ │

│ │ 策略实例： │ │

│ │ ├─ MultiFactorStrategy（纯技术指标，4因子加权） │ │

│ │ └─ MacroDemoStrategy（宏观CSV + MA共振，MA10/20） │ │

│
└──────────────────────────────────────────────────────────────────────┘
│

│
┌──────────────────────────────────────────────────────────────────────┐
│

│ │ DataAdapterChain（数据源降级：CTP → 缓存） │ │

│ │ AuditService（审计日志：audit_log表90d / event_queue表7d） │ │

│
└──────────────────────────────────────────────────────────────────────┘
│

└─────────────────────────────────────────────────────────────────────────────┘

## 3.2 数据流向（完整路径）

  ----------------------------------------------------------------------------------------------------------
  **步骤**          **名称**          **路径**                                             **触发条件**
  ----------------- ----------------- ---------------------------------------------------- -----------------
  Step 1            宏观数据采集      crawlers/{SYM}/AG_抓取\*.py 等脚本 → 写入            定时每日 20:00
                                      data/{SYM}/.parquet                                  CST（OpenClaw
                                                                                           cron 数据采集）+
                                                                                           14:30
                                                                                           CST（schtasks
                                                                                           日终打分）

  Step 2            因子标准化        core/normalizer/robust_normalizer.py →               Pipeline内
                                      MAD标准化（-3\~3分）                                 

  Step 3            IC权重计算        core/scoring/weight_engine.py →                      Pipeline内
                                      IC动态权重（滚动窗口120天）                          

  Step 4            日终打分          scripts/daily_scoring.py → Pipeline.run() → CSV输出  每日14:30定时

  Step 5            API服务           macro_api_server.py → 读取CSV → JSON返回             实时HTTP/WS

  Step 6            策略读取信号      MacroDemoStrategy.load_macro_signal() → CSV →        on_timer触发
                                      macro_direction                                      

  Step 7            技术信号          MA10/MA20交叉（BarGenerator + ArrayManager）         on_bar每分钟

  Step 8            共振过滤          仅当宏观方向与MA方向一致时才下单（use_macro=True）   策略内逻辑

  Step 9            风控检查          CTPGateway内部风控 + RiskManagerApp（待激活）        CTA引擎内

  Step 10           下单执行          buy/sell → CtpGateway → 交易所                       仅限模拟盘
  ----------------------------------------------------------------------------------------------------------

## 3.3 项目目录结构

项目根目录：D:\\futures_v6\\，包含两个独立子系统：

**macro_engine/（宏观打分层，Python 3.11，FastAPI）** +
**run.py（VNpy执行层，Python 3.11，VNpy 4.3.0）**

  ----------------------------------------------------------------------------------------------------------------------
  **路径**                           **说明**                                                    **备注**
  ---------------------------------- ----------------------------------------------------------- -----------------------
  futures_v6\\（根目录）                                                                         

  run.py                             VNpy主入口（MainEngine初始化 + CtaStrategyApp + 策略加载）  

  api\\                              宏观层API服务（FastAPI，端口8000）                          

  macro_api_server.py                FastAPI应用，路由：/api/macro/signal/\*, /ws/macro_updates  

  macro_scoring_engine.py            CSV读取+评分逻辑，被API层调用                               

  macro_history_backfill.py          历史数据回填（从Frankfurter/API获取历史汇率等）             

  schemas.py                         Pydantic请求/响应模型                                       

  collectors\\                       数据采集器（akshare封装）                                   

  macro_engine\\                     宏观打分引擎（独立模块）                                    

  config\\                           22个品种因子配置子目录                                      

  factors\\                          YAML因子定义（品种_因子名.yaml，如 RU_TS_ROLL_YIELD.yaml）  

  instruments\\                      33个品种特性配置（33个YAML，合约乘数/保证金率等）           

  factor_meta.json                   因子元数据（IC驱动权重，2026-04-21更新）                    

  core\\                             核心计算引擎                                                

  interfaces.py                      6个抽象接口（DataProvider/Normalizer/WeightCalculator等）   

  pipeline\\                         PipelineNode基类 +                                          
                                     4个Node（Normalize/Orthogonalize/Weight/Direction）         

  scoring\\weight_engine.py          IC动态权重计算（WeightEngine类）                            

  normalizer\\robust_normalizer.py   MAD标准化（去除极端值，MAD=median\|xi-x\|）                 

  data\\pit_service.py               PIT数据服务（point-in-time，K线去未来函数）                 

  crawlers\\                         30+品种因子数据采集脚本（品种_中文说明.py格式）             

  RU\\CU\\AG\\AU\\BR\\NR\\\...       每个品种一个子目录，run_all.py统一调度                      

  output\\                           CSV信号输出目录（宏观打分引擎 → VNpy的共享边界）            

  RU_macro_daily_YYYYMMDD.csv        格式：row_type=SUMMARY/FACTOR, direction, compositeScore等  

  data\\                             原始因子数据（parquet格式）                                 

  {SYM}\\                            每个品种子目录                                              

  event_bus.py                       事件总线（内存+JSON持久化，7天清理）                        

  strategies\\                       （已迁移至根目录 strategies\\）                             

  strategies\\                       VNpy策略文件（MacroDemoStrategy + MultiFactorStrategy）     

  macro_demo_strategy.py             宏观共振策略（CSV信号 + MA10/MA20交叉）                     

  multi_factor_strategy.py           纯技术多因子策略（MA偏离+RSI+ATR+成交量+ADX动态权重）       

  simple_ma_test.py                  极简均线测试策略（纯MA20，用于系统链路测试）                

  frontend\\                         前端（Vite + React + TypeScript + Zustand + ECharts）       

  src\\components\\macro\\           宏观信号看板（MacroDashboard.tsx + SignalChart.tsx）        

  src\\store\\                       Zustand状态管理                                             

  src\\services\\                    Axios API调用封装                                           
  ----------------------------------------------------------------------------------------------------------------------

# 第四章 二次开发模块详解

## 4.1 宏观打分引擎（macro_engine/）

这是核心二次开发模块，将 VNpy 外部的宏观基本面数据转化为交易信号，与
VNpy 原生的技术面策略形成互补。

### 4.1.1 Pipeline 架构

  --------------------------------------------------------------------------------------------------------
  **节点**            **功能**          **实现**                                         **状态**
  ------------------- ----------------- ------------------------------------------------ -----------------
  NormalizeNode       MAD标准化         调用                                             已实现
                                        robust_normalizer.py，去极值后标准化到-3\~+3分   

  OrthogonalizeNode   正交化            当前为直传（simplified），未来可实现             简化版
                                        Gram-Schmidt                                     

  WeightNode          IC权重            调用 weight_engine.py，滚动120天IC计算动态权重   已实现

  DirectionNode       方向判定          confirm_days=2，首次运行直接确认，防止开盘误判   已实现
  --------------------------------------------------------------------------------------------------------

### 4.1.2 因子体系

当前接入品种：RU / CU / AU / AG（4品种完整），BR / NR / SA / TA（稀疏）

- **RU（橡胶）：**RU_TS_ROLL_YIELD（展期收益率）, RU_DEM_TIRE\_\*(需求),
  RU_INV\_\*(库存), RU_POS_NET（净持仓）, RU_SPD\_\*(价差)

- **CU（沪铜）：**CU_LME_SPREAD_DIFF（LME升贴水变动）,
  CU_INV_LME（伦铜库存）, CU_INV_SHFE（上期所库存）, CU_POS_NET,
  CU_SPD_BASIS

- **AU（黄金）：**AU_MACRO_GOLD_SILVER_RATIO（金银比）,
  AU_MACRO_US10Y（美债实际利率）, AU_MACRO_US_CPI,
  AU_MACRO_DXY（美元指数）

- **AG（白银）：**AG_MACRO_GOLD_SILVER_RATIO, AG_INV_SHFE（仓单）,
  AG_POS_CFTC_NET（CFTC净持仓）, AG_SPD_SHFE_COMEX（跨市价差）

### 4.1.3 IC 因子有效性排名（2026-04-21 验证）

  ----------------------------------------------------------------------------------
  **品种**          **因子**                     **IC**            **显著性**
  ----------------- ---------------------------- ----------------- -----------------
  AG                AG_MACRO_GOLD_SILVER_RATIO   -0.402            \*\*\*

  CU                USD_CNY（沪铜间接因子）      -0.398            \*\*\*

  AU                USD_INDEX                    -0.377            \*\*\*

  AU                DXY动量                      -0.297            \*\*

  RU                深浅色价差                   -0.285            \*\*
  ----------------------------------------------------------------------------------

## 4.2 宏观共振策略（MacroDemoStrategy）

文件：D:\\futures_v6\\strategies\\macro_demo_strategy.py，继承
CtaTemplate（VNpy原生）

- 核心逻辑（9步）：

- on_init → load_macro_signal() 读取今日CSV宏观信号

- on_timer → 每隔一段时间重新读取CSV（宏观信号日更新）

- on_tick → BarGenerator 聚合 Tick → 1min Bar

- on_bar → ArrayManager 更新K线数组（size=100）

- MA10 \> MA20 → tech_direction = LONG；MA10 \< MA20 → tech_direction =
  SHORT

- macro_direction == LONG AND tech_direction == LONG → 候选做多

- macro_direction == SHORT AND tech_direction == SHORT → 候选做空

- use_macro=False 时，忽略宏观信号，仅用MA交叉

- buy/sell → CtpGateway → 交易所SimNow

## 4.3 多因子技术策略（MultiFactorStrategy）

文件：D:\\futures_v6\\strategies\\multi_factor_strategy.py，继承
CtaTemplate（VNpy原生）

四因子体系 + ADX市场状态识别：

  ------------------------------------------------------------------------------------------------------
  **因子**                **默认权重**            **计算方式**
  ----------------------- ----------------------- ------------------------------------------------------
  趋势因子                weight_trend=0.4        MA20偏离度（价格/MA20 - 1）

  动量因子                weight_momentum=0.3     RSI14（talib.RSI）

  波动因子                weight_volatility=0.2   ATR变化率（ATR今日/ATR昨日 - 1）

  成交量因子              weight_volume=0.1       成交量/20日均量 - 1

  ADX动态权重             ADX\>25时增加趋势权重   趋势市场：趋势因子权重×1.2，其他×0.8；震荡市场：反之
  ------------------------------------------------------------------------------------------------------

## 4.4 DataAdapterChain（数据源降级）

文件：D:\\futures_v6\\run.py（DataAdapterChain 类），扩展 VNpy
的数据源能力：

- 优先级：CTP实时行情（优先） → 本地缓存（降级兜底）

- 网关断开事件：监听 eGateway 事件，自动标记数据源健康状态

- 告警事件：发布 eDataSourceAlert 事件，触发 UI 告警条（黄色/红色分级）

## 4.5 AuditService（审计日志）

文件：D:\\futures_v6\\run.py（AuditService 类），在 VNpy
事件引擎上扩展的审计层：

- 监听 eStrategy 事件 → 记录策略启动/停止

- 监听 eOrder 事件 → 记录下单请求（direction/offset/volume/price）

- 监听 eTrade 事件 → 记录成交记录（tradeid/品种/方向/手数/价格）

- 监听 eRiskRule 事件 → 记录风控规则触发

- audit_log 表：保留90天（保留 90 天（SQLite，可手动修改））

- event_queue 表：保留7天（运行数据，事件溯源）

# 第五章 待开发模块（蓝图对照）

## 5.1 总体状态

*以下模块在 V6.0 规划文档（期货智能交易系统 V6.0
.docx）中已规划，但尚未实现。列出接口规格以便后续开发：*

## 5.2 风控规则系统（未实现）

**现状：**run.py 中有 RiskManagerApp（VNpy原生），但未激活。现有
meltdown.yaml 仅包含单品种止损参数。

**规划：插件化风控规则链（V6.0 规划第6.2节）。接口定义：**

class RiskRule(ABC):\
\@property\
def rule_id(self) -\> str: \...\
\@property\
def rule_name(self) -\> str: \...\
\@abstractmethod\
def check(self, context: OrderContext) -\> RuleCheckResult: \...\
\@abstractmethod\
def get_config_schema(self) -\> dict: \...\
\
class RuleCheckResult:\
passed: bool\
reason: str\
action: str \# \"block\" \| \"warn\" \| \"adjust\"\
\
class OrderContext:\
symbol: str\
direction: Direction\
volume: int\
price: float\
strategy_name: str\
portfolio_risk: float\
current_positions: Dict\[str, PositionData\]

- 13条预置规则（V6.0规划 6.2.3节）：

- **单日亏损上限（daily_loss_limit）：**账户当日亏损达到阈值时禁止新开仓（默认2%）

- **连续亏损限制（consecutive_loss）：**连续亏损N笔后降低仓位（默认3笔×50%仓位）

- **单品种仓位上限（position_limit）：**单品种手数不超过配置值

- **隔夜保护（overnight_protect）：**夜盘收盘前15分钟强平所有持仓（可选）

- **熔断机制（meltdown）：**单日最大亏损达到阈值时停止所有策略

- **黑名单防护（blacklist_guard）：**TA/NI等品种禁止交易

- **观察池收紧（observe_pool）：**观察池品种仓位×0.3、止损倍数×1.3

## 5.3 订单管理层（❌ 未开发）

**现状：**VNpy 原生提供 OrderData / TradeData / StopOrder + CtaTemplate
的 buy/sell 基础下单。

**待开发扩展（V6.0规划 6.3节）：**

  ----------------------------------------------------------------------------------------------------------
  **功能**                **规格**                                                  **现状**
  ----------------------- --------------------------------------------------------- ------------------------
  TWAP拆单                大单分时成交，避免冲击成本                                单笔超过N手时分N批发送

  撤单追单                3秒未成→撤单；追2跳重新挂单；连续3次失败→品种拉黑30分钟   已有基础逻辑，需完善

  组合风险分配            总可用风险预算 = 资金×单笔风险比例×总仓位上限系数         待与风控系统联动

  止盈止损托管            CTP条件单（RB/CU/M/AU） + 本地托管监控（JM/LH/ZN/BR/SA）  需完善本地监控逻辑
  ----------------------------------------------------------------------------------------------------------

## 5.4 前端扩展（⚠️ 规划中）

**现状：**MacroDashboard.tsx（宏观信号看板）已实现。SignalChart.tsx（历史打分）已修复。

**待开发（V6.0规划第2章用户链路）：**

- **情报中心：**每日大事/异动品种提示。宏观事件日历（可复用爬虫数据）

- **品种管理面板：**20个品种分类和参数配置。读取
  config/instruments/\*.yaml

- **策略管理面板：**策略CRUD/参数调节/启停控制。需连接 CtaEngine API

- **下单面板：**手动下单/改单/撤单。需连接 CtpGateway order API

- **风控设置面板：**风控规则开关/阈值修改。需连接 RiskRuleRegistry

- **回测中心：**Walk-Forward/GA参数优化可视化。直接复用
  CtaBacktesterApp界面

## 5.5 宏观因子监控升级（YIYI规划，待确认）

因子分析师YIYI提出升级方案（2026-04-23），方向：增强统计验证能力。整合路径：

- Chart 1-3（IC曲线/IR序列/因子热力图）在现有 React 前端扩展（不新建
  Dash）

- 5维信号评分（IC_norm/Stability/Decay/Breadth/RegimeFit）扩展
  core/scoring/weight_engine.py

- Bootstrap CI + FDR校正 新增因子验证模块（复用现有 Pipeline）

- HMM Regime 检测 新增 core/regime/hmm_detector.py（需确认VIX数据源）

- 拥挤度监控 新增 crowding_detector.py，输出增强CSV

- Parquet迁移 双写模式（短期），避免一次性替换所有CSV读点

# 第六章 功能对照总表：VNpy / 已开发 / 待开发

**说明：**VNpy原生 = VNpy 4.3.0自带，不需要开发 \| 已开发 =
我们已二次开发 \| 待开发 = 蓝图规划，尚未实现

  -----------------------------------------------------------------------------------------------------------------------------------
  **分类**       **功能**                             **来源**       **状态**               **路径/说明**
  -------------- ------------------------------------ -------------- ---------------------- -----------------------------------------
  行情数据       Tick/K线实时行情（CTP）              VNpy原生       ✅ 已接入              CtpGateway → MainEngine → EventEngine

  行情数据       历史K线存储（SQLite）                VNpy原生       ✅ 已接入              vnpy-sqlite → DataManagerApp

  行情数据       AKShare历史行情                      VNpy原生       ✅ 已接入              vnpy-akshare → akshare数据源

  行情数据       宏观因子爬取（汇率/CFTC/库存）       二次开发       ✅ 已开发              crawlers/{SYM}/品种_抓取\*.py

  行情数据       PIT数据服务（去未来函数）            二次开发       ✅ 已开发              core/data/pit_service.py

  行情数据       数据源降级（CTP→缓存）               二次开发       ✅ 已开发              DataAdapterChain（run.py）

  行情数据       多数据源整合（Bloomberg/路透）       V6.0规划       ❌ 未开发              待定

  策略引擎       CTA策略基类                          VNpy原生       ✅ 已使用              CtaTemplate（vnpy-ctastrategy）

  策略引擎       MA共振宏观策略                       二次开发       ✅ 已开发              strategies/macro_demo_strategy.py

  策略引擎       多因子技术策略                       二次开发       ✅ 已开发              strategies/multi_factor_strategy.py

  策略引擎       市场状态识别（ADX）                  二次开发       ✅ 已开发              MultiFactorStrategy内嵌

  策略引擎       策略工厂（装饰器注册）               V6.0规划       ❌ 未开发              CtaEngine已支持，UI未接入

  策略引擎       策略参数UI声明驱动                   V6.0规划       ❌ 未开发              需前端配套

  风控系统       止损单（STOPORDER）                  VNpy原生       ✅ 已使用              CtaTemplate.send_order(stop=True)

  风控系统       VNpy风控App界面                      VNpy原生       ✅ 已加载              RiskManagerApp（run.py）

  风控系统       插件化风控规则链                     二次开发       ❌ 未开发              需新建 core/risk/rule\_\*.py

  风控系统       审计日志（90天保留，SQLite）         二次开发       ✅ 已开发              AuditService（run.py）

  风控系统       黑名单品种禁止                       V6.0规划       ❌ 未开发              需集成到下单流程

  风控系统       梯度降仓（观察池）                   二次开发       ⚠️ 参数已有            MultiFactorStrategy内 observe\_\*-\* 参数

  执行层         订单状态机                           VNpy原生       ✅ 已使用              OrderData.status 自动流转

  执行层         撤单追单（3秒超时）                  V6.0规划       ❌ 未开发              MultiFactorStrategy内有基础逻辑

  执行层         TWAP拆单                             V6.0规划       ❌ 未开发              待实现

  执行层         滑点控制                             V6.0规划       ⚠️ 参数已有            滑点参数预留，未激活

  回测           事件驱动回测                         VNpy原生       ✅ 已可用              CtaBacktesterApp（run.py）

  回测           Walk-Forward滚动优化                 VNpy原生       ✅ 已可用              BacktestingEngine.run_bf_optimization()

  回测           GA/Grid参数优化                      VNpy原生       ✅ 已可用              BacktestingEngine.run_ga_optimization()

  回测           历史打分回测（Paper Trading）        二次开发       ⚠️ RU/ZN/RB/NI         需验证其他品种
                                                                     四品种配置，当前全部   
                                                                     pos=0，连续 9 天无成交 

  宏观层         日终打分Pipeline                     二次开发       ✅ 已开发              scripts/daily_scoring.py

  宏观层         IC动态权重计算                       二次开发       ✅ 已开发              core/scoring/weight_engine.py

  宏观层         MAD标准化                            二次开发       ✅ 已开发              core/normalizer/robust_normalizer.py

  宏观层         因子IC验证（Bootstrap CI）           YIYI规划       ❌ 未开发              待YIYI方案确认

  宏观层         HMM Regime检测                       YIYI规划       ❌ 未开发              待VIX数据源确认

  宏观层         拥挤度监控                           YIYI规划       ❌ 未开发              待YIYI方案确认

  宏观层         Parquet数据迁移                      YIYI规划       ❌ 未开发              建议双写渐进迁移

  API层          FastAPI宏观信号服务                  二次开发       ✅ 已开发              api/macro_api_server.py

  API层          WebSocket实时推送                    二次开发       ❌ 未开发（规划中）    macro_api_server.py /ws

  API层          策略/订单/风控REST API               V6.0规划       ❌ 未开发              待设计

  前端           宏观信号看板（图表）                 二次开发       ✅ 已开发              frontend/src/components/macro/

  前端           历史打分图表                         二次开发       ✅ 已修复              SignalChart.tsx

  前端           情报中心/异动提示                    V6.0规划       ❌ 未开发              待开发

  前端           策略管理面板                         V6.0规划       ❌ 未开发              需连接CtaEngine

  前端           下单/改单/撤单面板                   V6.0规划       ❌ 未开发              需连接CtpGateway

  前端           风控设置面板                         V6.0规划       ❌ 未开发              需连接RiskRuleRegistry

  前端           断连状态恢复（useReplicatedState）   V6.0规划       ❌ 未开发              WebSocket版本字段方案已规划

  运维           Windows定时任务（日终打分）          二次开发       ✅ 已配置              schtasks每日14:30

  运维           日志管理                             VNpy原生       ✅ 已使用              LogEngine + log/目录

  运维           数据库自动备份                       V6.0规划       ❌ 未开发              待实现

  运维           Docker部署                           V6.0规划       ❌ 未开发              因Windows环境，不优先

  运维           因子数据更新监控                     二次开发       ✅ 已配置              crawlers/{SYM}/run_all.py
  -----------------------------------------------------------------------------------------------------------------------------------

# 第七章 接口规格与数据流

## 7.1 核心接口：CSV边界文件

**CSV文件（macro_engine/output/{SYMBOL}\_macro_daily\_{YYYYMMDD}.csv）是宏观层与执行层的唯一共享边界，任何模块不得修改其格式。**

  --------------------------------------------------------------------------------------
  **字段名**              **格式**                   **说明**
  ----------------------- -------------------------- -----------------------------------
  row_type                SUMMARY 或 FACTOR          SUMMARY=汇总行，FACTOR=因子明细行

  symbol                  如 RU/CU/AU/AG             品种代码

  direction               LONG / SHORT / NEUTRAL     方向信号

  composite_score         浮点数（0\~100）           综合评分，NEUTRAL时≈50

  confidence              HIGH / MEDIUM / LOW        信号置信度，Low时不交易

  updated_at              ISO8601时间戳              信号生成时间

  factor_name /           因子名/因子标准化值/权重   FACTOR行才有
  factor_value /                                     
  factor_weight                                      
  --------------------------------------------------------------------------------------

## 7.2 REST API 接口（FastAPI宏观层）

  ---------------------------------------------------------------------------------------------------------------------------
  **方法**          **端点**                                   **说明**                   **响应示例**
  ----------------- ------------------------------------------ -------------------------- -----------------------------------
  GET               /api/macro/signal/all                      所有品种最新信号           { symbols: \[{symbol, direction,
                                                                                          score, confidence, updatedAt}\] }

  GET               /api/macro/signal/{symbol}                 单品种信号（含因子明细）   { symbol, direction, score,
                                                                                          confidence, factors: \[{name,
                                                                                          value, weight}\], updatedAt }

  GET               /api/macro/factor/{symbol}                 因子明细                   等同于 /signal/{symbol}.factors

  GET               /api/macro/score-history/{symbol}?days=N   历史打分（来自CSV          { dates: \[\], scores: \[\],
                                                               backfill）                 directions: \[\] }

  WS                /ws/macro_updates                          WebSocket实时推送          每日14:30打分完成后推送全品种信号

  GET               /api/macro/health                          服务健康检查               { status: \"ok\", version:
                                                                                          \"ctp\"\|\"cache\", last_update }
  ---------------------------------------------------------------------------------------------------------------------------

## 7.3 VNpy 事件类型（EventEngine）

VNpy 原生事件类型（全部可用）：

**本系统自定义事件：**

  -------------------------------------------------------------------------------------------
  **事件类型**            **数据**                **说明**
  ----------------------- ----------------------- -------------------------------------------
  eTick                   TickData                行情数据到达（每Tick一次）

  eBar                    BarData                 K线闭合（由BarGenerator触发）

  eTrade                  TradeData               订单成交

  eOrder                  OrderData               订单状态变化

  ePosition               PositionData            持仓变化

  eAccount                AccountData             账户资金变化

  eContract               ContractData            合约信息推送

  eError                  str                     错误信息

  eLog                    LogData                 日志消息

  eDataSourceAlert        dict                    数据源告警（降级/恢复），DataAdapterChain
                                                  发布

  eRiskRule               dict                    风控规则触发（未来扩展）

  eMacroSignal            dict                    宏观信号更新（未来可接入 VNpy 事件流）
  -------------------------------------------------------------------------------------------

# 第八章 命名规范

  --------------------------------------------------------------------------------------------------------------------
  **对象**               **格式**                          **示例**                   **备注**          **来源**
  ---------------------- --------------------------------- -------------------------- ----------------- --------------
  类名                   PascalCase                        如 MacroDemoStrategy,      VNpy一致          
                                                           RiskContext, WeightEngine                    

  方法名                 snake_case                        如 load_macro_signal,      VNpy一致          
                                                           calculate_weight, on_bar                     

  因子代码               品种_因子名（英文全大写下划线）   如 RU_TS_ROLL_YIELD,       见下方详细说明    
                                                           CU_LME_SPREAD_DIFF                           

  YAML文件名             品种_说明.yaml                    如 RU_TS_ROLL_YIELD.yaml,  配置层命名        
                                                           CU_INV_SHFE.yaml                             

  Python文件名（爬虫）   品种_中文说明.py                  如 CU_抓取LME库存.py,      数据采集脚本      
                                                           AG_抓取黄金白银比.py                         

  因子名称（YAML         中文自由文本                      如                         因子元数据        
  name字段）                                               \"RU近月合约滚动收益率\"                     

  配置键                 snake_case                        如                         YAML配置          
                                                           signal_zscore_threshold,                     
                                                           ic_window_days                               

  CSV字段名              camelCase                         如 compositeScore,         API响应JSON       
                                                           rowType, updatedAt                           

  VNpy事件               eXxxXxx 格式                      如 eDataSourceAlert,       自定义事件        
                                                           eRiskRule, eMacroSignal                      

  策略参数               snake_case（小写+下划线）         如 fast_window,            CtaTemplate一致   
                                                           stop_loss_atr_mult                           

  枚举值                 全大写                            如 LONG, SHORT, NEUTRAL,   VNpy.constant     
                                                           TREND, RANGE                                 
  --------------------------------------------------------------------------------------------------------------------

## 8.1 因子代码详细规则

因子代码格式：品种_因子类别_具体描述，全大写，下划线分隔，不超过30字符。

- **RU_TS_ROLL_YIELD：**RU=橡胶, TS=期限结构, ROLL_YIELD=滚动收益率

- **CU_LME_SPREAD_DIFF：**CU=铜, LME=伦敦金属, SPREAD_DIFF=升贴水变化

- **AU_MACRO_GOLD_SILVER_RATIO：**AU=黄金, MACRO=宏观,
  GOLD_SILVER_RATIO=金银比

- **AG_POS_CFTC_NET：**AG=白银, POS=持仓, CFTC_NET=CFTC净持仓

- **RU_INV_QINGDAO：**RU=橡胶, INV=库存, QINGDAO=青岛仓库

# 第九章 部署与运维

## 9.1 当前运行模式

**当前系统为双进程架构：**

  ----------------------------------------------------------------------------------------------
  **进程**                 **启动命令**                               **说明**
  ------------------------ ------------------------------------------ --------------------------
  进程1（VNpy执行层）      python D:\\futures_v6\\run.py              GUI界面 + CTP连接 +
                                                                      策略运行

  进程2（FastAPI宏观层）   uvicorn                                    端口8000，无UI
                           D:\\futures_v6\\api.macro_api_server:app   

  定时任务（日终打分）     schtasks每日14:30                          执行
                                                                      scripts/daily_scoring.py

  前端（可选）             cd D:\\futures_v6\\frontend && npm run dev 端口5173
  ----------------------------------------------------------------------------------------------

## 9.2 日志文件

- **VNpy日志：**D:\\futures_v6\\logs\\ --- 策略日志 + 网关日志

- **API日志：**D:\\futures_v6\\api\\api_server.log --- FastAPI请求日志

- **审计日志：**\~/.vntrader/audit.db --- SQLite，表：audit_log（90d）/
  event_queue（7d）

- **因子输出：**D:\\futures_v6\\macro_engine\\output\\ ---
  每日CSV信号文件

## 9.3 日常运维

- **查看API状态：**curl http://localhost:8000/api/macro/health

- → 检查宏观层是否正常运行

- **查看实时信号：**curl http://localhost:8000/api/macro/signal/all

- → JSON格式全品种信号

- **检查数据采集：**python D:\\futures_v6\\api\\trigger_collection.py

- → 手动触发当日因子采集

- **检查定时任务：**schtasks /query /tn \"FuturesMacro_DailyScoring\"

- → 确认14:30日终任务状态

- **审计日志备份：**sqlite3 \~/.vntrader/audit.db \".backup
  audit_backup.db\"

- → 定期备份

- **清理历史日志：**python
  D:\\futures_v6\\run.py（AuditService自动清理）

- → 90d/7d自动

# 附录A 快速启动脚本

\@echo off\
chcp 65001 \> nul\
echo =================== V6.0 系统启动 ===================\
\
echo \[1/3\] 启动宏观层 API（后台）\...\
start \"MacroAPI\" cmd /k \"cd /d D:\\futures_v6\\api && python
macro_api_server.py\"\
\
echo \[2/3\] 等待API就绪（5秒）\...\
timeout /t 5 /nobreak \> nul\
\
echo \[3/3\] 启动VNpy执行层\...\
python D:\\futures_v6\\run.py\
\
pause

# 附录B 关键文件清单

  ---------------------------------------------------------------------------------------------------
  **路径**                                                        **说明**
  --------------------------------------------------------------- -----------------------------------
  D:\\futures_v6\\run.py                                          VNpy主入口，MainEngine初始化

  D:\\futures_v6\\api\\macro_api_server.py                        FastAPI宏观服务，端口8000

  D:\\futures_v6\\macro_engine\\scripts\\daily_scoring.py         日终打分定时任务

  D:\\futures_v6\\strategies\\macro_demo_strategy.py              宏观共振策略

  D:\\futures_v6\\strategies\\multi_factor_strategy.py            多因子技术策略

  D:\\futures_v6\\macro_engine\\core\\scoring\\weight_engine.py   IC权重计算

  D:\\futures_v6\\macro_engine\\config\\factor_meta.json          因子元数据与权重

  D:\\futures_v6\\macro_engine\\output\\                          CSV信号输出目录

  D:\\futures_v6\\frontend\\                                      React前端（Vite 5173）

  C:\\Users\\Administrator\\strategies\\macro_demo_strategy.py    （旧位置，已迁移）
  ---------------------------------------------------------------------------------------------------
