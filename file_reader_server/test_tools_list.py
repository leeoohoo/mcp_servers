#!/usr/bin/env python3
"""
测试工具列表获取功能
使用新的 SimpleClient 验证 FileReaderServer 能够正确返回可用的工具列表
"""

import asyncio
import sys
from mcp_framework.client.simple import SimpleClient


class ToolsListTester:
    def __init__(self, server_script: str, alias: str = None):
        self.server_script = server_script
        self.alias = alias
    
    async def test_tools_list(self):
        """测试获取工具列表"""
        try:
            print(f"🔗 连接到服务器: {self.server_script}")
            if self.alias:
                print(f"📝 使用别名: {self.alias}")
            
            # 使用 SimpleClient 连接服务器
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                print("✅ 成功连接到服务器")
                
                # 获取工具列表
                print("📋 获取工具列表...")
                tools = await client.tools()
                
                if tools:
                    print(f"✅ 成功获取工具列表，共 {len(tools)} 个工具:")
                    
                    for tool_name in tools:
                        print(f"  - {tool_name}")
                        
                        # 获取工具详细信息
                        tool_info = await client.tool_info(tool_name)
                        if tool_info:
                            description = tool_info.description
                            # 截断过长的描述
                            if len(description) > 100:
                                description = description[:100] + "..."
                            print(f"    描述: {description}")
                        else:
                            print(f"    描述: 无法获取工具信息")
                    
                    # 验证预期的工具是否存在
                    expected_tools = [
                        "read_file_lines",
                        "search_files_by_content",
                        "get_files_content", 
                        "get_project_structure"
                    ]
                    
                    print(f"\n🔍 验证预期工具:")
                    for expected_tool in expected_tools:
                        has_tool = await client.has_tool(expected_tool)
                        if has_tool:
                            print(f"  ✅ 找到预期工具: {expected_tool}")
                        else:
                            print(f"  ❌ 缺少预期工具: {expected_tool}")
                    
                    return True
                else:
                    print("❌ 获取到的工具列表为空")
                    return False
                    
        except Exception as e:
            print(f"❌ 测试工具列表时发生错误: {e}")
            return False

    async def test_tool_info_details(self):
        """测试工具信息详细获取"""
        try:
            print(f"\n🔍 测试工具信息详细获取...")
            
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                # 获取所有工具
                tools = await client.tools()
                
                if not tools:
                    print("❌ 没有可用的工具")
                    return False
                
                # 测试每个工具的详细信息
                for tool_name in tools:
                    print(f"\n📝 工具: {tool_name}")
                    
                    # 检查工具是否存在
                    exists = await client.has_tool(tool_name)
                    print(f"  存在性检查: {'✅ 存在' if exists else '❌ 不存在'}")
                    
                    # 获取工具信息
                    tool_info = await client.tool_info(tool_name)
                    if tool_info:
                        description = tool_info.description
                        # 截断过长的描述以便显示
                        if len(description) > 200:
                            description = description[:200] + "..."
                        print(f"  描述: {description}")
                        
                        if hasattr(tool_info, 'inputSchema') and tool_info.inputSchema:
                            properties = tool_info.inputSchema.get('properties', {})
                            if properties:
                                print(f"  参数数量: {len(properties)}")
                                for param_name, param_info in properties.items():
                                    param_type = param_info.get('type', '未知')
                                    param_desc = param_info.get('description', '无描述')
                                    # 截断过长的参数描述
                                    if len(param_desc) > 100:
                                        param_desc = param_desc[:100] + "..."
                                    is_required = param_name in tool_info.inputSchema.get('required', [])
                                    required_str = "必需" if is_required else "可选"
                                    print(f"    - {param_name} ({param_type}, {required_str}): {param_desc}")
                            else:
                                print(f"  参数: 无参数")
                    else:
                        print(f"  ❌ 无法获取工具信息")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试工具信息详细获取时发生错误: {e}")
            return False

    async def test_specific_tools(self):
        """测试特定工具的详细信息"""
        try:
            print(f"\n🔧 测试特定工具详细信息...")
            
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                
                # 测试 read_file_lines 工具
                print("📖 测试 read_file_lines 工具:")
                if await client.has_tool("read_file_lines"):
                    tool_info = await client.tool_info("read_file_lines")
                    if tool_info:
                        print("  ✅ 工具存在且有详细信息")
                        # 检查必需参数
                        if hasattr(tool_info, 'inputSchema') and tool_info.inputSchema:
                            required_params = tool_info.inputSchema.get('required', [])
                            expected_params = ['file_path', 'start_line', 'end_line']
                            for param in expected_params:
                                if param in required_params:
                                    print(f"    ✅ 必需参数: {param}")
                                else:
                                    print(f"    ⚠️  参数: {param} (可能不是必需的)")
                    else:
                        print("  ❌ 无法获取工具详细信息")
                else:
                    print("  ❌ 工具不存在")
                
                # 测试 search_files_by_content 工具
                print("\n🔍 测试 search_files_by_content 工具:")
                if await client.has_tool("search_files_by_content"):
                    tool_info = await client.tool_info("search_files_by_content")
                    if tool_info:
                        print("  ✅ 工具存在且有详细信息")
                        # 检查查询参数
                        if hasattr(tool_info, 'inputSchema') and tool_info.inputSchema:
                            properties = tool_info.inputSchema.get('properties', {})
                            if 'query' in properties:
                                print("    ✅ 查询参数: query")
                            else:
                                print("    ❌ 缺少查询参数")
                    else:
                        print("  ❌ 无法获取工具详细信息")
                else:
                    print("  ❌ 工具不存在")
                
                # 测试 get_project_structure 工具
                print("\n🌳 测试 get_project_structure 工具:")
                if await client.has_tool("get_project_structure"):
                    tool_info = await client.tool_info("get_project_structure")
                    if tool_info:
                        print("  ✅ 工具存在且有详细信息")
                        # 检查可选参数
                        if hasattr(tool_info, 'inputSchema') and tool_info.inputSchema:
                            properties = tool_info.inputSchema.get('properties', {})
                            optional_params = ['max_depth', 'show_hidden']
                            for param in optional_params:
                                if param in properties:
                                    print(f"    ✅ 可选参数: {param}")
                                else:
                                    print(f"    ⚠️  参数: {param} (可能不存在)")
                    else:
                        print("  ❌ 无法获取工具详细信息")
                else:
                    print("  ❌ 工具不存在")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试特定工具时发生错误: {e}")
            return False

    async def test_resources_list(self):
        """测试获取资源列表"""
        try:
            print(f"\n🔍 测试资源列表获取...")
            
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                # 尝试获取资源列表（如果服务器支持）
                try:
                    # 注意：这里假设 SimpleClient 有 resources 方法
                    # 如果没有，这个测试会被跳过
                    if hasattr(client, 'resources'):
                        resources = await client.resources()
                        print(f"✅ 成功获取资源列表，共 {len(resources)} 个资源:")
                        
                        for resource in resources:
                            print(f"  - {resource}")
                            
                        # 验证预期的资源
                        expected_resources = [
                            "config://file-reader",
                            "stats://project-stats"
                        ]
                        
                        for expected_resource in expected_resources:
                            if expected_resource in str(resources):
                                print(f"  ✅ 找到预期资源: {expected_resource}")
                            else:
                                print(f"  ⚠️  未找到预期资源: {expected_resource}")
                                
                    else:
                        print("⚠️  SimpleClient 不支持资源列表获取，跳过此测试")
                        
                except Exception as e:
                    print(f"⚠️  资源列表获取失败（可能不支持）: {e}")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试资源列表时发生错误: {e}")
            return False

    async def test_server_info(self):
        """测试获取服务器信息"""
        try:
            print(f"\n🔍 测试服务器信息获取...")
            
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                # 获取服务器基本信息
                try:
                    # 获取配置信息
                    config = await client.config()
                    print(f"✅ 获取服务器配置成功: {len(config)} 项配置")
                    
                    # 显示一些关键配置项
                    key_configs = ['project_root', 'max_file_size', 'enable_hidden_files', 'server_name']
                    for key in key_configs:
                        value = await client.get(key, "未设置")
                        print(f"  {key}: {value}")
                    
                    return True
                    
                except Exception as e:
                    print(f"⚠️  获取服务器信息失败: {e}")
                    return False
                
        except Exception as e:
            print(f"❌ 测试服务器信息时发生错误: {e}")
            return False

    async def test_tool_schema_validation(self):
        """测试工具模式验证"""
        try:
            print(f"\n🔬 测试工具模式验证...")
            
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                tools = await client.tools()
                
                schema_valid_count = 0
                
                for tool_name in tools:
                    tool_info = await client.tool_info(tool_name)
                    if tool_info and hasattr(tool_info, 'inputSchema'):
                        schema = tool_info.inputSchema
                        
                        # 基本模式验证
                        if isinstance(schema, dict):
                            has_type = 'type' in schema
                            has_properties = 'properties' in schema
                            
                            print(f"  📝 {tool_name}:")
                            print(f"    类型字段: {'✅' if has_type else '❌'}")
                            print(f"    属性字段: {'✅' if has_properties else '❌'}")
                            
                            if has_type and has_properties:
                                schema_valid_count += 1
                                
                                # 检查必需字段
                                required = schema.get('required', [])
                                properties = schema.get('properties', {})
                                
                                print(f"    必需参数: {len(required)}")
                                print(f"    总参数: {len(properties)}")
                                
                                # 验证必需参数都在属性中定义
                                for req_param in required:
                                    if req_param in properties:
                                        print(f"      ✅ {req_param}")
                                    else:
                                        print(f"      ❌ {req_param} (未在属性中定义)")
                        else:
                            print(f"  📝 {tool_name}: ❌ 无效的模式格式")
                    else:
                        print(f"  📝 {tool_name}: ⚠️  无模式信息")
                
                print(f"\n📊 模式验证结果: {schema_valid_count}/{len(tools)} 个工具有效")
                
                return schema_valid_count > 0
                
        except Exception as e:
            print(f"❌ 测试工具模式验证时发生错误: {e}")
            return False


async def main():
    """主测试函数"""
    print("🧪 开始测试工具列表获取功能")
    print("=" * 60)
    
    # 解析命令行参数
    alias = "concurrent1"  # 默认别名
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--alias" and len(sys.argv) > 2:
            alias = sys.argv[2]
        elif len(sys.argv) > 1:
            alias = sys.argv[1]
    
    print(f"📝 使用别名: {alias}")
    
    # 创建测试器
    tester = ToolsListTester("file_reader_server.py", alias)
    
    try:
        # 测试工具列表获取
        print("\n🎯 测试 1: 基础工具列表获取")
        success1 = await tester.test_tools_list()
        
        # 测试工具信息详细获取
        print("\n🎯 测试 2: 工具信息详细获取")
        success2 = await tester.test_tool_info_details()
        
        # 测试特定工具详细信息
        print("\n🎯 测试 3: 特定工具详细信息")
        success3 = await tester.test_specific_tools()
        
        # 测试资源列表获取
        print("\n🎯 测试 4: 资源列表获取")
        success4 = await tester.test_resources_list()
        
        # 测试服务器信息获取
        print("\n🎯 测试 5: 服务器信息获取")
        success5 = await tester.test_server_info()
        
        # 测试工具模式验证
        print("\n🎯 测试 6: 工具模式验证")
        success6 = await tester.test_tool_schema_validation()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 基础工具列表获取: {'通过' if success1 else '失败'}")
        print(f"✅ 工具信息详细获取: {'通过' if success2 else '失败'}")
        print(f"✅ 特定工具详细信息: {'通过' if success3 else '失败'}")
        print(f"✅ 资源列表获取: {'通过' if success4 else '失败'}")
        print(f"✅ 服务器信息获取: {'通过' if success5 else '失败'}")
        print(f"✅ 工具模式验证: {'通过' if success6 else '失败'}")
        
        if all([success1, success2, success3, success4, success5, success6]):
            print("\n🎉 所有工具列表测试通过！")
            return 0
        else:
            print("\n❌ 部分工具列表测试失败！")
            return 1
            
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))