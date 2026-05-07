#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dce_scraper.py
通用 DCE（大连商品交易所）数据抓取器

使用 Playwright chromium headless 浏览器绕过 DCE WAF 级 JS 挑战。
所有 HTTP 层方案（requests/AKShare/session）均返回 412，只有浏览器自动化能通过。

功能:
- fetch_dce_position_rank(date_str, symbol) — 获取指定日期、品种的持仓排名数据
- 结果缓存（同一天同一品种不重复请求）
- 返回 pandas DataFrame

DCE 持仓排名页面 URL 格式:
  http://www.dce.com.cn/publicweb/quotesdata/memberDealPosiQuotes.html
    ?memberDealPosiQuotes.variety={symbol小写}
    &memberDealPosiQuotes.trade_type=0
    &year={year}
    &month={month-1}  # DCE 月份从0开始！5月=4
    &day={day}
    &contract.contract_id=all
    &contract.variety_id={symbol小写}
"""

import os
import sys
import time
import datetime
import sqlite3
import pandas as pd
from typing import Optional, Tuple

# ============================================================
# 配置
# ============================================================

# 缓存数据库路径（与 pit_data.db 同目录）
_CACHE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pit_data.db")

# Playwright 超时配置（毫秒）
PAGE_TIMEOUT = 30000        # 页面加载超时
JS_CHALLENGE_WAIT = 5000    # 等待 JS 挑战通过
TABLE_WAIT = 10000          # 等待表格渲染

# 最大重试次数
MAX_RETRIES = 3


def _get_cache_table():
    """确保缓存表存在"""
    conn = sqlite3.connect(_CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dce_position_cache (
            date_str TEXT,
            symbol TEXT,
            data_json TEXT,
            cached_at TEXT,
            PRIMARY KEY (date_str, symbol)
        )
    """)
    conn.commit()
    conn.close()


def _get_cached(date_str: str, symbol: str) -> Optional[pd.DataFrame]:
    """从缓存获取数据"""
    _get_cache_table()
    conn = sqlite3.connect(_CACHE_DB)
    row = conn.execute(
        "SELECT data_json FROM dce_position_cache WHERE date_str=? AND symbol=?",
        (date_str, symbol.upper())
    ).fetchone()
    conn.close()
    if row:
        import json
        try:
            data = json.loads(row[0])
            return pd.DataFrame(data)
        except Exception:
            pass
    return None


def _set_cache(date_str: str, symbol: str, df: pd.DataFrame):
    """写入缓存"""
    import json
    _get_cache_table()
    data_json = json.dumps(df.to_dict(orient='records'), ensure_ascii=False)
    conn = sqlite3.connect(_CACHE_DB)
    conn.execute(
        "INSERT OR REPLACE INTO dce_position_cache (date_str, symbol, data_json, cached_at) VALUES (?, ?, ?, ?)",
        (date_str, symbol.upper(), data_json, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def fetch_dce_position_rank(date_str: str, symbol: str, use_cache: bool = True) -> Optional[pd.DataFrame]:
    """
    获取 DCE 持仓排名数据

    参数:
        date_str: 日期字符串，格式 'YYYYMMDD' 或 'YYYY-MM-DD'
        symbol: 品种代码，如 'LH', 'PP', 'EG' 等
        use_cache: 是否使用缓存（默认 True）

    返回:
        pandas DataFrame，包含持仓排名数据；失败返回 None

    DataFrame 列:
        名次, 会员简称, 持买仓量, 持买增减, 持卖仓量, 持卖增减
    """
    # 标准化日期
    date_str = date_str.replace('-', '')
    if len(date_str) != 8:
        print(f"[DCE] 无效日期格式: {date_str}，需要 YYYYMMDD")
        return None

    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    symbol_lower = symbol.lower()

    # 检查缓存
    if use_cache:
        cached = _get_cached(date_str, symbol)
        if cached is not None and not cached.empty:
            print(f"[DCE] 命中缓存: {symbol} {date_str} ({len(cached)} rows)")
            return cached

    # 构建 URL（DCE 月份从 0 开始！5月=4）
    url = (
        f"http://www.dce.com.cn/publicweb/quotesdata/memberDealPosiQuotes.html"
        f"?memberDealPosiQuotes.variety={symbol_lower}"
        f"&memberDealPosiQuotes.trade_type=0"
        f"&year={year}"
        f"&month={month - 1}"
        f"&day={day}"
        f"&contract.contract_id=all"
        f"&contract.variety_id={symbol_lower}"
    )

    print(f"[DCE] 请求: {symbol} {date_str}")
    print(f"[DCE] URL: {url}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = _fetch_with_playwright(url, symbol, date_str)
            if df is not None and not df.empty:
                _set_cache(date_str, symbol, df)
                print(f"[DCE] 成功: {symbol} {date_str} ({len(df)} rows)")
                return df
            else:
                print(f"[DCE] 尝试 {attempt}/{MAX_RETRIES}: 表格为空")
        except Exception as e:
            print(f"[DCE] 尝试 {attempt}/{MAX_RETRIES}: {type(e).__name__}: {str(e)[:200]}")

        if attempt < MAX_RETRIES:
            time.sleep(2)

    print(f"[DCE] 失败: {symbol} {date_str} 所有尝试均失败")
    return None


def _fetch_with_playwright(url: str, symbol: str, date_str: str) -> Optional[pd.DataFrame]:
    """使用 Playwright 抓取 DCE 页面"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        page = context.new_page()

        try:
            # 导航到页面，等待网络空闲（JS 挑战通过）
            page.goto(url, timeout=PAGE_TIMEOUT, wait_until='networkidle')
            print(f"[DCE] 页面加载完成，等待 JS 渲染...")

            # 额外等待表格渲染
            page.wait_for_timeout(JS_CHALLENGE_WAIT)

            # 等待表格出现
            table_selector = 'table.table_style'
            try:
                page.wait_for_selector(table_selector, timeout=TABLE_WAIT)
            except Exception:
                # 备用选择器
                table_selector = 'table'
                try:
                    page.wait_for_selector(table_selector, timeout=5000)
                except Exception:
                    print(f"[DCE] 未找到表格元素")
                    return None

            # 解析表格
            df = _parse_position_table(page, table_selector)
            return df

        finally:
            browser.close()


def _parse_position_table(page, table_selector: str) -> Optional[pd.DataFrame]:
    """解析 DCE 持仓排名表格"""
    # 获取所有表格
    tables = page.query_selector_all(table_selector)

    if not tables:
        print(f"[DCE] 页面无表格")
        return None

    # DCE 持仓排名通常有多个表（成交量、持买仓、持卖仓等）
    # 我们需要找包含 "持买仓量" 或 "持卖仓量" 的表格
    target_table = None
    for table in tables:
        text = table.inner_text()
        if '持买仓量' in text or '持卖仓量' in text or '持买仓' in text:
            target_table = table
            break

    if target_table is None:
        # 尝试用 pandas 直接读取所有表格
        print(f"[DCE] 未找到持仓排名表格，尝试读取所有表格...")
        html_content = page.content()
        try:
            dfs = pd.read_html(html_content)
            for df in dfs:
                cols = [str(c) for c in df.columns]
                if any('买' in c for c in cols) and any('卖' in c for c in cols):
                    return df
        except Exception as e:
            print(f"[DCE] pd.read_html 失败: {e}")
        return None

    # 从目标表格提取数据
    html = target_table.outer_html()
    try:
        dfs = pd.read_html(html)
        if dfs:
            df = dfs[0]
            # 清理列名
            df.columns = [str(c).strip() for c in df.columns]
            # 过滤掉合计行
            if '名次' in df.columns:
                df = df[df['名次'].apply(lambda x: str(x).isdigit() if pd.notna(x) else False)]
            print(f"[DCE] 解析到 {len(df)} 行数据")
            return df
    except Exception as e:
        print(f"[DCE] 表格解析失败: {e}")

    return None


def compute_net_position(df: pd.DataFrame) -> Optional[float]:
    """
    从持仓排名 DataFrame 计算净持仓

    净持仓 = sum(持买仓量) - sum(持卖仓量)

    返回: float 净持仓值，失败返回 None
    """
    if df is None or df.empty:
        return None

    long_col = None
    short_col = None

    for col in df.columns:
        col_str = str(col)
        if '买' in col_str and '仓' in col_str and '增' not in col_str:
            long_col = col
        elif '卖' in col_str and '仓' in col_str and '增' not in col_str:
            short_col = col

    if long_col is None or short_col is None:
        print(f"[DCE] 无法识别买/卖仓列: {list(df.columns)}")
        return None

    total_long = pd.to_numeric(df[long_col], errors='coerce').sum()
    total_short = pd.to_numeric(df[short_col], errors='coerce').sum()
    net = float(total_long - total_short)

    print(f"[DCE] 持买仓合计: {total_long:.0f}, 持卖仓合计: {total_short:.0f}, 净持仓: {net:.0f}")
    return net


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python dce_scraper.py <YYYYMMDD> <SYMBOL>")
        print("示例: python dce_scraper.py 20260506 LH")
        sys.exit(1)

    date_arg = sys.argv[1]
    symbol_arg = sys.argv[2].upper()

    print(f"=== DCE 持仓排名抓取 ===")
    print(f"品种: {symbol_arg}, 日期: {date_arg}")

    df = fetch_dce_position_rank(date_arg, symbol_arg, use_cache=False)

    if df is not None and not df.empty:
        print(f"\n=== 数据 ({len(df)} 行) ===")
        print(df.to_string(index=False))

        net = compute_net_position(df)
        if net is not None:
            print(f"\n净持仓: {net:.0f} 手")
    else:
        print(f"\n[失败] 未获取到 {symbol_arg} {date_arg} 的持仓排名数据")
        sys.exit(1)
