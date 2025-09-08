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
    
    async def summarize_progress(self, messages: List[Dict[str, Any]], conversation_id: str) -> List[Dict[str, Any]]:
        """总结当前进度并生成新的消息列表
        
        Args:
            messages: 当前的消息列表
            conversation_id: 会话ID
            
        Returns:
            总结后的新消息列表
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
            "content": "请总结到目前为止的对话内容和工具调用结果，提取重要信息和关键发现。总结应包括：\n"
                       "1. 用户的主要需求和问题\n"
                       "2. 已经完成的工具调用及其结果\n"
                       "3. 已经发现的关键信息\n"
                       "4. 下一步应该采取的行动\n"
                       "总结应简洁明了，重点突出，便于继续执行任务。"
        }
        summary_request_messages.append(summary_instruction)
        
        # 添加所有消息用于总结
        for msg in messages:
            if msg.get('role') != 'system':  # 跳过系统消息，因为已经添加过
                summary_request_messages.append(msg)
        
        # 添加总结请求
        summary_request_messages.append({
            "role": "user",
            "content": "请根据以上对话和工具调用结果，生成一个总结。"
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
            
            # 执行总结请求
            response_messages = await summary_handler.chat_completion()
            
            # 获取总结内容
            summary_content = ""
            if response_messages and len(response_messages) > 0:
                for msg in reversed(response_messages):
                    if msg.get('role') == 'assistant' and msg.get('content'):
                        summary_content = msg.get('content')
                        break
            
            if not summary_content:
                logger.warning("⚠️ 未能获取有效的总结内容")
                return messages
                
            logger.info(f"📝 总结内容: {summary_content[:100]}..." if len(summary_content) > 100 else f"📝 总结内容: {summary_content}")
            
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
            return new_messages
            
        except Exception as e:
            logger.error(f"❌ 总结当前进度失败: {e}")
            # 如果总结失败，返回原始消息列表
            return messages
    
    async def generate_summary_stream(self, messages: List[Dict[str, Any]], conversation_id: str) -> AsyncGenerator[Any, None]:
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
            "data": "\n\n🔄 **已完成5次工具调用，正在生成总结...**\n\n"
        }, ensure_ascii=False)
        yield summary_start_info
        
        # 调用AI总结当前内容
        summarized_messages = await self.summarize_progress(messages, conversation_id)
        
        # 发送总结完成信息
        summary_done_info = json.dumps({
            "type": "content",
            "data": "\n\n✅ **总结完成，继续执行任务...**\n\n---\n\n"
        }, ensure_ascii=False)
        yield summary_done_info
        
        # 通过yield返回总结后的消息列表
        yield summarized_messages