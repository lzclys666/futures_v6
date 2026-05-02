"""
自定义爬虫采集器
=================
用于采集需要特殊处理的自定义数据源

注意：
- 每个自定义数据源需要单独实现采集函数
- 遵循统一的输入输出接口
- 错误处理要完整，记录详细日志
"""

import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
import requests
import time


def collect_custom(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集自定义数据源
    
    Args:
        factor: 因子配置，包含 api_params 等
        
    Returns:
        采集到的数据 DataFrame
        
    Raises:
        Exception: 采集失败时抛出异常
    """
    api_params = factor.get("api_params", {})
    collector_type = api_params.get("type")
    
    if not collector_type:
        raise ValueError("api_params.type 未指定")
    
    # 根据类型调用对应的采集函数
    if collector_type == "web_scrape":
        return _collect_web_scrape(api_params)
    elif collector_type == "api_request":
        return _collect_api_request(api_params)
    elif collector_type == "file_import":
        return _collect_file_import(api_params)
    else:
        raise ValueError(f"不支持的自定义采集类型: {collector_type}")


def _collect_web_scrape(api_params: Dict[str, Any]) -> pd.DataFrame:
    """网页爬虫采集
    
    Args:
        api_params: 包含 url, selector, headers 等参数
        
    Returns:
        采集到的数据 DataFrame
    """
    from bs4 import BeautifulSoup
    
    url = api_params.get("url")
    if not url:
        raise ValueError("url 未指定")
    
    headers = api_params.get("headers", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 根据 selector 提取数据
        selector = api_params.get("selector")
        if selector:
            data = _extract_from_soup(soup, selector)
        else:
            data = _extract_table(soup)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        raise Exception(f"网页爬虫采集失败: {str(e)}")


def _collect_api_request(api_params: Dict[str, Any]) -> pd.DataFrame:
    """API 请求采集
    
    Args:
        api_params: 包含 url, method, headers, body 等参数
        
    Returns:
        采集到的数据 DataFrame
    """
    url = api_params.get("url")
    if not url:
        raise ValueError("url 未指定")
    
    method = api_params.get("method", "GET")
    headers = api_params.get("headers", {})
    body = api_params.get("body")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")
        
        response.raise_for_status()
        data = response.json()
        
        # 转换为 DataFrame
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # 尝试提取数据字段
            data_key = api_params.get("data_key", "data")
            if data_key in data:
                return pd.DataFrame(data[data_key])
            else:
                return pd.DataFrame([data])
        else:
            raise Exception(f"无法解析的响应格式: {type(data)}")
            
    except Exception as e:
        raise Exception(f"API 请求采集失败: {str(e)}")


def _collect_file_import(api_params: Dict[str, Any]) -> pd.DataFrame:
    """文件导入采集
    
    Args:
        api_params: 包含 file_path, format 等参数
        
    Returns:
        采集到的数据 DataFrame
    """
    import os
    
    file_path = api_params.get("file_path")
    if not file_path:
        raise ValueError("file_path 未指定")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    file_format = api_params.get("format", "csv")
    
    try:
        if file_format == "csv":
            df = pd.read_csv(file_path, encoding=api_params.get("encoding", "utf-8"))
        elif file_format == "excel":
            df = pd.read_excel(file_path)
        elif file_format == "json":
            df = pd.read_json(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_format}")
        
        return df
        
    except Exception as e:
        raise Exception(f"文件导入失败: {str(e)}")


def _extract_from_soup(soup, selector: str) -> list[dict]:
    """从 BeautifulSoup 提取数据
    
    Args:
        soup: BeautifulSoup 对象
        selector: CSS 选择器
        
    Returns:
        提取的数据列表
    """
    elements = soup.select(selector)
    data = []
    
    for elem in elements:
        # 提取文本
        item = {"text": elem.get_text(strip=True)}
        # 提取属性
        if elem.get("href"):
            item["href"] = elem.get("href")
        if elem.get("data-value"):
            item["value"] = elem.get("data-value")
        
        data.append(item)
    
    return data


def _extract_table(soup) -> List[Dict]:
    """从 HTML 表格提取数据
    
    Args:
        soup: BeautifulSoup 对象
        
    Returns:
        提取的数据列表
    """
    table = soup.find("table")
    if not table:
        return []
    
    data = []
    headers = []
    
    # 提取表头
    header_row = table.find("thead")
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
    
    # 提取数据行
    rows = table.find("tbody") or table
    for row in rows.find_all("tr")[1:] if headers else rows.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if headers:
            item = {headers[i]: cell.get_text(strip=True) for i, cell in enumerate(cells)}
        else:
            item = {f"col_{i}": cell.get_text(strip=True) for i, cell in enumerate(cells)}
        data.append(item)
    
    return data
