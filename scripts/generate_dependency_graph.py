#!/usr/bin/env python3
"""
AST解析器：生成真实依赖关系图
目标：抛弃高级观念，把代码真实的调用关系全部扒出来
"""

import ast
import os
import json
from pathlib import Path
from collections import defaultdict

class DependencyAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports = defaultdict(list)
        self.function_calls = defaultdict(list)
        self.class_inheritance = defaultdict(list)
        self.current_function = None
        self.current_class = None
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports[self.current_function or 'module'].append({
                'type': 'import',
                'module': alias.name,
                'asname': alias.asname
            })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imports[self.current_function or 'module'].append({
                'type': 'from_import',
                'module': node.module,
                'name': alias.name,
                'asname': alias.asname
            })
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        
        # 记录函数定义
        self.function_calls[node.name] = {
            'type': 'function_def',
            'args': [arg.arg for arg in node.args.args],
            'calls': []
        }
        
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        
        # 记录类继承关系
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.class_inheritance[node.name].append(base.id)
        
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Call(self, node):
        if self.current_function:
            func_info = self.function_calls.get(self.current_function)
            if func_info is None:
                func_info = {'type': 'function_def', 'args': [], 'calls': []}
                self.function_calls[self.current_function] = func_info
            
            if isinstance(node.func, ast.Name):
                # 函数调用
                func_info['calls'].append({
                    'type': 'call',
                    'function': node.func.id,
                    'line': node.lineno
                })
            elif isinstance(node.func, ast.Attribute):
                # 方法调用
                if isinstance(node.func.value, ast.Name):
                    func_info['calls'].append({
                        'type': 'method_call',
                        'object': node.func.value.id,
                        'method': node.func.attr,
                        'line': node.lineno
                    })
        
        self.generic_visit(node)

def analyze_file(filepath):
    """分析单个Python文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
            analyzer = DependencyAnalyzer()
            analyzer.visit(tree)
            return {
                'file': str(filepath),
                'imports': dict(analyzer.imports),
                'functions': dict(analyzer.function_calls),
                'classes': dict(analyzer.class_inheritance)
            }
        except SyntaxError as e:
            print(f"语法错误: {filepath} - {e}")
            return None

def analyze_project(root_dir):
    """分析整个项目"""
    root_path = Path(root_dir)
    all_dependencies = {
        'project': str(root_path),
        'files': {},
        'dependencies': defaultdict(list)
    }
    
    # 分析所有Python文件
    for py_file in root_path.rglob('*.py'):
        # 跳过venv和node_modules
        if 'venv' in str(py_file) or 'node_modules' in str(py_file):
            continue
            
        result = analyze_file(py_file)
        if result:
            relative_path = py_file.relative_to(root_path)
            all_dependencies['files'][str(relative_path)] = result
            
            # 构建依赖关系图
            for func_name, func_info in result['functions'].items():
                for call in func_info.get('calls', []):
                    if call['type'] in ['call', 'method_call']:
                        all_dependencies['dependencies'][str(relative_path)].append({
                            'from': func_name,
                            'to': call.get('function') or call.get('method'),
                            'line': call['line'],
                            'type': call['type']
                        })
    
    return all_dependencies

def generate_dependency_graph():
    """生成依赖关系图并保存"""
    print("开始分析项目依赖关系...")
    
    # 分析后端API
    api_deps = analyze_project(r'D:\futures_v6\api')
    
    # 分析宏观引擎
    macro_deps = analyze_project(r'D:\futures_v6\macro_engine')
    
    # 分析VeighNa策略
    strategy_deps = {}
    strategy_file = Path(r'C:\Users\Administrator\strategies\macro_demo_strategy.py')
    if strategy_file.exists():
        result = analyze_file(strategy_file)
        if result:
            strategy_deps = result
    
    # 合并所有依赖
    full_graph = {
        'api': api_deps,
        'macro_engine': macro_deps,
        'strategy': strategy_deps,
        'metadata': {
            'generated_at': __import__('datetime').datetime.now().isoformat(),
            'total_files': len(api_deps.get('files', {})) + len(macro_deps.get('files', {})) + (1 if strategy_deps else 0)
        }
    }
    
    # 保存为JSON
    output_file = r'D:\futures_v6\docs\ARCHITECTURE.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_graph, f, indent=2, ensure_ascii=False)
    
    print(f"依赖图已生成: {output_file}")
    print(f"共分析 {full_graph['metadata']['total_files']} 个文件")
    
    # 生成简化视图
    generate_simplified_view(full_graph)
    
    return full_graph

def generate_simplified_view(full_graph):
    """生成简化的依赖视图"""
    simple_view = {
        'core_interfaces': {
            'macro_api_server.py': [],
            'macro_scoring_engine.py': [],
            'daily_scoring.py': [],
            'macro_demo_strategy.py': []
        },
        'call_chains': []
    }
    
    # 提取核心调用链
    for module, deps in full_graph.items():
        if module == 'metadata':
            continue
            
        for file_path, file_deps in deps.get('files', {}).items():
            # 只关注核心文件
            core_files = ['macro_api_server.py', 'macro_scoring_engine.py', 'daily_scoring.py', 'macro_demo_strategy.py']
            if any(cf in file_path for cf in core_files):
                for func_name, func_info in file_deps.get('functions', {}).items():
                    calls = [c for c in func_info.get('calls', []) if c['type'] in ['call', 'method_call']]
                    if calls:
                        simple_view['call_chains'].append({
                            'file': file_path,
                            'function': func_name,
                            'calls': calls
                        })
    
    # 保存简化视图
    simple_file = r'D:\futures_v6\docs\ARCHITECTURE_SIMPLE.json'
    with open(simple_file, 'w', encoding='utf-8') as f:
        json.dump(simple_view, f, indent=2, ensure_ascii=False)
    
    print(f"简化视图已生成: {simple_file}")

if __name__ == '__main__':
    generate_dependency_graph()
