# core/pipeline/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class PipelineNode(ABC):
    """流水线节点抽象基类"""
    
    @abstractmethod
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据并返回更新后的数据字典。
        data: 当前流水线数据
        context: 全局上下文（symbol, as_of_date, config等）
        """
        pass
    
    @classmethod
    def from_config(cls, config: Dict) -> 'PipelineNode':
        """从配置创建节点实例"""
        return cls()


class Pipeline:
    """流水线执行引擎"""
    
    def __init__(self, nodes: List[PipelineNode]):
        self.nodes = nodes
        self._output_formatter = None  # 可选的后处理钩子，接收完整data dict
    
    def set_output_formatter(self, formatter):
        """设置输出格式化回调：formatter(data: Dict, context: Dict) -> Any"""
        self._output_formatter = formatter
    
    def run(self, initial_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        data = initial_data.copy()
        for node in self.nodes:
            data = node.process(data, context)
        if self._output_formatter:
            self._output_formatter(data, context)
        return data