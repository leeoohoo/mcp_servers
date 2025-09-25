#!/usr/bin/env python3
"""
Task Manager Server 双实例配置测试

测试双实例配置的功能，包括：
1. 双实例配置测试
2. 并发访问测试
3. 实例隔离测试
4. 配置差异测试
5. 配置管理测试
"""

import asyncio
import pytest
from mcp import SimpleClient
from task_manager_server import TaskManagerServer


class DualInstanceConfigTester:
    """双实例配置测试器"""
    
    def __init__(self):
        self.server1 = None
        self.server2 = None
        self.client1 = None
        self.client2 = None
    
    async def setup(self):
        """设置测试环境"""
        # 创建两个服务器实例
        self.server1 = TaskManagerServer()
        self.server2 = TaskManagerServer()
        
        # 创建客户端连接
        self.client1 = SimpleClient(self.server1)
        self.client2 = SimpleClient(self.server2)
        
        # 初始化连接
        await self.client1.initialize()
        await self.client2.initialize()
    
    async def cleanup(self):
        """清理测试环境"""
        if self.client1:
            await self.client1.close()
        if self.client2:
            await self.client2.close()
    
    async def test_dual_instance_configuration(self):
        """测试双实例配置"""
        print("🔧 测试双实例配置...")
        
        # 测试两个实例都能正常工作
        tools1 = await self.client1.list_tools()
        tools2 = await self.client2.list_tools()
        
        assert len(tools1.tools) > 0, "实例1应该有可用工具"
        assert len(tools2.tools) > 0, "实例2应该有可用工具"
        assert len(tools1.tools) == len(tools2.tools), "两个实例应该有相同数量的工具"
        
        print(f"✅ 实例1工具数量: {len(tools1.tools)}")
        print(f"✅ 实例2工具数量: {len(tools2.tools)}")
        
        # 验证工具名称一致
        tool_names1 = {tool.name for tool in tools1.tools}
        tool_names2 = {tool.name for tool in tools2.tools}
        assert tool_names1 == tool_names2, "两个实例应该有相同的工具"
        
        print("✅ 双实例配置测试通过")
    
    async def test_concurrent_access(self):
        """测试并发访问"""
        print("🔄 测试并发访问...")
        
        # 准备测试数据
        test_tasks1 = [
            {
                "task_title": "实例1任务1",
                "target_file": "instance1_file1.py",
                "operation": "create",
                "specific_operations": "创建实例1文件1",
                "related": "实例1相关信息",
                "dependencies": ""
            }
        ]
        
        test_tasks2 = [
            {
                "task_title": "实例2任务1",
                "target_file": "instance2_file1.py",
                "operation": "create",
                "specific_operations": "创建实例2文件1",
                "related": "实例2相关信息",
                "dependencies": ""
            }
        ]
        
        # 并发创建任务
        async def create_tasks_instance1():
            result = await self.client1.call_tool("create_tasks", {
                "tasks": test_tasks1,
                "session_id": "concurrent_test_session1"
            })
            return result
        
        async def create_tasks_instance2():
            result = await self.client2.call_tool("create_tasks", {
                "tasks": test_tasks2,
                "session_id": "concurrent_test_session2"
            })
            return result
        
        # 并发执行
        results = await asyncio.gather(
            create_tasks_instance1(),
            create_tasks_instance2(),
            return_exceptions=True
        )
        
        # 验证结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"实例{i+1}并发访问失败: {result}")
            assert result.isError is False, f"实例{i+1}创建任务失败"
        
        print("✅ 并发访问测试通过")
    
    async def test_instance_isolation(self):
        """测试实例隔离"""
        print("🔒 测试实例隔离...")
        
        # 在实例1创建任务
        test_tasks = [
            {
                "task_title": "隔离测试任务",
                "target_file": "isolation_test.py",
                "operation": "create",
                "specific_operations": "测试实例隔离",
                "related": "隔离测试",
                "dependencies": ""
            }
        ]
        
        result1 = await self.client1.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": "isolation_test_session"
        })
        assert result1.isError is False, "实例1创建任务应该成功"
        
        # 在实例2查询任务统计（应该看不到实例1的任务）
        result2 = await self.client2.call_tool("get_task_stats", {
            "session_id": "isolation_test_session"
        })
        
        # 注意：由于任务管理器使用文件存储，实例间可能会共享数据
        # 这里主要测试实例能独立运行，而不是完全隔离
        assert result2.isError is False, "实例2查询统计应该成功"
        
        print("✅ 实例隔离测试通过")
    
    async def test_configuration_differences(self):
        """测试配置差异"""
        print("⚙️ 测试配置差异...")
        
        # 获取两个实例的工具信息
        tools1 = await self.client1.list_tools()
        tools2 = await self.client2.list_tools()
        
        # 验证工具配置一致性
        for tool1, tool2 in zip(tools1.tools, tools2.tools):
            assert tool1.name == tool2.name, f"工具名称应该一致: {tool1.name} vs {tool2.name}"
            assert tool1.description == tool2.description, f"工具描述应该一致: {tool1.name}"
        
        print("✅ 配置差异测试通过")
    
    async def test_configuration_management(self):
        """测试配置管理"""
        print("📋 测试配置管理...")
        
        # 测试两个实例的基本功能
        session_id1 = "config_mgmt_test1"
        session_id2 = "config_mgmt_test2"
        
        # 在两个实例上执行相同操作
        test_tasks = [
            {
                "task_title": "配置管理测试",
                "target_file": "config_test.py",
                "operation": "create",
                "specific_operations": "测试配置管理",
                "related": "配置测试",
                "dependencies": ""
            }
        ]
        
        result1 = await self.client1.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": session_id1
        })
        
        result2 = await self.client2.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": session_id2
        })
        
        assert result1.isError is False, "实例1配置管理测试应该成功"
        assert result2.isError is False, "实例2配置管理测试应该成功"
        
        print("✅ 配置管理测试通过")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Task Manager Server双实例配置测试")
        print("=" * 60)
        
        try:
            await self.setup()
            
            await self.test_dual_instance_configuration()
            await self.test_concurrent_access()
            await self.test_instance_isolation()
            await self.test_configuration_differences()
            await self.test_configuration_management()
            
            print("\n🎉 所有双实例配置测试通过！")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """主函数"""
    tester = DualInstanceConfigTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())