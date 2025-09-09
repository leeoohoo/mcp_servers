#!/usr/bin/env python3
"""
任务管理器 MCP 服务器（注解版本）
基于 EnhancedMCPServer 和装饰器系统的任务管理服务器

主要功能:
1. create_tasks - 创建单个或批量任务（流式输出）
2. get_next_executable_task - 获取下一个可执行任务（流式输出）
3. complete_task - 标记任务为已完成（流式输出）
4. get_task_stats - 获取任务统计信息（流式输出）
5. query_tasks - 根据条件查询任务（流式输出）
6. get_current_executing_task - 获取当前正在执行的任务（流式输出）

架构优化:
- 分离业务逻辑到 TaskManagerService
- 实现按需加载，避免内存过载
- 使用 LRU 缓存机制
- 支持配置参数动态调整
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from typing_extensions import Annotated

# 导入任务管理服务
from task_manager_service import TaskManagerService


from mcp_framework.core import EnhancedMCPServer

# 导入装饰器
from mcp_framework.core.decorators import (
    Required as R,
    Optional as O,

)

# 配置日志
logger = logging.getLogger("task_manager_server")


class TaskManagerServer(EnhancedMCPServer):
    """基于注解装饰器的任务管理器MCP服务器"""

    def __init__(self):
        super().__init__(
            name="task-manager-server",
            version="2.0.0",
            description="任务管理器MCP服务器，基于注解装饰器系统提供流式任务管理功能"
        )
        # 在构造函数中就初始化服务，使用默认值
        self.task_manager_service = TaskManagerService()
        logger.info("TaskManagerServer initialized")

    async def initialize(self) -> None:
        """初始化服务器（实现基类抽象方法）"""
        
        # 调用基类的初始化（如果存在）
        if hasattr(super(), 'initialize'):
            await super().initialize()
        
        # 获取配置参数并重新初始化服务（如果需要）
        try:
            data_dir = self.get_config_value("data_dir")
            if data_dir and data_dir.strip():
                # 如果配置了数据目录，重新初始化服务
                self.task_manager_service = TaskManagerService(data_dir.strip())
                logger.info(f"Using configured data directory: {data_dir}")
            else:
                # 使用默认的数据目录
                logger.info("Using default data directory: task_data")
        except Exception as e:
            logger.warning(f"Failed to get config, using default: {e}")
        
        # 确保服务已初始化
        if self.task_manager_service is None:
            self.task_manager_service = TaskManagerService()
            logger.info("Initialized task manager service with defaults")
    
    @property
    def setup_server_params(self):
        """设置服务器参数"""
        
        @self.decorators.server_param
        def data_dir(
            self,
            value: Annotated[str, R("Data directory for storing task files")]
        ) -> str:
            """Data directory for task storage
            
            Specifies the directory where task data files will be stored.
            Each conversation-request pair will have its own JSON file.
            
            Default: './task_data'
            """
            return value
        

        @self.decorators.server_param
        def auto_save(
            self,
            value: Annotated[bool, R("Whether to automatically save tasks to disk")]
        ) -> bool:
            """Auto-save tasks to disk
            
            When enabled, tasks are automatically saved to disk after creation
            or status updates. Disable for better performance if manual saves
            are preferred.
            
            Default: True
            """
            return value
    
    async def on_config_updated(self, config_key: str, new_value: Any) -> None:
        """配置更新回调方法"""
        if config_key == "data_dir":
            try:
                # 使用新的动态更新方法
                if self.task_manager_service:
                    data_dir = str(new_value).strip() if new_value else ""
                    result = self.task_manager_service.update_data_dir(data_dir)
                    
                    if result.get("success"):
                        logger.info(f"Config updated successfully: {result['message']}")
                    else:
                        logger.error(f"Failed to update data directory: {result.get('error', 'Unknown error')}")
                else:
                    # 如果服务未初始化，创建新服务
                    data_dir = str(new_value).strip() if new_value else "task_data"
                    self.task_manager_service = TaskManagerService(data_dir)
                    logger.info(f"Created new task manager service with data dir: {data_dir}")
            except Exception as e:
                logger.error(f"Error updating config {config_key}: {e}")
        elif config_key == "auto_save":
            try:
                if self.task_manager_service and hasattr(self.task_manager_service, 'set_auto_save'):
                    self.task_manager_service.set_auto_save(bool(new_value))
                    logger.info(f"Auto save updated to: {new_value}")
            except Exception as e:
                logger.error(f"Error updating auto save: {e}")
    
    def _normalize_stream_chunk(self, chunk: str) -> str:
        """标准化流式输出块"""
        if not chunk:
            return ""
        
        # 确保以换行符结尾
        if not chunk.endswith('\n'):
            chunk += '\n'
        
        return chunk

    @property
    def setup_tools(self):
        """设置工具装饰器"""

        @self.streaming_tool(description="📝 **Task Creator** - Creates single or batch tasks with comprehensive validation.\n" +
                         "\n✨ **Features**: Batch task creation, Field validation, Progress tracking, File-based persistence, Direct file overwrite\n" +
                         "🎯 **Use Cases**: Project planning, Task breakdown, Workflow management, Team coordination\n" +
                         "\n📋 **Required Parameters**:\n" +
                         "• tasks (list): List of task objects, each containing the required fields below\n" +
                         "• session_id (string): Session ID for task grouping and isolation (if file exists, it will be overwritten)\n" +
                         "\n📝 **Task Object Fields** (each task object must contain):\n" +
                         "• task_title (string): Task title, concise description of the task\n" +
                         "• target_file (string): Target file path or name\n" +
                         "• operation (string): Operation type (e.g., create, update, delete, analyze)\n" +
                         "• specific_operations (string): Detailed operation description\n" +
                         "• related (string): Related information or context\n" +
                         "• dependencies (string): Dependent task IDs, comma-separated, empty string if no dependencies\n" +
                         "• task_id (string, optional): Custom task ID, if not provided a UUID will be generated\n" +
                         "\n📄 **Request Example**:\n" +
                         "{\n" +
                         "  \"tasks\": [\n" +
                         "    {\n" +
                         "      \"task_title\": \"Create User Model\",\n" +
                         "      \"target_file\": \"models/user.py\",\n" +
                         "      \"operation\": \"create\",\n" +
                         "      \"specific_operations\": \"Define User class with id, name, email fields\",\n" +
                         "      \"related\": \"Core model for user management system\",\n" +
                         "      \"dependencies\": \"\"\n" +
                         "    },\n" +
                         "    {\n" +
                         "      \"task_title\": \"Create User Service\",\n" +
                         "      \"target_file\": \"services/user_service.py\",\n" +
                         "      \"operation\": \"create\",\n" +
                         "      \"specific_operations\": \"Implement user CRUD operations\",\n" +
                         "      \"related\": \"Depends on user model\",\n" +
                         "      \"dependencies\": \"task_id_1\"\n" +
                         "    },\n" +
                         "    {\n" +
                         "      \"task_id\": \"custom_task_id_2\",\n" +
                         "      \"task_title\": \"Create User Model\",\n" +
                         "      \"target_file\": \"models/user.py\",\n" +
                         "      \"operation\": \"update\",\n" +
                         "      \"specific_operations\": \"Add address and phone fields to User class\",\n" +
                         "      \"related\": \"Enhanced user model with contact information\",\n" +
                         "      \"dependencies\": \"\"\n" +
                         "    }\n" +
                         "  ],\n" +
                         "  \"session_id\": \"session_123\"\n" +
                         "}\n" +
                         "\n⚠️ **Output Format**: Streams creation progress and saves to session_id.json (overwrites if exists)\n" +
                         "💡 Perfect for organizing complex projects with dependent tasks and clear tracking.", role="planner")
        async def create_tasks(
                tasks: Annotated[List[Dict[str, Any]], R("List of tasks to create, each containing required fields")],
                session_id: Annotated[str, R("Session ID for task grouping and isolation (if file exists, it will be overwritten)")]
        ) -> AsyncGenerator[str, None]:
            """Creates single or batch tasks with validation and progress tracking, overwrites existing file if session_id exists"""
            async for chunk in self.task_manager_service.create_tasks_stream(tasks, session_id):
                yield self._normalize_stream_chunk(chunk)
        
        @self.streaming_tool(description="▶️ **Task Executor** - Returns current in-progress task or finds next executable task.\n" +
                         "✨ Features: In-progress task tracking, Dependency resolution, Status checking, Priority ordering\n" +
                         "🎯 Use Cases: Workflow execution, Task scheduling, Dependency management, Progress tracking\n" +
                         "📋 **Required Parameters**: session_id (parameter is mandatory)\n" +
                         "⚠️ **Output Format**: Streams current in-progress task or next executable task details\n" +
                         "💡 If a task is already in progress, returns that task. Otherwise finds next executable task.", role="development")
        async def get_next_executable_task(
                session_id: Annotated[str, R("Session ID for task grouping and isolation")]
        ) -> AsyncGenerator[str, None]:
            """Finds the next executable task based on dependencies and status"""
            async for chunk in self.task_manager_service.get_next_executable_task_stream(session_id):
                yield self._normalize_stream_chunk(chunk)
        
        @self.streaming_tool(description="✅ **Task Completer** - Marks tasks as completed with validation and persistence.\n" +
                         "✨ Features: Task validation, Status updates, File persistence, Progress tracking\n" +
                         "🎯 Use Cases: Task completion, Workflow progression, Status management, Record keeping\n" +
                         "📋 **Required Parameters**: task_id (parameter is mandatory)\n" +
                         "⚠️ **Output Format**: Streams completion status and saves to corresponding JSON file\n" +
                         "💡 Automatically updates task status and maintains data consistency.", role="inspector")
        async def complete_task(
                task_id: Annotated[str, R("Task ID to mark as completed")]
        ) -> AsyncGenerator[str, None]:
            """Marks a task as completed with validation and persistence"""
            async for chunk in self.task_manager_service.complete_task_stream(task_id):
                yield self._normalize_stream_chunk(chunk)
        
        @self.streaming_tool(description="📊 **Task Statistics** - Provides comprehensive task analytics and metrics.\n" +
                         "✨ Features: Status breakdown, Progress tracking, Session filtering, Real-time stats\n" +
                         "🎯 Use Cases: Project monitoring, Progress reporting, Performance analysis, Team oversight\n" +
                         "📋 **Required Parameters**: session_id (parameter is mandatory)\n" +
                         "⚠️ **Output Format**: Streams detailed statistics and task breakdowns\n" +
                         "💡 Perfect for monitoring project progress and team productivity.", role="manager")
        async def get_task_stats(
                session_id: Annotated[str, R("Session ID for task grouping and isolation")]
        ) -> AsyncGenerator[str, None]:
            """Provides comprehensive task analytics and metrics"""
            async for chunk in self.task_manager_service.get_task_stats_stream(session_id):
                yield self._normalize_stream_chunk(chunk)
        

        @self.streaming_tool(description="🔍 **Current Task Inspector** - Retrieves the currently executing task for inspection.\n" +
                         "✨ Features: Current task tracking, Detailed task information, Execution status monitoring, Execution process viewing\n" +
                         "🎯 Use Cases: Task inspection, Progress monitoring, Current status checking, Quality assurance\n" +
                         "📋 **Required Parameters**: session_id (parameter is mandatory)\n" +
                         "⚠️ **Output Format**: Streams current executing task details with comprehensive information including execution process\n" +
                         "💡 Perfect for inspectors to check what task is currently being executed and view saved execution process.", role="inspector")
        async def get_current_executing_task(
                session_id: Annotated[str, R("Session ID for task grouping and isolation")]
        ) -> AsyncGenerator[str, None]:
            """Retrieves the currently executing task for inspection"""
            async for chunk in self.task_manager_service.get_current_executing_task_stream(session_id):
                yield self._normalize_stream_chunk(chunk)
        
        @self.streaming_tool(description="💾 **Task Execution Recorder** - Saves task execution process for development tracking.\n" +
                         "✨ Features: Execution process storage, Task validation, File-based persistence, Progress tracking\n" +
                         "🎯 Use Cases: Development documentation, Process recording, Task completion tracking, Quality assurance\n" +
                         "📋 **Required Parameters**: task_id, execution_process (BOTH parameters are mandatory)\n" +
                         "⚠️ **Output Format**: Streams save confirmation and creates individual execution file per task\n" +
                         "💡 Perfect for developers to record their execution process after completing tasks.", role="development")
        async def save_task_execution(
                task_id: Annotated[str, R("Task ID to save execution process for")],
                execution_process: Annotated[str, R("Detailed execution process description")]
        ) -> AsyncGenerator[str, None]:
            """Saves task execution process for development tracking"""
            async for chunk in self.task_manager_service.save_task_execution_stream(task_id, execution_process):
                yield self._normalize_stream_chunk(chunk)


def main():
    """主函数"""
    try:
        # 导入 MCP 框架启动器
        from mcp_framework import run_server_main
        
        # 创建服务器实例
        server = TaskManagerServer()
        
        # 使用 MCP 框架启动器启动服务器
        run_server_main(
            server_instance=server,
            server_name="Task Manager MCP Server",
            default_port=8004,
            default_host="localhost",
            required_dependencies=[]
        )
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        import sys
        sys.exit(1)


# 启动服务器
if __name__ == "__main__":
    main()