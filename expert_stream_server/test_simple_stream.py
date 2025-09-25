#!/usr/bin/env python3
"""
简单的流式调用测试
"""

import asyncio
import json
import logging
from mcp_framework.client.simple import SimpleClient

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_simple_stream():
    """测试简单的流式调用"""
    print("🧪 测试简单流式调用...")
    
    try:
        async with SimpleClient("expert_stream_server.py", alias="test_no_config") as client:
            print("✅ 成功连接到服务器")
            
            # 检查工具是否存在
            has_tool = await client.has_tool("query_expert_stream")
            print(f"工具存在: {has_tool}")
            
            if has_tool:
                print("\n开始流式调用...")
                print("问题: 什么是Python?")
                print("回答: ", end="", flush=True)
                
                chunk_count = 0
                total_content = ""
                error_chunks = []
                
                try:
                    async for chunk in client.call_stream("query_expert_stream", question="什么是Python?"):
                        chunk_count += 1
                        logger.debug(f"收到第 {chunk_count} 个块: {repr(chunk)}")
                        print(f"\n[块{chunk_count}] 原始数据: {repr(chunk)}")
                        
                        # 尝试解析JSON
                        try:
                            chunk_data = json.loads(chunk)
                            if isinstance(chunk_data, dict):
                                chunk_type = chunk_data.get("type", "unknown")
                                chunk_content = chunk_data.get("data", "")
                                print(f"[块{chunk_count}] 类型: {chunk_type}, 内容: {repr(chunk_content)}")
                                
                                if chunk_type == "content":
                                    print(chunk_content, end="", flush=True)
                                    total_content += chunk_content
                                elif chunk_type == "error":
                                    print(f"\n❌ 错误: {chunk_content}")
                                    error_chunks.append(chunk_content)
                                else:
                                    print(f"[块{chunk_count}] 其他类型: {chunk_type}")
                            else:
                                print(f"[块{chunk_count}] 非字典数据: {chunk_data}")
                        except json.JSONDecodeError:
                            # 如果不是JSON，直接输出
                            print(f"[块{chunk_count}] 非JSON数据: {chunk}")
                            total_content += chunk
                        
                except Exception as stream_error:
                    print(f"\n❌ 流式调用错误: {stream_error}")
                    import traceback
                    traceback.print_exc()
                
                print(f"\n\n✅ 流式调用完成")
                print(f"总块数: {chunk_count}")
                print(f"总内容长度: {len(total_content)}")
                print(f"错误块数: {len(error_chunks)}")
                
                if error_chunks:
                    print("错误信息:")
                    for i, error in enumerate(error_chunks):
                        print(f"  错误 {i+1}: {error}")
                
                if total_content:
                    print(f"内容预览: {total_content[:200]}...")
                else:
                    print("⚠️ 没有接收到任何内容")
                    
                    # 如果没有内容，尝试一个更简单的问题
                    print("\n🔄 尝试更简单的问题...")
                    chunk_count2 = 0
                    async for chunk in client.call_stream("query_expert_stream", question="你好"):
                        chunk_count2 += 1
                        print(f"简单问题块 {chunk_count2}: {repr(chunk)}")
                        if chunk_count2 >= 3:  # 只看前3个块
                            break
                    
                    if chunk_count2 == 0:
                        print("⚠️ 简单问题也没有返回任何块")
            else:
                print("❌ 工具不存在")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_stream())