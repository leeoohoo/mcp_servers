"""删除文件操作

处理文件删除相关的逻辑。
"""

import os
from typing import AsyncGenerator, Optional
from .base_operation import BaseOperation


class RemoveOperation(BaseOperation):
    """删除文件操作类"""
    
    async def execute(
        self, 
        file_path: str, 
        line: Optional[str] = None, 
        content: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """执行删除文件操作
        
        Args:
            file_path: 文件路径
            line: 行号（删除操作不使用）
            content: 内容（删除操作不使用）
            
        Yields:
            操作结果的字符串流
        """
        try:
            # 验证文件访问权限（文件必须存在）
            validated_path = self.validate_file_access(file_path, allow_nonexistent=False)
            yield f"\n🔍 文件: {validated_path}\n"
            
            # 删除文件
            os.remove(validated_path)
            yield f"\n✅ 文件删除成功: {validated_path}\n"
            
        except PermissionError as e:
            yield f"\n❌ 权限错误: {str(e)}\n"
        except Exception as e:
            yield f"\n❌ 删除文件时出错: {str(e)}\n"