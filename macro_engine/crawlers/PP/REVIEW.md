# PP 因子采集脚本复查报告

**复查时间**: 2026-05-02 10:00  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\PP\`  
**复查人**: mimo subagent

---

## 一、脚本清单（共12个）

| # | 脚本名 | 状态 | 数据源 | 备注 |
|---|--------|------|--------|------|
| 1 | PP_CFR中国丙烯到岸价格.py | ⚠️ Stub | 无（L4占位） | 付费源待配 |
| 2 | PP_拉丝-共聚价差.py | ⚠️ Stub | 无（L4占位） | 付费源待配 |
| 3 | PP_线型低密度聚乙烯-聚丙烯价差.py | ⚠️ Stub | 无（L4占位） | AKShare待验证 |
| 4 | PP_聚丙烯仓单库存.py | ⚠️ Stub | 无（L4占位） | DCE接口待验证 |
| 5 | PP_聚丙烯期现基差.py | ⚠️ Stub | 无（L4占位） | 付费源待配 |
| 6 | PP_聚丙烯期货净持仓.py | ⚠️ Stub | 无（L4占位） | DCE接口待验证 |
| 7 | PP_聚丙烯期货收盘价.py | ✅ 运行正常 | AKShare L1 | 实际有数据 |
| 8 | PP_聚丙烯期货持仓量.py | ✅ 运行正常 | AKShare L1 | 实际有数据 |
| 9 | PP_聚丙烯港口库存.py | ⚠️ Stub | 无（L4占位） | 付费源待配 |
| 10 | PP_聚丙烯袋装比例.py | ⚠️ Stub | 无（L4占位） | 付费源待配 |
| 11 | PP_聚丙烯装置开工率.py | ⚠️ Stub | 无（L4占位） | 付费源待配 |
| 12 | PP_run_all.py | ✅ 运行正常 | 编排器 | 2/2成功 |

---

## 二、范式检查逐项结果

### PP_run_all.py（编排器）
- [✅] 脚本头部有 docstring
- [✅] try-except 错误处理（有 timeout + exception 分支）
- [✅] 网络请求有超时（subprocess timeout=120）
- [⚠️] 魔法数字部分：`"="*50` 分割线、`timeout=120` 硬编码
- [❌] 无类型注解（`run_all` 函数无 `-> None` 等）
- [✅] 日志记录完善（INFO级别日志写文件）
- [N/A] 数据不写 CSV，走 db_utils
- [N/A] 无中文文件名问题
- [N/A] 中断/恢复逻辑：subprocess 模式天然隔离

### PP_聚丙烯期货收盘价.py / PP_聚丙烯期货持仓量.py（实际运行脚本）
- [✅] 脚本头部有 docstring
- [✅] try-except 错误处理（两层：AKShare 失败 → L4 fallback）
- [⚠️] 无网络请求 timeout（akshare 调用未设 timeout 参数）
- [⚠️] 魔法数字：`"PP0"` 硬编码合约代码，`120` 秒重试等未提取常量
- [❌] 无类型注解（`main()` 函数无返回值类型标注 `-> int`）
- [✅] 日志记录（print/sys.stdout.write 分级输出 `[L1]` `[L4]` `[WARN]`）
- [N/A] 数据写 db，不走 CSV
- [N/A] 无中文文件名
- [N/A] 不需要中断恢复

### 其余10个 Stub 脚本（统一问题模式）
- [✅] 脚本头部有 docstring
- [✅] try-except（有 `except Exception as e`）
- [⚠️] 无网络请求（跳过数据采集，直接写 stub）
- [✅] 魔法数字全部定义为顶部常量 `_FACTOR_*`
- [❌] 无类型注解（`run(auto=False)` 无 `-> int`）
- [✅] 日志记录（`print("[跳过]")`、`print("[OK]")`、`print("[WARN]")`）
- [N/A] 不涉及 CSV
- [N/A] 无中文文件名
- [N/A] 无需中断恢复

---

## 三、运行验证

**执行命令**: `python PP_run_all.py --auto`

```
PP Data Collection @ 2026-05-02 10:00:15.115935
Scripts: 2
==================================================
>>> PP_聚丙烯期货收盘价.py...
[OK] PP_聚丙烯期货收盘价.py done
>>> PP_聚丙烯期货持仓量.py...
[OK] PP_聚丙烯期货持仓量.py done
==================================================
PP Done  3.3s  2/2
[OK] All done
==================================================
```

**日志写入数据确认**（来源: `crawlers/logs/*PP*.log`）：
```
[L1] PP_FUT_CLOSE=8822.0 (2026-04-30) done
[DB] 写入成功: PP_FUT_CLOSE = 8822.0
[L1] PP_FUT_OI=443162.0 (2026-04-30) done
[DB] 写入成功: PP_FUT_OI = 443162.0
[Done] 2/2
```

⚠️ **注意**：日志文件存在编码问题，中文字符显示为乱码（`鑱氫笝鐑` 等），但数据写入本身正常。

---

## 四、主要问题汇总

| 优先级 | 问题 | 影响脚本 |
|--------|------|----------|
| 🔴 高 | 仅2/12脚本实际采集数据，10个Stub无真实数据源 | 10个因子 |
| 🔴 高 | 无 README.md（规范要求必须存在） | 全部 |
| 🟡 中 | 10个Stub脚本状态标记为"待修复"但超过1个月无进展 | 全部Stub |
| 🟡 中 | AKShare调用无 timeout 参数（网络异常可能hang） | PP期货收盘价/持仓量 |
| 🟡 中 | 函数无类型注解（`main() -> int`、`run(auto=False) -> int`） | 全部脚本 |
| 🟡 中 | 日志中文乱码（subprocess + UTF-8配置失效） | PP_run_all.py |
| 🟢 低 | 魔法数字（如 `PP0` 合约代码、`timeout=120`）未提取常量 | PP期货相关脚本 |
| 🟢 低 | 编排器 `scripts` 列表只有2个脚本，未覆盖全部12个 | PP_run_all.py |

---

## 五、行动建议

1. **立即**：创建 README.md（参考模板见下方）
2. **高优先级**：为10个Stub脚本配置真实数据源（优先尝试AKShare四层漏斗）
3. **中优先级**：为AKShare调用添加 `timeout=30` 参数
4. **中优先级**：统一为所有函数添加类型注解
5. **低优先级**：修正日志编码（`sys.stdout.reconfigure` 在 subprocess 中可能失效，需改用 `encoding='utf-8'` 在 subprocess.run 中传递）

---

## 六、README.md 更新内容

见同目录下 `README.md`
