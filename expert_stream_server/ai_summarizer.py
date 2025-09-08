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
        system_message = None
        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg
                break

        # 构建用于总结的消息列表
        summary_request_messages = []

        # 添加系统消息
        if system_message:
            summary_request_messages.append(system_message)

        # 添加总结指令
        summary_instruction = {
            "role": "system",
            "content": """You are a professional conversation analysis specialist. Please generate a structured summary report based on the following conversation history and tool call results.

            ## Summary Requirements:
            1. **Original User Intent Identification**: Accurately extract the user's core problems and ultimate objectives
            2. **Key Information Filtering**: Filter important information directly related to the original intent from conversations and tool call results
            3. **Deduplication Processing**: Avoid redundant content and merge similar information
            4. **Priority Ranking**: Sort information by importance and relevance
    
            ## Output Format:
            ### 🎯 Core User Requirements
            - [Concisely describe the user's main problems and objectives]
    
            ### 📋 Key Information Acquired
            - [List core findings related to requirements by importance]
            - [Include important data fragments obtained from tool calls]
    
            ### ✅ Completed Key Operations
            - [List important tool calls executed and their core results]
    
            ### 🔍 Information Gap Analysis
            - [Identify information still needed to be acquired]
            - [Avoid redundant queries for existing information]
    
            ### 📝 Next Action Recommendations
            - [Based on current information status, suggest specific next steps]
    
            ## Important Notes:
            - Focus on relevance to the user's original requirements
            - Filter out irrelevant conversation content
            - Highlight key data obtained from tool calls
            - Provide clear guidance for subsequent operations to avoid duplicate queries"""
        }
        summary_request_messages.append(summary_instruction)

        # 添加所有消息用于总结
        for msg in messages:
            if msg.get('role') != 'system':  # 跳过系统消息，因为已经添加过
                summary_request_messages.append(msg)

        # 添加总结请求
        summary_request_messages.append({
            "role": "user",
            "content": """Please generate a precise summary report based on the above conversation history.
        
                ## Analysis Focus:
                1. Identify the user's real needs and ultimate goals from the beginning of the conversation
                2. Extract core information related to requirements from all tool call results
                3. Identify what information has been acquired and what still needs to be supplemented
                4. To avoid duplicate queries, clearly mark verified key data points
                
                ## Output Requirements:
                - Use structured format for easy understanding and use by subsequent AI
                - Highlight information fragments most relevant to original requirements
                - Provide clear next-step operation guidance
                - Mark the source of important information (conversation vs tool calls)
                
                Please generate the summary report."""
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

            # 添加原始用户问题（第一个用户消息）
            first_user_message = None
            for msg in messages:
                if msg.get('role') == 'user':
                    first_user_message = msg
                    break

            if first_user_message:
                new_messages.append(first_user_message)

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
