"""查看文件操作

处理文件查看相关的逻辑。
"""

import os
from typing import AsyncGenerator, Optional
from .base_operation import BaseOperation
from file_operations import PreciseTextModifier, get_markdown_language, show_directory_structure


class ViewOperation(BaseOperation):
    """查看文件操作类"""
    
    async def execute(
        self, 
        file_path: str, 
        line: Optional[str] = None, 
        content: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """执行查看文件操作
        
        Args:
            file_path: 文件路径
            line: 行号或行范围
            content: 内容（查看操作不使用）
            
        Yields:
            操作结果的字符串流
        """
        try:
            # 验证文件访问权限
            validated_path = self.validate_file_access(file_path, allow_nonexistent=False)
            yield f"\n🔍 文件: {validated_path}\n"
            
            # 特殊处理目录情况
            if os.path.isdir(validated_path):
                # 获取配置
                project_root = self.get_config_value("project_root", "")
                if not project_root:
                    project_root = os.getcwd()
                
                # 规范化路径
                project_root = os.path.abspath(project_root)
                normalized_dir_path = os.path.normpath(validated_path)
                normalized_project_root = os.path.normpath(project_root)
                
                # 安全检查：确保目录路径在project_root下
                if not normalized_dir_path.startswith(normalized_project_root):
                    yield f"\n❌ 安全限制：只允许查看项目根目录 {project_root} 下的目录\n"
                    return
                
                yield f"\n📁 检测到目录，展示目录结构...\n"
                
                # 展示目录结构
                async for chunk in show_directory_structure(validated_path, max_depth=10, include_hidden=False):
                    yield chunk
                
                yield f"\n✅ 目录结构展示完成!\n"
                return
            
            # 解析行号参数
            start_line, end_line = self.parse_line_range(line)
            
            # 创建文件修改器（不备份，只读取）
            modifier = PreciseTextModifier(validated_path, backup=False)
            
            # 文件查看逻辑
            actual_start = start_line or 1
            actual_end = end_line or modifier.get_line_count()
            markdown_language = get_markdown_language(validated_path)
            
            yield f"\n👀 查看第 {actual_start}-{actual_end} 行:\n\n"
            yield f"```{markdown_language}\n"
            
            lines = modifier.get_lines(actual_start, actual_end)
            for i, line in enumerate(lines, actual_start):
                line_content = line.rstrip()
                yield f"{i}:{line_content}\n"
            
            yield "```\n"
            yield f"\n✅ 查看完成!\n"
            
        except Exception as e:
            yield f"\n❌ 查看文件时出错: {str(e)}\n"