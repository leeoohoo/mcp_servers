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
    
    def get_config_value(self, key: str, default=None):
        """获取配置值的统一方法
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        # 调用父类的 get_config_value 方法，而不是直接访问 server_config
        return super().get_config_value(key, default)
    


    @property
    def setup_tools(self):
        """设置工具装饰器"""
        
        # 获取当前工具描述和参数描述
        description = self.get_config_value('tool_description', 
            "🤖 **Development Assistant** - Professional Development Task Executor\n\n" +
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
        
        parameter_description = self.get_config_value('parameter_description',
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
        )

        @self.streaming_tool(description=description)
        async def query_expert_stream(
                question: Annotated[str, R(parameter_description)]
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

        @self.resource(uri="config://expert", name="Expert Config", description="专家服务器配置信息")
        async def expert_config_resource(uri: str) -> Dict[str, Any]:
            """获取专家服务器配置信息"""
            mcp_servers_config = self.get_config_value("mcp_servers", "")
            mcp_servers = self._parse_mcp_servers_config(mcp_servers_config)
            
            stdio_mcp_servers_config = self.get_config_value("stdio_mcp_servers", "")
            stdio_mcp_servers = self._parse_mcp_servers_config(stdio_mcp_servers_config)

            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps({
                        "config_info": {
                            "api_key": "***" if self.get_config_value("api_key") else "",
                            "base_url": self.get_config_value("base_url", "https://api.openai.com/v1"),
                            "model_name": self.get_config_value("model_name", "gpt-3.5-turbo"),
                            "system_prompt": self.get_config_value("system_prompt", ""),
                            "mcp_servers": mcp_servers,
                            "stdio_mcp_servers": stdio_mcp_servers
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
            param: Annotated[str, StringParam(
                display_name="模型名称",
                description="输入要使用的AI模型名称",
                default_value="kimi-k2-turbo-preview",
                required=False,
                placeholder="例如: gpt-3.5-turbo, gpt-4, kimi-k2-turbo-preview"
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
        
        @self.decorators.server_param("stdio_mcp_servers")
        async def stdio_mcp_servers_param(
            param: Annotated[str, StringParam(
                display_name="Stdio协议MCP服务器配置",
                description="Stdio协议MCP服务器配置（格式：name1:script_path1--alias,name2:script_path2--alias）",
                required=False,
                default_value="",
                placeholder="file-manager:file_manager.py--alias,task-runner:task_runner.js--alias"
            )]
        ):
            """Stdio协议MCP服务器配置参数"""
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
        
        @self.decorators.server_param("tool_description")
        async def tool_description_param(
            param: Annotated[str, StringParam(
                display_name="工具描述",
                description="自定义工具的描述信息",
                default_value="🤖 **Development Assistant** - Professional Development Task Executor",
                required=False
            )]
        ):
            """工具描述参数"""
            pass
        
        @self.decorators.server_param("parameter_description")
        async def parameter_description_param(
            param: Annotated[str, StringParam(
                display_name="参数描述",
                description="自定义工具参数的描述信息",
                default_value="🎯 **Task Request Parameter**: Send task request to development assistant",
                required=False
            )]
        ):
            """参数描述参数"""
            pass
            
        @self.decorators.server_param("summary_interval")
        async def summary_interval_param(
            param: Annotated[int, ServerParam(
                display_name="工具调用总结间隔",
                description="每执行多少轮工具调用后进行一次总结",
                param_type="integer",
                default_value=5,
                required=False
            )]
        ):
            """工具调用总结间隔参数"""
            pass
            
        @self.decorators.server_param("max_rounds")
        async def max_rounds_param(
            param: Annotated[int, ServerParam(
                display_name="最大工具调用轮数",
                description="AI对话中允许的最大工具调用轮数",
                param_type="integer",
                default_value=25,
                required=False
            )]
        ):
            """最大工具调用轮数参数"""
            pass
            
        @self.decorators.server_param("summary_instruction")
        async def summary_instruction_param(
            param: Annotated[str, StringParam(
                display_name="总结指令内容",
                description="AI总结器使用的系统指令内容",
                required=False,
                default_value="You are a professional conversation analysis and requirement prediction expert. Please intelligently analyze and preserve data segments from tool call results that are crucial for subsequent operations based on the user's original requirements.",
                placeholder="输入总结指令内容..."
            )]
        ):
            """总结指令内容参数"""
            pass
            
        @self.decorators.server_param("summary_request")
        async def summary_request_param(
            param: Annotated[str, StringParam(
                display_name="总结请求内容",
                description="AI总结器使用的用户请求内容",
                required=False,
                default_value="Please intelligently analyze and generate a precise data retention report based on the user's original requirements.",
                placeholder="输入总结请求内容..."
            )]
        ):
            """总结请求内容参数"""
            pass
            
        @self.decorators.server_param("summary_length_threshold")
        async def summary_length_threshold_param(
            param: Annotated[int, ServerParam(
                display_name="总结长度阈值",
                description="触发总结的消息总长度阈值（字符数）",
                param_type="integer",
                default_value=30000,
                required=False
            )]
        ):
            """总结长度阈值参数"""
            pass

        
        return True

    async def initialize(self) -> None:
        """初始化服务器"""
        import os
        
        # 检查是否为测试模式
        testing_mode = os.environ.get("TESTING_MODE", "false").lower() == "true"
        
        if testing_mode:
            logger.info("🧪 测试模式已启用，跳过 api_key 验证")

        # 触发装饰器工具注册
        _ = self.setup_tools
        # 触发服务器参数注册
        _ = self.setup_server_params

        # 准备配置值字典，使用 get_config_value 方法获取配置
        config_values = {
            "api_key": self.get_config_value("api_key", "test-api-key" if testing_mode else None),
            "base_url": self.get_config_value("base_url", "https://api.openai.com/v1"),
            "model_name": self.get_config_value("model_name", "gpt-3.5-turbo"),
            "system_prompt": self.get_config_value("system_prompt", "你是一个专业的AI助手，能够提供准确、详细和有用的回答。"),
            "mcp_servers": self.get_config_value("mcp_servers", ""),
            "stdio_mcp_servers": self.get_config_value("stdio_mcp_servers", ""),
            "mongodb_url": self.get_config_value("mongodb_url", ""),
            "history_limit": self.get_config_value("history_limit", 10),
            "enable_history": self.get_config_value("enable_history", True),
            "role": self.get_config_value("role", ""),
            "tool_description": self.get_config_value("tool_description", "🤖 **Development Assistant** - Professional Development Task Executor"),
            "parameter_description": self.get_config_value("parameter_description", "🎯 **Task Request Parameter**: Send task request to development assistant"),
            "summary_interval": self.get_config_value("summary_interval", 5),
            "max_rounds": self.get_config_value("max_rounds", 25),
            "summary_instruction": self.get_config_value("summary_instruction", "You are a professional conversation analysis and requirement prediction expert. Please intelligently analyze and preserve data segments from tool call results that are crucial for subsequent operations based on the user's original requirements."),
            "summary_request": self.get_config_value("summary_request", "Please intelligently analyze and generate a precise data retention report based on the user's original requirements."),
            "summary_length_threshold": self.get_config_value("summary_length_threshold", 30000)
        }

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


