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
        
        # 终端管理工具
        @self.streaming_tool(
            description="创建新的终端实例"
        )
        async def create_terminal(
            working_directory: Annotated[str, O("工作目录路径")] = None
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
                
                yield json.dumps({
                    "success": True,
                    "data": {
                        "terminal_id": terminal.terminal_id,
                        "working_directory": terminal.working_directory,
                        "status": terminal.status,
                        "created_at": terminal.created_at.isoformat()
                    },
                    "message": "终端创建成功"
                }, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"创建终端异常: {e}")
                yield json.dumps({
                    "success": False,
                    "error": str(e),
                    "error_code": "INTERNAL_ERROR"
                }, ensure_ascii=False)
        
        @self.streaming_tool(
            description="获取所有终端列表"
        )
        async def get_terminals(
            status_filter: Annotated[str, O("状态过滤器 (active/inactive/all)")] = "all"
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
            description="删除指定的终端"
        )
        async def delete_terminal(
            terminal_id: Annotated[str, R("终端ID")]
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
            description="在指定终端中执行命令"
        )
        async def execute_command(
            terminal_id: Annotated[str, R("终端ID")],
            command: Annotated[str, R("要执行的命令")],
            command_type: Annotated[str, O("命令类型 (normal/service/interactive)")] = "normal",
            follow: Annotated[bool, O("是否持续跟踪输出")] = True
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
            description="通过终端ID获取当前运行命令的实时输出"
        )
        async def get_terminal_current_output(
            terminal_id: Annotated[str, R("终端ID")],
            follow: Annotated[bool, O("是否持续跟踪输出")] = True
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
            description="终止指定终端当前正在执行的命令"
        )
        async def kill_command(
            terminal_id: Annotated[str, R("终端ID")]
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
            description="获取终端命令历史"
        )
        async def get_terminal_commands(
            terminal_id: Annotated[str, R("终端ID")],
            page: Annotated[int, O("页码")] = 1,
            limit: Annotated[int, O("每页数量")] = 10
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
        
        @self.streaming_tool(
            description="获取正在运行的命令列表"
        )
        async def get_running_commands(
            terminal_id: Annotated[str, O("终端ID (可选，不指定则获取所有)")] = None
        ) -> AsyncGenerator[str, None]:
            """获取正在运行的命令"""
            try:
                commands = self.command_service.get_running_commands(terminal_id)
                
                # 首先返回统计信息
                yield json.dumps({
                    "type": "summary",
                    "data": {
                        "count": len(commands),
                        "terminal_filter": terminal_id
                    }
                }, ensure_ascii=False)
                
                # 流式返回每个运行中的命令
                for i, command in enumerate(commands):
                    yield json.dumps({
                        "type": "running_command",
                        "data": {
                            "index": i,
                            "command_id": command.command_id,
                            "terminal_id": command.terminal_id,
                            "command": command.command,
                            "status": command.status,
                            "command_type": command.command_type,
                            "start_time": command.start_time.isoformat() if command.start_time else None,
                            "pid": command.pid
                        }
                    }, ensure_ascii=False)
                    
                    # 每3个命令暂停一下
                    if (i + 1) % 3 == 0:
                        await asyncio.sleep(0.01)
                
                # 发送完成信号
                yield json.dumps({
                    "type": "complete",
                    "message": f"获取到 {len(commands)} 个正在运行的命令"
                }, ensure_ascii=False)
                
            except Exception as e:
                self.logger.error(f"获取运行命令列表异常: {e}")
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
            
            # 使用框架的通用配置处理流程
            config_values = self._setup_decorators_and_log_config(
                required_keys=[],
                config_defaults={
                    'storage_type': 'file',
                    'mongodb_uri': 'mongodb://admin:password@localhost:27017/terminal_manager?authSource=admin',
                    'data_dir': 'data',
                    'max_terminals': 10,
                    'enable_cleanup': True,
                    'cleanup_threshold_minutes': 20
                }
            )
            
            # 配置数据库
            db_config = {
                'storage_type': config_values.get('storage_type', 'file'),
                'mongodb_uri': config_values.get('mongodb_uri', 'mongodb://admin:password@localhost:27017/terminal_manager?authSource=admin'),
                'data_dir': config_values.get('data_dir', 'data')
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
            self.terminal_service = TerminalService()
            self.command_service = CommandService()
            
            # 使用框架的工具日志记录功能
            self._log_tools_info()
            
            self.logger.info("Terminal MCP Server 初始化完成")
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            raise
    
    def get_server_parameters(self) -> List[ServerParameter]:
        """获取服务器参数配置"""
        return super().get_server_parameters()


