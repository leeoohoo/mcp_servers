import json
import logging
import uuid
from typing import Dict, List, AsyncGenerator

# 使用绝对导入，但不包含包名前缀
from ai_client import AiClient
from ai_request_handler import AiRequestHandler
from chat_history_manager import ChatHistoryManager
from mcp_tool_execute import McpToolExecute
from mcp_framework.core import parse_mcp_servers_config

# 配置日志
logger = logging.getLogger("ExpertService")


class ExpertService:
    """专家服务类"""

    @classmethod
    async def from_config(cls, config_values: Dict[str, any]) -> 'ExpertService':
        """从配置字典创建并初始化 ExpertService 实例"""
        # 解析MCP服务器配置
        mcp_servers = parse_mcp_servers_config(config_values["mcp_servers"])
        if mcp_servers:
            logger.info(f"🔧 解析到的MCP服务器: {mcp_servers}")
        
        # 创建服务实例
        service = cls(
            api_key=config_values["api_key"],
            base_url=config_values["base_url"],
            model_name=config_values["model_name"],
            system_prompt=config_values["system_prompt"],
            mcp_servers=mcp_servers
        )
        
        # 初始化服务
        await service.initialize()
        
        return service

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model_name: str = "gpt-3.5-turbo", system_prompt: str = "",
                 mcp_servers: List[Dict[str, str]] = None, mongodb_url: str = "",
                 history_limit: int = 10, enable_history: bool = True):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.system_prompt = system_prompt or "你是一个专业的AI助手，能够提供准确、详细和有用的回答。"
        self.mcp_servers = mcp_servers or []

        # 聊天历史配置
        self.enable_history = enable_history
        self.history_limit = history_limit

        # 生成固定的会话ID，整个服务生命周期内使用同一个
        self.conversation_id = f"expert_conv_{uuid.uuid4().hex[:16]}"

        # 移除停止标志，使用框架提供的停止功能

        # 初始化MCP工具执行器
        self.mcp_tool_execute = McpToolExecute(self.mcp_servers)

        # 初始化聊天记录管理器
        self.chat_history = ChatHistoryManager(
            mongodb_url=mongodb_url,
            history_limit=history_limit,
            enable_history=enable_history
        )

        logger.info(f"Expert Service initialized with model: {self.model_name}")
        logger.info(f"Configured MCP servers: {len(self.mcp_servers)}")
        logger.info(f"Chat history enabled: {enable_history}, limit: {history_limit}")
        logger.info(f"Fixed conversation ID: {self.conversation_id}")

    async def initialize(self):
        """初始化服务"""
        await self.mcp_tool_execute.init()
        await self.chat_history.initialize()

    async def shutdown(self):
        """关闭服务，清理资源"""
        logger.info("🛑 正在关闭Expert服务...")
        
        # 框架会自动处理停止逻辑
        
        # 等待一小段时间确保abort操作完成
        import asyncio
        await asyncio.sleep(0.1)
        
        # 清理MCP工具执行器
        if hasattr(self.mcp_tool_execute, 'cleanup'):
            try:
                await self.mcp_tool_execute.cleanup()
            except Exception as e:
                logger.warning(f"清理MCP工具执行器时出现警告: {e}")
        
        # 清理聊天历史管理器
        if hasattr(self.chat_history, 'close'):
            try:
                await self.chat_history.close()
            except Exception as e:
                logger.warning(f"关闭聊天历史管理器时出现警告: {e}")
        
        logger.info("✅ Expert服务已关闭")

    async def _summarize_history(self, history_messages: List[Dict]) -> str:
        """使用AI总结历史记录内容"""
        if not history_messages:
            return ""

        # 构建历史记录文本
        history_text = ""
        for msg in history_messages:
            role = "用户" if msg['role'] == 'user' else "助手"
            history_text += f"{role}: {msg['content']}\n"

        # 构建总结请求
        summary_messages = [
            {
                "role": "system",
                "content": "你是一个专业的对话总结助手。请简洁地总结以下对话历史的主要内容和上下文，重点关注用户的需求和已讨论的关键信息。总结应该简洁明了，不超过200字。"
            },
            {
                "role": "user",
                "content": f"请总结以下对话历史：\n\n{history_text}"
            }
        ]

        try:
            # 创建AI客户端进行总结
            model_config = {
                'api_key': self.api_key,
                'base_url': self.base_url,
                'model_name': self.model_name,
                'temperature': 0.3,
                'max_tokens': 300
            }

            ai_handler = AiRequestHandler(
                messages=summary_messages,
                tools=[],  # 总结时不需要工具
                conversation_id=f"summary_{uuid.uuid4().hex[:8]}",
                callback=None,
                model_config=model_config
            )

            response_messages = await ai_handler.chat_completion()
            summary = response_messages[-1]['content'] if response_messages else ""

            logger.info(f"📝 历史记录总结完成: {summary[:50]}...")
            return summary

        except Exception as e:
            logger.error(f"❌ 历史记录总结失败: {e}")
            return ""

    async def ask_expert(self, question: str) -> str:
        """向AI专家提问"""
        try:
            logger.info(f"🤖 收到问题: {question[:100]}..." if len(question) > 100 else f"🤖 收到问题: {question}")

            # 使用固定的会话ID
            conversation_id = self.conversation_id

            # 构建system prompt
            system_prompt = self.system_prompt

            # 如果启用聊天历史，获取并总结历史记录
            if self.enable_history:
                history_messages = await self.chat_history.get_history(conversation_id, self.history_limit)
                logger.info(f"📝 加载历史记录: {len(history_messages)} 条")

                if history_messages:
                    # 总结历史记录
                    history_summary = await self._summarize_history(history_messages)
                    if history_summary:
                        system_prompt += f"\n\n【对话历史总结】\n{history_summary}"
                        logger.info(f"📝 已将历史记录总结加入system prompt")

                # 保存用户问题
                await self.chat_history.save_message(conversation_id, "user", question)

            # 构建消息列表（只包含system prompt和当前问题）
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]

            logger.info(f"🤖 构建消息列表，共 {len(messages)} 条消息")

            model_config = {
                'api_key': self.api_key,
                'base_url': self.base_url,
                'model_name': self.model_name,
                'temperature': 0.7,
                'max_tokens': 2000
            }

            # 获取可用工具
            tools = self.mcp_tool_execute.get_tools()
            logger.info(f"🛠️ 获取到 {len(tools)} 个可用工具")

            logger.info(f"🤖 创建AI客户端，会话ID: {conversation_id}")

            ai_client = AiClient(
                messages, conversation_id, tools, model_config,
                None, self.mcp_tool_execute
            )

            # 开始处理
            logger.info(f"🤖 开始AI对话处理")
            await ai_client.start()

            # 返回最后的助手回复
            for message in reversed(messages):
                if message.get('role') == 'assistant' and message.get('content'):
                    result = message['content']
                    # 只在启用历史记录时保存助手回复
                    if self.enable_history:
                        await self.chat_history.save_message(conversation_id, "assistant", result)
                        logger.info(f"💾 已保存助手回复到聊天历史，会话ID: {conversation_id}")
                    logger.info(f"🤖 AI回答: {result[:200]}..." if len(result) > 200 else f"🤖 AI回答: {result}")
                    return result

            logger.warning(f"⚠️ 没有获得有效的AI回复")
            return "抱歉，没有获得有效回复。"

        except Exception as e:
            logger.error(f"❌ Ask expert failed: {e}")
            return f"处理请求时出错: {str(e)}"

    async def ask_expert_stream(self, question: str) -> AsyncGenerator[str, None]:
        """向AI专家提问（流式响应）"""
        try:
            logger.info(
                f"🌊 收到流式问题: {question[:100]}..." if len(question) > 100 else f"🌊 收到流式问题: {question}")

            # 使用固定的会话ID
            conversation_id = self.conversation_id

            # 构建system prompt
            system_prompt = self.system_prompt

            # 如果启用聊天历史，获取并总结历史记录
            if self.enable_history:
                history_messages = await self.chat_history.get_history(conversation_id, self.history_limit)
                logger.info(f"📝 流式模式加载历史记录: {len(history_messages)} 条")

                if history_messages:
                    # 总结历史记录
                    history_summary = await self._summarize_history(history_messages)
                    if history_summary:
                        system_prompt += f"\n\n【对话历史总结】\n{history_summary}"
                        logger.info(f"📝 已将历史记录总结加入流式system prompt")

                # 保存用户问题
                await self.chat_history.save_message(conversation_id, "user", question)

            # 构建消息列表（只包含system prompt和当前问题）
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]

            logger.info(f"🌊 构建流式消息列表，共 {len(messages)} 条消息")

            model_config = {
                'api_key': self.api_key,
                'base_url': self.base_url,
                'model_name': self.model_name,
                'temperature': 0.7,
                'max_tokens': 2000
            }

            # 获取可用工具
            tools = self.mcp_tool_execute.get_tools()
            logger.info(f"🛠️ 流式模式获取到 {len(tools)} 个可用工具")

            # 创建流式回调
            stream_data = []
            assistant_response = ""

            def stream_callback(event_type, data):
                logger.info(f"🌊 流式回调: {event_type} - {str(data)[:100]}..." if len(
                    str(data)) > 100 else f"🌊 流式回调: {event_type} - {data}")
                stream_data.append({"type": event_type, "data": data})

            logger.info(f"🌊 创建流式AI客户端，会话ID: {conversation_id}")

            ai_client = AiClient(
                messages, conversation_id, tools, model_config,
                stream_callback, self.mcp_tool_execute
            )

            # AI客户端现在由框架管理

            # 开始流式对话
            logger.info(f"🌊 开始流式AI对话处理")
            chunk_count = 0
            assistant_content = ""

            async for chunk in ai_client.start_stream():

                chunk_count += 1
                logger.info(f"🌊 产生第 {chunk_count} 个流式块: {chunk[:50]}..." if len(
                    chunk) > 50 else f"🌊 产生第 {chunk_count} 个流式块: {chunk}")

                # 收集助手回复内容用于保存到历史记录
                try:
                    chunk_data = json.loads(chunk)
                    # 确保chunk_data是字典类型才调用.get()方法
                    if isinstance(chunk_data, dict) and chunk_data.get("type") == "content" and "data" in chunk_data:
                        assistant_content += chunk_data["data"]
                except (json.JSONDecodeError, KeyError, AttributeError):
                    pass

                yield chunk

            # 保存助手回复到聊天历史
            if self.enable_history and assistant_content.strip():
                await self.chat_history.save_message(
                    conversation_id, "assistant", assistant_content.strip()
                )
                logger.info(f"💾 已保存助手回复到聊天历史，会话ID: {conversation_id}")

            logger.info(f"🌊 流式对话完成，总共产生 {chunk_count} 个块")

        except Exception as e:
            logger.error(f"❌ Ask expert stream failed: {e}")
            yield json.dumps({"type": "error", "data": f"查询专家失败: {str(e)}"}, ensure_ascii=False)
