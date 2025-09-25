#!/usr/bin/env python3
"""
测试 ExpertService 初始化
"""
import asyncio
import os
import sys
import logging

# 设置测试环境变量
os.environ["TESTING_MODE"] = "true"

# 配置日志
logging.basicConfig(level=logging.DEBUG)

from expert_service import ExpertService

async def test_expert_service_init():
    """测试 ExpertService 初始化"""
    print("🧪 测试 ExpertService 初始化...")
    
    try:
        config_values = {
            "api_key": "sk-test-key-for-testing-purposes-only-1234567890",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-3.5-turbo",
            "system_prompt": "你是一个专业的AI助手",
            "mcp_servers": [],  # 空列表
            "mongodb_url": "",
            "history_limit": 10,
            "enable_history": True,
            "role": "",
            "summary_interval": 5,
            "max_rounds": 25,
            "summary_instruction": "",
            "summary_request": "",
            "summary_length_threshold": 30000
        }
        
        print("📝 配置参数:")
        for key, value in config_values.items():
            if key == "api_key":
                print(f"  {key}: {value[:10]}...")
            else:
                print(f"  {key}: {value}")
        
        print("\n🚀 开始初始化 ExpertService...")
        service = await ExpertService.from_config(config_values)
        
        print("✅ ExpertService 初始化成功!")
        print(f"  - API Key: {service.api_key[:10]}...")
        print(f"  - Model: {service.model_name}")
        print(f"  - MCP Servers: {len(service.mcp_servers)}")
        print(f"  - Tools: {len(service.mcp_tool_execute.tools)}")
        
        # 清理
        await service.shutdown()
        print("🧹 服务已关闭")
        
        return True
        
    except Exception as e:
        print(f"❌ ExpertService 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await test_expert_service_init()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))