#!/usr/bin/env python3
"""
简单配置测试
"""
import asyncio
import os
import sys
from mcp_framework.client.simple import SimpleClient

# 设置测试环境变量
os.environ["TESTING_MODE"] = "true"

async def test_simple_config():
    """测试简单配置操作"""
    print("🧪 测试简单配置操作...")
    
    try:
        server_script = "expert_stream_server.py"
        alias = "test_simple_config"
        
        async with SimpleClient(server_script, alias=alias) as client:
            print(f"✅ 成功连接到 SimpleClient '{alias}'")
            
            # 测试获取配置
            print("📋 测试获取配置...")
            config = await client.config()
            print(f"✅ 获取配置成功: {len(config)} 项")
            
            # 测试设置单个配置项
            print("🔧 测试设置单个配置项...")
            test_key = "test_key"
            test_value = "test_value"
            
            try:
                success = await client.set(test_key, test_value)
                if success:
                    print(f"✅ 设置配置项成功: {test_key} = {test_value}")
                else:
                    print(f"⚠️  设置配置项返回 False: {test_key}")
            except Exception as e:
                print(f"❌ 设置配置项失败: {e}")
                return False
            
            # 测试获取单个配置项
            print("📖 测试获取单个配置项...")
            try:
                value = await client.get(test_key, "default")
                print(f"✅ 获取配置项成功: {test_key} = {value}")
                
                if value == test_value:
                    print("✅ 配置验证成功")
                    return True
                else:
                    print(f"❌ 配置验证失败: 期望 {test_value}, 实际 {value}")
                    return False
            except Exception as e:
                print(f"❌ 获取配置项失败: {e}")
                return False
                
    except Exception as e:
        print(f"❌ 简单配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await test_simple_config()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))