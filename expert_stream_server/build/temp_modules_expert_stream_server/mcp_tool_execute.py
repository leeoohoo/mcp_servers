import json
import logging
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator
import aiohttp

# 配置日志
logger = logging.getLogger("McpToolExecute")


class McpToolExecute:
    """MCP工具执行器"""

    def __init__(self, mcp_servers: List[Dict[str, str]]):
        self.mcp_servers = mcp_servers
        self.tools = []
        self.tool_metadata = {}  # 存储工具元数据

    async def init(self):
        """初始化，构建工具列表"""
        await self.build_tools()

    # execute 非流式方法已移除

    async def execute_stream(self, tool_calls: List[Dict[str, Any]], callback=None) -> AsyncGenerator[Dict[str, Any], None]:
        """执行工具调用（流式版本）"""
        logger.info(f"🔧 开始执行流式工具调用，共 {len(tool_calls)} 个工具")

        for i, tool_call in enumerate(tool_calls):
            stream_generator = None
            try:
                # 确保tool_call是字典类型
                if not isinstance(tool_call, dict):
                    logger.error(f"❌ 工具调用不是字典类型: {type(tool_call)} - {tool_call}")
                    continue

                # 解析工具调用
                tool_name = tool_call.get('function', {}).get('name') or tool_call.get('name')
                tool_args = tool_call.get('function', {}).get('arguments') or tool_call.get('arguments', {})

                logger.info(f"🔧 执行流式工具 {i + 1}/{len(tool_calls)}: {tool_name}")

                # 确保tool_args是正确的类型
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        logger.warning(f"❌ Failed to parse tool arguments: {tool_args}")
                        tool_args = {}
                elif not isinstance(tool_args, dict):
                    logger.warning(f"❌ 工具参数不是字典类型: {type(tool_args)} - {tool_args}，转换为空字典")
                    tool_args = {}

                # 查找工具信息
                tool_info = self.find_tool_info(tool_name)
                if not tool_info:
                    raise Exception(f"Tool not found: {tool_name}")

                # 首先尝试流式调用
                accumulated_content = ""
                stream_success = False
                tool_call_id = tool_call.get('id', f"call_{uuid.uuid4().hex[:16]}")

                try:
                    stream_generator = self.call_mcp_tool_stream(
                        tool_info['server_url'],
                        tool_info['original_name'],
                        tool_args
                    )

                    logger.info(f"🔧 开始流式调用工具: {tool_name}")
                    chunk_count = 0
                    
                    async for chunk in stream_generator:
                        # 安全地处理不同类型的 chunk
                        chunk_str = self._safe_chunk_to_string(chunk)
                        accumulated_content += chunk_str
                        chunk_count += 1

                        logger.debug(f"🔧 工具 {tool_name} 收到第 {chunk_count} 个流式块: {chunk_str[:100]}...")

                        if callback:
                            callback('tool_stream_chunk', {
                                'tool_name': tool_name,
                                'chunk': chunk_str
                            })

                        # 生成流式结果
                        yield {
                            'tool_call_id': tool_call_id,
                            'role': 'tool',
                            'name': tool_name,
                            'content': chunk_str,
                            'is_stream': True
                        }

                    stream_success = True
                    logger.info(f"✅ 工具 {tool_name} 流式调用成功，共收到 {chunk_count} 个块，累积内容长度: {len(accumulated_content)}")

                except GeneratorExit:
                    logger.info(f"🛑 工具 {tool_name} 的流式执行被提前终止")
                    # 即使被提前终止，也要生成最终结果
                    if accumulated_content:
                        logger.info(f"🔧 工具 {tool_name} 被终止但有累积内容，生成最终结果")
                        yield {
                            'tool_call_id': tool_call_id,
                            'role': 'tool',
                            'name': tool_name,
                            'content': accumulated_content,
                            'is_stream': False,
                            'is_final': True
                        }
                    return  # 直接返回，不要重新抛出

                except Exception as stream_error:
                    logger.error(f"❌ 流式调用失败: {stream_error}")
                    raise stream_error

                # 只有流式调用成功时才生成最终结果
                if stream_success:
                    logger.info(f"🔧 工具 {tool_name} 准备生成最终结果，累积内容长度: {len(accumulated_content)}")
                    logger.info(f"🔧 累积内容预览: {accumulated_content[:200]}...")
                    
                    yield {
                        'tool_call_id': tool_call_id,
                        'role': 'tool',
                        'name': tool_name,
                        'content': accumulated_content,
                        'is_stream': False,
                        'is_final': True
                    }
                    logger.info(f"✅ 流式工具 {tool_name} 执行成功，最终结果已生成")

            except GeneratorExit:
                logger.info(f"🛑 工具调用流被提前终止")
                # 即使被提前终止，也要确保已处理的工具有最终结果
                if 'accumulated_content' in locals() and accumulated_content:
                    logger.info(f"🔧 工具 {tool_name} 流被终止但有累积内容，生成最终结果")
                    yield {
                        'tool_call_id': tool_call.get('id', f"call_{uuid.uuid4().hex[:16]}"),
                        'role': 'tool',
                        'name': tool_name,
                        'content': accumulated_content,
                        'is_stream': False,
                        'is_final': True
                    }
                return  # 直接返回，不要重新抛出

            except Exception as e:
                logger.error(f"❌ Failed to execute tool {tool_name}: {e}")
                yield {
                    'tool_call_id': tool_call.get('id', f"call_{uuid.uuid4().hex[:16]}"),
                    'role': 'tool',
                    'name': tool_name,
                    'content': json.dumps({'error': str(e)}, ensure_ascii=False),
                    'is_stream': False,
                    'is_final': True,
                    'is_error': True
                }
            finally:
                # 确保流式生成器被正确关闭
                if stream_generator:
                    try:
                        await stream_generator.aclose()
                    except Exception as close_error:
                        logger.debug(f"🧹 关闭流式生成器: {close_error}")

        logger.info(f"🔧 流式工具调用完成")

    def _safe_chunk_to_string(self, chunk) -> str:
        """安全地将chunk转换为字符串"""
        if isinstance(chunk, str):
            return chunk
        elif isinstance(chunk, (list, tuple)):
            try:
                if all(isinstance(item, str) for item in chunk):
                    return ''.join(chunk)
                else:
                    return json.dumps(chunk, ensure_ascii=False)
            except Exception:
                return str(chunk)
        elif isinstance(chunk, dict):
            try:
                return json.dumps(chunk, ensure_ascii=False)
            except Exception:
                return str(chunk)
        elif chunk is None:
            return ""
        else:
            return str(chunk)


    def find_tool_info(self, tool_name: str) -> Optional[Dict[str, str]]:
        """根据工具名称查找工具信息"""
        return self.tool_metadata.get(tool_name)

    async def call_mcp_tool_stream(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """调用MCP工具（流式版本，使用远端 SSE /sse/tool/call 接口）"""
        session = None
        response = None

        # 计算 SSE 接口地址
        sse_url = server_url
        if sse_url.endswith('/mcp'):
            sse_url = sse_url[:-4] + '/sse/tool/call'
        elif '/mcp' in sse_url:
            sse_url = sse_url.replace('/mcp', '/sse/tool/call')
        else:
            sse_url = sse_url.rstrip('/') + '/sse/tool/call'

        logger.info(f"🔧 调用SSE接口: {sse_url}")

        try:
            headers = {
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }

            payload = {
                'tool_name': tool_name,
                'arguments': arguments or {}
            }

            logger.info(f"🔧 发送请求: {payload}")

            timeout = aiohttp.ClientTimeout(total=120, connect=10)
            session = aiohttp.ClientSession(timeout=timeout)
            response = await session.post(sse_url, json=payload, headers=headers)

            logger.info(f"🔧 响应状态: {response.status}")

            if response.status != 200:
                error_text = await response.text()
                logger.error(f"❌ HTTP错误: {response.status} - {error_text}")
                raise Exception(f"HTTP {response.status}: {error_text}")

            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' not in content_type:
                error_text = await response.text()
                logger.error(f"❌ 非SSE响应: {content_type} - {error_text}")
                raise Exception(f"Expected SSE response but got {content_type}: {error_text}")

            # 解析 SSE 流
            buffer = ""
            chunk_count = 0

            logger.info(f"🔧 开始读取SSE流...")

            async for chunk_bytes in response.content.iter_chunked(1024):
                chunk_count += 1
                chunk_str = chunk_bytes.decode('utf-8')
                buffer += chunk_str

                # 处理完整的事件（以\n\n分隔）
                while '\n\n' in buffer:
                    event_block, buffer = buffer.split('\n\n', 1)

                    if not event_block.strip():
                        continue

                    # 解析事件块
                    event_type = None
                    data_content = ""

                    for line in event_block.split('\n'):
                        line = line.strip()
                        if line.startswith('event:'):
                            event_type = line[6:].strip()
                        elif line.startswith('data:'):
                            data_content = line[5:].strip()

                    # 处理不同类型的事件
                    if event_type == 'error':
                        logger.error(f"❌ 收到错误事件: {data_content}")
                        try:
                            error_data = json.loads(data_content) if data_content else {}
                            error_msg = error_data.get('message', data_content)
                        except:
                            error_msg = data_content
                        raise Exception(f"Remote SSE error: {error_msg}")

                    elif event_type == 'end':
                        logger.info(f"🔧 收到结束事件")
                        return

                    elif event_type == 'data' or not event_type:
                        # 处理数据事件
                        if data_content:
                            try:
                                data_obj = json.loads(data_content)

                                # 根据数据类型提取内容
                                content_to_yield = None

                                if isinstance(data_obj, dict):
                                    # 优先查找 chunk 字段
                                    if 'chunk' in data_obj:
                                        content_to_yield = str(data_obj['chunk'])
                                    # 查找 display 字段（项目结构等）
                                    elif 'display' in data_obj:
                                        content_to_yield = str(data_obj['display']) + '\n'
                                    # 查找 content 字段
                                    elif 'content' in data_obj:
                                        content_to_yield = str(data_obj['content'])
                                    # 查找嵌套的数据
                                    elif 'data' in data_obj and isinstance(data_obj['data'], dict):
                                        nested_data = data_obj['data']
                                        if 'chunk' in nested_data:
                                            content_to_yield = str(nested_data['chunk'])
                                        elif 'display' in nested_data:
                                            content_to_yield = str(nested_data['display']) + '\n'
                                        elif 'content' in nested_data:
                                            content_to_yield = str(nested_data['content'])

                                    # 忽略某些控制消息
                                    data_type = data_obj.get('type', '')
                                    if data_type in ['structure_start', 'structure_complete']:
                                        continue

                                if content_to_yield:
                                    logger.info(f"🔧 提取到内容，长度: {len(content_to_yield)}")
                                    yield content_to_yield
                                else:
                                    logger.debug(f"🔧 数据对象中没有找到可用内容: {data_obj}")

                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️ JSON解析失败: {e}, 原始内容: {repr(data_content)}")
                                # 如果不是JSON，直接返回内容
                                if data_content:
                                    logger.info(f"🔧 直接返回非JSON内容，长度: {len(data_content)}")
                                    yield data_content
                    else:
                        logger.debug(f"🔧 忽略未知事件类型: {event_type}")

            # 处理缓冲区中剩余的不完整事件
            if buffer.strip():
                logger.warning(f"⚠️ 缓冲区中有未处理的内容: {repr(buffer)}")

            logger.info(f"🔧 SSE流读取完成，共处理 {chunk_count} 个chunk")

        except GeneratorExit:
            logger.info(f"🛑 MCP工具流式调用被提前终止: {tool_name}")
            return
        except Exception as e:
            logger.error(f"❌ MCP工具流式调用失败 {tool_name}: {e}")
            raise
        finally:
            await self._cleanup_stream_resources(response, session, tool_name)

    async def _cleanup_stream_resources(self, response, session, tool_name: str):
        """清理流式资源"""
        try:
            if response:
                try:
                    # 确保响应内容被完全消费或关闭
                    if not response.closed:
                        logger.debug(f"🧹 正在关闭响应流: {tool_name}")
                        response.close()
                except Exception as close_error:
                    logger.warning(f"⚠️ 关闭响应时出现警告 {tool_name}: {close_error}")

            if session:
                try:
                    if not session.closed:
                        logger.debug(f"🧹 正在关闭会话: {tool_name}")
                        await session.close()
                except Exception as close_error:
                    logger.warning(f"⚠️ 关闭会话时出现警告 {tool_name}: {close_error}")

        except Exception as cleanup_error:
            logger.warning(f"⚠️ 清理资源时出现警告 {tool_name}: {cleanup_error}")

    def _extract_content_as_string(self, result) -> str:
        """从结果中提取内容并转换为字符串"""
        if isinstance(result, dict):
            content = result.get('content', '')
            if isinstance(content, str):
                return content
            elif isinstance(content, (list, dict)):
                return json.dumps(content, ensure_ascii=False)
            elif content is not None:
                return str(content)
            else:
                # 如果没有content字段，返回整个result
                return json.dumps(result, ensure_ascii=False) if result else ""
        elif isinstance(result, str):
            return result
        elif isinstance(result, (list, dict)):
            return json.dumps(result, ensure_ascii=False)
        elif result is not None:
            return str(result)
        else:
            return ""


    async def build_tools(self):
        """构建工具列表"""
        try:
            self.tools = []
            self.tool_metadata = {}

            logger.info(f"🔧 开始构建工具列表，配置的MCP服务器数量: {len(self.mcp_servers)}")

            for mcp_server in self.mcp_servers:
                try:
                    logger.info(f"🔧 正在从MCP服务器获取工具: {mcp_server['name']} ({mcp_server['url']})")

                    # 调用MCP服务获取tools
                    request = {
                        'jsonrpc': '2.0',
                        'id': f"req_{uuid.uuid4().hex[:16]}",
                        'method': 'tools/list',
                        'params': {}
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.post(mcp_server['url'], json=request, timeout=30) as response:
                            if response.status != 200:
                                logger.warning(
                                    f"❌ Failed to get tools from {mcp_server['name']}: HTTP {response.status}")
                                continue

                            data = await response.json()
                            if 'error' in data:
                                logger.warning(
                                    f"❌ MCP tools/list failed for {mcp_server['name']}: {data['error']['message']}")
                                continue

                            result = data.get('result', {})
                            server_tools = result.get('tools', []) if isinstance(result, dict) else []
                            logger.info(f"✅ 从 {mcp_server['name']} 获取到 {len(server_tools)} 个工具")

                            # 转换为OpenAI工具格式
                            for tool in server_tools:
                                prefixed_name = f"{mcp_server['name']}_{tool['name']}"

                                openai_tool = {
                                    'type': 'function',
                                    'function': {
                                        'name': prefixed_name,
                                        'description': tool.get('description', ''),
                                        'parameters': tool.get('inputSchema', tool.get('parameters', {}))
                                    }
                                }

                                # 存储元数据
                                self.tool_metadata[prefixed_name] = {
                                    'original_name': tool['name'],
                                    'server_name': mcp_server['name'],
                                    'server_url': mcp_server['url']
                                }

                                self.tools.append(openai_tool)
                                logger.info(f"  - 添加工具: {prefixed_name} ({tool.get('description', '')})")

                except Exception as e:
                    logger.error(f"❌ Failed to get tools from MCP server {mcp_server['name']}: {e}")
                    continue

            logger.info(f"🛠️ 工具列表构建完成，总计 {len(self.tools)} 个工具")

        except Exception as e:
            logger.error(f"❌ buildTools failed: {e}")
            raise

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        return self.tools
