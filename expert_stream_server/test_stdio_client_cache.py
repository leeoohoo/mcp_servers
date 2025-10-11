#!/usr/bin/env python3
"""
测试 stdio 客户端缓存优化效果
"""

import asyncio
import time
import logging
from mcp_tool_execute import McpToolExecute

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StdioClientCacheTest")


async def test_stdio_client_cache_performance():
    """测试 stdio 客户端缓存的性能提升"""
    
    # 配置测试用的 stdio MCP 服务器
    stdio_mcp_servers = [
        {
            "name": "Expert Stream Server",
            "command": "python /Users/lilei/project/learn/mcp_servers/expert_stream_server/expert_stream_server.py",
            "alias": "test_cache_performance",
            "protocol": "stdio"
        }
    ]
    
    logger.info("🚀 开始测试 stdio 客户端缓存性能...")
    
    # 使用异步上下文管理器确保资源正确清理
    async with McpToolExecute([], stdio_mcp_servers) as executor:
        
        # 测试参数
        test_calls = 5
        tool_name = "query_expert_stream"
        test_arguments = {"question": "什么是Python？"}
        
        # 获取第一个 stdio 服务器的信息
        server_info = stdio_mcp_servers[0]
        server_name = server_info["name"]
        command = server_info["command"]
        alias = server_info["alias"]
        
        logger.info(f"📊 准备进行 {test_calls} 次连续调用测试...")
        logger.info(f"   服务器: {server_name}")
        logger.info(f"   工具: {tool_name}")
        logger.info(f"   别名: {alias}")
        
        # 记录每次调用的时间
        call_times = []
        total_start_time = time.time()
        
        for i in range(test_calls):
            logger.info(f"🔧 执行第 {i+1}/{test_calls} 次调用...")
            
            call_start_time = time.time()
            
            try:
                # 调用 stdio 工具
                result_chunks = []
                async for chunk in executor.call_stdio_tool_stream(
                    server_name, command, alias, tool_name, test_arguments
                ):
                    result_chunks.append(chunk)
                
                call_end_time = time.time()
                call_duration = call_end_time - call_start_time
                call_times.append(call_duration)
                
                total_content_length = sum(len(str(chunk)) for chunk in result_chunks)
                
                logger.info(f"   ✅ 第 {i+1} 次调用完成")
                logger.info(f"      耗时: {call_duration:.3f}s")
                logger.info(f"      响应长度: {total_content_length} 字符")
                logger.info(f"      响应块数: {len(result_chunks)}")
                
                if i == 0:
                    logger.info(f"      首次调用（包含客户端创建）")
                else:
                    logger.info(f"      缓存调用（复用客户端）")
                
            except Exception as e:
                logger.error(f"   ❌ 第 {i+1} 次调用失败: {e}")
                call_times.append(float('inf'))
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # 分析性能数据
        logger.info(f"\n📊 性能测试结果分析:")
        logger.info(f"=" * 60)
        
        if len(call_times) > 0 and all(t != float('inf') for t in call_times):
            first_call_time = call_times[0]
            cached_call_times = call_times[1:] if len(call_times) > 1 else []
            
            logger.info(f"   首次调用耗时: {first_call_time:.3f}s （包含客户端创建）")
            
            if cached_call_times:
                avg_cached_time = sum(cached_call_times) / len(cached_call_times)
                min_cached_time = min(cached_call_times)
                max_cached_time = max(cached_call_times)
                
                logger.info(f"   缓存调用平均耗时: {avg_cached_time:.3f}s")
                logger.info(f"   缓存调用最快: {min_cached_time:.3f}s")
                logger.info(f"   缓存调用最慢: {max_cached_time:.3f}s")
                
                # 计算性能提升
                if avg_cached_time > 0:
                    speedup = (first_call_time - avg_cached_time) / first_call_time * 100
                    logger.info(f"   性能提升: {speedup:.1f}% （缓存调用比首次调用快）")
                    
                    if speedup > 0:
                        logger.info(f"   ✅ 客户端缓存优化生效！")
                    else:
                        logger.info(f"   ⚠️ 缓存效果不明显，可能需要进一步优化")
            
            logger.info(f"   总耗时: {total_duration:.3f}s")
            logger.info(f"   平均每次调用: {sum(call_times)/len(call_times):.3f}s")
            
        else:
            logger.error(f"   ❌ 测试失败，无法分析性能数据")
        
        # 检查缓存状态
        cache_count = len(executor._stdio_clients)
        logger.info(f"\n🔍 缓存状态检查:")
        logger.info(f"   当前缓存的客户端数量: {cache_count}")
        
        if cache_count > 0:
            for cache_key in executor._stdio_clients.keys():
                logger.info(f"   缓存键: {cache_key}")
        
        logger.info(f"\n✅ 测试完成，客户端将自动清理...")


async def main():
    """主函数"""
    try:
        await test_stdio_client_cache_performance()
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())