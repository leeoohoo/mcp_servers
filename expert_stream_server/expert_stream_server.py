

import asyncio
import logging
import sys

from expert_MCP_server_annotated import ExpertMCPServerAnnotated

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

# 导入MCP框架
from mcp_framework import (
    run_server_main,
)

# 配置日志
logger = logging.getLogger("expert_server")




def main():
    """主函数"""
    # 创建服务器实例
    server = ExpertMCPServerAnnotated()
    
    # 使用新的启动器
    run_server_main(
        server_instance=server,
        server_name="Expert Stream Server",
        default_port=8083,
        default_host="localhost",
        required_dependencies=["openai", "aiohttp"]
    )


if __name__ == "__main__":
    main()