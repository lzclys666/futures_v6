# EC 因子采集脚本 — 复查报告

**复查时间:** 2026-05-02 09:24 GMT+8  
**复查人:** mimo  
**工作目录:** `D:\futures_v6\macro_engine\crawlers\EC\`

---

## 一、脚本清单

| 脚本 | 状态 | 关键问题 |
|------|------|----------|
| `EC_run_all.py` | ⚠️ 可运行但不规范 | 无 docstring、无 type hints、使用 print 而非 logging |
| `EC_欧线期货收盘价.py` | ⛔ 无法运行 | **缺少 `import sys`**、**缺少 `import datetime`** |
| `EC_欧线期货持仓量.py` | ⛔ 无法运行 | **缺少 `import sys`**、**缺少 `import datetime`** |

---

## 二、逐项范式检查

### 2.1 EC_run_all.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ❌ | 无任何文档说明 |
| try-except | ✅ | 有 `except Exception as e` |
| timeout | ✅ | subprocess.run(timeout=30) |
| 魔法数字 | ✅ | SCRIPTS 列表、SCRIPT_DIR 常量 |
| 类型注解 | ❌ | 无任何类型标注 |
| 日志记录 | ❌ | 仅用 print，无 logging 模块 |
| CSV 规范 | N/A | 纯调度脚本 |
| 中文文件名 | ✅ | 通过变量 s 引用，无硬编码 |
| 中断恢复 | ❌ | 无 |

### 2.2 EC_欧线期货收盘价.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ✅ | 有，符合 Header 规范 |
| try-except | ✅ | `except Exception as e`（可接受） |
| timeout | ❌ | `ak.futures_main_sina()` 无 timeout 参数 |
| 魔法数字 | ✅ | FCODE/SYM/EMIN/EMAX 均为常量 |
| 类型注解 | ❌ | `fetch()` 和 `main()` 均无返回类型标注 |
| 日志记录 | ⚠️ | 使用 print，无 logging 模块 |
| CSV/DB 输出 | ✅ | 通过 db_utils 写入 pit_data.db |
| 中文文件名 | ✅ | 用 db_utils，无硬编码 |
| 中断恢复 | ✅ | L4 兜底逻辑存在 |
| **可运行性** | ⛔ | **NameError: name 'sys' is not defined** |

**实际字节验证（`import sys` 丢失）:**
```
Line 16: b'"""\r'
Line 17: b"sys.path.insert(0, 'd:/futures_v6/macro_engine/crawlers/common')\r"  ← sys 未导入
Line 18: b'from db_utils import save_to_db, get_latest_value\r'
Line 19: b'import akshare as ak\r'
Line 20: b'import pandas as pd\r'
```
**Line 17 直接使用 `sys.path.insert()` 但前面没有 `import sys` 语句。**

**`datetime` 同样缺失:**
```
Line 51: b"    save_to_db(FCODE, SYM, datetime.date.today(), obs_date, raw_value, source_co"
```
调用 `datetime.date.today()` 但无 `import datetime`。

### 2.3 EC_欧线期货持仓量.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ✅ | 有，符合 Header 规范 |
| try-except | ✅ | `except Exception as e` |
| timeout | ❌ | `ak.futures_main_sina()` 无 timeout |
| 魔法数字 | ✅ | FCODE/SYM/EMIN/EMAX 均为常量 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | 使用 print，无 logging 模块 |
| CSV/DB 输出 | ✅ | 通过 db_utils |
| 中文文件名 | ✅ | 无硬编码 |
| 中断恢复 | ✅ | L4 兜底逻辑存在 |
| **可运行性** | ⛔ | **NameError: name 'sys' is not defined** |

**与收盘价脚本问题完全一致：缺失 `import sys` 和 `import datetime`。**

---

## 三、运行验证

### EC_run_all.py 执行日志

```
==================================================
EC @ 2026-05-02T09:24:57.333212
==================================================
>> EC_欧线期货收盘价.py
>> EC_欧线期货持仓量.py
==================================================
EC Done 0.1s OK=0/2
==================================================
```

**两个子脚本均在 0.1s 内失败，OK=0/2。**

### 子脚本单独执行（EC_欧线期货收盘价.py）

```
Traceback (most recent call last):
  File "D:\futures_v6\macro_engine\crawlers\EC\EC_欧线期货收盘价.py", line 17, in <module>
    sys.path.insert(0, 'd:/futures_v6/macro_engine/crawlers/common')
    ^^^
NameError: name 'sys' is not defined
```

---

## 四、根本原因

两个因子脚本的 `import sys` 和 `import datetime` 语句被意外删除。

脚本原始应该包含（但在当前文件中缺失）:
```python
import sys        # 用于 sys.path.insert
import datetime   # 用于 datetime.date.today()
```

文件第 17 行直接调用 `sys.path.insert()` 但前面没有 `import sys`，导致 Python 在解析阶段（不是运行时）就抛出 `NameError`。

---

## 五、修复方案

**对 EC_欧线期货收盘价.py 和 EC_欧线期货持仓量.py 均需：**

在 `"""..."""` 闭合后、第一条语句前，插入：

```python
import sys
import datetime
```

完整 import 块应为：
```python
import sys
import datetime
from db_utils import save_to_db, get_latest_value
import akshare as ak
import pandas as pd
```

---

## 六、README.md 问题

当前 README.md 存在**品种名与内容严重不符**：

| README 声明 | 脚本实际内容 |
|-------------|--------------|
| EC — 玉米 | 脚本 docstring 为"欧线期货" |
| 品种代码 EC | 欧线期货（欧洲集装箱运费） |
| 交易所 DCE | 欧线期货在 IF（国际能源交易所）|
| 合约代码 C | 欧线期货代码为 EC0/EC1... |

**建议：** README 顶部品种信息需全面修正，或由因子分析师确认品种定义。

---

## 七、摘要

- ✅ Header 规范：符合（有 docstring 模板）
- ✅ 四层漏斗逻辑：存在（L4 兜底）
- ✅ 魔法数字：已常量化管理
- ⛔ **无法运行**：缺失 `import sys` 和 `import datetime`（两个脚本均如此）
- ❌ 无 timeout 配置（AKShare 网络请求）
- ❌ 无类型注解
- ❌ 使用 print 而非 logging 模块
- ⚠️ README.md 品种信息与脚本内容不符

**优先级：P0**（阻塞性问题，脚本完全无法运行）
