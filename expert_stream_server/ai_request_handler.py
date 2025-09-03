import logging
from typing import Any, Dict, List, AsyncGenerator
from openai import AsyncOpenAI

# 配置日志
logger = logging.getLogger("AiRequestHandler")


class AiRequestHandler:
    """AI请求处理器"""

    def __init__(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                 conversation_id: str, callback, model_config: Dict[str, Any]):
        self.messages = messages
        self.tools = tools
        self.conversation_id = conversation_id
        self.callback = callback
        self.model_config = model_config
        self.is_aborted = False
        self.client = None

    async def _get_client(self):
        """获取或创建OpenAI客户端"""
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=self.model_config['api_key'],
                base_url=self.model_config['base_url']
            )
        return self.client

    async def _close_client(self):
        """安全关闭客户端"""
        if self.client is not None:
            try:
                # 确保所有异步生成器都被正确关闭
                await self.client.close()
                logger.debug("OpenAI客户端已成功关闭")
            except Exception as e:
                logger.warning(f"关闭OpenAI客户端时出现警告: {e}")
            finally:
                self.client = None

    # chat_completion 非流式方法已移除

    async def chat_completion_stream(self) -> AsyncGenerator[str, None]:
        """执行流式聊天完成"""
        stream = None
        try:
            if self.callback:
                self.callback('ai_request_start', {
                    'conversation_id': self.conversation_id,
                    'messages_count': len(self.messages)
                })

            # 获取客户端
            client = await self._get_client()
            
            payload = self.build_payload()
            payload['stream'] = True

            stream = await client.chat.completions.create(**payload)

            # 初始化累积变量
            content = ""
            tool_calls = []  # 使用列表来按索引存储

            try:
                async for chunk in stream:
                    if self.is_aborted:
                        logger.info("流式处理被中止")
                        break

                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta

                        # 处理内容
                        if delta.content:
                            content += delta.content
                            if self.callback:
                                self.callback('ai_stream_chunk', {
                                    'content': delta.content
                                })
                            # 返回JSON格式的增量内容，而不是累积内容
                            import json
                            yield json.dumps({"type": "content", "data": delta.content}, ensure_ascii=False)

                        # 处理工具调用
                        if delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                self._process_tool_call_delta(tool_calls, tool_call)

                        # 检查是否完成
                        if chunk.choices[0].finish_reason:
                            break
            except Exception as stream_error:
                logger.error(f"流式处理过程中出现错误: {stream_error}")
                # 确保流被正确关闭
                if stream and hasattr(stream, 'close'):
                    try:
                        await stream.close()
                    except Exception as close_error:
                        logger.warning(f"关闭流时出现警告: {close_error}")
                raise stream_error

            # 构建最终结果
            result = {
                'role': 'assistant',
                'content': content,
                'tool_calls': [call for call in tool_calls if call.get('id')]  # 过滤掉空的tool_calls
            }

            # 只有当有内容或工具调用时才添加到消息历史
            if result['content'] or result['tool_calls']:
                self.messages.append(result)

            if self.callback:
                self.callback('ai_response', {
                    'content': result['content'],
                    'tool_calls': result['tool_calls'],
                    'conversation_id': self.conversation_id
                })

        except Exception as e:
            logger.error(f"Stream chat completion failed: {e}")
            if self.callback:
                self.callback('error', {
                    'message': str(e),
                    'conversation_id': self.conversation_id
                })
            raise e
        finally:
            # 确保流被正确关闭
            if stream and hasattr(stream, 'close'):
                try:
                    await stream.close()
                except Exception as close_error:
                    logger.warning(f"在finally中关闭流时出现警告: {close_error}")
            # 确保客户端被正确关闭
            await self._close_client()

    # handle_stream_response 非流式方法已移除

    def build_payload(self) -> Dict[str, Any]:
        """构建请求载荷"""
        payload = {
            'model': self.model_config['model_name'],
            'messages': self.messages,
            'temperature': self.model_config.get('temperature', 0.7),
            'max_tokens': 16000
        }

        if self.tools:
            payload['tools'] = self.tools
            payload['tool_choice'] = 'auto'
            logger.info(
                f"🤖 AI请求参数: 模型={payload['model']}, 消息数={len(payload['messages'])}, 工具数={len(payload['tools'])}, 温度={payload['temperature']}, 最大令牌={payload['max_tokens']}")
        else:
            logger.info(
                f"🤖 AI请求参数: 模型={payload['model']}, 消息数={len(payload['messages'])}, 无工具, 温度={payload['temperature']}, 最大令牌={payload['max_tokens']}")

        return payload

    def abort(self):
        """中止请求"""
        self.is_aborted = True
        # 立即关闭客户端连接以避免异步生成器错误
        if self.client is not None:
            import asyncio
            try:
                # 创建一个任务来异步关闭客户端
                asyncio.create_task(self._close_client())
            except Exception as e:
                logger.warning(f"在abort中关闭客户端时出现警告: {e}")

    def _process_tool_call_delta(self, tool_calls_list: List, tool_call_delta):
        """统一处理工具调用增量数据"""
        if not hasattr(tool_call_delta, 'index') or tool_call_delta.index is None:
            logger.warning("Tool call delta missing index, skipping")
            return

        index = tool_call_delta.index

        # 确保列表有足够的元素
        while len(tool_calls_list) <= index:
            tool_calls_list.append({
                'id': '',
                'type': 'function',
                'function': {'name': '', 'arguments': ''}
            })

        current_call = tool_calls_list[index]

        # 只在有值时更新（避免覆盖已有值）
        if hasattr(tool_call_delta, 'id') and tool_call_delta.id:
            current_call['id'] = tool_call_delta.id
        if hasattr(tool_call_delta, 'type') and tool_call_delta.type:
            current_call['type'] = tool_call_delta.type

        if hasattr(tool_call_delta, 'function') and tool_call_delta.function:
            if hasattr(tool_call_delta.function, 'name') and tool_call_delta.function.name:
                current_call['function']['name'] = tool_call_delta.function.name
            if hasattr(tool_call_delta.function, 'arguments') and tool_call_delta.function.arguments:
                current_call['function']['arguments'] += tool_call_delta.function.arguments


