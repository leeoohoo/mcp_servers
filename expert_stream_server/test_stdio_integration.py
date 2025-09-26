#!/usr/bin/env python3
"""
测试 stdio MCP 服务器集成功能
"""

import asyncio
import logging
import os
import sys
from expert_service import ExpertService, parse_stdio_mcp_servers_config
from mcp_tool_execute import McpToolExecute

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestStdioIntegration")

async def test_stdio_tool_execution():
    """测试 stdio 工具执行功能"""
    logger.info("🧪 开始测试 stdio 工具执行功能")
    
    try:
        # 配置 stdio MCP 服务器
        # 使用相对路径指向 file_write_server
        file_write_server_path = "expert_stream_server.py"
        stdio_config = f"file-writer:{file_write_server_path}--file-mgr"
        
        logger.info(f"📝 使用 stdio 配置: {stdio_config}")
        
        # 解析配置
        stdio_servers = parse_stdio_mcp_servers_config(stdio_config)
        logger.info(f"📋 解析后的 stdio 服务器配置: {stdio_servers}")
        
        # 创建 McpToolExecute 实例
        mcp_executor = McpToolExecute(
            mcp_servers=[],  # 没有 HTTP 服务器
            stdio_mcp_servers=stdio_servers
        )
        
        # 初始化
        await mcp_executor.init()
        
        # 构建工具列表
        logger.info("🔧 开始构建工具列表...")
        await mcp_executor.build_tools()
        
        # 获取工具列表
        tools = mcp_executor.get_tools()
        logger.info(f"🛠️ 获取到 {len(tools)} 个工具:")
        
        for tool in tools:
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description']
            logger.info(f"  - {tool_name}: {tool_desc}")
        
        # 测试工具调用 - 使用 modify_file 工具
        if tools:
            # 找到 modify_file 工具
            modify_tool = None
            for tool in tools:
                if 'modify_file' in tool['function']['name']:
                    modify_tool = tool
                    break
            
            if modify_tool:
                tool_name = modify_tool['function']['name']
                logger.info(f"🔍 测试工具调用: {tool_name}")
                
                # 准备工具调用参数 - 创建一个测试文件
                tool_calls = [{
                    'id': 'test_call_1',
                    'type': 'function',
                    'function': {
                        'name': tool_name,
                        'arguments': '{"file_path": "test_stdio.txt", "action": "create", "content": "Hello from stdio test!"}'
                    }
                }]
                
                # 执行工具调用
                logger.info("🚀 开始执行工具调用...")
                results = []
                async for result in mcp_executor.execute_stream(tool_calls):
                    results.append(result)
                    logger.info(f"📤 工具调用结果: {result}")
                
                if results:
                    logger.info("✅ stdio 工具调用测试成功！")
                    return True
                else:
                    logger.error("❌ 没有收到工具调用结果")
                    return False
            else:
                logger.warning("⚠️ 没有找到 modify_file 工具")
                return False
        else:
            logger.error("❌ 没有获取到任何工具")
            return False
            
    except Exception as e:
        logger.error(f"❌ stdio 工具执行测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_expert_service_with_stdio():
    """测试 ExpertService 与 stdio 服务器的集成"""
    logger.info("🧪 开始测试 ExpertService 与 stdio 服务器集成")
    
    try:
        # 配置参数
        config_values = {
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-3.5-turbo",
            "system_prompt": "你是一个测试助手",
            "mcp_servers": "",  # 没有 HTTP 服务器
            "stdio_mcp_servers": f"file-writer:../file_write_server/file_write_server.py--file-mgr",
            "mongodb_url": "",
            "enable_history": False
        }
        
        # 创建 ExpertService 实例
        logger.info("🏗️ 创建 ExpertService 实例...")
        service = await ExpertService.from_config(config_values)
        
        # 检查工具是否正确加载
        tools = service.mcp_tool_execute.get_tools()
        logger.info(f"🛠️ ExpertService 加载了 {len(tools)} 个工具")
        
        if tools:
            logger.info("✅ ExpertService 与 stdio 服务器集成测试成功！")
            return True
        else:
            logger.error("❌ ExpertService 没有加载任何工具")
            return False
            
    except Exception as e:
        logger.error(f"❌ ExpertService 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    logger.info("🚀 开始 stdio 集成测试")
    
    # 检查 file_write_server 是否存在
    file_write_server_path = "../file_write_server/file_write_server.py"
    if not os.path.exists(file_write_server_path):
        logger.error(f"❌ 找不到测试用的 MCP 服务器: {file_write_server_path}")
        return
    
    logger.info(f"✅ 找到测试用的 MCP 服务器: {file_write_server_path}")
    
    # 运行测试
    test_results = []
    
    # 测试1: stdio 工具执行
    logger.info("\n" + "="*50)
    logger.info("测试1: stdio 工具执行功能")
    logger.info("="*50)
    result1 = await test_stdio_tool_execution()
    test_results.append(("stdio 工具执行", result1))
    
    # 测试2: ExpertService 集成
    logger.info("\n" + "="*50)
    logger.info("测试2: ExpertService 与 stdio 服务器集成")
    logger.info("="*50)
    result2 = await test_expert_service_with_stdio()
    test_results.append(("ExpertService 集成", result2))
    
    # 输出测试结果
    logger.info("\n" + "="*50)
    logger.info("测试结果汇总")
    logger.info("="*50)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 所有 stdio 集成测试通过！")
    else:
        logger.error("💥 部分测试失败，请检查日志")

if __name__ == "__main__":
    asyncio.run(main())