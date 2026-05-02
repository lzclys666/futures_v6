"""
交易所官网爬虫
==============
爬取国内期货交易所官方数据

支持交易所：
- SHFE（上期所）：铜、铝、锌、铅、镍、锡、黄金、白银、螺纹钢、橡胶等
- DCE（大商所）：豆粕、豆油、棕榈油、玉米、焦煤、焦炭等
- CZCE（郑商所）：白糖、棉花、PTA、甲醇、玻璃等
- CFFEX（中金所）：股指期货、国债期货
- INE（原油中心）：原油、低硫燃料油、20 号胶等

注意：
- 遵守交易所 robots.txt 和使用条款
- 设置合理的请求间隔，避免被封 IP
- 部分交易所需要处理反爬机制

依赖：
    pip install requests beautifulsoup4 lxml
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
import re


# 交易所基础 URL
EXCHANGE_URLS = {
    "SHFE": "http://www.shfe.com.cn",
    "DCE": "http://www.dce.com.cn",
    "CZCE": "http://www.czce.com.cn",
    "CFFEX": "http://www.cffex.com.cn",
    "INE": "http://www.ine.com.cn"
}

# 请求头（模拟浏览器）
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def collect_exchange(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集交易所数据
    
    Args:
        factor: 因子配置，包含 api_params 等
        
    Returns:
        采集到的数据 DataFrame
        
    Raises:
        Exception: 采集失败时抛出异常
    """
    api_params = factor.get("api_params", {})
    exchange = api_params.get("exchange")
    crawler_type = api_params.get("crawler_type")
    
    if not exchange:
        raise ValueError("api_params.exchange 未指定")
    
    if not crawler_type:
        raise ValueError("api_params.crawler_type 未指定")
    
    # 获取爬虫函数
    crawler_func = _get_crawler_func(exchange, crawler_type)
    
    # 准备参数
    params = {k: v for k, v in api_params.items() if k not in ["exchange", "crawler_type"]}
    
    # 调用爬虫
    try:
        df = crawler_func(params)
    except Exception as e:
        raise Exception(f"{exchange}.{crawler_type} 爬取失败：{str(e)}")
    
    # 数据验证
    if df is None or df.empty:
        raise Exception(f"{exchange}.{crawler_type} 返回空数据")
    
    # PIT 处理
    pit_config = factor.get("pit_requirement", {})
    if pit_config.get("need_pit", False):
        df = _add_observation_date(df, pit_config)
    
    return df


def _get_crawler_func(exchange: str, crawler_type: str):
    """获取爬虫函数
    
    Args:
        exchange: 交易所代码
        crawler_type: 爬虫类型
        
    Returns:
        爬虫函数
    """
    crawlers = {
        "SHFE": {
            "daily_data": _shfe_daily_data,
            "warehouse_receipt": _shfe_warehouse_receipt,
        },
        "DCE": {
            "daily_data": _dce_daily_data,
            "settlement": _dce_settlement,
        },
        "CZCE": {
            "daily_data": _czce_daily_data,
            "settlement": _czce_settlement,
        },
        "CFFEX": {
            "daily_data": _cffex_daily_data,
            "settlement": _cffex_settlement,
        },
        "INE": {
            "daily_data": _ine_daily_data,
        }
    }
    
    if exchange not in crawlers:
        raise ValueError(f"不支持的交易所：{exchange}")
    
    if crawler_type not in crawlers[exchange]:
        raise ValueError(f"不支持的爬虫类型：{crawler_type}")
    
    return crawlers[exchange][crawler_type]


# ============ 上期所 (SHFE) 爬虫 ============

def _shfe_daily_data(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取上期所日线数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        日线数据 DataFrame
    """
    trade_date = params.get("trade_date")
    product = params.get("product")  # 品种代码，如 cu, al, ru
    
    if not trade_date:
        raise ValueError("需要 trade_date 参数")
    
    # 上期所日线数据 URL
    url = f"http://www.shfe.com.cn/data/dailydata/kx/kx{trade_date}.dat"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        # 解析数据（上期所返回的是特殊格式）
        data = _parse_shfe_dat(response.text)
        
        df = pd.DataFrame(data)
        
        # 品种过滤
        if product:
            df = df[df["product"] == product.upper()]
        
        return df
        
    except Exception as e:
        raise Exception(f"爬取上期所日线数据失败：{str(e)}")


def _shfe_warehouse_receipt(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取上期所仓单数据
    
    Args:
        params: 包含 start_date, end_date, product 等参数
        
    Returns:
        仓单数据 DataFrame
    """
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    product = params.get("product")
    
    # 上期所仓单数据 URL
    url = "http://www.shfe.com.cn/data/futuresdata/warehouseReceipt/warehouseReceiptQuery"
    
    data_list = []
    current_date = datetime.strptime(start_date, "%Y%m%d")
    end_date_obj = datetime.strptime(end_date, "%Y%m%d")
    
    while current_date <= end_date_obj:
        try:
            # 构造请求参数
            payload = {
                "tradeDate": current_date.strftime("%Y%m%d"),
                "product": product or ""
            }
            
            response = requests.post(url, json=payload, headers=DEFAULT_HEADERS, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("data"):
                data_list.extend(result["data"])
            
            # 避免请求过快
            time.sleep(1)
            
        except Exception as e:
            print(f"警告：{current_date} 仓单数据获取失败：{str(e)}")
        
        current_date += timedelta(days=1)
    
    return pd.DataFrame(data_list)


# ============ 大商所 (DCE) 爬虫 ============

def _dce_daily_data(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取大商所日线数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        日线数据 DataFrame
    """
    trade_date = params.get("trade_date")
    
    if not trade_date:
        raise ValueError("需要 trade_date 参数")
    
    # 大商所日线数据 URL
    url = "http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html"
    
    payload = {
        "dayQuotes.variety": "all",
        "dayQuotes.trade_type": 0,
        "year": trade_date[:4],
        "month": str(int(trade_date[4:6]) - 1),  # 月份从 0 开始
        "day": trade_date[6:]
    }
    
    try:
        response = requests.post(url, data=payload, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        data = _parse_dce_table(soup)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"爬取大商所日线数据失败：{str(e)}")


def _dce_settlement(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取大商所结算数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        结算数据 DataFrame
    """
    trade_date = params.get("trade_date")
    
    # 大商所结算数据 URL
    url = f"http://www.dce.com.cn/publicweb/quotesdata/settlement.html?settlement.settlement_date={trade_date}"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        data = _parse_dce_table(soup)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"爬取大商所结算数据失败：{str(e)}")


# ============ 郑商所 (CZCE) 爬虫 ============

def _czce_daily_data(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取郑商所日线数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        日线数据 DataFrame
    """
    trade_date = params.get("trade_date")
    
    if not trade_date:
        raise ValueError("需要 trade_date 参数")
    
    # 郑商所日线数据 URL
    url = f"http://www.czce.com.cn/cn/DFSStaticFiles/Future/{trade_date[:4]}/FutureDataDaily.htm"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        data = _parse_czce_table(soup)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"爬取郑商所日线数据失败：{str(e)}")


def _czce_settlement(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取郑商所结算数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        结算数据 DataFrame
    """
    trade_date = params.get("trade_date")
    
    # 郑商所结算数据 URL
    url = f"http://www.czce.com.cn/cn/DFSStaticFiles/Settlement/{trade_date[:4]}/SettlementDataDaily.htm"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        data = _parse_czce_table(soup)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"爬取郑商所结算数据失败：{str(e)}")


# ============ 中金所 (CFFEX) 爬虫 ============

def _cffex_daily_data(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取中金所日线数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        日线数据 DataFrame
    """
    trade_date = params.get("trade_date")
    
    if not trade_date:
        raise ValueError("需要 trade_date 参数")
    
    # 中金所日线数据 URL
    url = f"http://www.cffex.com.cn/fzjy/mrhq/{trade_date[:4]}{trade_date[4:6]}/{trade_date[6:]}/index.xml"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        # 解析 XML
        soup = BeautifulSoup(response.text, "xml")
        data = _parse_cffex_xml(soup)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"爬取中金所日线数据失败：{str(e)}")


def _cffex_settlement(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取中金所结算数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        结算数据 DataFrame
    """
    # 实现类似 _cffex_daily_data
    pass


# ============ 原油中心 (INE) 爬虫 ============

def _ine_daily_data(params: Dict[str, Any]) -> pd.DataFrame:
    """爬取原油中心日线数据
    
    Args:
        params: 包含 trade_date, product 等参数
        
    Returns:
        日线数据 DataFrame
    """
    trade_date = params.get("trade_date")
    
    if not trade_date:
        raise ValueError("需要 trade_date 参数")
    
    # 原油中心日线数据 URL
    url = f"http://www.ine.com.cn/data/dailydata/kx/kx{trade_date}.dat"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        
        # 解析数据（类似上期所格式）
        data = _parse_shfe_dat(response.text)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"爬取原油中心日线数据失败：{str(e)}")


# ============ 数据解析函数 ============

def _parse_shfe_dat(text: str) -> List[Dict]:
    """解析上期所 dat 格式数据
    
    Args:
        text: 原始文本
        
    Returns:
        数据列表
    """
    # 上期所 dat 格式解析逻辑
    # 实际实现需要根据具体格式调整
    data = []
    
    # 示例解析（简化版）
    lines = text.strip().split("\n")
    for line in lines:
        if line.startswith("<"):
            continue
        parts = line.split("\t")
        if len(parts) >= 10:
            data.append({
                "product": parts[0],
                "contract": parts[1],
                "open": parts[2],
                "high": parts[3],
                "low": parts[4],
                "close": parts[5],
                "volume": parts[6],
                "open_interest": parts[7],
            })
    
    return data


def _parse_dce_table(soup: BeautifulSoup) -> List[Dict]:
    """解析大商所 HTML 表格
    
    Args:
        soup: BeautifulSoup 对象
        
    Returns:
        数据列表
    """
    data = []
    table = soup.find("table", class_="dataTable")
    
    if not table:
        return data
    
    rows = table.find_all("tr")[1:]  # 跳过表头
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 8:
            data.append({
                "product": cells[0].get_text(strip=True),
                "contract": cells[1].get_text(strip=True),
                "open": cells[2].get_text(strip=True),
                "high": cells[3].get_text(strip=True),
                "low": cells[4].get_text(strip=True),
                "close": cells[5].get_text(strip=True),
                "volume": cells[6].get_text(strip=True),
                "open_interest": cells[7].get_text(strip=True),
            })
    
    return data


def _parse_czce_table(soup: BeautifulSoup) -> List[Dict]:
    """解析郑商所 HTML 表格
    
    Args:
        soup: BeautifulSoup 对象
        
    Returns:
        数据列表
    """
    data = []
    table = soup.find("table")
    
    if not table:
        return data
    
    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 8:
            data.append({
                "product": cells[0].get_text(strip=True),
                "contract": cells[1].get_text(strip=True),
                "open": cells[2].get_text(strip=True),
                "high": cells[3].get_text(strip=True),
                "low": cells[4].get_text(strip=True),
                "close": cells[5].get_text(strip=True),
                "volume": cells[6].get_text(strip=True),
                "open_interest": cells[7].get_text(strip=True),
            })
    
    return data


def _parse_cffex_xml(soup: BeautifulSoup) -> List[Dict]:
    """解析中金所 XML 数据
    
    Args:
        soup: BeautifulSoup 对象
        
    Returns:
        数据列表
    """
    data = []
    
    for item in soup.find_all("DailyData"):
        data.append({
            "product": item.get("productid", ""),
            "contract": item.get("contractid", ""),
            "open": item.get("openprice", ""),
            "high": item.get("highprice", ""),
            "low": item.get("lowprice", ""),
            "close": item.get("closeprice", ""),
            "volume": item.get("volume", ""),
            "open_interest": item.get("openinterest", ""),
        })
    
    return data


def _add_observation_date(df: pd.DataFrame, pit_config: Dict[str, Any]) -> pd.DataFrame:
    """添加观测日期（PIT 数据）
    
    Args:
        df: 原始 DataFrame
        pit_config: PIT 配置
        
    Returns:
        添加 obs_date 列的 DataFrame
    """
    df["obs_date"] = datetime.now().strftime("%Y-%m-%d")
    return df


# ============ 接口函数注册表 ============

FUNCTION_MAP = {
    "SHFE": {
        "daily_data": _shfe_daily_data,
        "warehouse_receipt": _shfe_warehouse_receipt,
    },
    "DCE": {
        "daily_data": _dce_daily_data,
        "settlement": _dce_settlement,
    },
    "CZCE": {
        "daily_data": _czce_daily_data,
        "settlement": _czce_settlement,
    },
    "CFFEX": {
        "daily_data": _cffex_daily_data,
        "settlement": _cffex_settlement,
    },
    "INE": {
        "daily_data": _ine_daily_data,
    }
}
