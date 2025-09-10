"""基础操作抽象类

定义所有文件操作的通用接口和共享方法。
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import os
from file_operations import validate_file_access


class BaseOperation(ABC):
    """文件操作基础类"""
    
    def __init__(self, server_instance):
        """初始化操作实例
        
        Args:
            server_instance: 服务器实例，用于获取配置
        """
        self.server = server_instance
    
    def get_config_value(self, key: str, default=None):
        """获取配置值"""
        return self.server.get_config_value(key, default)
    
    def validate_file_access(self, file_path: str, allow_nonexistent: bool = False) -> str:
        """验证文件访问权限
        
        Args:
            file_path: 文件路径
            allow_nonexistent: 是否允许不存在的文件
            
        Returns:
            验证后的文件路径
        """
        project_root = self.get_config_value("project_root", "")
        max_file_size_mb = self.get_config_value("max_file_size", 10)
        enable_hidden_files = self.get_config_value("enable_hidden_files", False)
        
        return validate_file_access(
            file_path, 
            project_root, 
            max_file_size_mb, 
            enable_hidden_files, 
            allow_nonexistent=allow_nonexistent
        )
    
    @abstractmethod
    async def execute(
        self, 
        file_path: str, 
        line: Optional[str] = None, 
        content: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """执行操作
        
        Args:
            file_path: 文件路径
            line: 行号或行范围（可选）
            content: 内容（可选）
            
        Yields:
            操作结果的字符串流
        """
        pass
    
    def parse_line_range(self, line: str) -> tuple[Optional[int], Optional[int]]:
        """解析行号参数
        
        Args:
            line: 行号字符串，如 '5' 或 '5-10'
            
        Returns:
            (start_line, end_line) 元组
        """
        if not line:
            return None, None
            
        if '-' in line:
            parts = line.split('-')
            start_line = int(parts[0]) if parts[0] else None
            end_line = int(parts[1]) if parts[1] else None
            return start_line, end_line
        else:
            line_num = int(line)
            return line_num, line_num