#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from mcp_tool_execute import McpToolExecute
from expert_service import parse_stdio_mcp_servers_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestToolCallFix")

async def test_tool_call_fix():
    """测试修复后的工具调用功能"""
    try:
        logger.info("🧪 开始测试修复后的工具调用功能...")
        
        # 配置 stdio MCP 服务器
        stdio_config = "file-writer:../file_write_server/file_write_server.py--file-mgr"
        stdio_servers = parse_stdio_mcp_servers_config(stdio_config)
        
        logger.info(f"📋 解析到的stdio服务器配置: {stdio_servers}")
        
        # 创建 McpToolExecute 实例
        mcp_executor = McpToolExecute(
            mcp_servers=[],  # 没有HTTP服务器
            stdio_mcp_servers=stdio_servers
        )
        
        # 构建工具列表
        await mcp_executor.build_tools()
        tools = mcp_executor.get_tools()
        
        logger.info(f"🛠️ 构建的工具列表: {len(tools)} 个工具")
        for tool in tools:
            logger.info(f"  - {tool['function']['name']}: {tool['function']['description']}")
        
        # 测试用户提到的工具调用
        tool_calls = [{
            'function': {
                'arguments': '{"action": "view", "file_path": "."}', 
                'name': 'file-writer_modify_file'
            }, 
            'id': 'file-writer_modify_file:0', 
            'type': 'function'
        }]
        
        logger.info(f"🔧 开始执行工具调用: {tool_calls}")
        
        # 执行工具调用
        results = []
        async for result in mcp_executor.execute_stream(tool_calls):
            results.append(result)
            logger.info(f"📤 收到结果: {result.get('name', 'unknown')} - {len(result.get('content', ''))} 字符")
        
        logger.info(f"✅ 工具调用执行完成，共收到 {len(results)} 个结果")
        
        # 显示最终结果
        for i, result in enumerate(results):
            if result.get('is_final'):
                logger.info(f"📋 最终结果 {i+1}: {result.get('content', '')[:200]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tool_call_fix())
    if success:
        print("🎉 测试成功！")
    else:
        print("❌ 测试失败！")