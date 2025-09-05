import json
import logging
from typing import Any, Dict, AsyncGenerator
from typing_extensions import Annotated

from expert_service import ExpertService
from mcp_framework.core import EnhancedMCPServer
from mcp_framework.core.decorators import (
    Required as R,
    ServerParam, StringParam, BooleanParam, SelectParam
)

# 配置日志
logger = logging.getLogger("ExpertMCPServerAnnotated")


class ExpertMCPServerAnnotated(EnhancedMCPServer):
    """基于注解装饰器的专家MCP服务器"""

    def __init__(self):
        super().__init__(
            name="expert-server-annotated",
            version="1.0.0",
            description="AI专家服务器，基于注解装饰器系统提供完整的AI工具调用体系"
        )
        self.expert_service = None

    @property
    def setup_tools(self):
        """设置工具装饰器"""

        # @self.streaming_tool(
        #     description="**Development Planner** - Analyzes project status and creates development execution plans\n\n" +
        #                 "**Input Parameter**: question (string) - Development requirements or objectives\n\n" +
        #                 "**Planning Capabilities**:\n" +
        #                 "• Scan project structure and existing codebase\n" +
        #                 "• Identify tech stack and development patterns\n" +
        #                 "• Create detailed development plans\n" +
        #                 "• Plan task execution order and dependencies\n" +
        #                 "• Estimate development effort and timeline\n\n" +
        #                 "**Output**: Structured development plan containing:\n" +
        #                 "- Project analysis results\n" +
        #                 "- Priority-ordered task list\n" +
        #                 "- Specific execution instructions for each task\n" +
        #                 "- File paths and operation types\n" +
        #                 "- Inter-task dependencies\n\n" +
        #                 "**Usage**: query_expert_stream(question=\"Feature to implement or problem to solve\")"
        # )
        # async def query_expert_stream(
        #         question: Annotated[str, R(
        #             "Describe the development objective to be planned, for example:\n" +
        #             "• 'Implement user management system'\n" +
        #             "• 'Refactor existing code architecture'\n" +
        #             "• 'Add payment functionality module'\n" +
        #             "• 'Optimize system performance'\n" +
        #             "• 'Fix known bug list'"
        #         )]
        # ) -> AsyncGenerator[str, None]:
        #
        #     """Development Assistant - Professional development task support"""
        #     if not question:
        #         yield json.dumps({"error": "Question parameter cannot be empty"}, ensure_ascii=False)
        #         return
        #
        #     try:
        #         async for chunk in self.expert_service.ask_expert_stream(question):
        #             # Use base class standardized method to process chunk
        #             yield self._normalize_stream_chunk(chunk)
        #     except Exception as e:
        #         # Use base class error handling method
        #         yield await self._handle_stream_error("query_expert_stream", e)

        @self.streaming_tool(
            description="🤖 **Development Assistant** - Professional Development Task Executor\n\n" +
                        "## 🛠️ Core Capabilities:\n" +
                        "• **Code Development** - Implementation in various programming languages\n" +
                        "• **Issue Diagnosis** - Bug fixes, performance optimization, error troubleshooting\n" +
                        "• **Architecture Design** - System design, technology selection, best practices\n" +
                        "• **File Operations** - Code refactoring, batch modifications, project building\n" +
                        "• **Environment Setup** - Development environment configuration, deployment setup, toolchain management\n\n" +
                        "## 📤 Task Execution Results:\n" +
                        "• **Task Completed** - Successfully completed development task with complete solution\n" +
                        "• **Task Partially Completed** - Main functionality completed, with notes on incomplete parts and reasons\n" +
                        "• **Task Failed** - Unable to complete task, detailed failure reasons and suggestions provided\n" +
                        "• **Need More Information** - Task description insufficient, additional requirements needed\n" +
                        "• **Task Beyond Capability** - Task complexity exceeds current processing capability\n\n" +
                        "💡 **Working Method**: Automatically retrieves assigned development tasks, analyzes requirements, executes and provides execution status feedback."
        )
        async def query_expert_stream(
                question: Annotated[str, R(
                    "🎯 **Task Request Parameter**: Send task request to development assistant\n\n" +
                    "📋 **Standard Request Format**:\n" +
                    "• 'I have some development tasks, please help me complete them'\n" +
                    "• 'There are several development requirements to handle, please assist'\n" +
                    "• 'Please process the following development tasks'\n\n" +
                    "📝 **Manager Additional Instructions**:\n" +
                    "• 'Prioritize urgent tasks, focus on code quality'\n" +
                    "• 'Follow company coding standards, add detailed comments'\n" +
                    "• 'These tasks are complex, provide feedback if issues arise'\n" +
                    "• 'Use latest tech stack, ensure code maintainability'"
                )]
        ) -> AsyncGenerator[str, None]:
            """Development Assistant - Professional development task support"""
            if not question:
                yield json.dumps({"error": "Question parameter cannot be empty"}, ensure_ascii=False)
                return

            try:
                async for chunk in self.expert_service.ask_expert_stream(question):
                    # Use base class standardized method to process chunk
                    yield self._normalize_stream_chunk(chunk)
            except Exception as e:
                # Use base class error handling method
                yield await self._handle_stream_error("query_expert_stream", e)

        # @self.streaming_tool(
        #     description="🔍 **Task Inspector** - I am a professional task completion verification expert\n\n" +
        #                 "👋 **Who I Am**: A professional inspector responsible for checking and verifying task execution status\n\n" +
        #                 "🎯 **My Responsibilities**:\n" +
        #                 "• Check if tasks are completed according to requirements\n" +
        #                 "• Verify code quality and best practices\n" +
        #                 "• Evaluate whether work results meet standards\n" +
        #                 "• Provide professional improvement suggestions\n\n" +
        #                 "🔧 **My Capabilities**:\n" +
        #                 "• Automatically retrieve current task details and requirements\n" +
        #                 "• Review all work submitted by executors\n" +
        #                 "• Conduct comprehensive quality assessment and code review\n" +
        #                 "• Provide clear completion status judgment (Completed/Incomplete)\n\n" +
        #                 "💬 **How to Communicate with Me**: Simply tell me what you want me to inspect, and I'll handle all technical details automatically"
        # )
        # async def query_expert_stream(
        #         question: Annotated[str, R(
        #             "💬 **Your Question**: Tell me what you want me to inspect\n\n" +
        #             "✅ **Common Question Examples**:\n" +
        #             "• 'Please check if the current task has been completed'\n" +
        #             "• 'Help me verify the executor's work quality'\n" +
        #             "• 'Check the task completion status'\n" +
        #             "• 'Evaluate the current work results'"
        #         )]
        # ) -> AsyncGenerator[str, None]:
        #     """Development Assistant - Professional development task support"""
        #     if not question:
        #         yield json.dumps({"error": "Question parameter cannot be empty"}, ensure_ascii=False)
        #         return
        #
        #     try:
        #         async for chunk in self.expert_service.ask_expert_stream(question):
        #             # Use base class standardized method to process chunk
        #             yield self._normalize_stream_chunk(chunk)
        #     except Exception as e:
        #         # Use base class error handling method
        #         yield await self._handle_stream_error("query_expert_stream", e)

        @self.resource(uri="config://expert", name="Expert Config", description="专家服务器配置信息")
        async def expert_config_resource(uri: str) -> Dict[str, Any]:
            """获取专家服务器配置信息"""
            config = self.server_config
            mcp_servers_config = config.get("mcp_servers", "")
            mcp_servers = self._parse_mcp_servers_config(mcp_servers_config)

            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps({
                        "config_info": {
                            "api_key": "***" if config.get("api_key") else "",
                            "base_url": config.get("base_url", "https://api.openai.com/v1"),
                            "model_name": config.get("model_name", "gpt-3.5-turbo"),
                            "system_prompt": config.get("system_prompt", ""),
                            "mcp_servers": mcp_servers
                        }
                    }, ensure_ascii=False)
                }]
            }
        
        return True

    @property
    def setup_server_params(self):
        """设置服务器参数装饰器"""
        
        @self.decorators.server_param("api_key")
        async def api_key_param(
            param: Annotated[str, ServerParam(
                display_name="API密钥",
                description="OpenAI API密钥",
                param_type="password",
                required=True,
                placeholder="sk-..."
            )]
        ):
            """API密钥参数"""
            pass
        
        @self.decorators.server_param("base_url")
        async def base_url_param(
            param: Annotated[str, StringParam(
                display_name="API基础URL",
                description="API基础URL",
                required=False,
                default_value="https://api.moonshot.cn/v1",
                placeholder="https://api.openai.com/v1"
            )]
        ):
            """API基础URL参数"""
            pass
        
        @self.decorators.server_param("model_name")
        async def model_name_param(
            param: Annotated[str, SelectParam(
                display_name="模型名称",
                description="选择要使用的AI模型",
                options=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview", "gpt-4o", "kimi-k2-turbo-preview"],
                default_value="kimi-k2-turbo-preview",
                required=False
            )]
        ):
            """模型名称参数"""
            pass
        
        @self.decorators.server_param("system_prompt")
        async def system_prompt_param(
            param: Annotated[str, StringParam(
                display_name="系统提示词",
                description="系统提示词",
                required=False,
                default_value="你是一个专业的AI助手，能够通过工具帮用查询当前目录下的内容。",
                placeholder="输入系统提示词..."
            )]
        ):
            """系统提示词参数"""
            pass
        
        @self.decorators.server_param("mcp_servers")
        async def mcp_servers_param(
            param: Annotated[str, StringParam(
                display_name="MCP服务器配置",
                description="MCP服务器配置（格式：name1:url1,name2:url2）",
                required=False,
                default_value="file-reader: http://localhost:8001/mcp",
                placeholder="terminal-server:http://localhost:8001,file-server:http://localhost:8002"
            )]
        ):
            """MCP服务器配置参数"""
            pass
        
        @self.decorators.server_param("mongodb_url")
        async def mongodb_url_param(
            param: Annotated[str, StringParam(
                display_name="MongoDB连接URL",
                description="MongoDB数据库连接URL，如果不配置则使用文件存储",
                required=False,
                default_value="",
                placeholder="mongodb://localhost:27017/chat_history"
            )]
        ):
            """MongoDB连接URL参数"""
            pass
        
        @self.decorators.server_param("history_limit")
        async def history_limit_param(
            param: Annotated[str, StringParam(
                display_name="历史记录查询条数",
                description="每次对话时查询的历史记录条数",
                required=False,
                default_value="10",
                placeholder="10"
            )]
        ):
            """历史记录查询条数参数"""
            pass
        
        @self.decorators.server_param("enable_history")
        async def enable_history_param(
            param: Annotated[bool, BooleanParam(
                display_name="启用聊天记录",
                description="是否启用聊天记录功能",
                required=False,
                default_value=False,
            )]
        ):
            """启用聊天记录参数"""
            pass
        
        @self.decorators.server_param("role")
        async def role_param(
            param: Annotated[str, StringParam(
                display_name="角色设定",
                description="AI助手的角色设定",
                required=False,
                default_value="",
                placeholder="输入角色设定..."
            )]
        ):
            """角色设定参数"""
            pass
        
        return True

    async def initialize(self) -> None:
        """初始化服务器"""
        # 使用框架的通用配置处理流程
        config_values = self._setup_decorators_and_log_config(
            required_keys=["api_key"],
            config_defaults={
                "api_key": None,
                "base_url": "https://api.openai.com/v1",
                "model_name": "gpt-3.5-turbo",
                "system_prompt": "你是一个专业的AI助手，能够提供准确、详细和有用的回答。",
                "mcp_servers": ""
            }
        )

        # 使用工厂方法创建并初始化专家服务
        self.expert_service = await ExpertService.from_config(config_values)

        # 使用框架的工具日志记录功能
        self._log_tools_info()

        logger.info("✅ Expert MCP Server (Annotated) initialized successfully")

    async def shutdown(self) -> None:
        """关闭服务器"""
        if self._initialized and self.expert_service:
            # 正确关闭专家服务
            try:
                await self.expert_service.shutdown()
            except Exception as e:
                logger.warning(f"关闭专家服务时出现警告: {e}")
            finally:
                self.expert_service = None
                logger.info("🛑 Expert Service已清理")
        
        # 调用父类的shutdown方法
        await super().shutdown()


