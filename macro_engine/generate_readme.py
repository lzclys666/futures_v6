#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_readme.py - 为每个品种生成README.md"""
import os, sys, yaml

BASE = r"D:\futures_v6\macro_engine"
COMMON_DIR = os.path.join(BASE, "crawlers", "common")
sys.path.insert(0, COMMON_DIR)
DB_PATH = os.path.join(BASE, "pit_data.db")
DB_TABLE = "pit_factor_observations"  # 修正表名

# 品种元数据（中文名、交易所、合约代码模式）
META = {
    "AG":  ("白银",   "SHFE", "AG",   "贵金属"),
    "AL":  ("铝",     "SHFE", "AL",   "有色金属"),
    "AO":  ("豆一",   "DCE",  "A",    "农产品"),
    "AU":  ("黄金",   "SHFE", "AU",   "贵金属"),
    "BR":  ("合成橡胶","NR/SHFE","BR","能化"),
    "BU":  ("沥青",   "SHFE", "BU",   "能化"),
    "CU":  ("铜",     "SHFE", "CU",   "有色金属"),
    "EC":  ("玉米",   "DCE",  "C",    "农产品"),
    "I":   ("铁矿石", "DCE",  "I",    "黑色金属"),
    "JM":  ("焦煤",   "DCE",  "JM",   "黑色金属"),
    "LC":  ("鲜辣椒", "DCE",  "L",    "农产品"),
    "LH":  ("生猪",   "DCE",  "LH",   "农产品"),
    "M":   ("豆粕",   "DCE",  "M",    "农产品"),
    "NI":  ("镍",     "SHFE", "NI",   "有色金属"),
    "NR":  ("天然橡胶","NR/SHFE","NR","能化"),
    "P":   ("棕榈油", "DCE",  "P",    "农产品"),
    "RB":  ("螺纹钢", "SHFE", "RB",   "黑色金属"),
    "RU":  ("橡胶",   "SHFE", "RU",   "能化"),
    "SA":  ("纯碱",   "CZC",  "SA",   "能化"),
    "SC":  ("原油",   "INE",  "SC",   "能化"),
    "SN":  ("锡",     "SHFE", "SN",   "有色金属"),
    "TA":  ("PTA",    "CZC",  "TA",   "能化"),
    "ZN":  ("锌",     "SHFE", "ZN",   "有色金属"),
}

def get_scripts(sym):
    """获取品种所有py脚本"""
    d = os.path.join(BASE, "crawlers", sym)
    if not os.path.isdir(d):
        return []
    files = []
    for f in os.listdir(d):
        if f.endswith(".py"):
            files.append(f)
    return sorted(files)

def get_factors(sym):
    """读取品种所有YAML因子配置"""
    d = os.path.join(BASE, "config", "factors", sym)
    if not os.path.isdir(d):
        return []
    factors = []
    for f in os.listdir(d):
        if f.endswith(".yaml"):
            path = os.path.join(d, f)
            with open(path, "r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
            factors.append({"file": f, "data": data})
    return sorted(factors, key=lambda x: x["file"])

def get_db_stats(sym):
    """从数据库统计该品种因子数量和数据点数"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(DISTINCT factor_code) FROM {DB_TABLE} WHERE symbol=?", (sym,))
        fc_count = cur.fetchone()[0] or 0
        cur.execute(f"SELECT COUNT(*) FROM {DB_TABLE} WHERE symbol=?", (sym,))
        row_count = cur.fetchone()[0] or 0
        conn.close()
        return fc_count, row_count
    except:
        return 0, 0

def read_script_preview(path, max_lines=50):
    """读取脚本前几行，判断是否为stub"""
    if not os.path.isfile(path):
        return None, "文件不存在"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    text = content[:3000]  # 检查前3000字符
    # 永久跳过/废弃脚本（不写占位符）
    if "[跳过]" in text or "[跳过] 无免费" in text:
        return "stub", text
    if "[SKIP]" in text or "⛔" in text:
        return "stub", text
    if "永久跳过" in text or "已废弃" in text:
        return "stub", text
    if "return  # TODO" in text or "pass  # TODO" in text:
        return "stub", text
    if "INSERT OR REPLACE" in text:
        return "working", text
    if "save_to_db" in text:
        return "working", text
    return "unknown", text

def classify_scripts(scripts, sym):
    """分类脚本：working/stub/简单"""
    working, stubs, simple = [], [], []
    for s in scripts:
        if s.endswith("_run_all.py"):
            simple.append(s)
            continue
        path = os.path.join(BASE, "crawlers", sym, s)
        status, _ = read_script_preview(path)
        if status == "stub":
            stubs.append(s)
        elif status == "working":
            working.append(s)
        else:
            simple.append(s)
    return working, stubs, simple

def build_readme(sym):
    """为单个品种构建README内容"""
    meta = META.get(sym, (sym, "未知", sym, "未知"))
    name, exchange, code, category = meta

    scripts = get_scripts(sym)
    factors = get_factors(sym)
    fc_count, row_count = get_db_stats(sym)
    working, stubs, simple = classify_scripts(scripts, sym)

    # 数据源判断（从爬虫脚本中提取）
    sources = set()
    for s in scripts:
        if s.endswith("_run_all.py"):
            continue
        path = os.path.join(BASE, "crawlers", sym, s)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if "akshare" in content.lower():
                    sources.add("AKShare")
                if "sinajs" in content or "sina.com" in content:
                    sources.add("新浪财经")
                if "shfe" in content.lower() or "dce" in content.lower():
                    sources.add("交易所官网")
                if "东方财富" in content or "eastmoney" in content:
                    sources.add("东方财富")
                if "tushare" in content.lower():
                    sources.add("Tushare")
                if "FRED" in content or "fred" in content.lower():
                    sources.add("美联储FRED")
                if "付费" in content or "年费" in content or "mysteel" in content.lower():
                    sources.add("付费源(Mysteel/汾渭/隆众)")
            except:
                pass

    # 因子列表
    factor_lines = []
    for f in factors:
        fname = f["file"].replace(".yaml", "")
        data = f["data"]
        desc = ""
        if data and isinstance(data, dict):
            desc = data.get("description", "") or data.get("factor_group", "")
        factor_lines.append(f"- `{fname}` — {desc}")

    # 脚本状态表
    script_lines = []
    for s in working:
        script_lines.append(f"- `{s}` ✅")
    for s in simple:
        script_lines.append(f"- `{s}` 🔧")
    for s in stubs:
        script_lines.append(f"- `{s}` ⏸️（stub）")

    # 运行命令
    run_cmd = f"python crawlers/{sym}/{sym}_run_all.py --auto"

    lines = []
    lines.append(f"# {sym} — {name} 期货数据采集")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"| 字段 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 品种代码 | `{sym}` |")
    lines.append(f"| 中文名称 | {name} |")
    lines.append(f"| 交易所 | {exchange} |")
    lines.append(f"| 合约代码 | {code} |")
    lines.append(f"| 品种分类 | {category} |")
    lines.append(f"| 因子数量 | {len(factors)} |")
    lines.append(f"| 数据库因子数 | {fc_count} |")
    lines.append(f"| 数据库记录数 | {row_count} |")
    lines.append("")
    lines.append("## 数据源")
    lines.append("")
    if sources:
        lines.append("> " + " / ".join(sorted(sources)))
    else:
        lines.append("> 待扫描")
    lines.append("")
    lines.append("## 因子配置")
    lines.append("")
    if factor_lines:
        lines.extend(factor_lines)
    else:
        lines.append("_暂无YAML配置_")
    lines.append("")
    lines.append("## 爬虫脚本")
    lines.append("")
    lines.append(f"总计：{len(scripts)} 个脚本（working {len(working)} / simple {len(simple)} / stub {len(stubs)}）")
    lines.append("")
    if script_lines:
        lines.extend(script_lines)
    else:
        lines.append("_暂无脚本_")
    lines.append("")
    lines.append("## 运行方式")
    lines.append("")
    lines.append("```bash")
    lines.append(f"# 批量采集（推荐）")
    lines.append(f"{run_cmd}")
    lines.append(f"")
    lines.append(f"# 单脚本测试")
    lines.append(f"python crawlers/{sym}/<脚本名>.py --auto")
    lines.append("```")
    lines.append("")
    lines.append("## 状态摘要")
    lines.append("")
    if stubs:
        lines.append(f"> ⚠️ 存在 {len(stubs)} 个 stub 脚本，待因子分析师推送任务后开发")
    if working:
        lines.append(f"> ✅ {len(working)} 个脚本可正常运行")
    if not stubs and working:
        lines.append("> ✅ 全部脚本已就绪")
    from datetime import date
    today = date.today().isoformat()
    lines.append("")
    lines.append("---")
    lines.append(f"_生成时间: {today} | auto-generated by generate_readme.py_")

    return "\n".join(lines)


def main():
    syms = sorted([d for d in os.listdir(os.path.join(BASE, "crawlers"))
                   if os.path.isdir(os.path.join(BASE, "crawlers", d))
                   and d not in ("common", "logs", "__pycache__")])

    written = []
    for sym in syms:
        if sym not in META:
            continue  # 跳过不在元数据的目录
        content = build_readme(sym)
        readme_path = os.path.join(BASE, "crawlers", sym, "README.md")
        with open(readme_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(content)
        written.append(sym)
        print(f"[OK] {sym}/README.md")

    print(f"\n完成，共生成 {len(written)} 个 README.md")
    print("品种: " + ", ".join(written))

if __name__ == "__main__":
    main()
