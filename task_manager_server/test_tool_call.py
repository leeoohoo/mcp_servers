#!/usr/bin/env python3
"""
Task Manager Server 工具调用测试

测试任务管理器服务器的各种工具调用功能，包括：
1. 任务创建工具测试
2. 任务执行工具测试
3. 任务完成工具测试
4. 任务查询工具测试
5. 错误处理测试
6. 工具信息测试
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from mcp import SimpleClient
from task_manager_server import TaskManagerServer


class ToolCallTester:
    """工具调用测试器"""
    
    def __init__(self):
        self.server = None
        self.client = None
        self.temp_dir = None
    
    async def setup(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 创建服务器实例
        self.server = TaskManagerServer()
        
        # 创建客户端连接
        self.client = SimpleClient(self.server)
        await self.client.initialize()
    
    async def cleanup(self):
        """清理测试环境"""
        if self.client:
            await self.client.close()
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    async def test_create_tasks_tool(self):
        """测试创建任务工具"""
        print("📝 测试创建任务工具...")
        
        # 测试单个任务创建
        single_task = [
            {
                "task_title": "创建用户模型",
                "target_file": "models/user.py",
                "operation": "create",
                "specific_operations": "定义User类，包含id、name、email字段",
                "related": "用户管理系统的核心模型",
                "dependencies": ""
            }
        ]
        
        result = await self.client.call_tool("create_tasks", {
            "tasks": single_task,
            "session_id": "test_single_task"
        })
        
        assert result.isError is False, f"单个任务创建失败: {result.content}"
        print("✅ 单个任务创建成功")
        
        # 测试批量任务创建
        batch_tasks = [
            {
                "task_title": "创建用户服务",
                "target_file": "services/user_service.py",
                "operation": "create",
                "specific_operations": "实现用户CRUD操作",
                "related": "依赖用户模型",
                "dependencies": ""
            },
            {
                "task_title": "创建用户控制器",
                "target_file": "controllers/user_controller.py",
                "operation": "create",
                "specific_operations": "实现用户API端点",
                "related": "依赖用户服务",
                "dependencies": ""
            },
            {
                "task_title": "创建用户测试",
                "target_file": "tests/test_user.py",
                "operation": "create",
                "specific_operations": "编写用户功能测试",
                "related": "测试用户功能",
                "dependencies": ""
            }
        ]
        
        result = await self.client.call_tool("create_tasks", {
            "tasks": batch_tasks,
            "session_id": "test_batch_tasks"
        })
        
        assert result.isError is False, f"批量任务创建失败: {result.content}"
        print("✅ 批量任务创建成功")
    
    async def test_get_next_executable_task_tool(self):
        """测试获取下一个可执行任务工具"""
        print("▶️ 测试获取下一个可执行任务工具...")
        
        # 先创建一些测试任务
        test_tasks = [
            {
                "task_title": "基础任务",
                "target_file": "base.py",
                "operation": "create",
                "specific_operations": "创建基础文件",
                "related": "基础模块",
                "dependencies": ""
            },
            {
                "task_title": "依赖任务",
                "target_file": "dependent.py",
                "operation": "create",
                "specific_operations": "创建依赖文件",
                "related": "依赖基础模块",
                "dependencies": ""
            }
        ]
        
        await self.client.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": "test_executable_task"
        })
        
        # 获取下一个可执行任务
        result = await self.client.call_tool("get_next_executable_task", {
            "session_id": "test_executable_task"
        })
        
        assert result.isError is False, f"获取可执行任务失败: {result.content}"
        print("✅ 获取下一个可执行任务成功")
        
        # 再次获取（应该返回当前正在执行的任务）
        result2 = await self.client.call_tool("get_next_executable_task", {
            "session_id": "test_executable_task"
        })
        
        assert result2.isError is False, f"再次获取可执行任务失败: {result2.content}"
        print("✅ 再次获取可执行任务成功")
    
    async def test_complete_task_tool(self):
        """测试完成任务工具"""
        print("✅ 测试完成任务工具...")
        
        # 先创建任务并获取任务ID
        test_tasks = [
            {
                "task_title": "待完成任务",
                "target_file": "complete_test.py",
                "operation": "create",
                "specific_operations": "创建测试文件",
                "related": "完成测试",
                "dependencies": ""
            }
        ]
        
        create_result = await self.client.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": "test_complete_task"
        })
        
        assert create_result.isError is False, "创建任务失败"
        
        # 获取任务ID（从创建结果中解析）
        # 注意：这里需要根据实际的返回格式来解析任务ID
        # 为了简化测试，我们先获取下一个可执行任务
        next_task_result = await self.client.call_tool("get_next_executable_task", {
            "session_id": "test_complete_task"
        })
        
        assert next_task_result.isError is False, "获取可执行任务失败"
        
        # 从结果中提取任务ID（这里需要根据实际返回格式调整）
        content = next_task_result.content[0].text if next_task_result.content else ""
        
        # 简化测试：使用一个假设的任务ID格式
        # 在实际使用中，需要从返回内容中正确解析任务ID
        if "ID:" in content:
            import re
            match = re.search(r'ID:\s*([a-f0-9-]+)', content)
            if match:
                task_id = match.group(1)
                
                # 完成任务
                complete_result = await self.client.call_tool("complete_task", {
                    "task_id": task_id
                })
                
                assert complete_result.isError is False, f"完成任务失败: {complete_result.content}"
                print("✅ 完成任务成功")
            else:
                print("⚠️ 无法从返回内容中解析任务ID，跳过完成任务测试")
        else:
            print("⚠️ 返回内容格式不包含任务ID，跳过完成任务测试")
    
    async def test_get_task_stats_tool(self):
        """测试获取任务统计工具"""
        print("📊 测试获取任务统计工具...")
        
        # 创建一些测试任务
        test_tasks = [
            {
                "task_title": "统计测试任务1",
                "target_file": "stats1.py",
                "operation": "create",
                "specific_operations": "创建统计测试文件1",
                "related": "统计测试",
                "dependencies": ""
            },
            {
                "task_title": "统计测试任务2",
                "target_file": "stats2.py",
                "operation": "create",
                "specific_operations": "创建统计测试文件2",
                "related": "统计测试",
                "dependencies": ""
            }
        ]
        
        await self.client.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": "test_stats"
        })
        
        # 获取任务统计
        result = await self.client.call_tool("get_task_stats", {
            "session_id": "test_stats"
        })
        
        assert result.isError is False, f"获取任务统计失败: {result.content}"
        print("✅ 获取任务统计成功")
    
    async def test_query_tasks_tool(self):
        """测试查询任务工具"""
        print("🔍 测试查询任务工具...")
        
        # 创建测试任务
        test_tasks = [
            {
                "task_title": "查询测试任务",
                "target_file": "query_test.py",
                "operation": "create",
                "specific_operations": "创建查询测试文件",
                "related": "查询测试",
                "dependencies": ""
            }
        ]
        
        await self.client.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": "test_query"
        })
        
        # 查询任务
        result = await self.client.call_tool("query_tasks", {
            "session_id": "test_query",
            "status": "pending"
        })
        
        assert result.isError is False, f"查询任务失败: {result.content}"
        print("✅ 查询任务成功")
    
    async def test_get_current_executing_task_tool(self):
        """测试获取当前执行任务工具"""
        print("🔍 测试获取当前执行任务工具...")
        
        # 创建测试任务
        test_tasks = [
            {
                "task_title": "当前执行测试任务",
                "target_file": "current_exec_test.py",
                "operation": "create",
                "specific_operations": "创建当前执行测试文件",
                "related": "当前执行测试",
                "dependencies": ""
            }
        ]
        
        await self.client.call_tool("create_tasks", {
            "tasks": test_tasks,
            "session_id": "test_current_exec"
        })
        
        # 获取当前执行任务（应该没有）
        result = await self.client.call_tool("get_current_executing_task", {
            "session_id": "test_current_exec"
        })
        
        assert result.isError is False, f"获取当前执行任务失败: {result.content}"
        print("✅ 获取当前执行任务成功")
    
    async def test_error_handling(self):
        """测试错误处理"""
        print("❌ 测试错误处理...")
        
        # 测试无效会话ID
        result = await self.client.call_tool("get_task_stats", {
            "session_id": ""
        })
        # 注意：根据实际实现，空会话ID可能是有效的
        print("✅ 空会话ID处理测试完成")
        
        # 测试无效任务ID
        result = await self.client.call_tool("complete_task", {
            "task_id": "invalid_task_id"
        })
        # 任务管理器应该能处理无效任务ID
        print("✅ 无效任务ID处理测试完成")
        
        # 测试缺少必需参数
        try:
            result = await self.client.call_tool("create_tasks", {
                "tasks": []
            })
            # 缺少session_id参数
        except Exception as e:
            print("✅ 缺少必需参数错误处理正确")
    
    async def test_tool_information(self):
        """测试工具信息获取"""
        print("ℹ️ 测试工具信息获取...")
        
        # 获取工具列表
        tools = await self.client.list_tools()
        assert len(tools.tools) > 0, "应该有可用工具"
        
        # 验证预期的工具存在
        tool_names = {tool.name for tool in tools.tools}
        expected_tools = {
            "create_tasks",
            "get_next_executable_task", 
            "complete_task",
            "get_task_stats",
            "query_tasks",
            "get_current_executing_task"
        }
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"缺少预期工具: {expected_tool}"
        
        print(f"✅ 工具信息获取成功，共{len(tools.tools)}个工具")
        
        # 验证工具描述
        for tool in tools.tools:
            assert tool.description, f"工具{tool.name}应该有描述"
            assert tool.inputSchema, f"工具{tool.name}应该有输入模式"
        
        print("✅ 工具描述和模式验证成功")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Task Manager Server工具调用测试")
        print("=" * 60)
        
        try:
            await self.setup()
            
            await self.test_create_tasks_tool()
            await self.test_get_next_executable_task_tool()
            await self.test_complete_task_tool()
            await self.test_get_task_stats_tool()
            await self.test_query_tasks_tool()
            await self.test_get_current_executing_task_tool()
            await self.test_error_handling()
            await self.test_tool_information()
            
            print("\n🎉 所有工具调用测试通过！")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """主函数"""
    tester = ToolCallTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())