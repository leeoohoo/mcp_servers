#!/usr/bin/env python3
"""
简单测试：专门测试获取 file-reader-server 的工具列表
"""

import asyncio
import logging
from mcp_tool_execute import McpToolExecute

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_simple_tools_list")

async def test_get_tools_list():
    """测试获取工具列表"""
    logger.info("🔧 开始测试获取 file-reader-server 工具列表...")
    
    # 配置 stdio MCP 服务器
    stdio_mcp_servers = [
        {
            "name": "file_reader_server",
            "command": "/Users/lilei/project/learn/mcp_servers/file_reader_server/dist/file-reader-server",
            "alias": "file_reader"
        }
    ]
    
    # 创建 McpToolExecute 实例
    mcp_executor = McpToolExecute(
        mcp_servers=[],  # 没有 HTTP 服务器
        stdio_mcp_servers=stdio_mcp_servers
    )
    
    try:
        # 初始化并构建工具列表
        await mcp_executor.init()
        
        # 获取工具列表
        tools = mcp_executor.tools
        tool_metadata = mcp_executor.tool_metadata
        
        logger.info(f"📋 获取到 {len(tools)} 个工具")
        
        if len(tools) > 0:
            logger.info("✅ 成功获取工具列表！")
            
            # 打印工具信息
            for i, tool in enumerate(tools, 1):
                tool_name = tool.get('function', {}).get('name', 'Unknown')
                description = tool.get('function', {}).get('description', 'No description')
                logger.info(f"  {i}. {tool_name}: {description}")
                
                # 打印工具元数据
                if tool_name in tool_metadata:
                    metadata = tool_metadata[tool_name]
                    logger.info(f"     - 服务器: {metadata.get('server_name', 'Unknown')}")
                    logger.info(f"     - 协议: {metadata.get('protocol', 'Unknown')}")
                    logger.info(f"     - 原始名称: {metadata.get('original_name', 'Unknown')}")
            
            return True
        else:
            logger.error("❌ 没有获取到任何工具")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False
    finally:
        # 清理资源
        await mcp_executor.close()

async def main():
    """主函数"""
    logger.info("🚀 开始简单工具列表测试...")
    
    success = await test_get_tools_list()
    
    if success:
        logger.info("🎉 测试成功完成！")
    else:
        logger.error("💥 测试失败！")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())