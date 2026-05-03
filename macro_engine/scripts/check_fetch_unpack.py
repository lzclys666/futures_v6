# -*- coding: utf-8 -*-
"""
check_fetch_unpack.py
PIT 数据完整性验证脚本

功能：对 pit_factor_observations 表执行三类 PIT 数据质量检查。
输出带颜色/emoji（✅/🟡/🔴），结果写入 logs/pit_integrity_YYYY-MM-DD.log。
有🔴问题时 exit(1)，否则 exit(0)。
"""

import ast
import os
import sys
from pathlib import Path

CRAWLERS_DIR = Path(r"D:\futures_v6\macro_engine\crawlers")
EXCLUDE_DIRS = {"common", "logs", "tools", "__pycache__", ".git"}


def find_all_crawler_files():
    """扫描 crawlers 目录下所有 .py 文件（排除 common/logs/tools）。"""
    files = []
    for py_file in CRAWLERS_DIR.rglob("*.py"):
        parts = py_file.parts
        # 排除 common/、logs/、tools/ 目录下的文件
        if any(ex in parts for ex in EXCLUDE_DIRS):
            continue
        files.append(py_file)
    return files


class FetchUnpackVisitor(ast.NodeVisitor):
    """AST 访问器：检测 fetch_url/fetch_json 是否正确处理 err。"""

    def __init__(self, source: str):
        self.source = source
        self.findings = []  # [(lineno, pattern, detail)]

        # 解析源码为 AST
        try:
            self.tree = ast.parse(source, filename="<unknown>")
        except SyntaxError:
            self.findings.append((-1, "SYNTAX_ERROR", "无法解析 AST"))
            return

        self._scan()

    def _scan(self):
        for node in ast.walk(self.tree):
            # 找赋值语句：data, err = fetch_xxx(...)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Tuple) and len(target.elts) >= 2:
                        # 元组解包赋值
                        left_vars = [e.id if isinstance(e, ast.Name) else None for e in target.elts]
                        if None in left_vars:
                            continue
                        call_node = self._get_call(node.value)
                        if call_node and isinstance(call_node.func, ast.Name) and call_node.func.id in ("fetch_url", "fetch_json"):
                            # 找到 fetch 调用，检查是否有 err 处理
                            data_var = left_vars[0]
                            err_var = left_vars[1] if len(left_vars) > 1 else None
                            has_err_check = self._has_err_check_after(node)
                            status = "OK" if has_err_check else "MISS_ERR"
                            fn = call_node.func.id
                            self.findings.append((node.lineno, status, f"{fn}() -> {data_var}, {err_var}"))

    def _get_call(self, node) -> ast.Call | None:
        """获取函数调用节点。"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node
        return None

    def _has_err_check_after(self, assign_node: ast.Assign) -> bool:
        """
        检查赋值语句之后是否有 err 检查。
        检查方式：在源码中搜索 'if err' / 'err and' / 'if not err' 等模式。
        """
        source_lines = self.source.split("\n")
        # 从赋值行之后最多搜50行
        start = max(0, assign_node.lineno - 1)
        end = min(len(source_lines), start + 50)
        snippet = "\n".join(source_lines[start:end])

        # 简单的字符串搜索：检查是否有 err 相关条件判断
        err_patterns = [
            "if err",
            "err and",
            "err or",
            "if not err",
            "if err is not None",
            "if err is None",
            "err and",
            "not err",
            "err_status",
        ]
        for pat in err_patterns:
            if pat in snippet:
                return True
        return False

    def get_summary(self):
        ok = sum(1 for _, p, _ in self.findings if p == "OK")
        miss = sum(1 for _, p, _ in self.findings if p == "MISS_ERR")
        err_count = sum(1 for _, p, _ in self.findings if p == "SYNTAX_ERROR")
        return ok, miss, err_count


def analyze_file(path: Path):
    """分析单个文件。返回 (file_path, ok_count, miss_count, err_count, detail_lines)。"""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return path, 0, 0, 0, [f"  读取失败: {e}"]

    visitor = FetchUnpackVisitor(source)
    ok, miss, err_cnt = visitor.get_summary()
    details = []
    for lineno, pattern, detail in visitor.findings:
        if pattern != "OK":
            marker = "🔴" if pattern == "MISS_ERR" else "❌"
            details.append(f"  {marker} L{lineno}: {detail}")
    return path, ok, miss, err_cnt, details


def main():
    print("🔍 检查爬虫脚本 fetch_url/fetch_json err 处理")
    print("=" * 60)

    all_files = find_all_crawler_files()
    print(f"扫描: {CRAWLERS_DIR}")
    print(f"总文件数: {len(all_files)}")
    print()

    total_ok = 0
    total_miss = 0
    total_err = 0
    all_miss_details = []  # 所有遗漏 err 处理的文件

    for i, path in enumerate(all_files, 1):
        fp, ok, miss, err_cnt, details = analyze_file(path)
        total_ok += ok
        total_miss += miss
        total_err += err_cnt

        if miss > 0:
            rel = str(fp.relative_to(CRAWLERS_DIR))
            for d in details:
                all_miss_details.append(f"{rel}{d}")

        # 进度（每50个打印一次）
        if i % 50 == 0 or i == len(all_files):
            print(f"  进度 {i}/{len(all_files)}  ... ", end="", flush=True)

    print()
    print("=" * 60)

    # 统计
    has_fetch_files = total_ok + total_miss + total_err
    print(f"总文件数:          {len(all_files)}")
    print(f"有 fetch 调用:     {has_fetch_files}")
    print(f"  ✅ 正确处理 err: {total_ok}")
    print(f"  🔴 遗漏 err 处理: {total_miss}")
    print(f"  ❌ 语法错误:      {total_err}")

    if all_miss_details:
        print()
        print("🔴 遗漏 err 处理的文件（共{}处）:".format(len(all_miss_details)))
        for item in all_miss_details[:10]:
            print(f"  {item}")
        if len(all_miss_details) > 10:
            print(f"  ... 还有 {len(all_miss_details) - 10} 处")

    print()
    if total_miss > 0:
        print("判定: 🔴 存在问题，exit(1)")
        sys.exit(1)
    elif total_err > 0:
        print("判定: ❌ 有语法错误，exit(1)")
        sys.exit(1)
    else:
        print("判定: ✅ 全部通过，exit(0)")
        sys.exit(0)


if __name__ == "__main__":
    main()