import json
import logging
from typing import Any, Dict, List, AsyncGenerator

from ai_request_handler import AiRequestHandler

# 配置日志
logger = logging.getLogger("AiSummarizer")


class AiSummarizer:
    """AI总结器
    
    用于在工具调用过程中生成总结，提取重要信息和下一步行动。
    """

    def __init__(self, model_config: Dict[str, Any]):
        """初始化AI总结器
        
        Args:
            model_config: AI模型配置
        """
        self.model_config = model_config
        # 从model_config中获取总结指令和请求内容，如果没有则使用默认值
        self.summary_instruction = model_config.get("summary_instruction", "")
        self.summary_request = model_config.get("summary_request", "")


    async def summarize_progress_stream(self, messages: List[Dict[str, Any]], conversation_id: str) -> AsyncGenerator[
        Any, None]:
        """总结当前进度并生成新的消息列表（流式版本）
        
        Args:
            messages: 当前的消息列表
            conversation_id: 会话ID
            
        Yields:
            总结过程中的流式内容或总结后的消息列表
        """
        logger.info(f"🔍 开始总结当前进度，消息数量: {len(messages)}")

        # 提取系统消息
       
        # 构建用于总结的消息列表
        summary_request_messages = []


        # 添加总结指令（系统消息应该在用户消息之前）
        summary_instruction = {
            "role": "system",
            "content": self.summary_instruction
        }
        summary_request_messages.append(summary_instruction)
        
        # 将非系统消息转换为整体文本，并添加到summary_request后面
        messages_text = ""
        for msg in messages:
            if msg.get('role') != 'system':  # 跳过系统消息
                role = msg.get('role', '')
                content = msg.get('content', '')
                messages_text += f"\n\n{role.upper()}: {content}"
        
        # 添加总结请求（用户消息）- 将原始消息文本添加到summary_request后面
        summary_request_messages.append({
            "role": "user",
            "content": self.summary_request + "\n\nThe following is the dialogue content that needs to be analyzed.：[" + messages_text+"]"
        })

        try:
            # 创建AI请求处理器进行总结
            summary_handler = AiRequestHandler(
                messages=summary_request_messages,
                tools=[],  # 总结时不需要工具
                conversation_id=f"summary_{conversation_id}",
                callback=None,
                model_config=self.model_config
            )

            # 执行总结请求（使用流式方法并实时yield内容）
            response_messages = []
            content_chunks = []

            # 使用流式方法获取响应并实时yield
            async for chunk in summary_handler.chat_completion_stream():
                import json
                try:
                    chunk_data = json.loads(chunk)
                    if chunk_data.get('type') == 'content' and chunk_data.get('data'):
                        content_chunks.append(chunk_data.get('data'))
                        # 实时yield出AI生成的内容
                        yield chunk
                except Exception as e:
                    logger.error(f"处理总结流式响应时出错: {e}")

            # 合并所有内容块
            if content_chunks:
                # 构建助手消息
                assistant_message = {
                    "role": "assistant",
                    "content": "".join(content_chunks)
                }
                response_messages.append(assistant_message)

            # 获取总结内容
            summary_content = ""
            if response_messages and len(response_messages) > 0:
                for msg in reversed(response_messages):
                    if msg.get('role') == 'assistant' and msg.get('content'):
                        summary_content = msg.get('content')
                        break

            if not summary_content:
                logger.warning("⚠️ 未能获取有效的总结内容")
                yield messages
                return

            logger.info(f"📝 总结内容: {summary_content[:100]}..." if len(
                summary_content) > 100 else f"📝 总结内容: {summary_content}")

            # 构建新的消息列表
            new_messages = []

            # 添加原始系统消息
            if system_message:
                new_messages.append(system_message)

            # 添加原始用户问题（第一个用户消息）- 确保第一条用户消息始终保存
            first_user_message = None
            for msg in messages:
                if msg.get('role') == 'user':
                    first_user_message = msg
                    break

            # 确保第一条用户消息一直保存下来
            if first_user_message:
                new_messages.append(first_user_message)
                logger.info(f"📌 保存第一条用户消息: {first_user_message.get('content', '')[:50]}...")
            else:
                logger.warning("⚠️ 未找到第一条用户消息")

            # 添加总结消息
            summary_message = {
                "role": "assistant",
                "content": f"以下是当前进度的总结：\n\n{summary_content}\n\n我将基于这个总结继续完成剩余任务。"
            }
            new_messages.append(summary_message)

            logger.info(f"✅ 总结完成，生成了 {len(new_messages)} 条新消息")
            yield new_messages

        except Exception as e:
            logger.error(f"❌ 总结当前进度失败: {e}")
            # 如果总结失败，yield原始消息列表
            yield messages

    async def summarize_progress(self, messages: List[Dict[str, Any]], conversation_id: str) -> List[Dict[str, Any]]:
        """总结当前进度并生成新的消息列表（非流式版本，保留向后兼容）
        
        Args:
            messages: 当前的消息列表
            conversation_id: 会话ID
            
        Returns:
            总结后的新消息列表
        """
        # 创建一个列表来存储结果
        result = None

        # 调用流式版本并获取最后一个结果
        async for item in self.summarize_progress_stream(messages, conversation_id):
            if isinstance(item, list):
                result = item

        # 返回结果或原始消息
        return result if result else messages

    async def generate_summary_stream(self, messages: List[Dict[str, Any]], conversation_id: str) -> AsyncGenerator[
        Any, None]:
        """生成总结的流式版本
        
        Args:
            messages: 当前的消息列表
            conversation_id: 会话ID
            
        Yields:
            总结过程中的流式内容或总结后的消息列表
        """
        # 生成总结开始信息
        summary_start_info = json.dumps({
            "type": "content",
            "data": "\n\n🔄 **让我整理一下现在的执行情况...**\n\n"
        }, ensure_ascii=False)
        yield summary_start_info

        # 调用流式总结方法并传递所有流式内容
        async for item in self.summarize_progress_stream(messages, conversation_id):
            # 如果是列表，说明是最终的总结消息列表
            if isinstance(item, list):
                # 发送总结完成信息
                summary_done_info = json.dumps({
                    "type": "content",
                    "data": "\n\n✅ **总结完成，继续执行任务...**\n\n---\n\n"
                }, ensure_ascii=False)
                yield summary_done_info
                # 返回总结后的消息列表
                yield item
            else:
                # 传递流式内容
                yield item
