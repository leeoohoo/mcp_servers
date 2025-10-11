#!/usr/bin/env python3
"""
测试全新的别名是否工作正常，然后尝试复现test_no_config1的问题
"""

import asyncio
import sys
import os
from mcp_framework.client.simple import SimpleClient

async def test_alias(alias: str, description: str):
    """测试指定别名"""
    print(f"\n🧪 测试别名 '{alias}' ({description})...")
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        async with SimpleClient("expert_stream_server.py", alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
            init_time = asyncio.get_event_loop().time() - start_time
            print(f"✅ 别名 '{alias}' 初始化成功 (耗时: {init_time:.2f}s)")
            
            # 测试基本功能
            tools = await client.tools()
            config = await client.config()
            
            print(f"   🔧 工具数量: {len(tools)}")
            print(f"   📋 配置项数量: {len(config)}")
            
            return True
            
    except Exception as e:
        print(f"❌ 别名 '{alias}' 测试失败: {e}")
        return False

async def simulate_config_pollution(alias: str):
    """模拟配置污染，看是否能复现问题"""
    print(f"\n🔬 模拟配置污染别名 '{alias}'...")
    
    try:
        # 先正常连接
        async with SimpleClient("expert_stream_server.py", alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
            print(f"✅ 首次连接成功")
            
            # 设置一些复杂配置（类似test_dual_instance_config.py中的配置）
            complex_config = {
                "api_key": "sk-4jkOOy4t0qnY2t0rCQbEddyZaaMpYscsGZQ32Fa34GnIND8p",
                "model_name": "kimi-k2-0905-preview",
                "base_url": "https://api.openai.com/v1",
                "system_prompt": "你是一个专业的AI助手，能够提供准确、详细和有用的回答。",
                "mcp_servers": "[]",
                "stdio_mcp_servers": "",
                "mongodb_url": "",
                "history_limit": "10",
                "enable_history": False,
                "role": "development_assistant",
                "tool_description": "🤖 **Development Assistant** - Professional Development Task Executor",
                "parameter_description": "🎯 **Task Request Parameter**: Send task request to development assistant",
                "summary_interval": 5,
                "max_rounds": 25,
                "summary_instruction": "You are a professional conversation analysis and requirement prediction expert.",
                "summary_request": "Please intelligently analyze and generate a precise data retention report.",
                "summary_length_threshold": 30000,
                "custom_setting": "test_pollution_value",
                "log_level": "DEBUG",
                "max_connections": 50,
                "timeout": 60
            }
            
            print(f"🔧 设置复杂配置...")
            update_success = await client.update(**complex_config)
            print(f"   配置更新结果: {update_success}")
            
            # 验证配置
            final_config = await client.config()
            print(f"   最终配置项数量: {len(final_config)}")
            
        print(f"✅ 配置污染完成")
        return True
        
    except Exception as e:
        print(f"❌ 配置污染失败: {e}")
        return False

async def main():
    """主函数"""
    print(f"🚀 开始测试别名问题...")
    
    # 测试全新的别名
    fresh_alias = f"test_fresh_{int(asyncio.get_event_loop().time())}"
    success1 = await test_alias(fresh_alias, "全新别名")
    
    if success1:
        # 模拟配置污染
        pollution_success = await simulate_config_pollution(fresh_alias)
        
        if pollution_success:
            # 再次测试被污染的别名
            print(f"\n🔄 重新测试被污染的别名...")
            success2 = await test_alias(fresh_alias, "被污染的别名")
            
            if not success2:
                print(f"\n🎯 发现问题！配置污染导致别名无法正常工作")
            else:
                print(f"\n🤔 奇怪，配置污染后别名仍然正常工作")
    
    # 最后测试问题别名
    print(f"\n🎯 测试问题别名 test_no_config1...")
    await test_alias("test_no_config1", "问题别名")
    
    print(f"\n📊 测试完成")

if __name__ == "__main__":
    asyncio.run(main())