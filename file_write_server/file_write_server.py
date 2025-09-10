#!/usr/bin/env python3
import asyncio
import os
from typing import Annotated, Optional, Any, AsyncGenerator
from mcp_framework import EnhancedMCPServer, run_server_main
from mcp_framework.core.decorators import (
    Required as R,
    Optional as O,
    IntRange,
    BooleanParam,
    PathParam,
    ServerParam
)
from file_operations import (
    PreciseTextModifier,
    get_markdown_language,
    show_directory_structure,
    validate_file_access
)
from operations import (
    CreateOperation,
    RemoveOperation,
    EditOperation,
    InsertOperation,
    DeleteOperation,
    ViewOperation
)





class FileWriteServer(EnhancedMCPServer):
    """文件修改 MCP 服务器"""
    
    def __init__(self):
        super().__init__(
            name="FileWriteServer",
            version="1.0.0",
            description="基于行号的精准文件修改服务器"
        )
        
        # 初始化操作实例
        self.operations = {
            "create": CreateOperation(self),
            "remove": RemoveOperation(self),
            "edit": EditOperation(self),
            "insert": InsertOperation(self),
            "delete": DeleteOperation(self),
            "view": ViewOperation(self)
        }
    

    

        
    
    async def initialize(self):
        """初始化服务器"""
        self.logger.info("FileWriteServer 初始化完成")
    

    
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
                default_value=False,
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
                        "• `view` - View file content (entire file or specified range) or directory structure\n" +
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
                        "• `view`: Optional line parameter - view entire file if not passed, view specified range if passed. If path is a directory, shows directory structure recursively\n" +
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
                yield f"\n🔧 操作: {action}\n"
                
                # 检查操作是否支持
                if action not in self.operations:
                    yield f"\n❌ 不支持的操作: {action}\n"
                    yield f"\n📋 支持操作: {', '.join(self.operations.keys())}\n"
                    return
                
                # 使用对应的操作实例执行操作
                operation = self.operations[action]
                async for result in operation.execute(file_path, line, content):
                    yield result
                

                

                
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