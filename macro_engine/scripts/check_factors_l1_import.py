# -*- coding: utf-8 -*-
"""
scripts/check_factors_l1_import.py
因子采集 L1 import 验证脚本

扫描 crawlers/{SYMBOL}/ 下的所有 .py 脚本，逐个验证 import 是否成功。
只插入 CRAWLERS 根目录到 sys.path，不插入子包路径（避免假性 ImportError）。

验收标准：假性 ImportError < 1%（约 3 个 / 368 个脚本）
"""
import sys
import os
from pathlib import Path
import py_compile
import importlib.util

# 项目根目录
PROJECT_ROOT = Path(r"D:\futures_v6\macro_engine")
CRAWLERS = PROJECT_ROOT / "crawlers"
sys.path.insert(0, str(CRAWLERS))

# 排除目录
EXCLUDE_DIRS = {"__pycache__", "logs", "tools", "_shared", "common", "collectors"}
# 排除文件名
EXCLUDE_FILES = {"__init__.py", "AG_run_all.py", "AL_run_all.py", "RU_run_all.py",
                 "AU_run_all.py", "RB_run_all.py", "JM_run_all.py", "CU_run_all.py",
                 "_batch_fix_sa.py", "phase3_v2_collect.py", "phase3_v2_collect_v2.py",
                 "phase3_v2_collect_report.py", "add_collect.py"}


def get_all_scripts():
    """获取所有需要检查的脚本"""
    scripts = []
    for subdir in sorted(CRAWLERS.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name in EXCLUDE_DIRS:
            continue
        for py_file in sorted(subdir.glob("*.py")):
            if py_file.name in EXCLUDE_FILES:
                continue
            scripts.append(py_file)
    return scripts


def check_syntax(script_path):
    """纯语法检查（py_compile）"""
    try:
        py_compile.compile(str(script_path), doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)[:120]
    except Exception as e:
        return False, str(e)[:120]


def check_import(script_path):
    """验证单个脚本的 import 是否成功（隔离子进程）"""
    import subprocess
    script_name = str(script_path)
    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
             "PYTHONPATH": str(CRAWLERS)}
    )
    try:
        stdout, stderr = proc.communicate(timeout=30)
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            if "ImportError" in stderr_text or "ModuleNotFoundError" in stderr_text:
                return "IMPORT_ERROR", stderr_text[:200]
            # 业务逻辑错误（网络、超时）不算 import 失败
            return "OK", ""
        return "OK", ""
    except subprocess.TimeoutExpired:
        proc.kill()
        return "TIMEOUT", "30s timeout"


def main():
    scripts = get_all_scripts()
    print(f"[L1 Import Check] 发现 {len(scripts)} 个待检查脚本（排除 run_all / __init__ / collect）")
    print(f"[L1 Import Check] sys.path[0] = {sys.path[0]}")
    print()

    results = []
    syntax_errors = []
    import_errors = []

    for i, script in enumerate(scripts):
        rel_path = str(script.relative_to(CRAWLERS))
        print(f"[{i+1}/{len(scripts)}] {rel_path} ...", end=" ", flush=True)

        # 语法检查
        ok, err = check_syntax(script)
        if not ok:
            print(f"SYNTAX_ERROR")
            syntax_errors.append({"path": rel_path, "error": err})
            results.append({"path": rel_path, "status": "SYNTAX_ERROR", "error": err})
            continue

        # import 检查（子进程隔离）
        status, err = check_import(script)
        print(status)
        results.append({"path": rel_path, "status": status, "error": err})
        if status == "IMPORT_ERROR":
            import_errors.append({"path": rel_path, "error": err})

    # 汇总
    print()
    print("=" * 60)
    print("【L1 Import 检查汇总】")
    print(f"  总脚本数   : {len(scripts)}")
    print(f"  语法错误   : {len(syntax_errors)}")
    print(f"  ImportError: {len(import_errors)}")

    # 假性 ImportError 特征：No module named 'common'
    fake_import_errors = [e for e in import_errors if "No module named 'common'" in e["error"]]
    real_import_errors = [e for e in import_errors if "No module named 'common'" not in e["error"]]
    print(f"  其中假性  : {len(fake_import_errors)} ({100*len(fake_import_errors)/max(len(scripts),1):.1f}%)")
    print(f"  真实缺失  : {len(real_import_errors)}")

    if import_errors:
        print()
        print("【ImportError 详情（前 15）】")
        for e in import_errors[:15]:
            print(f"  {e['path']}: {e['error'][:120]}")

    # 验收判断
    fake_rate = len(fake_import_errors) / max(len(scripts), 1)
    if fake_rate < 0.01:
        print(f"\n[PASS] B1-3 验收通过：假性 ImportError {len(fake_import_errors)}/{len(scripts)} ({fake_rate:.1%}) < 1%")
    else:
        print(f"\n[WARN] B1-3 假性率 {fake_rate:.1%} 仍需优化")

    return results


if __name__ == "__main__":
    main()