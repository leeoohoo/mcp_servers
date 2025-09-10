"""删除内容操作

处理文件内容删除相关的逻辑。
"""

from typing import AsyncGenerator, Optional
from .base_operation import BaseOperation
from file_operations import PreciseTextModifier


class DeleteOperation(BaseOperation):
    """删除内容操作类"""
    
    async def execute(
        self, 
        file_path: str, 
        line: Optional[str] = None, 
        content: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """执行删除内容操作
        
        Args:
            file_path: 文件路径
            line: 要删除的行号或行范围
            content: 内容（删除操作不使用）
            
        Yields:
            操作结果的字符串流
        """
        try:
            # 验证参数
            if not line:
                yield f"\n❌ 删除需要 line 参数\n"
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
            
            yield f"\n🗑️ 删除第 {start_line}-{end_line} 行...\n"
            modifier.delete_lines(start_line, end_line)
            
            saved_path = modifier.save()
            yield f"\n✅ 删除完成! 文件: {saved_path}\n"
            yield f"\n📊 文件总行数: {modifier.get_line_count()}\n"
            
        except Exception as e:
            yield f"\n❌ 删除内容时出错: {str(e)}\n"