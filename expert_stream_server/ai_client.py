import json
import logging

from typing import Any, Dict, List, Optional, AsyncGenerator

# 使用绝对导入，但不包含包名前缀
from ai_request_handler import AiRequestHandler
from ai_summarizer import AiSummarizer
from mcp_tool_execute import McpToolExecute

# 配置日志
logger = logging.getLogger("AiClient")


class AiClient:
    """AI客户端"""

    def __init__(self, messages: List[Dict[str, Any]], conversation_id: str,
                 tools: List[Dict[str, Any]], model_config: Dict[str, Any],
                 callback, mcp_tool_execute: McpToolExecute, summary_interval: int = 5,
                 max_rounds: int = 25, summary_instruction: str = "", summary_request: str = ""):
        self.messages = messages
        self.conversation_id = conversation_id
        self.tools = tools
        self.model_config = model_config
        self.callback = callback
        self.mcp_tool_execute = mcp_tool_execute
        self.is_aborted = False
        self.current_ai_request_handler = None
        self.summary_interval = summary_interval
        self.max_rounds = max_rounds
        self.summary_instruction = summary_instruction
        self.summary_request = summary_request
        
        # 将总结指令和请求内容添加到model_config中
        model_config_with_summary = model_config.copy()
        model_config_with_summary["summary_instruction"] = summary_instruction
        model_config_with_summary["summary_request"] = summary_request
        
        # 初始化AI总结器
        self.ai_summarizer = AiSummarizer(model_config_with_summary)

    # 非流式方法已移除，只保留流式版本

    async def start_stream(self) -> AsyncGenerator[str, None]:
        """开始流式AI对话"""
        try:
            if self.callback:
                self.callback("conversation_start", {"conversation_id": self.conversation_id})

            async for chunk in self.handle_tool_call_recursively_stream(max_rounds=self.max_rounds, current_round=0):
                yield chunk

            if self.callback:
                self.callback("conversation_end", {"conversation_id": self.conversation_id})

        except Exception as e:
            if self.callback:
                self.callback("error", {"error": str(e)})
            yield json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False)

    async def handle_tool_call_recursively_stream(self, max_rounds: int, current_round: int, summarized_messages: List[Dict[str, Any]] = None) -> AsyncGenerator[
        str, None]:
        """递归处理工具调用（流式版本）"""
        logger.info(f"🌊 开始第 {current_round + 1} 轮流式AI对话处理")

        if current_round >= max_rounds:
            logger.warning(f"⚠️ 达到最大轮数限制 ({max_rounds})")
            return

        if self.is_aborted:
            logger.info('🛑 Request aborted')
            return
            
        # 如果提供了总结后的消息，使用它们替换当前消息
        if summarized_messages:
            logger.info(f"🔄 使用总结后的消息重新开始对话，消息数量: {len(summarized_messages)}")
            self.messages = summarized_messages

        # 检查是否有待执行的工具调用
        has_pending_tools = (self.messages and
                             self.messages[-1].get('role') == 'assistant' and
                             self.messages[-1].get('tool_calls', []))

        if has_pending_tools:
            logger.info(f"🔧 第 {current_round + 1} 轮：发现待执行的工具调用")

            # 🌊 流式执行工具并实时yield内容
            async for chunk in self._execute_pending_tool_calls_stream():
                yield chunk
                
            # 检查是否达到配置的工具调用次数（使用current_round+1判断，因为current_round从0开始计数）
            if current_round + 1 >= self.summary_interval:  # 达到配置的轮数
                logger.info(f"🔄 已达到{self.summary_interval}轮对话，开始生成总结")
                
                # 使用AI总结器生成总结
                summarized_messages = None
                async for chunk in self.ai_summarizer.generate_summary_stream(self.messages, self.conversation_id):
                    if isinstance(chunk, list):
                        # 如果返回的是消息列表，保存它
                        summarized_messages = chunk
                    else:
                        # 否则是流式内容，直接yield
                        yield chunk
                
                # 如果成功获取到总结后的消息
                if summarized_messages:
                    # 使用总结后的消息重新开始对话，并将current_round重置为0
                    async for chunk in self.handle_tool_call_recursively_stream(max_rounds, 0, summarized_messages):
                        yield chunk
                    return
            
            # 工具执行完成后，进入下一轮递归
            # 注意：这里不再递增current_round，因为在AI响应后的工具调用中已经递增了
            else:
                async for chunk in self.handle_tool_call_recursively_stream(max_rounds, current_round+1):
                    yield chunk

        else:
            # 没有工具调用，进行AI聊天
            async for chunk in self.chat_completion_stream():
                yield chunk

            # 检查AI响应后是否有新的工具调用
            has_new_tools = (self.messages and
                             self.messages[-1].get('role') == 'assistant' and
                             self.messages[-1].get('tool_calls', []))

            if has_new_tools:
                async for chunk in self.handle_tool_call_recursively_stream(max_rounds, current_round + 1):
                    yield chunk

    async def _execute_pending_tool_calls_stream(self) -> AsyncGenerator[str, None]:
        """执行待处理的工具调用（流式版本）"""
        if not self.messages:
            return

        latest_message = self.messages[-1]
        tool_calls = latest_message.get('tool_calls', [])

        if not tool_calls:
            return

        logger.info(f"🔧 开始执行 {len(tool_calls)} 个工具调用")

        # 🌊 首先yield工具调用信息（工具名称和参数）
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                tool_name = tool_call.get('function', {}).get('name') or tool_call.get('name', 'unknown')
                tool_args = tool_call.get('function', {}).get('arguments', '') or tool_call.get('arguments', '')
                tool_call_id = tool_call.get('id', '')
                
                # 格式化工具调用信息为Markdown格式
                try:
                    # 尝试解析参数JSON
                    if isinstance(tool_args, str):
                        import json as json_module
                        args_dict = json_module.loads(tool_args)
                        formatted_args = "\n".join([f"  - **{k}**: {v}" for k, v in args_dict.items()])
                    else:
                        formatted_args = f"  - {tool_args}"
                except:
                    formatted_args = f"  - {tool_args}"
                
                # yield工具调用开始信息（Markdown格式）
                tool_call_markdown = f"\n🔧 **调用工具**: `{tool_name}`\n\n**参数**:\n{formatted_args}\n"
                
                tool_call_info = json.dumps({
                    "type": "content",
                    "data": tool_call_markdown
                }, ensure_ascii=False)
                yield tool_call_info

        if self.callback:
            self.callback('tool_call', tool_calls)

        # 检查停止工具调用
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_name = tool_call.get('function', {}).get('name') or tool_call.get('name')
            if tool_name == 'stop_conversation':
                logger.info(f"🛑 收到停止对话请求")
                if self.callback:
                    self.callback('conversation_stopped', {'reason': '用户请求停止'})
                return

        # 累积每个工具的完整内容
        tool_contents = {}  # tool_call_id -> 累积的内容
        tool_results = []

        # 执行并累积所有流式内容
        async for tool_result in self.mcp_tool_execute.execute_stream(tool_calls, self.callback):
            tool_call_id = tool_result.get('tool_call_id')
            tool_name = tool_result.get('name')
            content = tool_result.get('content', '')
            is_final = tool_result.get('is_final', False)

            logger.info(
                f"🔧 收到工具结果: tool_call_id={tool_call_id}, name={tool_name}, content_len={len(content)}, is_final={is_final}")

            if not tool_call_id:
                logger.warning(f"⚠️ 工具结果缺少 tool_call_id")
                continue

            # 🌊 实时yield工具执行的流式内容
            if content and not is_final:
                # 格式化工具输出
                tool_chunk = json.dumps({
                    "type": "tool_stream",
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "content": content
                }, ensure_ascii=False)
                yield tool_chunk

            # 累积内容
            if tool_call_id not in tool_contents:
                tool_contents[tool_call_id] = ""

            if not is_final:
                tool_contents[tool_call_id] += content
            else:
                # 最终结果
                final_content = tool_contents[tool_call_id] + content if tool_contents[tool_call_id] else content

                complete_result = {
                    'tool_call_id': tool_call_id,
                    'role': 'tool',
                    'name': tool_name,
                    'content': final_content
                }
                tool_results.append(complete_result)

        # 添加工具结果到消息历史
        logger.info(f"🔧 添加 {len(tool_results)} 个工具结果到消息历史")
        self.messages.extend(tool_results)

        if self.callback:
            self.callback('tool_result', tool_results)

        # 🌊 为每个完成的工具发送结束信号（Markdown格式）
        for tool_result in tool_results:
            tool_name = tool_result.get('name', 'unknown')
            content_length = len(tool_result.get('content', ''))
            
            # 格式化工具执行完成信息为Markdown格式
            tool_end_markdown = f"\n✅ **工具执行完成**: `{tool_name}` (输出长度: {content_length} 字符)\n"
            
            tool_end_info = json.dumps({
                "type": "content",
                "data": tool_end_markdown
            }, ensure_ascii=False)
            yield tool_end_info

        # 发送工具执行完成信号（Markdown格式）
        if tool_results:
            completion_markdown = f"\n🎉 **所有工具执行完成** (共 {len(tool_results)} 个工具)\n\n---\n"
            completion_signal = json.dumps({
                "type": "content",
                "data": completion_markdown
            }, ensure_ascii=False)
            yield completion_signal

    async def chat_completion_stream(self) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        try:
            logger.info(f"🌊 创建流式AI请求处理器，消息数: {len(self.messages)}, 工具数: {len(self.tools)}")
            self.current_ai_request_handler = AiRequestHandler(
                self.messages, self.tools, self.conversation_id,
                self.callback, self.model_config
            )

            logger.info(f"🌊 开始执行流式聊天完成请求")
            chunk_count = 0
            async for chunk in self.current_ai_request_handler.chat_completion_stream():
                chunk_count += 1
                logger.debug(f"🌊 产生第 {chunk_count} 个流式块: {chunk[:50]}..." if len(
                    chunk) > 50 else f"🌊 产生第 {chunk_count} 个流式块: {chunk}")
                yield chunk

            # 🔧 关键修复：将AiRequestHandler的消息历史同步回AiClient
            # AiRequestHandler在处理过程中会将AI响应添加到其本地messages中
            # 我们需要将这些更新同步回AiClient的messages
            logger.info(f"🔧 同步消息历史：AiRequestHandler消息数 {len(self.current_ai_request_handler.messages)}, AiClient消息数 {len(self.messages)}")
            
            # 如果AiRequestHandler的消息数量更多，说明有新的AI响应被添加
            if len(self.current_ai_request_handler.messages) > len(self.messages):
                # 获取新添加的消息
                new_messages = self.current_ai_request_handler.messages[len(self.messages):]
                self.messages.extend(new_messages)
                logger.info(f"🔧 已同步 {len(new_messages)} 条新消息到AiClient，当前总消息数: {len(self.messages)}")
                
                # 打印最新消息的信息
                if new_messages:
                    latest_msg = new_messages[-1]
                    logger.info(f"🔧 最新同步的消息角色: {latest_msg.get('role')}, 工具调用数: {len(latest_msg.get('tool_calls', []))}")

            logger.info(f"✅ 流式聊天完成请求执行成功，总共产生 {chunk_count} 个块")

        except Exception as e:
            logger.error(f"❌ Stream chat completion error: {e}")
            if self.callback:
                self.callback('error', e)
            yield json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False)

    def abort(self):
        """中止请求"""
        self.is_aborted = True
        if self.current_ai_request_handler:
            self.current_ai_request_handler.abort()
