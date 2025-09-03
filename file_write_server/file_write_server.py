#!/usr/bin/env python3
import asyncio
import os
import shutil
from typing import Annotated, List, Dict, Union, Optional, Any, AsyncGenerator
from mcp_framework import EnhancedMCPServer, run_server_main
from mcp_framework.core.decorators import (
    Required as R,
    Optional as O,
    IntRange,
    BooleanParam,
    PathParam,
    ServerParam
)


class PreciseTextModifier:
    """精准文本修改器 - 基于行号的文本编辑工具"""
    
    def __init__(self, file_path: str, backup: bool = True):
        self.file_path = file_path
        self.original_content = None
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 创建备份
        if backup:
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()
            self.original_content = ''.join(self.lines)
    
    def modify_line(self, line_num: int, new_content: str) -> 'PreciseTextModifier':
        """修改单行"""
        if 1 <= line_num <= len(self.lines):
            self.lines[line_num - 1] = new_content + '\n' if not new_content.endswith('\n') else new_content
        else:
            raise IndexError(f"行号 {line_num} 超出范围 (1-{len(self.lines)})")
        return self
    
    def modify_range(self, start_line: int, end_line: int, new_content: Union[str, List[str]]) -> 'PreciseTextModifier':
        """修改行范围"""
        if start_line < 1 or end_line > len(self.lines) or start_line > end_line:
            raise IndexError(f"行号范围无效: {start_line}-{end_line}, 文件总行数: {len(self.lines)}")
        
        if isinstance(new_content, str):
            new_lines = [new_content + '\n'] if not new_content.endswith('\n') else [new_content]
        else:
            new_lines = [line + '\n' if not line.endswith('\n') else line for line in new_content]
        
        start_idx = start_line - 1
        end_idx = end_line
        self.lines = self.lines[:start_idx] + new_lines + self.lines[end_idx:]
        return self
    
    def insert_lines(self, line_num: int, content: Union[str, List[str]]) -> 'PreciseTextModifier':
        """在指定行号后插入内容"""
        if line_num < 0 or line_num > len(self.lines):
            raise IndexError(f"插入位置无效: {line_num}, 文件总行数: {len(self.lines)}")
        
        if isinstance(content, str):
            content = [content]
        
        insert_lines = [line + '\n' if not line.endswith('\n') else line for line in content]
        self.lines = self.lines[:line_num] + insert_lines + self.lines[line_num:]
        return self
    
    def delete_lines(self, start_line: int, end_line: int) -> 'PreciseTextModifier':
        """删除指定范围的行"""
        if start_line < 1 or end_line > len(self.lines) or start_line > end_line:
            raise IndexError(f"删除范围无效: {start_line}-{end_line}, 文件总行数: {len(self.lines)}")
        
        start_idx = start_line - 1
        end_idx = end_line
        self.lines = self.lines[:start_idx] + self.lines[end_idx:]
        return self
    
    def batch_modify(self, modifications: Dict[int, str]) -> 'PreciseTextModifier':
        """批量修改多行"""
        # 从后往前修改避免行号变化
        for line_num in sorted(modifications.keys(), reverse=True):
            self.modify_line(line_num, modifications[line_num])
        return self
    
    def get_lines(self, start_line: Optional[int] = None, end_line: Optional[int] = None) -> List[str]:
        """获取指定范围的行"""
        if start_line is None and end_line is None:
            return self.lines
        
        start_idx = (start_line - 1) if start_line else 0
        end_idx = end_line if end_line else len(self.lines)
        return self.lines[start_idx:end_idx]
    
    def save(self, output_path: Optional[str] = None) -> str:
        """保存文件"""
        path = output_path or self.file_path
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(self.lines)
        return path
    
    def get_content(self) -> str:
        """获取当前内容"""
        return ''.join(self.lines)
    
    def get_line_count(self) -> int:
        """获取总行数"""
        return len(self.lines)


class FileWriteServer(EnhancedMCPServer):
    """文件修改 MCP 服务器"""
    
    def __init__(self):
        super().__init__(
            name="FileWriteServer",
            version="1.0.0",
            description="基于行号的精准文件修改服务器"
        )
    
    def _get_markdown_language(self, file_path: str) -> str:
        """根据文件扩展名获取markdown语言标识符"""
        from pathlib import Path
        extension = Path(file_path).suffix.lower()
        
        # 文件扩展名到markdown语言的映射
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.jsx': 'jsx',
            '.java': 'java',
            '.kt': 'kotlin',
            '.swift': 'swift',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.dart': 'dart',
            '.vue': 'vue',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'zsh',
            '.fish': 'fish',
            '.bat': 'batch',
            '.ps1': 'powershell',
            '.dockerfile': 'dockerfile',
            '.makefile': 'makefile',
            '.cmake': 'cmake',
            '.gradle': 'gradle',
            '.properties': 'properties',
            '.env': 'bash',
            '.gitignore': 'gitignore',
            '.md': 'markdown',
            '.txt': 'text',
            '.log': 'log',
            '.csv': 'csv',
            '.tsv': 'tsv'
        }
        
        return language_map.get(extension, 'text')
        
    
    async def initialize(self):
        """初始化服务器"""
        self.logger.info("FileWriteServer 初始化完成")
    
    def _validate_file_access(self, file_path: str) -> str:
        """验证文件访问权限"""
        # 获取配置
        project_root = self.get_config_value("project_root", "")
        max_file_size_mb = self.get_config_value("max_file_size", 10)
        enable_hidden_files = self.get_config_value("enable_hidden_files", False)
        
        # 处理相对路径
        if not os.path.isabs(file_path):
            if project_root:
                # 清理路径前缀，移除 ./ 等
                clean_path = file_path.lstrip('./').lstrip('\\')
                file_path = os.path.join(project_root, clean_path)
            else:
                file_path = os.path.abspath(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查是否为隐藏文件
        if not enable_hidden_files and os.path.basename(file_path).startswith('.'):
            raise PermissionError("不允许访问隐藏文件")
        
        # 检查文件大小
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > max_file_size_mb:
            raise ValueError(f"文件大小 ({file_size_mb:.2f}MB) 超过限制 ({max_file_size_mb}MB)")
        
        return file_path
    
    @property
    def setup_server_params(self):
        """设置服务器参数装饰器"""
        
        @self.decorators.server_param("project_root")
        async def project_root_param(
            param: Annotated[str, PathParam(
                display_name="项目根目录",
                description="服务器操作的根目录路径，留空使用当前目录",
                required=False,
                placeholder="/path/to/project"
            )]
        ):
            """项目根目录参数"""
            pass
        
        @self.decorators.server_param("max_file_size")
        async def max_file_size_param(
            param: Annotated[int, ServerParam(
                display_name="最大文件大小 (MB)",
                description="允许修改的最大文件大小，单位MB",
                param_type="integer",
                default_value=10,
                required=False
            )]
        ):
            """最大文件大小参数"""
            pass
        
        @self.decorators.server_param("enable_hidden_files")
        async def enable_hidden_files_param(
            param: Annotated[bool, BooleanParam(
                display_name="启用隐藏文件",
                description="是否允许修改以点(.)开头的隐藏文件",
                default_value=False,
                required=False
            )]
        ):
            """启用隐藏文件参数"""
            pass
        
        @self.decorators.server_param("auto_backup")
        async def auto_backup_param(
            param: Annotated[bool, BooleanParam(
                display_name="自动备份",
                description="修改文件前是否自动创建备份",
                default_value=True,
                required=False
            )]
        ):
            """自动备份参数"""
            pass
        
        return True
    
    async def on_config_updated(self, config_key: str, new_value: Any) -> None:
        """配置更新回调方法"""
        self.logger.info(f"配置已更新: {config_key} = {new_value}")
        # 这里可以根据需要添加特定配置的处理逻辑
    
    @property
    def setup_tools(self):
        """设置工具装饰器"""

        @self.streaming_tool(
            description="📝 **File Operations Tool** - Powerful file management tool\n" +
                        "\n🎯 **Supported Operation Types**:\n" +
                        "• `create` - Create new file (with optional initial content)\n" +
                        "• `edit` - Modify file content (single line or multi-line replacement)\n" +
                        "• `insert` - Insert new content at specified position\n" +
                        "• `delete` - Delete specified line or line range\n" +
                        "• `view` - View file content (entire file or specified range)\n" +
                        "• `remove` - Delete entire file\n" +
                        "\n📋 **Parameter Details**:\n" +
                        "\n**Parameter: `file_path`** (Required):\n" +
                        "• All operations must provide the complete path to the target file\n" +
                        "• Supports both absolute and relative paths\n" +
                        "• Examples: file_path='./src/main.py', file_path='/home/user/config.json'\n" +
                        "\n**Parameter: `action`** (Required):\n" +
                        "• Must be one of: create, edit, insert, delete, view, remove\n" +
                        "• Case-sensitive, must use lowercase\n" +
                        "• Examples: action='create', action='edit', action='view'\n" +
                        "\n**Parameter: `line`** (Conditionally Required):\n" +
                        "• `create`: No need to pass line parameter\n" +
                        "• `edit`: Must pass line parameter - specify line number or range to modify\n" +
                        "• `insert`: Must pass line parameter - specify line number for insertion position\n" +
                        "• `delete`: Must pass line parameter - specify line number or range to delete\n" +
                        "• `view`: Optional line parameter - view entire file if not passed, view specified range if passed\n" +
                        "• `remove`: No need to pass line parameter\n" +
                        "• Format: Single line '5' or range '5-10' or '1-' (from line 1 to end)\n" +
                        "• Examples: line='1', line='5-10', line='3-', line='-5'\n" +
                        "\n**Parameter: `content`** (Conditionally Required):\n" +
                        "• `create`: Optional content parameter - creates empty file if not passed, writes initial content if passed\n" +
                        "• `edit`: Must pass content parameter - new content will replace specified lines\n" +
                        "• `insert`: Must pass content parameter - content to be inserted\n" +
                        "• `delete`: No need to pass content parameter\n" +
                        "• `view`: No need to pass content parameter\n" +
                        "• `remove`: No need to pass content parameter\n" +
                        "• Use '\\n' to separate multi-line content\n" +
                        "• Examples: content='Hello World', content='Line1\\nLine2\\nLine3'\n" +
                        "\n💡 **Complete Usage Examples**:\n" +
                        "\n**Create File**:\n" +
                        "• Create empty file: file_path='test.txt', action='create'\n" +
                        "• Create with content: file_path='app.py', action='create', content='#!/usr/bin/env python3\\nprint(\"Hello\")'\n" +
                        "\n**View File**:\n" +
                        "• View entire file: file_path='config.json', action='view'\n" +
                        "• View specific lines: file_path='main.py', action='view', line='1-20'\n" +
                        "• View first 10 lines: file_path='log.txt', action='view', line='-10'\n" +
                        "\n**Edit File**:\n" +
                        "• Modify single line: file_path='config.py', action='edit', line='5', content='DEBUG = True'\n" +
                        "• Modify multiple lines: file_path='README.md', action='edit', line='1-3', content='# Project Title\\n\\nProject Description'\n" +
                        "• Replace to end: file_path='script.sh', action='edit', line='10-', content='echo \"new content\"'\n" +
                        "\n**Insert Content**:\n" +
                        "• Insert before line 5: file_path='index.html', action='insert', line='5', content='<meta charset=\"UTF-8\">'\n" +
                        "• Insert at beginning: file_path='main.py', action='insert', line='1', content='# -*- coding: utf-8 -*-'\n" +
                        "\n**Delete Content**:\n" +
                        "• Delete single line: file_path='temp.txt', action='delete', line='3'\n" +
                        "• Delete line range: file_path='old_code.py', action='delete', line='10-20'\n" +
                        "• Delete from line 5 to end: file_path='log.txt', action='delete', line='5-'\n" +
                        "\n**Delete File**:\n" +
                        "• Delete entire file: file_path='temp.txt', action='remove'\n" +
                        "\n📝 **Parameter Format Summary**:\n" +
                        "• All operations: file_path='path', action='operation_type'\n" +
                        "• Operations requiring line numbers: add line='line_number_or_range'\n" +
                        "• Operations requiring content: add content='file_content'\n" +
                        "\n⚠️ **Important Notes**:\n" +
                        "• Parameter names must match exactly: file_path, action, line, content\n" +
                        "• File path must be accurate, non-existent paths will cause errors\n" +
                        "• Edit operations directly modify original files, backup important files first\n" +
                        "• Line numbers start from 1, out-of-range numbers will be automatically adjusted"
        )
        async def modify_file(
                file_path: Annotated[str, R("File path")],
                action: Annotated[str, R("Operation: create|edit|insert|delete|view|remove")],
                line: Annotated[Optional[str], O("Line number or range (e.g.: 5 or 5-10)")] = None,
                content: Annotated[Optional[str], O("Content")] = None
        ) -> AsyncGenerator[str, None]:
            """简单易用的文件操作工具"""
            try:
                auto_backup = self.get_config_value("auto_backup", True)
                
                yield f"\n🔧 操作: {action}\n"
                
                # 新建文件操作
                if action == "create":
                    # 处理相对路径
                    if not os.path.isabs(file_path):
                        project_root = self.get_config_value("project_root", "")
                        if project_root:
                            # 清理路径前缀，移除 ./ 等
                            clean_path = file_path.lstrip('./').lstrip('\\')
                            file_path = os.path.join(project_root, clean_path)
                        else:
                            file_path = os.path.abspath(file_path)
                    
                    if os.path.exists(file_path):
                        yield f"\n❌ 文件已存在: {file_path}\n"
                        return
                    
                    # 创建目录（如果不存在）
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # 创建文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content or "")
                    
                    yield f"\n✅ 文件创建成功: {file_path}\n"
                    if content:
                        markdown_language = self._get_markdown_language(file_path)
                        yield f"📄 初始内容已写入:\n\n"
                        yield f"```{markdown_language}\n"
                        # 显示内容，带行号
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if line.strip():  # 只显示非空行
                                yield f"{i}:{line}\n"
                        yield "```\n"
                    return
                
                # 删除文件操作
                elif action == "remove":
                    # 处理相对路径
                    if not os.path.isabs(file_path):
                        project_root = self.get_config_value("project_root", "")
                        if project_root:
                            # 清理路径前缀，移除 ./ 等
                            clean_path = file_path.lstrip('./').lstrip('\\')
                            file_path = os.path.join(project_root, clean_path)
                        else:
                            file_path = os.path.abspath(file_path)
                    
                    if not os.path.exists(file_path):
                        yield f"\n❌ 文件不存在: {file_path}\n"
                        return
                    
                    # 创建备份（如果启用）
                    if auto_backup:
                        backup_path = f"{file_path}.backup"
                        shutil.copy2(file_path, backup_path)
                        yield f"\n💾 已创建备份: {backup_path}\n"
                    
                    # 删除文件
                    os.remove(file_path)
                    yield f"\n✅ 文件删除成功: {file_path}\n"
                    return
                
                # 其他操作需要验证文件访问权限
                validated_path = self._validate_file_access(file_path)
                yield f"\n🔍 文件: {validated_path}\n"
                
                # 解析行号参数
                start_line, end_line = None, None
                if line:
                    if '-' in line:
                        parts = line.split('-')
                        start_line, end_line = int(parts[0]), int(parts[1])
                    else:
                        start_line = end_line = int(line)
                
                modifier = PreciseTextModifier(validated_path, backup=auto_backup if action != 'view' else False)
                
                if action == "edit":
                    if not line or not content:
                        yield f"\n❌ 编辑需要 line 和 content 参数\n"
                        return
                    
                    if start_line == end_line:
                        yield f"\n📝 修改第 {start_line} 行...\n"
                        modifier.modify_line(start_line, content)
                    else:
                        yield f"\n📝 修改第 {start_line}-{end_line} 行...\n"
                        lines = content.split('\n') if '\n' in content else [content]
                        modifier.modify_range(start_line, end_line, lines)
                    
                    saved_path = modifier.save()
                    yield f"\n✅ 修改完成! 文件: {saved_path}\n"
                    
                elif action == "insert":
                    if not line or not content:
                        yield f"\n❌ 插入需要 line 和 content 参数\n"
                        return
                    
                    yield f"\n➕ 在第 {start_line} 行前插入...\n"
                    lines = content.split('\n') if '\n' in content else [content]
                    modifier.insert_lines(start_line, lines)
                    saved_path = modifier.save()
                    yield f"\n✅ 插入完成! 文件: {saved_path}\n"
                    
                elif action == "delete":
                    if not line:
                        yield f"\n❌ 删除需要 line 参数\n"
                        return
                    
                    yield f"\n🗑️ 删除第 {start_line}-{end_line} 行...\n"
                    modifier.delete_lines(start_line, end_line)
                    saved_path = modifier.save()
                    yield f"\n✅ 删除完成! 文件: {saved_path}\n"
                    
                elif action == "view":
                    actual_start = start_line or 1
                    actual_end = end_line or modifier.get_line_count()
                    markdown_language = self._get_markdown_language(validated_path)
                    
                    yield f"\n👀 查看第 {actual_start}-{actual_end} 行:\n\n"
                    yield f"```{markdown_language}\n"
                    
                    lines = modifier.get_lines(actual_start, actual_end)
                    for i, line in enumerate(lines, actual_start):
                        line_content = line.rstrip()
                        if line_content.strip():  # 只输出非空行
                            yield f"{i}:{line_content}\n"
                    
                    yield "```\n"
                    yield f"\n✅ 查看完成!\n"
                    return
                    
                else:
                    yield f"\n❌ 不支持的操作: {action}\n"
                    yield f"\n📋 支持操作: create, edit, insert, delete, view, remove\n"
                    return
                
                yield f"\n📊 文件总行数: {modifier.get_line_count()}\n"
                
            except Exception as e:
                yield f"\n❌ 操作失败: {str(e)}\n"
                yield f"\n📁 文件路径: {file_path}\n"
        
        return True


# 启动服务器
if __name__ == "__main__":
    server = FileWriteServer()
    run_server_main(
        server_instance=server,
        server_name="FileWriteServer",
        default_port=8080
    )