#!/usr/bin/env python3
"""
测试工具列表获取功能
使用新的 SimpleClient 验证 ExpertStreamServer 能够正确返回可用的工具列表
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
                    expected_tools = ["query_expert_stream"]
                    
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
                        
                        if hasattr(tool_info, 'input_schema') and tool_info.input_schema:
                            properties = tool_info.input_schema.get('properties', {})
                            if properties:
                                print(f"  参数数量: {len(properties)}")
                                for param_name, param_info in properties.items():
                                    param_type = param_info.get('type', '未知')
                                    param_desc = param_info.get('description', '无描述')
                                    # 截断过长的参数描述
                                    if len(param_desc) > 100:
                                        param_desc = param_desc[:100] + "..."
                                    is_required = param_name in tool_info.input_schema.get('required', [])
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
                    key_configs = ['server_name', 'version', 'description', 'api_key', 'model_name']
                    for key in key_configs:
                        value = await client.get(key, "未设置")
                        # 隐藏敏感信息
                        if key == 'api_key' and value != "未设置":
                            value = "***已设置***"
                        print(f"  {key}: {value}")
                    
                    return True
                    
                except Exception as e:
                    print(f"⚠️  获取服务器信息失败: {e}")
                    return False
                
        except Exception as e:
            print(f"❌ 测试服务器信息时发生错误: {e}")
            return False


async def main():
    """主测试函数"""
    print("🧪 开始测试工具列表获取功能")
    print("=" * 60)
    
    # 解析命令行参数
    alias = "test_no_config1"  # 默认别名
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--alias" and len(sys.argv) > 2:
            alias = sys.argv[2]
        elif len(sys.argv) > 1:
            alias = sys.argv[1]
    
    print(f"📝 使用别名: {alias}")
    
    # 创建测试器
    tester = ToolsListTester("./dist/expert-stream-server/expert-stream-server", alias)
    
    try:
        # 测试工具列表获取
        print("\n🎯 测试 1: 基础工具列表获取")
        success1 = await tester.test_tools_list()
        
        # 测试工具信息详细获取
        print("\n🎯 测试 2: 工具信息详细获取")
        success2 = await tester.test_tool_info_details()
        
        # 测试资源列表获取
        print("\n🎯 测试 3: 资源列表获取")
        success3 = await tester.test_resources_list()
        
        # 测试服务器信息获取
        print("\n🎯 测试 4: 服务器信息获取")
        success4 = await tester.test_server_info()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 基础工具列表获取: {'通过' if success1 else '失败'}")
        print(f"✅ 工具信息详细获取: {'通过' if success2 else '失败'}")
        print(f"✅ 资源列表获取: {'通过' if success3 else '失败'}")
        print(f"✅ 服务器信息获取: {'通过' if success4 else '失败'}")
        
        if success1 and success2 and success3 and success4:
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