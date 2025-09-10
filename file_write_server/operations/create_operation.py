"""创建文件操作

处理文件创建相关的逻辑。
"""

import os
from typing import AsyncGenerator, Optional
from .base_operation import BaseOperation
from file_operations import get_markdown_language


class CreateOperation(BaseOperation):
    """创建文件操作类"""
    
    async def execute(
        self, 
        file_path: str, 
        line: Optional[str] = None, 
        content: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """执行创建文件操作
        
        Args:
            file_path: 文件路径
            line: 行号（创建操作不使用）
            content: 文件初始内容
            
        Yields:
            操作结果的字符串流
        """
        try:
            # 验证文件访问权限（允许不存在的文件）
            validated_path = self.validate_file_access(file_path, allow_nonexistent=True)
            yield f"\n🔍 文件: {validated_path}\n"
            
            # 检查文件是否已存在
            if os.path.exists(validated_path):
                yield f"\n❌ 文件已存在: {validated_path}\n"
                return
            
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(validated_path), exist_ok=True)
            
            # 创建文件
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content or "")
            
            yield f"\n✅ 文件创建成功: {validated_path}\n"
            
            # 显示初始内容
            if content:
                markdown_language = get_markdown_language(validated_path)
                yield f"📄 初始内容已写入:\n\n"
                yield f"```{markdown_language}\n"
                # 显示内容，带行号
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if line.strip():  # 只显示非空行
                        yield f"{i}:{line}\n"
                yield "```\n"
                
        except PermissionError as e:
            yield f"\n❌ 权限错误: {str(e)}\n"
        except Exception as e:
            yield f"\n❌ 创建文件时出错: {str(e)}\n"