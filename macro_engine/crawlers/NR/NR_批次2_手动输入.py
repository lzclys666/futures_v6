#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次2_手动输入
因子: 待定义 = 批次2_手动输入

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db, get_latest_value

SYMBOL = "NR"

FACTORS = [
    {
        "code": "NR_SUP_ANRPC_PROD",
        "name": "ANRPC成员国天胶产量",
        "unit": "万吨",
        "bounds": (50, 200),
        "source": "ANRPC官网(付费订阅)",
        "hint": "ANRPC月度天然橡胶产量，成员国合计",
    },
    {
        "code": "NR_SUP_HATYAI_CUP",
        "name": "合艾杯胶价格",
        "unit": "泰铢/公斤",
        "bounds": (20, 80),
        "source": "Thai Rubber Association(付费)",
        "hint": "Hat Yai Cup Lump价格，Thai Rubber Association官网发布",
    },
    {
        "code": "NR_SUP_HATYAI_LATEX",
        "name": "合艾桶装浓缩乳胶",
        "unit": "泰铢/公斤",
        "bounds": (30, 100),
        "source": "Thai Rubber Association(付费)",
        "hint": "Hat Yai Bulk Concentrated Latex价格",
    },
    {
        "code": "NR_SUP_HATYAI_RSS3",
        "name": "合艾RSS3价格",
        "unit": "泰铢/公斤",
        "bounds": (40, 120),
        "source": "Thai Rubber Association(付费)",
        "hint": "Hat Yai RSS3价格",
    },
    {
        "code": "NR_SUP_RSS3_FOB",
        "name": "RSS3 FOB报价",
        "unit": "美分/磅",
        "bounds": (80, 300),
        "source": "SICOM/隆众资讯(付费)",
        "hint": "RSS3 FOB报价，换算为美分/磅",
    },
    {
        "code": "NR_CST_SEA_FREIGHT",
        "name": "泰港至中国主港运费",
        "unit": "美元/吨",
        "bounds": (5, 60),
        "source": "VLCC运费(付费)",
        "hint": "橡胶船运费，波斯湾至中国主港",
    },
    {
        "code": "NR_DEM_TIRE_EXPO",
        "name": "轮胎出口量",
        "unit": "万条/月",
        "bounds": (500, 10000),
        "source": "中国海关(付费)/隆众资讯",
        "hint": "中国橡胶轮胎出口量（万条/月）",
    },
]


def try_free_fx():
    """L1: 新浪财经免费获取 USDCNY"""
    try:
        from common.web_utils import fetch_url
        html, err = fetch_url(
            "https://hq.sinajs.cn/list=fx_susdcny",
            headers={"Referer": "https://finance.sina.com.cn"},
            timeout=5
        )
        if err:
            return None
        m = re.search(r'"([^"]+)"', html)
        if m:
            parts = m.group(1).split(',')
            if len(parts) > 0:
                val = float(parts[0])
                if 6.0 < val < 8.0:
                    return val
    except Exception:
        pass
    return None


def main():
    ensure_table()
    import argparse
    from datetime import date

    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    is_auto = args.auto

    today = date.today()
    pub_date = today.isoformat()
    obs_date = pub_date

    print(f"=" * 56)
    print(f"  NR批次2  付费因子手动录入  @ {pub_date}")
    print(f"=" * 56)

    if is_auto:
        print("[AUTO] 跳过付费因子，尝试免费替代...\n")
        # USDCNY 免费获取
        fx = try_free_fx()
        if fx:
            save_to_db("NR_CST_USDCNY", SYMBOL, pub_date, obs_date, fx,
                       source_confidence=1.0, source="新浪财经fx_susdcny")
            print(f"[OK] NR_CST_USDCNY={fx} 免费获取成功\n")
        else:
            val = get_latest_value("NR_CST_USDCNY", SYMBOL)
            if val:
                save_to_db("NR_CST_USDCNY", SYMBOL, pub_date, obs_date, val,
                           source_confidence=0.5, source="db_回补")
                print(f"[OK] NR_CST_USDCNY={val} L4回补成功\n")
            else:
                print(" NR_CST_USDCNY 无数据（需手动录入）\n")
        print("[AUTO] 完成（付费因子需手动录入）")
        return 0

    # 交互模式
    written = 0
    for f in FACTORS:
        code = f["code"]
        print(f"--- {code} ({f['name']}) ---")
        print(f"  单位: {f['unit']}  |  合理范围: {f['bounds']}")
        print(f"  数据源: {f['source']}")
        print(f"  提示: {f['hint']}")

        try:
            val_str = input(f"  输入 {code}（留空跳过）: ").strip()
        except EOFError:
            print("  （非交互，跳过）\n")
            continue

        if not val_str:
            print("  跳过\n")
            continue

        try:
            val = float(val_str)
        except ValueError:
            print("  无效数字，跳过\n")
            continue

        lo, hi = f["bounds"]
        if not (lo <= val <= hi):
            print(f"   值 {val} 超出 [{lo},{hi}]，确认[Y]: ", end="")
            try:
                confirm = input().strip().upper()
            except EOFError:
                confirm = "N"
            if confirm != "Y":
                print("  跳过\n")
                continue

        save_to_db(code, SYMBOL, pub_date, obs_date, val,
                   source_confidence=0.8, source=f["source"])
        print(f"[OK] {code}={val} ({f['unit']}) 写入成功\n")
        written += 1

    print(f"=" * 56)
    print(f"完成，共写入 {written} 个因子")
    print("=" * 56)


if __name__ == "__main__":
    exit(main())
