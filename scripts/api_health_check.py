#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api_health_check.py
API 服务健康监控脚本

检查 macro_api_server.py (端口 8000) 的各项服务状态：
- HTTP /health 健康端点
- /api/macro/signal/RU 信号数据接口
- WebSocket /ws/signal 信号推送
- WebSocket /ws/risk 风控推送

退出码:
  0 = 全部正常
  1 = 全部异常（服务不可用）
  2 = 部分异常（部分端点失败）
"""

import json
import sys
import time
import socket
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "http://localhost:8000"
WS_HOST = "localhost"
WS_PORT = 8000
TIMEOUT = 5  # 秒


def check_http_health():
    """检查 /health 健康端点"""
    result = {
        "endpoint": "/health",
        "type": "http",
        "status": "unknown",
        "latency_ms": None,
        "detail": ""
    }
    try:
        start = time.time()
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            latency = round((time.time() - start) * 1000, 1)
            body = resp.read().decode("utf-8")
            result["status"] = "ok" if resp.status == 200 else "error"
            result["latency_ms"] = latency
            result["detail"] = f"HTTP {resp.status}"
            # 尝试解析 JSON 响应
            try:
                data = json.loads(body)
                result["response"] = data
            except json.JSONDecodeError:
                result["response"] = body[:200]
    except urllib.error.URLError as e:
        result["status"] = "error"
        result["detail"] = f"连接失败: {e.reason}"
    except socket.timeout:
        result["status"] = "error"
        result["detail"] = f"超时 ({TIMEOUT}s)"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)[:200]
    return result


def check_signal_api():
    """检查 /api/macro/signal/RU 信号数据接口"""
    result = {
        "endpoint": "/api/macro/signal/RU",
        "type": "http",
        "status": "unknown",
        "latency_ms": None,
        "detail": ""
    }
    try:
        start = time.time()
        req = urllib.request.Request(f"{BASE_URL}/api/macro/signal/RU")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            latency = round((time.time() - start) * 1000, 1)
            body = resp.read().decode("utf-8")
            result["latency_ms"] = latency
            if resp.status == 200:
                try:
                    data = json.loads(body)
                    # 检查返回数据结构是否合理
                    if isinstance(data, dict) and ("signal" in data or "data" in data or "symbol" in data):
                        result["status"] = "ok"
                        result["detail"] = "返回有效信号数据"
                    elif isinstance(data, list) and len(data) > 0:
                        result["status"] = "ok"
                        result["detail"] = f"返回 {len(data)} 条数据"
                    else:
                        result["status"] = "warn"
                        result["detail"] = "返回数据结构异常"
                    result["has_data"] = True
                except json.JSONDecodeError:
                    result["status"] = "warn"
                    result["detail"] = "响应非 JSON 格式"
                    result["has_data"] = False
            else:
                result["status"] = "error"
                result["detail"] = f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        result["status"] = "error"
        result["detail"] = f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        result["status"] = "error"
        result["detail"] = f"连接失败: {e.reason}"
    except socket.timeout:
        result["status"] = "error"
        result["detail"] = f"超时 ({TIMEOUT}s)"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)[:200]
    return result


def check_ws_endpoint(path, name):
    """检查 WebSocket 端点是否可连接（TCP 层面）"""
    result = {
        "endpoint": path,
        "type": "websocket",
        "status": "unknown",
        "latency_ms": None,
        "detail": ""
    }
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((WS_HOST, WS_PORT))
        latency = round((time.time() - start) * 1000, 1)
        # TCP 连接成功，发送 WebSocket 握手
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {WS_HOST}:{WS_PORT}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(handshake.encode())
        resp = sock.recv(4096).decode("utf-8", errors="replace")
        sock.close()
        latency = round((time.time() - start) * 1000, 1)
        if "101" in resp:
            result["status"] = "ok"
            result["detail"] = "WebSocket 握手成功 (101 Switching Protocols)"
        elif "200" in resp or "HTTP/1.1" in resp:
            result["status"] = "warn"
            result["detail"] = "TCP 连接成功，但 WebSocket 握手未完成"
        else:
            result["status"] = "warn"
            result["detail"] = f"收到响应: {resp[:100]}"
        result["latency_ms"] = latency
    except socket.timeout:
        result["status"] = "error"
        result["detail"] = f"连接超时 ({TIMEOUT}s)"
    except ConnectionRefusedError:
        result["status"] = "error"
        result["detail"] = "连接被拒绝 (服务未启动?)"
    except OSError as e:
        result["status"] = "error"
        result["detail"] = f"OS 错误: {e}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)[:200]
    return result


def run_health_check():
    """执行所有健康检查，返回 JSON 报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "checks": [],
        "summary": {
            "total": 0,
            "ok": 0,
            "warn": 0,
            "error": 0
        },
        "overall_status": "unknown"
    }

    # 执行各项检查
    checks = [
        check_http_health(),
        check_signal_api(),
        check_ws_endpoint("/ws/signal", "信号推送"),
        check_ws_endpoint("/ws/risk", "风控推送"),
    ]

    report["checks"] = checks
    report["summary"]["total"] = len(checks)

    for c in checks:
        if c["status"] == "ok":
            report["summary"]["ok"] += 1
        elif c["status"] == "warn":
            report["summary"]["warn"] += 1
        else:
            report["summary"]["error"] += 1

    # 判定整体状态
    if report["summary"]["error"] == 0 and report["summary"]["warn"] == 0:
        report["overall_status"] = "healthy"
        exit_code = 0
    elif report["summary"]["error"] == report["summary"]["total"]:
        report["overall_status"] = "down"
        exit_code = 1
    else:
        report["overall_status"] = "degraded"
        exit_code = 2

    return report, exit_code


def main():
    report, exit_code = run_health_check()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
