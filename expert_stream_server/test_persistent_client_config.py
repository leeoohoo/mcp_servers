#!/usr/bin/env python3
"""
测试双实例配置管理 - 持久客户端版本
使用持久的 SimpleClient 实例，避免每次测试都重新创建连接
"""

import asyncio
import sys
import os
from mcp_framework.client.simple import SimpleClient


class PersistentClientTester:
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.clients = {}  # 存储持久的客户端实例
        self.config_dir = "/Users/lilei/project/config/test_mcp_server_config"
        
    async def setup_clients(self):
        """初始化持久的客户端实例"""
        print("🔧 初始化持久客户端实例...")
        
        aliases = ["test_no_config", "test_with_config"]
        
        for alias in aliases:
            try:
                print(f"   创建客户端实例: {alias}")
                client = SimpleClient(
                    self.server_script, 
                    alias=alias, 
                    config_dir=self.config_dir
                )
                await client.__aenter__()  # 手动进入异步上下文
                self.clients[alias] = client
                print(f"   ✅ 客户端 '{alias}' 创建成功")
            except Exception as e:
                print(f"   ❌ 客户端 '{alias}' 创建失败: {e}")
                raise
        
        print(f"✅ 所有客户端实例创建完成: {list(self.clients.keys())}")
    
    async def cleanup_clients(self):
        """清理所有客户端实例"""
        print("🧹 清理客户端实例...")
        
        for alias, client in self.clients.items():
            try:
                await client.__aexit__(None, None, None)  # 手动退出异步上下文
                print(f"   ✅ 客户端 '{alias}' 清理完成")
            except Exception as e:
                print(f"   ⚠️  客户端 '{alias}' 清理时出错: {e}")
        
        self.clients.clear()
        print("✅ 所有客户端实例已清理")
    
    def get_client(self, alias: str):
        """获取指定别名的客户端实例"""
        if alias not in self.clients:
            raise ValueError(f"客户端实例 '{alias}' 不存在")
        return self.clients[alias]
    
    async def test_instance_with_alias(self, alias: str):
        """测试指定别名的实例 - 使用持久客户端"""
        print(f"\n🧪 测试实例 '{alias}' (持久客户端)...")
        
        try:
            client = self.get_client(alias)
            print(f"✅ 使用现有客户端实例 '{alias}'")
            
            # 获取工具列表
            tools = await client.tools()
            print(f"   可用工具数量: {len(tools)}")
            
            # 验证 query_expert_stream 工具存在
            has_expert_tool = await client.has_tool("query_expert_stream")
            if not has_expert_tool:
                print(f"❌ 实例 '{alias}' 缺少 query_expert_stream 工具")
                return False
            
            print(f"✅ 实例 '{alias}' 包含 query_expert_stream 工具")
            
            # 测试专家查询
            print(f"   测试专家查询...")
            
            try:
                result = await client.call("query_expert_stream",
                    question=f"这是来自持久实例 {alias} 的测试查询，请简单回复确认收到。"
                )
                print(f"   ✅ 专家查询成功")
                response_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                print(f"   响应预览: {response_preview}")
            except Exception as e:
                print(f"   ❌ 专家查询失败: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 测试实例 '{alias}' 时发生错误: {e}")
            return False

    async def test_concurrent_instances(self):
        """测试并发访问不同实例 - 使用持久客户端"""
        print(f"\n🧪 测试并发访问不同实例 (持久客户端)...")
        
        async def test_instance_concurrent(alias: str):
            """并发测试单个实例"""
            try:
                client = self.get_client(alias)
                # 发送测试查询
                result = await client.call("query_expert_stream",
                    question=f"并发测试 - 持久实例 {alias}，请回复确认。时间戳: {asyncio.get_event_loop().time()}"
                )
                
                return True, alias, result
            except Exception as e:
                return False, alias, str(e)
        
        try:
            # 并发测试两个实例
            tasks = [
                test_instance_concurrent("test_no_config"),
                test_instance_concurrent("test_with_config")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            for result in results:
                if isinstance(result, Exception):
                    print(f"   ❌ 并发测试异常: {result}")
                else:
                    success, alias, content = result
                    if success:
                        print(f"   ✅ 实例 '{alias}' 并发测试成功")
                        success_count += 1
                    else:
                        print(f"   ❌ 实例 '{alias}' 并发测试失败: {content}")
            
            return success_count == len(tasks)
            
        except Exception as e:
            print(f"❌ 并发测试失败: {e}")
            return False

    async def test_instance_isolation(self):
        """测试实例隔离性 - 使用持久客户端"""
        print(f"\n🧪 测试实例隔离性 (持久客户端)...")
        
        try:
            # 在第一个实例中设置配置
            client1 = self.get_client("test_no_config")
            await client1.set("test_isolation_1", "持久实例1的配置值")
            print("   ✅ 持久实例1设置配置成功")
            
            # 在第二个实例中设置不同的配置
            client2 = self.get_client("test_with_config")
            await client2.set("test_isolation_2", "持久实例2的配置值")
            print("   ✅ 持久实例2设置配置成功")
            
            # 验证每个实例都能访问自己的配置
            value1 = await client1.get("test_isolation_1", "未设置")
            if value1 == "持久实例1的配置值":
                print("   ✅ 持久实例1能访问自己的配置")
            else:
                print(f"   ❌ 持久实例1配置验证失败: {value1}")
                return False
            
            value2 = await client2.get("test_isolation_2", "未设置")
            if value2 == "持久实例2的配置值":
                print("   ✅ 持久实例2能访问自己的配置")
            else:
                print(f"   ❌ 持久实例2配置验证失败: {value2}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 实例隔离测试失败: {e}")
            return False

    async def test_configuration_differences(self):
        """测试不同配置的差异 - 使用持久客户端"""
        print(f"\n🧪 测试配置差异 (持久客户端)...")
        
        try:
            configs = {}
            
            # 获取两个实例的工具信息
            for alias in ["test_no_config", "test_with_config"]:
                client = self.get_client(alias)
                tools = await client.tools()
                tool_info = await client.tool_info("query_expert_stream") if await client.has_tool("query_expert_stream") else None
                
                configs[alias] = {
                    "tool_count": len(tools),
                    "has_expert_tool": tool_info is not None,
                    "tool_description": tool_info.description if tool_info else None
                }
                
                print(f"   实例 '{alias}': {configs[alias]['tool_count']} 个工具")
            
            # 比较配置
            config1 = configs["test_no_config"]
            config2 = configs["test_with_config"]
            
            print(f"   配置比较:")
            print(f"     test_no_config: {config1['tool_count']} 工具, query_expert_stream: {config1['has_expert_tool']}")
            print(f"     test_with_config: {config2['tool_count']} 工具, query_expert_stream: {config2['has_expert_tool']}")
            
            # 验证两个实例都有基本功能
            if config1['has_expert_tool'] and config2['has_expert_tool']:
                print("   ✅ 两个实例都支持 query_expert_stream 工具")
                return True
            else:
                print("   ❌ 某些实例缺少必要工具")
                return False
                
        except Exception as e:
            print(f"❌ 配置差异测试失败: {e}")
            return False

    async def test_config_management(self):
        """测试配置管理功能 - 使用持久客户端"""
        print(f"\n🧪 测试配置管理功能 (持久客户端)...")
        
        try:
            # 为两个实例设置不同的配置
            configs_to_test = {
                "test_no_config": {
                    "server_name": "ExpertStreamServer",
                    "log_level": "DEBUG",
                    "max_connections": 50,
                    "timeout": 60,
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
                    "custom_setting": "persistent_expert_server1_value"
                },
                "test_with_config": {
                    "server_name": "ExpertStreamServer", 
                    "log_level": "WARNING",
                    "max_connections": 20,
                    "timeout": 45,
                    "api_key": "sk-test-key-for-testing-purposes-only-0987654321",
                    "model_name": "gpt-4",
                    "base_url": "https://api.openai.com/v1",
                    "system_prompt": "你是一个专业的AI助手，能够通过工具帮用查询当前目录下的内容。",
                    "mcp_servers": "[]",
                    "stdio_mcp_servers": "file-writer:../file_write_server/file_write_server.py--test_no_config",
                    "mongodb_url": "mongodb://localhost:27017/chat_history",
                    "history_limit": "20",
                    "enable_history": True,
                    "role": "code_reviewer",
                    "tool_description": "🔧 **Code Review Assistant** - Advanced Code Analysis Tool",
                    "parameter_description": "📝 **Code Analysis Parameter**: Submit code for professional review",
                    "summary_interval": 3,
                    "max_rounds": 15,
                    "summary_instruction": "You are an expert code analyzer. Focus on critical code patterns and potential issues.",
                    "summary_request": "Generate a comprehensive code analysis summary with actionable insights.",
                    "summary_length_threshold": 20000,
                    "custom_setting": "persistent_expert_server2_value"
                }
            }
            
            success_count = 0
            
            for alias, config_data in configs_to_test.items():
                print(f"\n   测试实例 '{alias}' 的配置管理 (持久客户端)...")
                
                try:
                    client = self.get_client(alias)
                    print(f"   ✅ 使用持久客户端 '{alias}'")
                    
                    # 获取当前配置
                    current_config = await client.config()
                    print(f"   📋 当前配置: {len(current_config)} 项")
                    
                    # 批量更新配置
                    print(f"   🔧 批量更新配置...")
                    update_success = await client.update(**config_data)
                    if update_success:
                        print(f"   ✅ 配置批量更新成功")
                    else:
                        print(f"   ⚠️  配置批量更新返回 False")
                    
                    # 逐个设置关键配置项
                    key_configs = [
                        ("custom_setting", config_data["custom_setting"]),
                        ("model_name", config_data["model_name"]),
                        ("log_level", config_data["log_level"])
                    ]
                    
                    for key, value in key_configs:
                        set_success = await client.set(key, value)
                        if set_success:
                            print(f"   ✅ 设置 {key} = {value}")
                        else:
                            print(f"   ⚠️  设置 {key} 失败")
                    
                    # 验证配置更新
                    updated_config = await client.config()
                    print(f"   🔍 验证配置: {len(updated_config)} 项")
                    
                    # 检查关键配置项
                    expected_setting = config_data["custom_setting"]
                    actual_setting = await client.get("custom_setting", "未设置")
                    
                    if actual_setting == expected_setting:
                        print(f"   ✅ 配置验证成功: custom_setting = {actual_setting}")
                        success_count += 1
                    else:
                        print(f"   ❌ 配置验证失败: 期望 {expected_setting}, 实际 {actual_setting}")
                    
                    # 显示其他配置项
                    model_name = await client.get("model_name", "未设置")
                    log_level = await client.get("log_level", "未设置")
                    print(f"   📊 其他配置: model_name={model_name}, log_level={log_level}")
                        
                except Exception as e:
                    print(f"   ❌ 实例 '{alias}' 配置管理失败: {e}")
            
            return success_count == len(configs_to_test)
            
        except Exception as e:
            print(f"❌ 配置管理测试失败: {e}")
            return False

    async def test_performance_comparison(self):
        """测试性能对比 - 持久客户端 vs 临时客户端"""
        print(f"\n🧪 测试性能对比...")
        
        import time
        
        # 测试持久客户端性能
        print("   测试持久客户端性能...")
        start_time = time.time()
        
        for i in range(5):
            client = self.get_client("test_no_config")
            tools = await client.tools()
            
        persistent_time = time.time() - start_time
        print(f"   持久客户端 5 次调用耗时: {persistent_time:.3f}s")
        
        # 测试临时客户端性能
        print("   测试临时客户端性能...")
        start_time = time.time()
        
        for i in range(5):
            async with SimpleClient(self.server_script, alias="test_no_config", config_dir=self.config_dir) as client:
                tools = await client.tools()
                
        temporary_time = time.time() - start_time
        print(f"   临时客户端 5 次调用耗时: {temporary_time:.3f}s")
        
        # 性能对比
        improvement = ((temporary_time - persistent_time) / temporary_time) * 100
        print(f"   📊 性能提升: {improvement:.1f}% (持久客户端更快)")
        
        return persistent_time < temporary_time


async def main():
    """主测试函数"""
    # 设置测试环境变量
    import os
    os.environ["TESTING_MODE"] = "true"
    
    print("🚀 ExpertStreamServer 持久客户端测试")
    print("=" * 60)
    
    # 创建测试器
    tester = PersistentClientTester("./dist/expert-stream-server")
    
    try:
        # 初始化持久客户端
        await tester.setup_clients()
        
        # 执行所有测试
        tests = [
            ("无配置实例测试", lambda: tester.test_instance_with_alias("test_no_config")),
            ("有配置实例测试", lambda: tester.test_instance_with_alias("test_with_config")),
            ("并发访问测试", tester.test_concurrent_instances),
            ("实例隔离测试", tester.test_instance_isolation),
            ("配置差异测试", tester.test_configuration_differences),
            ("配置管理测试", tester.test_config_management),
            ("性能对比测试", tester.test_performance_comparison),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n🎯 {test_name}")
            try:
                success = await test_func()
                results.append((test_name, success))
                if success:
                    print(f"✅ {test_name} 通过")
                else:
                    print(f"❌ {test_name} 失败")
            except Exception as e:
                print(f"❌ {test_name} 异常: {e}")
                results.append((test_name, False))
        
        # 输出测试总结
        print(f"\n📊 测试总结")
        print("=" * 60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        print(f"\n总体结果: {passed}/{total} 测试通过")
        
        if passed == total:
            print("🎉 所有测试都通过了！持久客户端工作正常。")
            return 0
        else:
            print("⚠️  部分测试失败，请检查配置和服务器状态。")
            return 1
            
    except Exception as e:
        print(f"❌ 测试过程中发生严重错误: {e}")
        return 1
    finally:
        # 清理资源
        await tester.cleanup_clients()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))