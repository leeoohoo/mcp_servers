#!/usr/bin/env python3
"""
Terminal Manager MCP Server 主启动文件
"""

import sys
import os
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# 导入 MCP 框架启动器
from mcp_framework import run_server_main

# 导入我们的服务器
from terminal_manager_server.terminal_mcp_server import TerminalMCPServer

# 配置日志
logger = logging.getLogger("terminal_mcp_server")


def main():
    """主函数"""
    try:
        # 创建服务器实例
        server = TerminalMCPServer()
        
        # 使用 MCP 框架启动器启动服务器
        run_server_main(
            server_instance=server,
            server_name="Terminal MCP Server",
            default_port=8080,
            default_host="localhost",
            required_dependencies=["pymongo", "psutil", "aiohttp"]
        )
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()