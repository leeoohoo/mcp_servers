#!/usr/bin/env python3
"""
Task Manager Server 工具列表测试

测试任务管理器服务器的工具列表功能，包括：
1. 工具列表获取测试
2. 工具详细信息测试
3. 特定工具详情测试
4. 资源列表测试
5. 服务器信息测试
6. 工具模式验证测试
"""

import asyncio
import json
from mcp import SimpleClient
from task_manager_server import TaskManagerServer


class ToolsListTester:
    """工具列表测试器"""
    
    def __init__(self):
        self.server = None
        self.client = None
    
    async def setup(self):
        """设置测试环境"""
        # 创建服务器实例
        self.server = TaskManagerServer()
        
        # 创建客户端连接
        self.client = SimpleClient(self.server)
        await self.client.initialize()
    
    async def cleanup(self):
        """清理测试环境"""
        if self.client:
            await self.client.close()
    
    async def test_list_tools(self):
        """测试获取工具列表"""
        print("📋 测试获取工具列表...")
        
        # 获取工具列表
        tools_response = await self.client.list_tools()
        
        assert tools_response is not None, "工具列表响应不应为空"
        assert hasattr(tools_response, 'tools'), "响应应包含tools属性"
        assert len(tools_response.tools) > 0, "应该有可用工具"
        
        print(f"✅ 成功获取工具列表，共{len(tools_response.tools)}个工具")
        
        # 打印所有工具名称
        for tool in tools_response.tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        return tools_response.tools
    
    async def test_tool_details(self):
        """测试工具详细信息"""
        print("🔍 测试工具详细信息...")
        
        tools = await self.test_list_tools()
        
        for tool in tools:
            # 验证工具基本属性
            assert tool.name, f"工具应该有名称"
            assert tool.description, f"工具{tool.name}应该有描述"
            assert tool.inputSchema, f"工具{tool.name}应该有输入模式"
            
            # 验证输入模式结构
            schema = tool.inputSchema
            assert isinstance(schema, dict), f"工具{tool.name}的输入模式应该是字典"
            assert 'type' in schema, f"工具{tool.name}的输入模式应该有type字段"
            
            print(f"✅ 工具{tool.name}详细信息验证通过")
    
    async def test_specific_tool_details(self):
        """测试特定工具详情"""
        print("🎯 测试特定工具详情...")
        
        tools = await self.client.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        
        # 测试create_tasks工具
        if "create_tasks" in tool_names:
            create_tasks_tool = next(tool for tool in tools.tools if tool.name == "create_tasks")
            
            # 验证create_tasks工具的特定属性
            assert "tasks" in str(create_tasks_tool.inputSchema), "create_tasks应该需要tasks参数"
            assert "session_id" in str(create_tasks_tool.inputSchema), "create_tasks应该需要session_id参数"
            assert "Task Creator" in create_tasks_tool.description, "create_tasks描述应该包含Task Creator"
            
            print("✅ create_tasks工具详情验证通过")
        
        # 测试get_next_executable_task工具
        if "get_next_executable_task" in tool_names:
            next_task_tool = next(tool for tool in tools.tools if tool.name == "get_next_executable_task")
            
            # 验证get_next_executable_task工具的特定属性
            assert "session_id" in str(next_task_tool.inputSchema), "get_next_executable_task应该需要session_id参数"
            assert "Task Executor" in next_task_tool.description, "get_next_executable_task描述应该包含Task Executor"
            
            print("✅ get_next_executable_task工具详情验证通过")
        
        # 测试complete_task工具
        if "complete_task" in tool_names:
            complete_tool = next(tool for tool in tools.tools if tool.name == "complete_task")
            
            # 验证complete_task工具的特定属性
            assert "task_id" in str(complete_tool.inputSchema), "complete_task应该需要task_id参数"
            assert "Task Completer" in complete_tool.description, "complete_task描述应该包含Task Completer"
            
            print("✅ complete_task工具详情验证通过")
        
        # 测试get_task_stats工具
        if "get_task_stats" in tool_names:
            stats_tool = next(tool for tool in tools.tools if tool.name == "get_task_stats")
            
            # 验证get_task_stats工具的特定属性
            assert "session_id" in str(stats_tool.inputSchema), "get_task_stats应该需要session_id参数"
            assert "Statistics" in stats_tool.description, "get_task_stats描述应该包含Statistics"
            
            print("✅ get_task_stats工具详情验证通过")
        
        # 测试query_tasks工具
        if "query_tasks" in tool_names:
            query_tool = next(tool for tool in tools.tools if tool.name == "query_tasks")
            
            # 验证query_tasks工具的特定属性
            assert "session_id" in str(query_tool.inputSchema), "query_tasks应该需要session_id参数"
            assert "Query" in query_tool.description, "query_tasks描述应该包含Query"
            
            print("✅ query_tasks工具详情验证通过")
        
        # 测试get_current_executing_task工具
        if "get_current_executing_task" in tool_names:
            current_tool = next(tool for tool in tools.tools if tool.name == "get_current_executing_task")
            
            # 验证get_current_executing_task工具的特定属性
            assert "session_id" in str(current_tool.inputSchema), "get_current_executing_task应该需要session_id参数"
            assert "Current Task Inspector" in current_tool.description, "get_current_executing_task描述应该包含Current Task Inspector"
            
            print("✅ get_current_executing_task工具详情验证通过")
    
    async def test_resources_list(self):
        """测试资源列表"""
        print("📚 测试资源列表...")
        
        try:
            # 获取资源列表
            resources_response = await self.client.list_resources()
            
            # 任务管理器可能没有资源，这是正常的
            if hasattr(resources_response, 'resources'):
                print(f"✅ 成功获取资源列表，共{len(resources_response.resources)}个资源")
                
                for resource in resources_response.resources:
                    print(f"  - {resource.uri}: {resource.name}")
            else:
                print("✅ 任务管理器没有定义资源（这是正常的）")
                
        except Exception as e:
            # 如果服务器不支持资源列表，这也是正常的
            print(f"✅ 服务器不支持资源列表或没有资源: {e}")
    
    async def test_server_info(self):
        """测试服务器信息"""
        print("ℹ️ 测试服务器信息...")
        
        # 通过工具列表验证服务器基本信息
        tools = await self.client.list_tools()
        
        # 验证服务器有预期的工具
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
            assert expected_tool in tool_names, f"服务器应该提供{expected_tool}工具"
        
        print("✅ 服务器信息验证通过")
        print(f"  - 服务器类型: Task Manager Server")
        print(f"  - 工具数量: {len(tools.tools)}")
        print(f"  - 核心功能: 任务管理、流式输出、会话隔离")
    
    async def test_tool_schema_validation(self):
        """测试工具模式验证"""
        print("🔧 测试工具模式验证...")
        
        tools = await self.client.list_tools()
        
        for tool in tools.tools:
            schema = tool.inputSchema
            
            # 验证基本模式结构
            assert isinstance(schema, dict), f"工具{tool.name}的模式应该是字典"
            assert 'type' in schema, f"工具{tool.name}的模式应该有type字段"
            assert schema['type'] == 'object', f"工具{tool.name}的模式类型应该是object"
            
            # 验证属性定义
            if 'properties' in schema:
                properties = schema['properties']
                assert isinstance(properties, dict), f"工具{tool.name}的属性应该是字典"
                
                # 验证每个属性都有类型定义
                for prop_name, prop_def in properties.items():
                    assert isinstance(prop_def, dict), f"工具{tool.name}的属性{prop_name}定义应该是字典"
                    assert 'type' in prop_def, f"工具{tool.name}的属性{prop_name}应该有类型定义"
            
            # 验证必需字段
            if 'required' in schema:
                required = schema['required']
                assert isinstance(required, list), f"工具{tool.name}的必需字段应该是列表"
            
            print(f"✅ 工具{tool.name}模式验证通过")
    
    async def test_tool_descriptions_quality(self):
        """测试工具描述质量"""
        print("📝 测试工具描述质量...")
        
        tools = await self.client.list_tools()
        
        for tool in tools.tools:
            description = tool.description
            
            # 验证描述不为空且有意义
            assert description and len(description.strip()) > 10, f"工具{tool.name}应该有有意义的描述"
            
            # 验证描述包含关键信息
            if tool.name == "create_tasks":
                assert "Task Creator" in description, "create_tasks描述应该包含Task Creator"
                assert "tasks" in description.lower(), "create_tasks描述应该提到tasks"
                assert "session_id" in description.lower(), "create_tasks描述应该提到session_id"
            
            elif tool.name == "get_next_executable_task":
                assert "Task Executor" in description, "get_next_executable_task描述应该包含Task Executor"
                assert "executable" in description.lower(), "get_next_executable_task描述应该提到executable"
            
            elif tool.name == "complete_task":
                assert "Task Completer" in description, "complete_task描述应该包含Task Completer"
                assert "completed" in description.lower(), "complete_task描述应该提到completed"
            
            print(f"✅ 工具{tool.name}描述质量验证通过")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Task Manager Server工具列表测试")
        print("=" * 60)
        
        try:
            await self.setup()
            
            await self.test_list_tools()
            await self.test_tool_details()
            await self.test_specific_tool_details()
            await self.test_resources_list()
            await self.test_server_info()
            await self.test_tool_schema_validation()
            await self.test_tool_descriptions_quality()
            
            print("\n🎉 所有工具列表测试通过！")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """主函数"""
    tester = ToolsListTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())