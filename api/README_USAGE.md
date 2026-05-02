# 因子数据采集框架使用指南

## 📁 文件结构

```
scripts/
├── factor_collector.py          # 主采集脚本
├── collectors/
│   ├── __init__.py
│   ├── akshare_collector.py     # AKShare 数据源
│   ├── tushare_collector.py     # Tushare 数据源
│   └── custom_collector.py      # 自定义爬虫
└── README_USAGE.md              # 本文档
```

---

## 🚀 快速开始

### 方式 A：手动触发（推荐）

#### 步骤 1：填写因子需求文件

复制模板并填写：

```bash
cp templates/factor_requirements_minimal_template.json factor_requirements.json
```

编辑 `factor_requirements.json`，添加你的因子需求。

#### 步骤 2：运行触发器（自动启动 mimo 子会话）

```bash
cd scripts
python trigger_collection.py ../factor_requirements.json
```

触发器会：
1. 验证需求文件格式
2. 启动 mimo 子会话
3. 传递文件路径（不传递完整 JSON）
4. 返回子会话状态

#### 步骤 3：查看结果

- **数据文件**: `data/raw_factors/{品种代码}/{因子代码}.csv`
- **采集摘要**: `data/collection_summary_{task_id}.json`
- **错误日志**: `logs/collection_errors_{task_id}.log`

---

### 方式 B：直接运行采集脚本

```bash
cd scripts
python factor_collector.py ../factor_requirements.json
```

适用于：
- 测试单个因子采集
- 调试数据源接口
- 不想要子会话隔离的场景

---

## 📝 示例：采集橡胶展期收益率

### 1. 创建需求文件

```json
{
  "task_info": {
    "created_at": "2026-04-16T13:00:00+08:00",
    "task_id": "TASK-20260416-003"
  },
  "factors": [
    {
      "factor_code": "RU_TS_ROLL_YIELD",
      "commodity": "RU",
      "data_source": "akshare",
      "api_params": {
        "function": "futures_main_sina",
        "symbol": "ru",
        "exchange": "shfe"
      },
      "output_path": "data/raw_factors/RU/",
      "priority": 1,
      "description": "橡胶主力合约日线数据"
    }
  ],
  "execution_order": ["RU_TS_ROLL_YIELD"],
  "global_config": {
    "stop_on_error": false
  }
}
```

### 2. 运行采集

```bash
python factor_collector.py factor_requirements.json
```

### 3. 输出

```
[启动] 任务 TASK-20260416-003，共 1 个因子
[1/1] 采集 RU_TS_ROLL_YIELD...
  ✓ 成功 -> data/raw_factors/RU/RU_TS_ROLL_YIELD.csv

[完成] 摘要已保存：data/collection_summary_TASK-20260416-003.json

==================================================
✅ 采集完成
  - 成功：1 因子
  - 失败：0 因子
  - 耗时：2.34 秒
==================================================
```

---

## ⚙️ 配置说明

### 数据源配置

#### AKShare（免费）
```json
{
  "data_source": "akshare",
  "api_params": {
    "function": "futures_main_sina",
    "symbol": "ru",
    "exchange": "shfe"
  }
}
```

#### Tushare（需 token）
```json
{
  "data_source": "tushare",
  "api_params": {
    "api_name": "cn_cpi",
    "params": {
      "start_date": "202001",
      "end_date": "202603"
    }
  }
}
```

**注意**: 使用 Tushare 前需设置环境变量：
```bash
set TUSHARE_TOKEN=your_token_here
```

#### Wind（商业数据源）
```json
{
  "data_source": "wind",
  "api_params": {
    "function": "wsd",
    "codes": ["RU2405.SHF", "RB2405.SHF"],
    "fields": ["open", "high", "low", "close", "volume"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }
}
```

**注意**: 
- 需要在安装了 Wind 终端的机器上运行
- 自动使用当前登录的 Wind 账号

#### 聚宽 JoinQuant（免费）
```json
{
  "data_source": "joinquant",
  "api_params": {
    "function": "get_futures_daily",
    "code": "ru2405.XSHG",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }
}
```

**注意**: 使用前需设置环境变量：
```bash
set JQ_USER=your_username
set JQ_PASS=your_password
```

#### 优矿 Uqer（通联数据）
```json
{
  "data_source": "uqer",
  "api_params": {
    "function": "futuresBar",
    "instrument": "RU2405.SHF",
    "beginDate": "20240101",
    "endDate": "20241231",
    "frequency": "D"
  }
}
```

**注意**: 使用前需设置环境变量：
```bash
set UQER_TOKEN=your_token_here
```

#### 交易所官网爬虫（免费）
```json
{
  "data_source": "exchange",
  "api_params": {
    "exchange": "SHFE",
    "crawler_type": "daily_data",
    "trade_date": "20240415",
    "product": "ru"
  }
}
```

**支持交易所**:
- `SHFE`: 上期所（铜、铝、锌、铅、镍、锡、黄金、白银、螺纹钢、橡胶等）
- `DCE`: 大商所（豆粕、豆油、棕榈油、玉米、焦煤、焦炭等）
- `CZCE`: 郑商所（白糖、棉花、PTA、甲醇、玻璃等）
- `CFFEX`: 中金所（股指期货、国债期货）
- `INE`: 原油中心（原油、低硫燃料油、20 号胶等）

**爬虫类型**:
- `daily_data`: 日线行情数据
- `settlement`: 结算数据
- `warehouse_receipt`: 仓单数据（仅上期所）

#### 自定义爬虫
```json
{
  "data_source": "custom",
  "api_params": {
    "type": "web_scrape",
    "url": "https://example.com/data",
    "selector": ".data-table tr"
  }
}
```

### 重试策略

```json
{
  "retry_config": {
    "max_retries": 3,
    "retry_interval_sec": 60,
    "fallback_strategy": "skip_and_log"
  }
}
```

- `max_retries`: 最大重试次数（默认 3）
- `retry_interval_sec`: 重试间隔秒数（默认 60）
- `fallback_strategy`: 失败策略
  - `skip_and_log`: 跳过并记录日志
  - `manual_intervention`: 需要人工介入

### PIT 数据要求

```json
{
  "pit_requirement": {
    "need_pit": true,
    "pivot_date_field": "trade_date",
    "observation_date_field": "obs_date"
  }
}
```

---

## 🐛 错误处理

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `AKShare 不存在函数` | 函数名拼写错误 | 检查 AKShare 文档确认函数名 |
| `Tushare 积分不足` | 接口需要更高积分 | 升级 Tushare 积分或换用其他数据源 |
| `网络请求超时` | 网络不稳定 | 增加 `retry_interval_sec` 或检查网络 |
| `文件不存在` | 自定义文件路径错误 | 检查 `file_path` 是否正确 |

### 查看错误日志

```bash
# 查看最新错误日志
type logs\collection_errors_TASK-20260416-003.log
```

---

## 📊 Token 节省技巧

### 1. 批量采集
一次性添加多个因子到 `factor_requirements.json`，而不是多次运行脚本。

### 2. 精简输出
脚本默认只输出极简摘要，详细日志写入文件。

### 3. 子会话隔离
在 OpenClaw 中使用子会话运行采集任务：

```python
sessions_spawn(
    runtime="subagent",
    mode="run",
    task="读取 factor_requirements.json 执行采集",
    label="mimo-data-collector",
    cleanup="delete"
)
```

### 4. 文件传递
因子分析师和程序员 mimo 之间通过文件传递需求，不在对话中传递完整 JSON。

---

## 🔧 扩展新数据源

### 步骤 1：创建采集器文件

在 `collectors/` 目录下创建新的采集器文件：

```python
# collectors/wind_collector.py
import pandas as pd
from typing import Dict, Any

def collect_wind(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集 Wind 数据"""
    # 实现采集逻辑
    pass
```

### 步骤 2：注册到主脚本

在 `factor_collector.py` 中添加到 `COLLECTOR_MAP`：

```python
from wind_collector import collect_wind

COLLECTOR_MAP = {
    "akshare": collect_akshare,
    "tushare": collect_tushare,
    "custom": collect_custom,
    "wind": collect_wind,  # 新增
}
```

---

## 📚 相关文档

- `templates/factor_requirements_template.json` - 完整版模板
- `templates/factor_requirements_minimal_template.json` - 精简版模板
- `templates/factor_requirements_field_guide.md` - 字段说明

---

## 📞 问题反馈

遇到问题请查看错误日志，或联系项目经理。
