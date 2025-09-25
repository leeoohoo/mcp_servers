#!/usr/bin/env python3
"""
测试双实例配置管理
使用新的 SimpleClient 验证不同配置的 FileWriteServer 实例能够正确工作
"""

import asyncio
import sys
import os
from mcp_framework.client.simple import SimpleClient


class DualInstanceTester:
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.test_file_1 = "test_instance_1.txt"
        self.test_file_2 = "test_instance_2.txt"
    
    async def test_instance_with_alias(self, alias: str, test_file: str):
        """测试指定别名的实例"""
        print(f"\n🧪 测试实例 '{alias}'...")
        
        try:
            async with SimpleClient(self.server_script, alias=alias) as client:
                print(f"✅ 成功连接到实例 '{alias}'")
                
                # 获取工具列表
                tools = await client.tools()
                print(f"   可用工具数量: {len(tools)}")
                
                # 验证 modify_file 工具存在
                has_modify_tool = await client.has_tool("modify_file")
                if not has_modify_tool:
                    print(f"❌ 实例 '{alias}' 缺少 modify_file 工具")
                    return False
                
                print(f"✅ 实例 '{alias}' 包含 modify_file 工具")
                
                # 测试文件操作
                print(f"   测试文件操作...")
                
                # 创建测试文件
                try:
                    result = await client.call("modify_file",
                        file_path=test_file,
                        action="create",
                        content=f"这是实例 {alias} 创建的文件\n第二行内容\n第三行内容"
                    )
                    print(f"   ✅ 创建文件成功")
                except Exception as e:
                    print(f"   ❌ 创建文件失败: {e}")
                    return False
                
                # 查看文件内容
                try:
                    result = await client.call("modify_file",
                        file_path=test_file,
                        action="view"
                    )
                    print(f"   ✅ 查看文件成功")
                    content_preview = str(result)[:50] + "..." if len(str(result)) > 50 else str(result)
                    print(f"   文件内容预览: {content_preview}")
                except Exception as e:
                    print(f"   ❌ 查看文件失败: {e}")
                    return False
                
                # 编辑文件
                try:
                    result = await client.call("modify_file",
                        file_path=test_file,
                        action="edit",
                        line="2",
                        content=f"由实例 {alias} 修改的第二行"
                    )
                    print(f"   ✅ 编辑文件成功")
                except Exception as e:
                    print(f"   ❌ 编辑文件失败: {e}")
                    return False
                
                return True
                
        except Exception as e:
            print(f"❌ 测试实例 '{alias}' 时发生错误: {e}")
            return False

    async def test_concurrent_instances(self):
        """测试并发访问不同实例"""
        print(f"\n🧪 测试并发访问不同实例...")
        
        async def test_instance_concurrent(alias: str, test_file: str):
            """并发测试单个实例"""
            try:
                async with SimpleClient(self.server_script, alias=alias) as client:
                    # 创建文件
                    await client.call("modify_file",
                        file_path=test_file,
                        action="create",
                        content=f"并发测试 - 实例 {alias}\n时间戳: {asyncio.get_event_loop().time()}"
                    )
                    
                    # 查看文件
                    result = await client.call("modify_file",
                        file_path=test_file,
                        action="view"
                    )
                    
                    return True, alias, result
            except Exception as e:
                return False, alias, str(e)
        
        try:
            # 并发测试两个实例
            tasks = [
                test_instance_concurrent("test_no_config", self.test_file_1),
                test_instance_concurrent("test_with_config", self.test_file_2)
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
        """测试实例隔离性"""
        print(f"\n🧪 测试实例隔离性...")
        
        try:
            # 在第一个实例中创建文件
            async with SimpleClient(self.server_script, alias="test_no_config") as client1:
                await client1.call("modify_file",
                    file_path="isolation_test_1.txt",
                    action="create",
                    content="实例1创建的文件"
                )
                print("   ✅ 实例1创建文件成功")
            
            # 在第二个实例中创建不同的文件
            async with SimpleClient(self.server_script, alias="test_with_config") as client2:
                await client2.call("modify_file",
                    file_path="isolation_test_2.txt",
                    action="create",
                    content="实例2创建的文件"
                )
                print("   ✅ 实例2创建文件成功")
            
            # 验证每个实例都能访问自己创建的文件
            async with SimpleClient(self.server_script, alias="test_no_config") as client1:
                result1 = await client1.call("modify_file",
                    file_path="isolation_test_1.txt",
                    action="view"
                )
                print("   ✅ 实例1能访问自己的文件")
            
            async with SimpleClient(self.server_script, alias="test_with_config") as client2:
                result2 = await client2.call("modify_file",
                    file_path="isolation_test_2.txt",
                    action="view"
                )
                print("   ✅ 实例2能访问自己的文件")
            
            # 清理隔离测试文件
            try:
                if os.path.exists("isolation_test_1.txt"):
                    os.remove("isolation_test_1.txt")
                if os.path.exists("isolation_test_2.txt"):
                    os.remove("isolation_test_2.txt")
                print("   🧹 清理隔离测试文件")
            except Exception as e:
                print(f"   ⚠️  清理隔离测试文件失败: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 实例隔离测试失败: {e}")
            return False

    async def test_configuration_differences(self):
        """测试不同配置的差异"""
        print(f"\n🧪 测试配置差异...")
        
        try:
            configs = {}
            
            # 获取两个实例的工具信息
            for alias in ["test_no_config", "test_with_config"]:
                async with SimpleClient(self.server_script, alias=alias) as client:
                    tools = await client.tools()
                    tool_info = await client.tool_info("modify_file") if await client.has_tool("modify_file") else None
                    
                    configs[alias] = {
                        "tool_count": len(tools),
                        "has_modify_file": tool_info is not None,
                        "tool_description": tool_info.description if tool_info else None
                    }
                    
                    print(f"   实例 '{alias}': {configs[alias]['tool_count']} 个工具")
            
            # 比较配置
            config1 = configs["test_no_config"]
            config2 = configs["test_with_config"]
            
            print(f"   配置比较:")
            print(f"     test_no_config: {config1['tool_count']} 工具, modify_file: {config1['has_modify_file']}")
            print(f"     test_with_config: {config2['tool_count']} 工具, modify_file: {config2['has_modify_file']}")
            
            # 验证两个实例都有基本功能
            if config1['has_modify_file'] and config2['has_modify_file']:
                print("   ✅ 两个实例都支持 modify_file 工具")
                return True
            else:
                print("   ❌ 某些实例缺少必要工具")
                return False
                
        except Exception as e:
            print(f"❌ 配置差异测试失败: {e}")
            return False

    async def test_config_management(self):
        """测试配置管理功能 - 使用 SimpleClient"""
        print(f"\n🧪 测试配置管理功能（SimpleClient）...")
        
        try:
            # 为两个实例设置不同的配置
            configs_to_test = {
                "test_no_config": {
                    "server_name": "FileWriteServer",
                    "log_level": "DEBUG",
                    "max_connections": 50,
                    "timeout": 60,
                    "default_dir": "/tmp/fileserver1",
                    "project_root": "/Users/lilei/project/work/zj/user_manager",
                    "max_file_size": 51,
                    "enable_hidden_files": True,
                    "custom_setting": "fileserver1_value"
                },
                "test_with_config": {
                    "server_name": "FileWriteServer", 
                    "log_level": "WARNING",
                    "max_connections": 20,
                    "timeout": 45,
                    "default_dir": "/tmp/fileserver2",
                    "project_root": "/tmp/fileserver2_workspace",
                    "max_file_size": 15,
                    "enable_hidden_files": False,
                    "custom_setting": "fileserver2_value"
                }
            }
            
            success_count = 0
            
            for alias, config_data in configs_to_test.items():
                print(f"\n   测试实例 '{alias}' 的配置管理...")
                
                try:
                    # 使用 SimpleClient 进行配置管理
                    async with SimpleClient(self.server_script, alias=alias) as client:
                        print(f"   ✅ 成功连接到 SimpleClient '{alias}'")
                        
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
                        
                        # 逐个设置关键配置项（确保设置成功）
                        key_configs = [
                            ("custom_setting", config_data["custom_setting"]),
                            ("max_file_size", config_data["max_file_size"]),
                            ("enable_hidden_files", config_data["enable_hidden_files"])
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
                        max_file_size = await client.get("max_file_size", "未设置")
                        enable_hidden = await client.get("enable_hidden_files", "未设置")
                        print(f"   📊 其他配置: max_file_size={max_file_size}, enable_hidden_files={enable_hidden}")
                            
                except Exception as e:
                    print(f"   ❌ 实例 '{alias}' 配置管理失败: {e}")
            
            return success_count == len(configs_to_test)
            
        except Exception as e:
            print(f"❌ 配置管理测试失败: {e}")
            return False

    async def test_config_with_simple_client(self):
        """测试 SimpleClient 的配置功能"""
        print(f"\n🧪 测试 SimpleClient 配置功能...")
        
        try:
            success_count = 0
            
            for alias in ["test_no_config", "test_with_config"]:
                print(f"\n   测试实例 '{alias}' 的 SimpleClient 配置...")
                
                try:
                    async with SimpleClient(self.server_script, alias=alias) as client:
                        # 获取配置
                        config = await client.config()
                        print(f"   📋 获取配置成功: {len(config)} 项")
                        
                        # 设置单个配置项
                        test_key = f"test_key_{alias}"
                        test_value = f"test_value_{alias}"
                        await client.set(test_key, test_value)
                        print(f"   ✅ 设置配置项成功: {test_key} = {test_value}")
                        
                        # 批量更新配置
                        batch_config = {
                            "batch_test_1": f"batch_value_1_{alias}",
                            "batch_test_2": f"batch_value_2_{alias}",
                            "enable_test_mode": True
                        }
                        await client.update(**batch_config)
                        print(f"   ✅ 批量更新配置成功: {len(batch_config)} 项")
                        
                        # 验证配置
                        updated_config = await client.config()
                        if test_key in updated_config and updated_config[test_key] == test_value:
                            print(f"   ✅ 配置验证成功")
                            success_count += 1
                        else:
                            print(f"   ❌ 配置验证失败")
                            
                except Exception as e:
                    print(f"   ❌ 实例 '{alias}' SimpleClient 配置测试失败: {e}")
            
            return success_count == 2
            
        except Exception as e:
            print(f"❌ SimpleClient 配置测试失败: {e}")
            return False

    def cleanup_test_files(self):
        """清理测试文件"""
        test_files = [self.test_file_1, self.test_file_2, "isolation_test_1.txt", "isolation_test_2.txt"]
        
        for test_file in test_files:
            try:
                if os.path.exists(test_file):
                    os.remove(test_file)
                    print(f"🧹 清理测试文件: {test_file}")
            except Exception as e:
                print(f"⚠️  清理测试文件 {test_file} 失败: {e}")


async def main():
    """主测试函数"""
    print("🚀 FileWriteServer 双实例配置测试")
    print("=" * 60)
    
    # 创建测试器
    tester = DualInstanceTester("/Users/lilei/project/learn/mcp_servers/file_reader_server/file_reader_server.py")
    
    try:
        # 清理可能存在的测试文件
        tester.cleanup_test_files()
        
        # 测试第一个实例
        print("\n🎯 测试 1: 无配置实例 (test_no_config)")
        success1 = await tester.test_instance_with_alias("test_no_config", tester.test_file_1)
        
        # 测试第二个实例
        print("\n🎯 测试 2: 有配置实例 (test_with_config)")
        success2 = await tester.test_instance_with_alias("test_with_config", tester.test_file_2)
        
        # 测试并发访问
        print("\n🎯 测试 3: 并发访问测试")
        success3 = await tester.test_concurrent_instances()
        
        # 测试实例隔离
        print("\n🎯 测试 4: 实例隔离测试")
        success4 = await tester.test_instance_isolation()
        
        # 测试配置差异
        print("\n🎯 测试 5: 配置差异测试")
        success5 = await tester.test_configuration_differences()
        
        # 测试配置管理
        print("\n🎯 测试 6: 配置管理测试")
        success6 = await tester.test_config_management()
        
        # 测试 SimpleClient 配置
        print("\n🎯 测试 7: SimpleClient 配置测试")
        success7 = await tester.test_config_with_simple_client()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 无配置实例测试: {'通过' if success1 else '失败'}")
        print(f"✅ 有配置实例测试: {'通过' if success2 else '失败'}")
        print(f"✅ 并发访问测试: {'通过' if success3 else '失败'}")
        print(f"✅ 实例隔离测试: {'通过' if success4 else '失败'}")
        print(f"✅ 配置差异测试: {'通过' if success5 else '失败'}")
        print(f"✅ 配置管理测试: {'通过' if success6 else '失败'}")
        print(f"✅ SimpleClient配置测试: {'通过' if success7 else '失败'}")
        
        if all([success1, success2, success3, success4, success5, success6, success7]):
            print("\n🎉 所有双实例配置测试通过！")
            result = 0
        else:
            print("\n❌ 部分双实例配置测试失败")
            result = 1
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        result = 1
    finally:
        # 清理测试文件
        tester.cleanup_test_files()
    
    return result


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))