# -*- coding: utf-8 -*-
"""
crawlers/common/io_win.py
Windows 环境 Python 标准输出修复

所有爬虫脚本在 Windows 下运行时，需要将 stdout/stderr 切换为 UTF-8 模式，
否则中文输出和特殊字符会导致编码错误。

使用方法（所有爬虫脚本顶部）:
    from common.io_win import fix_encoding
    fix_encoding()

必须在本模块 import任何可能输出中文的库之前调用。
"""
import sys
import io
import os

_IS_WINDOWS = os.name == "nt"

def fix_encoding():
    """
    在 Windows 环境下将 stdout/stderr 切换为 UTF-8 兼容模式。
    仅在 Windows 下生效，Linux/Mac 无操作。
    """
    if not _IS_WINDOWS:
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if stream.encoding.lower() in ("utf-8", "utf8"):
            continue
        try:
            new_stream = io.TextIOWrapper(
                stream.buffer if hasattr(stream, "buffer") else stream,
                encoding="utf-8",
                errors="replace",
                newline="\n",
            )
            setattr(sys, stream_name, new_stream)
        except Exception:
            pass
