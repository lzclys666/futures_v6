# -*- coding: utf-8 -*-
"""
crawlers/common/web_utils.py
公共 HTTP 请求工具

目的：统一 requests 会话管理、重试策略、编码处理。

使用方式:
    from common.web_utils import fetch_url, fetch_json
    value, err = fetch_url(url, encoding="gbk")
    value, err = fetch_json(url)
"""
import requests
import time
import re

# 全局会话（连接复用）
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
})

# 常用网站编码映射（避免每次探测）
ENCODING_MAP = {
    "alu.cn": "gbk",
    "sinajs.cn": "gbk",
    "hq.sinajs.cn": "gbk",
    "qq.com": "utf-8",
    "mysteel.com": "utf-8",
    "futures.cn": "gbk",
    "shfe.com.cn": "utf-8",
    "dce.com.cn": "utf-8",
    "czce.com.cn": "gbk",
    "ine.cn": "utf-8",
}


def fetch_url(url, encoding=None, timeout=15, retries=2, params=None):
    """
    获取网页内容，统一编码处理。

    参数:
        url:      目标 URL
        encoding: 手动指定编码，不传则自动探测
        timeout:  超时秒数（默认15）
        retries:  重试次数（默认2）
        params:   URL 查询参数 dict

    返回:
        (html_string, None)  成功
        (None, error_string) 失败
    """
    # 自动选择编码
    if encoding is None:
        for host, enc in ENCODING_MAP.items():
            if host in url:
                encoding = enc
                break
        if encoding is None:
            encoding = "utf-8"

    last_err = None
    for attempt in range(retries + 1):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            # 检测编码（部分网站header不准确）
            content_type = r.headers.get("Content-Type", "")
            if "charset" in content_type:
                enc_from_header = content_type.split("charset=")[-1].strip()
                if enc_from_header:
                    encoding = enc_from_header
            r.encoding = encoding
            return r.text, None
        except requests.exceptions.Timeout:
            last_err = f"请求超时 (attempt {attempt + 1}/{retries + 1})"
            time.sleep(1)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                last_err = f"403 Forbidden: {url}"
            else:
                last_err = f"HTTP {e.response.status_code if e.response else 'error'}"
            break  # 4xx 不重试
        except Exception as e:
            last_err = str(e)
            time.sleep(1)

    return None, last_err


def fetch_json(url, timeout=15, retries=2, params=None):
    """
    获取 JSON 数据（自动处理 API 响应）。

    返回:
        (dict/list, None)  成功
        (None, error_string) 失败
    """
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return data, None
        except Exception as e:
            last_err = f"JSON解析失败: {e}"
            time.sleep(1)
    return None, last_err


def extract_number(text, pattern=None, default=None):
    """
    从文本中提取数值。

    参数:
        text:    原始文本
        pattern: 正则表达式（默认找第一个数字）
        default: 失败时的默认值

    返回:
        (float, None) 或 (default, error_string)
    """
    try:
        if pattern:
            m = re.search(pattern, text)
        else:
            m = re.search(r"-?\d+\.?\d*", text)
        if m:
            return float(m.group()), None
    except Exception as e:
        return default, f"数值提取失败: {e}"
    return default, "未找到数字"


def extract_table_row(text, keywords, sep=None):
    """
    从网页文本中提取表格某一行。

    参数:
        text:     HTML 或纯文本
        keywords: 匹配关键字列表（行需包含所有关键字）
        sep:      分隔符（默认 None=自动检测）

    返回:
        (list[str], None)  成功（单元格列表）
        (None, error_msg)  失败
    """
    lines = text.split("\n") if not sep else text.split(sep)
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if all(kw in line_clean for kw in keywords):
            # 提取 td/th 内容
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", line, re.S)
            if cells:
                # 去 HTML 标签
                return [re.sub(r"<[^>]+>", "", c).strip() for c in cells], None
            # 纯文本分隔
            parts = re.split(r"[\t|,\s{2,}]+", line_clean)
            if len(parts) >= 2:
                return parts, None
    return None, f"未找到匹配关键字 {keywords} 的行"


def close_session():
    """关闭全局会话（脚本结束时调用）"""
    _SESSION.close()
