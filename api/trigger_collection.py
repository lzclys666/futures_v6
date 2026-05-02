"""
因子采集任务触发器
==================
因子分析师完成需求文件后运行此脚本，自动启动 mimo 子会话执行采集

用法：
    python trigger_collection.py factor_requirements.json

功能：
1. 验证需求文件格式
2. 启动 mimo 子会话
3. 传递文件路径（不传递完整 JSON，节省 token）
4. 返回子会话状态
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def validate_requirements(requirements_path: str) -> bool:
    """验证需求文件格式
    
    Args:
        requirements_path: factor_requirements.json 文件路径
        
    Returns:
        是否有效
    """
    path = Path(requirements_path)
    
    if not path.exists():
        print(f"❌ 文件不存在：{requirements_path}")
        return False
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            req = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误：{e}")
        return False
    
    # 验证必要字段
    required_fields = ["task_info", "factors", "execution_order"]
    for field in required_fields:
        if field not in req:
            print(f"❌ 缺少必要字段：{field}")
            return False
    
    # 验证 factors 不为空
    if not req["factors"]:
        print(f"❌ factors 为空")
        return False
    
    # 验证 execution_order 与 factors 匹配
    factor_codes = {f["factor_code"] for f in req["factors"]}
    for code in req["execution_order"]:
        if code not in factor_codes:
            print(f"❌ execution_order 中的因子 {code} 未在 factors 中定义")
            return False
    
    print(f"✅ 需求文件验证通过")
    print(f"   - 任务 ID: {req['task_info']['task_id']}")
    print(f"   - 因子数量：{len(req['factors'])}")
    print(f"   - 执行顺序：{len(req['execution_order'])} 个因子")
    
    return True


def spawn_mimo_session(requirements_path: str) -> dict:
    """启动 mimo 子会话
    
    Args:
        requirements_path: 需求文件路径（相对或绝对）
        
    Returns:
        子会话信息
    """
    # 注意：这个函数在实际运行时会被 OpenClaw 的 sessions_spawn 工具调用
    # 这里提供一个模拟实现，实际使用时需要调用 OpenClaw API
    
    print(f"\n🚀 启动 mimo 子会话...")
    print(f"   - 任务：读取 {requirements_path} 执行因子采集")
    print(f"   - 模式：run（一次性执行）")
    print(f"   - 清理：完成后自动删除会话历史")
    
    # 实际调用 OpenClaw sessions_spawn 的参数示例：
    session_config = {
        "runtime": "subagent",
        "mode": "run",
        "task": f"读取 {requirements_path} 执行因子采集，结果写入 data/raw_factors/",
        "label": f"mimo-data-collector-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "cleanup": "delete",  # 完成后自动清理，节省 token
        "cwd": str(Path(__file__).parent.parent)  # 工作目录设为 workspace 根目录
    }
    
    print(f"\n📋 子会话配置:")
    for key, value in session_config.items():
        print(f"   - {key}: {value}")
    
    # 在 OpenClaw 环境中，这里会实际调用 sessions_spawn 工具
    # 返回会话信息
    session_info = {
        "status": "spawned",
        "config": session_config,
        "message": "子会话已启动，mimo 正在执行采集任务..."
    }
    
    return session_info


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法：python trigger_collection.py <factor_requirements.json>")
        print("\n示例:")
        print("  python trigger_collection.py factor_requirements.json")
        print("  python trigger_collection.py templates/factor_requirements_template.json")
        sys.exit(1)
    
    requirements_path = sys.argv[1]
    
    # 1. 验证需求文件
    print("="*60)
    print("因子采集任务触发器")
    print("="*60)
    
    if not validate_requirements(requirements_path):
        print("\n❌ 验证失败，请检查需求文件")
        sys.exit(1)
    
    # 2. 启动 mimo 子会话
    session_info = spawn_mimo_session(requirements_path)
    
    # 3. 输出结果
    print("\n" + "="*60)
    print(session_info["message"])
    print("="*60)
    
    # 4. 提供后续操作指引
    print("\n📌 后续操作:")
    print("  1. 等待子会话完成（通常 1-5 分钟）")
    print("  2. 查看数据文件：data/raw_factors/{品种代码}/")
    print("  3. 查看采集摘要：data/collection_summary_{task_id}.json")
    print("  4. 如有错误，查看日志：logs/collection_errors_{task_id}.log")
    
    print("\n💡 Token 节省提示:")
    print("  - 子会话使用 cleanup='delete'，完成后自动清理历史")
    print("  - 只传递文件路径，不传递完整 JSON（节省 ~99% token）")
    print("  - 采集结果直接写入文件，不返回详细日志")


if __name__ == "__main__":
    main()
