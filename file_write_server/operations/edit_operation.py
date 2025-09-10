"""编辑文件操作

处理文件编辑相关的逻辑。
"""

from typing import AsyncGenerator, Optional
from .base_operation import BaseOperation
from file_operations import PreciseTextModifier


class EditOperation(BaseOperation):
    """编辑文件操作类"""
    
    async def execute(
        self, 
        file_path: str, 
        line: Optional[str] = None, 
        content: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """执行编辑文件操作
        
        Args:
            file_path: 文件路径
            line: 行号或行范围
            content: 新内容
            
        Yields:
            操作结果的字符串流
        """
        try:
            # 验证参数
            if not line or not content:
                yield f"\n❌ 编辑需要 line 和 content 参数\n"
                return
            
            # 验证文件访问权限
            validated_path = self.validate_file_access(file_path, allow_nonexistent=False)
            yield f"\n🔍 文件: {validated_path}\n"
            
            # 解析行号参数
            start_line, end_line = self.parse_line_range(line)
            
            # 获取自动备份配置
            auto_backup = self.get_config_value("auto_backup", True)
            
            # 创建文件修改器
            modifier = PreciseTextModifier(validated_path, backup=auto_backup)
            
            if start_line == end_line:
                yield f"\n📝 修改第 {start_line} 行...\n"
                modifier.modify_line(start_line, content)
            else:
                yield f"\n📝 修改第 {start_line}-{end_line} 行...\n"
                lines = content.split('\n') if '\n' in content else [content]
                modifier.modify_range(start_line, end_line, lines)
            
            saved_path = modifier.save()
            yield f"\n✅ 修改完成! 文件: {saved_path}\n"
            yield f"\n📊 文件总行数: {modifier.get_line_count()}\n"
            
        except Exception as e:
            yield f"\n❌ 编辑文件时出错: {str(e)}\n"