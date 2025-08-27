#!/usr/bin/env python3
"""
Terminal Manager MCP Server
基于 MCP 框架的终端管理服务器
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from typing_extensions import Annotated
import json
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# 导入 MCP 框架
from mcp_framework.core.base import EnhancedMCPServer
from mcp_framework.core.decorators import (
    Required as R, Optional as O, Str, Int, Bool,
    ServerParam, StringParam, BooleanParam, SelectParam
)
from mcp_framework.core.config import ServerParameter

# 导入现有的服务和模型
from terminal_manager_server.services.terminal_service import TerminalService
from terminal_manager_server.services.command_service import CommandService
from terminal_manager_server.models.database import db
from terminal_manager_server.utils.logger import setup_logging


class TerminalMCPServer(EnhancedMCPServer):
    """Terminal Manager MCP Server"""
    
    def __init__(self):
        super().__init__(
            name="Terminal MCP Server",
            version="1.0.0",
            description="基于 MCP 框架的终端管理服务器，提供终端创建、命令执行等功能"
        )
        
        # 初始化服务
        self.terminal_service = None
        self.command_service = None
        self.logger = logging.getLogger(__name__)
    
    @property
    def setup_server_params(self):
        """注册服务器参数"""
        
        @self.decorators.server_param("storage_type")
        async def storage_type_param(
            param: Annotated[str, SelectParam(
                display_name="存储类型",
                description="数据存储方式",
                options=["file", "mongodb"],
                default_value="file",
                required=True
            )]
        ):
            """存储类型参数"""
            pass
        
        @self.decorators.server_param("mongodb_uri")
        async def mongodb_uri_param(
            param: Annotated[str, ServerParam(
                display_name="MongoDB连接URI",
                description="完整的MongoDB连接字符串，包含用户名密码。示例：mongodb://username:password@localhost:27017/database_name?authSource=admin",
                param_type="string",
                default_value="mongodb://admin:password@localhost:27017/terminal_manager?authSource=admin",
                required=False
            )]
        ):
            """MongoDB URI参数"""
            pass
        
        @self.decorators.server_param("data_dir")
        async def data_dir_param(
            param: Annotated[str, ServerParam(
                display_name="数据目录",
                description="文件存储模式下的数据目录路径（当storage_type为'file'时使用）",
                param_type="string",
                default_value="data",
                required=False
            )]
        ):
            """数据目录参数"""
            pass
        
        @self.decorators.server_param("max_terminals")
        async def max_terminals_param(
            param: Annotated[int, ServerParam(
                display_name="最大终端数",
                description="允许创建的最大终端数量",
                param_type="integer",
                default_value=10,
                required=False
            )]
        ):
            """最大终端数参数"""
            pass
        
        @self.decorators.server_param("default_dir")
        async def default_dir_param(
            param: Annotated[str, ServerParam(
                display_name="默认工作目录",
                description="创建终端时的默认工作目录，只允许在此目录下创建终端",
                param_type="string",
                default_value="/Users/lilei/project/learn/test_dir",
                required=False
            )]
        ):
            """默认工作目录参数"""
            pass
        
        @self.decorators.server_param("enable_cleanup")
        async def enable_cleanup_param(
            param: Annotated[bool, ServerParam(
                display_name="启用自动清理",
                description="是否启用非活跃终端的自动清理",
                param_type="boolean",
                default_value=True,
                required=False
            )]
        ):
            """启用自动清理参数"""
            pass
        
        @self.decorators.server_param("cleanup_threshold_minutes")
        async def cleanup_threshold_param(
            param: Annotated[int, ServerParam(
                display_name="清理阈值（分钟）",
                description="终端非活跃多少分钟后被清理",
                param_type="integer",
                default_value=20,
                required=False
            )]
        ):
            """清理阈值参数"""
            pass
    
        return True
    
    @property
    def setup_tools(self):
        """注册所有工具"""
        
        # Terminal Management Tools
        @self.streaming_tool(
            description="""Create a new terminal instance
            
            Features:
            - Create a new terminal instance in the specified working directory
            - Each terminal has a unique ID and can execute commands independently
            - Support custom working directory, defaults to current directory
            
            Use Cases:
            - When you need to execute commands in different directories
            - When you need to run multiple tasks in parallel
            - When you need to isolate command execution environments for different projects
            
            Examples:
            1. Create default terminal: create_terminal()
            2. Create terminal in specific directory: create_terminal("/path/to/project")
            3. Create multiple terminals for different tasks
            """
        )
        async def create_terminal(
            working_directory: Annotated[str, O("""Working directory path
            
            Description: Initial working directory for the new terminal
            - If not specified, will use the current working directory
            - Path must exist and be accessible
            - Supports both relative and absolute paths
            - Must be within the configured default directory
            
            Examples:
            - "/Users/username/project" (absolute path)
            - "./src" (relative path)
            - "~/Documents" (user directory)
            """)] = None
        ) -> AsyncGenerator[str, None]:
            """创建新终端"""
            try:
                if working_directory is None:
                    working_directory = os.getcwd()
                
                terminal = self.terminal_service.create_terminal(working_directory)
                if not terminal:
                    yield json.dumps({
                        "success": False,
                        "error": "创建终端失败",
                        "error_code": "CREATION_FAILED"
                    }, ensure_ascii=False)
                    return
                
                # 检查是否是复用的终端
                from models.command import Command
                recent_commands = Command.find_recent_by_terminal_id(terminal.terminal_id, limit=1)
                is_reused = len(recent_commands) > 0
                
                yield json.dumps({
                    "success": True,
                    "data": {
                        "terminal_id": terminal.terminal_id,
                        "working_directory": terminal.working_directory,
                        "status": terminal.status,
                        "created_at": terminal.created_at.isoformat(),
                        "is_reused": is_reused
                    },
                    "message": "复用空闲终端" if is_reused else "创建新终端成功"
                }, ensure_ascii=False)
            except ValueError as ve:
                # 处理工作目录验证失败
                error_parts = str(ve).split(':')
                if len(error_parts) >= 2 and error_parts[0] == "INVALID_WORKING_DIRECTORY":
                    allowed_dir = error_parts[1]
                    yield json.dumps({
                        "success": False,
                        "error": f"工作目录不在允许范围内。请求目录: {working_directory}, 允许的工作目录: {allowed_dir}",
                        "error_code": "INVALID_WORKING_DIRECTORY",
                        "allowed_directory": allowed_dir
                    }, ensure_ascii=False)
                else:
                    yield json.dumps({
                        "success": False,
                        "error": str(ve),
                        "error_code": "VALIDATION_ERROR"
                    }, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"创建终端异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="""Get terminal list and detailed information
            
            Features:
            - Get detailed information about all terminals in the system
            - Display status, working directory, running commands for each terminal
            - Support filtering terminals by status
            - Include recent command execution history
            
            Return Information:
            - Terminal ID, status, creation time
            - Current working directory
            - Currently running commands (if any)
            - Recent 5 command history
            - Command execution statistics
            
            Use Cases:
            - View status of all terminals in the system
            - Monitor running tasks
            - Manage and clean up terminal resources
            
            Examples:
            1. Get all terminals: get_terminals()
            2. View only active terminals: get_terminals("active")
            3. View inactive terminals: get_terminals("inactive")
            """
        )
        async def get_terminals(
            status_filter: Annotated[str, O("""Terminal status filter
            
            Available values:
            - "all": Show all terminals (default)
            - "active": Show only active terminals
            - "inactive": Show only inactive terminals
            
            Description:
            - active: Terminal is running normally and can execute commands
            - inactive: Terminal has stopped or encountered an error
            
            Examples:
            - "all" - View all terminal statuses
            - "active" - Focus only on available terminals
            - "inactive" - Find terminals that need cleanup
            """)] = "all"
        ) -> AsyncGenerator[str, None]:
            """获取终端列表"""
            try:
                if status_filter == "active":
                    terminals = self.terminal_service.get_active_terminals()
                else:
                    # 获取所有终端的逻辑需要在 terminal_service 中实现
                    terminals = self.terminal_service.get_active_terminals()  # 暂时使用活跃终端
                
                terminal_list = []
                for terminal in terminals:
                    # 获取最近5个命令
                    from models.command import Command
                    recent_commands = Command.find_recent_by_terminal_id(terminal.terminal_id, limit=5)
                    
                    # 检查是否有正在运行的命令
                    running_command = Command.find_running_by_terminal_id(terminal.terminal_id)
                    is_running = running_command is not None
                    
                    # 格式化命令信息
                    commands_info = []
                    for cmd in recent_commands:
                        commands_info.append({
                            "command_id": cmd.command_id,
                            "command": cmd.command,
                            "status": cmd.status,
                            "command_type": cmd.command_type,
                            "start_time": cmd.start_time.isoformat() if cmd.start_time else None,
                            "end_time": cmd.end_time.isoformat() if cmd.end_time else None,
                            "exit_code": cmd.exit_code,
                            "duration": cmd.get_duration()
                        })
                    
                    terminal_info = {
                        "terminal_id": terminal.terminal_id,
                        "working_directory": terminal.working_directory,
                        "status": terminal.status,
                        "created_at": terminal.created_at.isoformat(),
                        "is_running": is_running,
                        "running_command": {
                            "command_id": running_command.command_id,
                            "command": running_command.command,
                            "status": running_command.status,
                            "start_time": running_command.start_time.isoformat() if running_command.start_time else None
                        } if running_command else None,
                        "recent_commands": commands_info,
                        "recent_commands_count": len(commands_info)
                    }
                    
                    terminal_list.append(terminal_info)
                
                yield json.dumps({
                    "success": True,
                    "data": {
                        "terminals": terminal_list,
                        "count": len(terminal_list)
                    },
                    "message": f"获取到 {len(terminal_list)} 个终端"
                }, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"获取终端列表异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="""Delete specified terminal instance
            
            Features:
            - Safely delete the specified terminal instance
            - Automatically terminate running commands in the terminal
            - Clean up related resources and data
            - Release system resources
            
            Important Notes:
            - Deletion operation is irreversible, use with caution
            - If there are important running tasks in the terminal, stop them manually first
            - The terminal ID will no longer be available after deletion
            
            Use Cases:
            - Clean up terminals that are no longer needed
            - Release system resources
            - Reset terminal environment
            
            Examples:
            1. Delete specific terminal: delete_terminal("terminal_123")
            2. Batch cleanup: first use get_terminals to view, then delete one by one
            """
        )
        async def delete_terminal(
            terminal_id: Annotated[str, R("""Terminal ID to delete
            
            Description:
            - Must be a valid terminal ID
            - Available terminal ID list can be obtained through get_terminals()
            - Format is usually a string, such as "terminal_123"
            
            How to obtain:
            1. Use get_terminals() to view all terminals
            2. Find the terminal_id to delete from the returned results
            3. Copy the complete ID string
            
            Examples:
            - "terminal_abc123" - Standard terminal ID
            - "term_001" - Short ID format
            """)]
        ) -> AsyncGenerator[str, None]:
            """删除终端"""
            try:
                success = self.terminal_service.delete_terminal(terminal_id)
                if success:
                    yield json.dumps({
                        "success": True,
                        "message": f"终端 {terminal_id} 删除成功"
                    }, ensure_ascii=False)
                else:
                    yield json.dumps({
                        "success": False,
                        "error": "删除终端失败",
                        "error_code": "DELETION_FAILED"
                    }, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"删除终端异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="""Execute command in specified terminal
            
            Features:
            - Execute shell commands in the specified terminal instance
            - Support real-time output streaming
            - Support different command execution types
            - Support monitoring of long-running commands
            
            Command Type Description:
            - normal: Regular commands like ls, cat, echo
            - service: Service commands like starting web servers
            - interactive: Interactive commands requiring user input
            
            Output Format:
            - command_start: Command starts executing
            - output: Real-time output content
            - command_complete: Command execution completed
            
            Use Cases:
            - Execute file operation commands
            - Start development servers
            - Run build scripts
            - Execute test commands
            
            Examples:
            1. Basic command: execute_command("term_001", "ls -la")
            2. Start service: execute_command("term_001", "npm start", "service")
            3. Quick execution: execute_command("term_001", "pwd", follow=False)
            """
        )
        async def execute_command(
            terminal_id: Annotated[str, R("""Target terminal ID
            
            Description:
            - Must be an existing active terminal ID
            - Available terminal list can be obtained through get_terminals()
            - Terminal must be in available state
            
            How to obtain:
            1. First call get_terminals() to view available terminals
            2. Select terminals with active status
            3. Copy the corresponding terminal_id
            
            Examples:
            - "terminal_abc123" - Standard format
            - "term_001" - Short format
            """)],
            command: Annotated[str, R("""Shell command to execute
            
            Description:
            - Supports all standard shell commands
            - Can include parameters and options
            - Supports pipe and redirection operations
            - Pay attention to command security
            
            Common command examples:
            - "ls -la" - List detailed file information
            - "cd /path/to/dir" - Change directory
            - "npm install" - Install dependencies
            - "python script.py" - Run Python script
            - "git status" - Check Git status
            - "ps aux | grep node" - Find processes
            
            Important notes:
            - Avoid executing dangerous commands (like rm -rf /)
            - For long-running commands, recommend setting command_type to service
            """)],
            command_type: Annotated[str, O("""Command execution type
            
            Available values:
            - "normal": Regular command (default)
            - "service": Service command
            - "interactive": Interactive command
            
            Type description:
            - normal: General shell commands that will end after execution
            - service: Long-running services like web servers
            - interactive: Commands requiring user interaction input
            
            Selection recommendations:
            - File operations, view commands → normal
            - Start servers, monitor processes → service
            - Need password input, confirmation → interactive
            
            Examples:
            - "normal" - ls, cat, echo
            - "service" - npm start, python -m http.server
            - "interactive" - ssh, sudo, mysql
            """)] = "normal",
            follow: Annotated[bool, O("""Whether to continuously track output
            
            Description:
            - True: Continuously monitor command output until completion (default)
            - False: Only get current output snapshot and return immediately
            
            Use cases:
            - True: Suitable for commands that need to see the complete execution process
            - False: Suitable for quick status check commands
            
            Note:
            - For service type commands, recommend setting to True
            - For quick query commands, can set to False for better efficiency
            
            示例：
            - True - 监控构建过程、服务启动
            - False - 快速查看当前目录、文件内容
            """)] = True,
            timeout_seconds: Annotated[int, O("""Command execution timeout in seconds
            
            Description:
            - Optional timeout for command execution
            - When timeout is reached, SSE stream will be automatically terminated
            - Only applies when follow=True
            - Set to 0 or None to disable timeout (default)
            
            Use cases:
            - Prevent long-running commands from blocking indefinitely
            - Useful for file execution, build processes, or test runs
            - Automatically stop monitoring after specified time
            
            Examples:
            - 30 - Timeout after 30 seconds
            - 300 - Timeout after 5 minutes
            - 0 - No timeout (default)
            
            Note:
            - Timeout only stops the SSE stream, the actual command may continue running
            - Use kill_command to actually terminate the running process
            """)] = 0
        ) -> AsyncGenerator[str, None]:
            """执行命令"""
            try:
                command_obj = self.command_service.execute_command(
                    terminal_id, command, command_type
                )
                
                if not command_obj:
                    yield json.dumps({
                        "success": False,
                        "error": "命令执行失败",
                        "error_code": "EXECUTION_FAILED"
                    }, ensure_ascii=False)
                    return
                
                # 首先返回命令开始执行的信息
                yield json.dumps({
                    "type": "command_start",
                    "success": True,
                    "data": {
                        "command_id": command_obj.command_id,
                        "terminal_id": command_obj.terminal_id,
                        "command": command_obj.command,
                        "status": command_obj.status,
                        "command_type": command_obj.command_type,
                        "start_time": command_obj.start_time.isoformat() if command_obj.start_time else None
                    },
                    "message": "命令开始执行"
                }, ensure_ascii=False)
                
                # 流式监控命令执行状态和输出
                command_id = command_obj.command_id
                last_sequence = 0
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    # 检查超时
                    if timeout_seconds > 0 and follow:
                        elapsed_time = asyncio.get_event_loop().time() - start_time
                        if elapsed_time >= timeout_seconds:
                            yield json.dumps({
                                "type": "timeout",
                                "data": {
                                    "command_id": command_id,
                                    "timeout_seconds": timeout_seconds,
                                    "elapsed_seconds": round(elapsed_time, 2),
                                    "message": f"命令执行超时 ({timeout_seconds}秒)，SSE 流已断开"
                                }
                            }, ensure_ascii=False)
                            break
                    
                    # 获取命令状态
                    current_command = self.command_service.get_command(command_id)
                    if not current_command:
                        break
                    
                    # 获取新的输出（使用序号来避免重复）
                    from models.output import Output
                    new_outputs = Output.find_by_command_id_after_sequence(command_id, last_sequence, 50)
                    
                    for output in new_outputs:
                        yield json.dumps({
                            "type": "output",
                            "data": {
                                "content": output.content,
                                "output_type": output.output_type,
                                "timestamp": output.timestamp.isoformat(),
                                "sequence": output.sequence
                            }
                        }, ensure_ascii=False)
                        last_sequence = max(last_sequence, output.sequence)
                    
                    # 检查命令是否完成
                    if current_command.status in ['completed', 'failed', 'killed']:
                        yield json.dumps({
                            "type": "command_complete",
                            "data": {
                                "command_id": command_id,
                                "status": current_command.status,
                                "exit_code": current_command.exit_code,
                                "end_time": current_command.end_time.isoformat() if current_command.end_time else None,
                                "duration": current_command.get_duration()
                            }
                        }, ensure_ascii=False)
                        break
                    
                    # 如果不需要持续跟踪，只获取一次输出就退出
                    if not follow:
                        yield json.dumps({
                            "type": "snapshot_complete",
                            "data": {
                                "command_id": command_id,
                                "status": current_command.status,
                                "message": "输出快照获取完成"
                            }
                        }, ensure_ascii=False)
                        break
                    
                    # 更短的等待时间以提供更实时的输出
                    await asyncio.sleep(0.1)
                
            except ValueError as ve:
                error_msg = str(ve)
                if "TERMINAL_NOT_FOUND" in error_msg:
                    yield json.dumps({
                        "success": False,
                        "error": "终端不存在",
                        "error_code": "TERMINAL_NOT_FOUND"
                    }, ensure_ascii=False)
                elif "TERMINAL_INACTIVE" in error_msg:
                    yield json.dumps({
                        "success": False,
                        "error": "终端状态不可用",
                        "error_code": "TERMINAL_INACTIVE"
                    }, ensure_ascii=False)
                elif "TERMINAL_BUSY" in error_msg:
                    yield json.dumps({
                        "success": False,
                        "error": "终端正忙，有命令正在执行",
                        "error_code": "TERMINAL_BUSY"
                    }, ensure_ascii=False)
                else:
                    yield json.dumps({
                        "success": False,
                        "error": error_msg,
                        "error_code": "VALIDATION_ERROR"
                    }, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"执行命令异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        

        
        @self.streaming_tool(
            description="""Get real-time output of currently running command in terminal
            
            Features:
            - Get real-time output of running commands in the specified terminal
            - Support streaming output, real-time display of command execution results
            - Can only get output of currently running commands
            - Returns appropriate message if terminal has no running commands
            
            Output Content:
            - Command standard output (stdout)
            - Command error output (stderr)
            - Command execution status changes
            - Timestamp information
            
            Use Cases:
            - Monitor progress of long-running tasks
            - View server startup logs
            - Track build process output
            - Debug command execution issues
            
            Important Notes:
            - Can only get output of currently running commands
            - For historical command output, use get_terminal_commands
            - Cannot get output if command has already finished
            
            Examples:
            1. Monitor current command: get_terminal_current_output("term_001")
            2. Quick status check: get_terminal_current_output("term_001", False)
            3. Continuous service monitoring: get_terminal_current_output("term_001", True)
            """
        )
        async def get_terminal_current_output(
            terminal_id: Annotated[str, R("""Target terminal ID
            
            Description:
            - Must be an existing terminal ID
            - Terminal must have running commands
            - Can use get_terminals() to see which terminals have running commands
            
            How to obtain:
            1. Use get_terminals() to view terminal list
            2. Find terminals with "is_running" as true
            3. Use the corresponding terminal_id
            
            Examples:
            - "terminal_abc123" - Terminal with running commands
            - "term_001" - Terminal executing tasks
            
            Tips:
            - Will receive NO_RUNNING_COMMAND error if terminal has no running commands
            - Recommend checking terminal status before calling this function
            """)],
            follow: Annotated[bool, O("""Whether to continuously track output
            
            Description:
            - True: Continuously monitor until command completion (default)
            - False: Get current output snapshot and return immediately
            
            Selection recommendations:
            - True: Suitable for monitoring long-running tasks
            - False: Suitable for quick status checks
            
            Behavior differences:
            - True: Will continuously output new content until command ends
            - False: Only returns currently available output content
            
            Use cases:
            - True: Monitor builds, tests, service startups
            - False: Quick progress checks
            
            Examples:
            - True - Complete monitoring of npm install process
            - False - Quick check of current download progress
            """)] = True
        ) -> AsyncGenerator[str, None]:
            """获取终端当前运行命令的实时输出"""
            try:
                # 验证终端是否存在
                from models.terminal import Terminal
                terminal = Terminal.find_by_id(terminal_id)
                if not terminal:
                    yield json.dumps({
                        "success": False,
                        "error": "终端不存在",
                        "error_code": "TERMINAL_NOT_FOUND"
                    }, ensure_ascii=False)
                    return
                
                # 查找当前运行的命令
                from models.command import Command
                running_command = Command.find_running_by_terminal_id(terminal_id)
                
                if not running_command:
                    yield json.dumps({
                        "success": False,
                        "error": "该终端当前没有运行中的命令",
                        "error_code": "NO_RUNNING_COMMAND"
                    }, ensure_ascii=False)
                    return
                
                # 返回命令开始信息
                yield json.dumps({
                    "type": "command_start",
                    "success": True,
                    "data": {
                        "command_id": running_command.command_id,
                        "terminal_id": running_command.terminal_id,
                        "command": running_command.command,
                        "status": running_command.status,
                        "command_type": running_command.command_type,
                        "start_time": running_command.start_time.isoformat() if running_command.start_time else None
                    },
                    "message": "开始获取命令实时输出"
                }, ensure_ascii=False)
                
                # 流式监控命令执行状态和输出
                command_id = running_command.command_id
                last_sequence = 0
                
                while True:
                    # 获取命令状态
                    current_command = self.command_service.get_command(command_id)
                    if not current_command:
                        break
                    
                    # 获取新的输出（使用序号来避免重复）
                    from models.output import Output
                    new_outputs = Output.find_by_command_id_after_sequence(command_id, last_sequence, 50)
                    
                    for output in new_outputs:
                        yield json.dumps({
                            "type": "output",
                            "data": {
                                "content": output.content,
                                "output_type": output.output_type,
                                "timestamp": output.timestamp.isoformat(),
                                "sequence": output.sequence
                            }
                        }, ensure_ascii=False)
                        last_sequence = max(last_sequence, output.sequence)
                    
                    # 检查命令是否完成
                    if current_command.status in ['completed', 'failed', 'killed']:
                        yield json.dumps({
                            "type": "command_complete",
                            "data": {
                                "command_id": command_id,
                                "status": current_command.status,
                                "exit_code": current_command.exit_code,
                                "end_time": current_command.end_time.isoformat() if current_command.end_time else None,
                                "duration": current_command.get_duration()
                            }
                        }, ensure_ascii=False)
                        break
                    
                    # 如果不需要持续跟踪，只获取一次输出就退出
                    if not follow:
                        yield json.dumps({
                            "type": "snapshot_complete",
                            "message": "输出快照获取完成"
                        }, ensure_ascii=False)
                        break
                    
                    # 更短的等待时间以提供更实时的输出
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"获取终端当前输出异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="""Send input to a running interactive command
            
            Functionality:
            - Send user input to currently running interactive commands
            - Support commands that require user interaction like npx create-react-app
            - Only works with commands marked as 'interactive' type
            - Input is sent to the command's stdin stream
            
            Interactive Command Examples:
            - npx create-react-app my-app (requires project name, template selection)
            - npm init (requires package information)
            - git commit (requires commit message in editor)
            - ssh connections (requires password/confirmation)
            - sudo commands (requires password)
            
            Usage Process:
            1. Execute command with command_type='interactive'
            2. Monitor command output for prompts
            3. Use this tool to send appropriate responses
            4. Repeat as needed for multiple prompts
            
            Input Format:
            - Plain text input (newline will be automatically added)
            - For yes/no prompts: "y", "n", "yes", "no"
            - For selections: "1", "2", "react", "typescript", etc.
            - For text input: any string value
            
            Examples:
            1. Answer yes/no: send_input_to_command("cmd_123", "y")
            2. Select option: send_input_to_command("cmd_123", "2")
            3. Enter name: send_input_to_command("cmd_123", "my-project")
            4. Choose template: send_input_to_command("cmd_123", "typescript")
            """
        )
        async def send_input_to_command(
            terminal_id: Annotated[str, R("""Target terminal ID
            
            Description:
            - Must be an existing active terminal ID
            - Terminal must have a running interactive command
            - Use get_terminals() to find available terminal IDs
            
            Examples:
            - "terminal_abc123" - Standard terminal ID
            - "term_001" - Short terminal ID
            - "interactive_term" - Named terminal
            """)],
            command_id: Annotated[str, R("""Running command ID
            
            Description:
            - Must be a currently running interactive command
            - Use get_terminal_current_output() to find running command ID
            - Command must be in 'running' status
            - Command must be of type 'interactive'
            
            Examples:
            - "cmd_abc123" - Standard command ID
            - "command_001" - Sequential command ID
            """)],
            input_text: Annotated[str, R("""Input text to send
            
            Description:
            - Text input to send to the interactive command
            - Newline character will be automatically added
            - Should match what the command is expecting
            
            Common Input Examples:
            - "y" or "yes" - Confirm prompts
            - "n" or "no" - Decline prompts
            - "1", "2", "3" - Menu selections
            - "my-project" - Project names
            - "typescript" - Template selections
            - "" - Empty input (just press Enter)
            
            Special Cases:
            - For password prompts: enter the actual password
            - For editor prompts: enter the text content
            - For file paths: enter absolute or relative paths
            """)]
        ) -> AsyncGenerator[str, None]:
            """向运行中的交互式命令发送输入"""
            try:
                # 验证终端
                terminal = self.terminal_service.get_terminal(terminal_id)
                if not terminal:
                    yield json.dumps({
                        "success": False,
                        "error": "终端不存在",
                        "error_code": "TERMINAL_NOT_FOUND"
                    }, ensure_ascii=False)
                    return
                
                # 发送输入
                success = self.command_service.send_input_to_command(command_id, input_text)
                
                if success:
                    yield json.dumps({
                        "success": True,
                        "message": f"成功发送输入到命令: {input_text}",
                        "data": {
                            "terminal_id": terminal_id,
                            "command_id": command_id,
                            "input_text": input_text
                        }
                    }, ensure_ascii=False)
                else:
                    yield json.dumps({
                        "success": False,
                        "error": "发送输入失败，请检查命令状态和类型",
                        "error_code": "SEND_INPUT_FAILED"
                    }, ensure_ascii=False)
                    
            except Exception as e:
                self.logger.error(f"发送输入异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="""Force terminate the running command in the specified terminal
            
            Functionality:
            - Force stop the currently running command in the specified terminal
            - Send SIGTERM signal for graceful shutdown, then SIGKILL if it fails
            - Clean up related processes and resources
            - Mark command status as terminated
            
            Termination process:
            1. Check if terminal has running commands
            2. Send SIGTERM signal for graceful shutdown
            3. Wait for a period, then send SIGKILL if process still exists
            4. Clean up process resources and update status
            
            Use cases:
            - Stop runaway long-running tasks
            - Terminate stuck command processes
            - Stop unnecessary services
            - Clean up zombie processes
            
            Precautions:
            - Force termination may cause data loss
            - Recommend trying normal shutdown first (like Ctrl+C)
            - Confirm before executing on important tasks
            - Terminated commands cannot be recovered
            
            Examples:
            1. Stop stuck build: kill_command("term_001")
            2. Terminate runaway service: kill_command("terminal_abc123")
            3. Clean zombie process: kill_command("term_service")
            """
        )
        async def kill_command(
            terminal_id: Annotated[str, R("""Target terminal ID
            
            Description:
            - Must be an existing terminal ID
            - Terminal must have running commands
            - Can use get_terminals() to see which terminals have running commands
            
            How to obtain:
            1. Use get_terminals() to view terminal list
            2. Find terminals with "is_running" as true
            3. Confirm the command content to terminate
            4. Use the corresponding terminal_id
            
            Safety checks:
            - Confirm terminal ID is correct
            - Confirm terminating the target command
            - Consider the impact of command termination
            
            Examples:
            - "terminal_abc123" - Terminal with stuck commands
            - "term_build" - Terminal needing build stop
            - "term_server" - Terminal needing service stop
            
            Error cases:
            - TERMINAL_NOT_FOUND: Terminal does not exist
            - NO_RUNNING_COMMAND: No running commands
            - KILL_FAILED: Termination operation failed
            """)]
        ) -> AsyncGenerator[str, None]:
            """终止终端当前运行的命令"""
            try:
                # 验证终端是否存在
                from models.terminal import Terminal
                terminal = Terminal.find_by_id(terminal_id)
                if not terminal:
                    yield json.dumps({
                        "success": False,
                        "error": "终端不存在",
                        "error_code": "TERMINAL_NOT_FOUND"
                    }, ensure_ascii=False)
                    return
                
                # 查找当前运行的命令
                from models.command import Command
                running_command = Command.find_running_by_terminal_id(terminal_id)
                
                if not running_command:
                    yield json.dumps({
                        "success": False,
                        "error": "该终端当前没有运行中的命令",
                        "error_code": "NO_RUNNING_COMMAND"
                    }, ensure_ascii=False)
                    return
                
                # 终止命令
                success = self.command_service.kill_command(running_command.command_id)
                if success:
                    yield json.dumps({
                        "success": True,
                        "data": {
                            "terminal_id": terminal_id,
                            "command_id": running_command.command_id,
                            "command": running_command.command
                        },
                        "message": f"终端 {terminal_id} 的命令已被终止"
                    }, ensure_ascii=False)
                else:
                    yield json.dumps({
                        "success": False,
                        "error": "终止命令失败",
                        "error_code": "KILL_FAILED"
                    }, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"终止命令异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="""Get command history for the specified terminal
            
            Functionality:
            - Get all command history executed in the specified terminal
            - Support paginated queries to avoid returning too much data at once
            - Sort by time in descending order, with newest commands first
            - Include detailed execution information and status for commands
            
            Return information:
            - Command ID and content
            - Execution status (running/completed/failed/killed)
            - Start and end times
            - Execution duration
            - Exit code
            - Command type
            
            Use cases:
            - View terminal operation history
            - Analyze command execution status
            - Debugging and troubleshooting
            - Auditing and logging
            
            Pagination details:
            - Default 20 records per page
            - Page numbers start from 1
            - Can adjust records per page as needed
            
            Examples:
            1. View recent commands: get_terminal_commands("term_001")
            2. View page 2: get_terminal_commands("term_001", 2)
            3. 50 per page: get_terminal_commands("term_001", 1, 50)
            4. View more history: get_terminal_commands("term_001", 3, 10)
            """
        )
        async def get_terminal_commands(
            terminal_id: Annotated[str, R("""Target terminal ID
            
            Description:
            - Must be an existing terminal ID
            - Can be active or inactive terminals
            - Get available terminal ID list through get_terminals()
            
            How to obtain:
            1. Use get_terminals() to view all terminals
            2. Select the terminal to view history
            3. Copy the corresponding terminal_id
            
            Examples:
            - "terminal_abc123" - Standard terminal ID
            - "term_001" - Short format ID
            - "build_terminal" - Descriptive ID
            
            Notes:
            - History records may still exist even if terminal is deleted
            - Will return TERMINAL_NOT_FOUND error if terminal doesn't exist
            """)],
            page: Annotated[int, O("""Page number
            
            Description:
            - Specify the page number to retrieve, starting from 1
            - Used for paginated queries to avoid returning too much data at once
            - Default is page 1 (newest commands)
            
            Pagination logic:
            - Page 1: Newest command records
            - Page 2: Earlier command records
            - And so on...
            
            Usage recommendations:
            - Usually start viewing from page 1
            - Increase page number to view earlier history
            - Combine with limit parameter to control records per page
            
            Examples:
            - 1 - View newest commands
            - 2 - View second page history
            - 5 - View earlier command history
            """)] = 1,
            limit: Annotated[int, O("""Number of commands to display per page
            
            Description:
            - Control the number of command records returned per page
            - Default is 20 records
            - Recommended range: 5-100 records
            
            Selection recommendations:
            - 10-20 records: Suitable for quick browsing
            - 50-100 records: Suitable for detailed analysis
            - 5-10 records: Suitable for mobile devices or simple viewing
            
            Performance considerations:
            - Larger numbers take longer to return
            - Recommend setting based on actual needs
            - For large history records, recommend using smaller limit
            
            Examples:
            - 10 - Quick view of recent 10 commands
            - 50 - Detailed analysis of recent 50 commands
            - 100 - Comprehensive view of command history
            """)] = 20
        ) -> AsyncGenerator[str, None]:
            """获取终端命令历史"""
            try:
                result = self.command_service.get_terminal_commands(
                    terminal_id, page, limit
                )
                
                if result is None:
                    yield json.dumps({
                        "success": False,
                        "error": "终端不存在",
                        "error_code": "TERMINAL_NOT_FOUND"
                    }, ensure_ascii=False)
                    return
                
                # 首先返回分页信息
                yield json.dumps({
                    "type": "pagination_info",
                    "data": {
                        "page": result.get('page', page),
                        "limit": result.get('limit', limit),
                        "total": result.get('total', 0),
                        "total_pages": result.get('total_pages', 0)
                    }
                }, ensure_ascii=False)
                
                # 流式返回命令记录
                commands = result.get('commands', [])
                for i, command in enumerate(commands):
                    yield json.dumps({
                        "type": "command_record",
                        "data": {
                            "index": i,
                            "command_id": command.get('command_id'),
                            "command": command.get('command'),
                            "status": command.get('status'),
                            "start_time": command.get('start_time'),
                            "end_time": command.get('end_time'),
                            "exit_code": command.get('exit_code')
                        }
                    }, ensure_ascii=False)
                    
                    # 每5条记录暂停一下
                    if (i + 1) % 5 == 0:
                        await asyncio.sleep(0.01)
                
                # 发送完成信号
                yield json.dumps({
                    "type": "complete",
                    "message": f"获取到 {len(commands)} 条命令记录"
                }, ensure_ascii=False)
                
            except Exception as e:
                self.logger.error(f"获取终端命令历史异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        

        
        return True
    
    async def initialize(self) -> None:
        """初始化服务器"""
        try:
            # 设置日志
            setup_logging()
            self.logger.info("正在初始化 Terminal MCP Server...")
            
            # 使用 get_config_value 方法获取配置值，避免配置文件被清空
            storage_type = self.get_config_value('storage_type', 'file')
            mongodb_uri = self.get_config_value('mongodb_uri', 'mongodb://admin:password@localhost:27017/terminal_manager?authSource=admin')
            data_dir = self.get_config_value('data_dir', 'data')
            default_dir = self.get_config_value('default_dir', '/Users/lilei/project/learn/test_dir')
            
            self.logger.info(f"当前配置: storage_type={storage_type}, data_dir={data_dir}, default_dir={default_dir}")
            
            # 触发装饰器工具注册（在配置读取之后）
            _ = self.setup_tools
            # 触发服务器参数注册（在配置读取之后）
            _ = self.setup_server_params
            
            # 配置数据库
            db_config = {
                'storage_type': storage_type,
                'mongodb_uri': mongodb_uri,
                'data_dir': data_dir
            }
            
            # 从 mongodb_uri 中提取数据库名
            mongodb_uri = db_config['mongodb_uri']
            if '/' in mongodb_uri:
                db_name = mongodb_uri.split('/')[-1].split('?')[0]
                db_config['mongodb_db'] = db_name
            else:
                db_config['mongodb_db'] = 'terminal_manager'
            
            # 配置数据库
            db.configure(db_config)
            
            # 初始化数据库连接
            if not db.is_connected():
                self.logger.error("数据库连接失败")
                raise Exception("数据库连接失败")
            
            # 初始化服务
            self.terminal_service = TerminalService(default_dir)
            self.command_service = CommandService()
            
            self.logger.info("Terminal MCP Server 初始化完成")
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            raise
    
    def get_server_parameters(self) -> List[ServerParameter]:
        """获取服务器参数配置"""
        return super().get_server_parameters()


