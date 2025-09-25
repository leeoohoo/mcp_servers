#!/usr/bin/env python3
"""
测试工具调用功能
使用新的 SimpleClient 验证 FileWriteServer 的 modify_file 工具调用功能
"""

import asyncio
import sys
import os
from mcp_framework.client.simple import SimpleClient


class ToolCallTester:
    def __init__(self, server_script: str, alias: str = None):
        self.server_script = server_script
        self.alias = alias
        self.test_file = "test_file.txt"
    
    async def test_modify_file_operations(self):
        """测试 modify_file 工具的各种操作"""
        print("\n🧪 测试 modify_file 工具操作...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                print("✅ 成功连接到服务器")
                
                # 验证工具是否存在
                has_modify_tool = await client.has_tool("modify_file")
                if not has_modify_tool:
                    print("❌ modify_file 工具不存在")
                    return False
                
                print("✅ 找到 modify_file 工具")
                
                # 1. 测试创建文件
                print("\n1. 测试创建文件...")
                try:
                    result = await client.call("modify_file", 
                        file_path=self.test_file,
                        action="create",
                        content="第一行内容\n第二行内容\n第三行内容"
                    )
                    print("✅ 创建文件成功")
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"❌ 创建文件失败: {e}")
                    return False
                
                # 2. 测试查看文件
                print("\n2. 测试查看文件...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="view"
                    )
                    print("✅ 查看文件成功")
                    print(f"   文件内容预览: {str(result)[:100]}...")
                except Exception as e:
                    print(f"❌ 查看文件失败: {e}")
                    return False
                
                # 3. 测试编辑文件
                print("\n3. 测试编辑文件...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="edit",
                        line="2",
                        content="修改后的第二行内容"
                    )
                    print("✅ 编辑文件成功")
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"❌ 编辑文件失败: {e}")
                    return False
                
                # 4. 测试插入内容
                print("\n4. 测试插入内容...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="insert",
                        line="2",
                        content="插入的新行"
                    )
                    print("✅ 插入内容成功")
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"❌ 插入内容失败: {e}")
                    return False
                
                # 5. 测试删除行
                print("\n5. 测试删除行...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="delete",
                        line="3"
                    )
                    print("✅ 删除行成功")
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"❌ 删除行失败: {e}")
                    return False
                
                # 6. 测试查看修改后的文件
                print("\n6. 测试查看修改后的文件...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="view"
                    )
                    print("✅ 查看修改后文件成功")
                    print(f"   修改后文件内容: {str(result)[:200]}...")
                except Exception as e:
                    print(f"❌ 查看修改后文件失败: {e}")
                    return False
                
                # 7. 测试删除文件
                print("\n7. 测试删除文件...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="remove"
                    )
                    print("✅ 删除文件成功")
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"❌ 删除文件失败: {e}")
                    return False
                
                return True
                
        except Exception as e:
            print(f"❌ 连接服务器或执行操作时发生错误: {e}")
            return False

    async def test_error_handling(self):
        """测试错误处理"""
        print("\n🧪 测试错误处理...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                
                # 测试不存在的文件操作
                print("\n1. 测试操作不存在的文件...")
                try:
                    result = await client.call("modify_file",
                        file_path="non_existent_file.txt",
                        action="view"
                    )
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"   预期的错误: {e}")
                
                # 测试无效的操作类型
                print("\n2. 测试无效的操作类型...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file,
                        action="invalid_action"
                    )
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"   预期的错误: {e}")
                
                # 测试缺少必需参数
                print("\n3. 测试缺少必需参数...")
                try:
                    result = await client.call("modify_file",
                        file_path=self.test_file
                        # 缺少 action 参数
                    )
                    print(f"   结果: {result}")
                except Exception as e:
                    print(f"   预期的错误: {e}")
                
                return True
                
        except Exception as e:
            print(f"❌ 错误处理测试失败: {e}")
            return False

    async def test_tool_info(self):
        """测试工具信息获取"""
        print("\n🧪 测试工具信息获取...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                
                # 获取 modify_file 工具信息
                tool_info = await client.tool_info("modify_file")
                
                if tool_info:
                    print("✅ 成功获取工具信息")
                    print(f"   工具名称: modify_file")
                    print(f"   工具描述: {tool_info.description}")
                    
                    if hasattr(tool_info, 'inputSchema') and tool_info.inputSchema:
                        properties = tool_info.inputSchema.get('properties', {})
                        print(f"   参数数量: {len(properties)}")
                        
                        for param_name, param_info in properties.items():
                            param_type = param_info.get('type', '未知')
                            param_desc = param_info.get('description', '无描述')
                            is_required = param_name in tool_info.inputSchema.get('required', [])
                            required_str = "必需" if is_required else "可选"
                            print(f"     - {param_name} ({param_type}, {required_str}): {param_desc}")
                    
                    return True
                else:
                    print("❌ 无法获取工具信息")
                    return False
                    
        except Exception as e:
            print(f"❌ 工具信息获取测试失败: {e}")
            return False

    def cleanup_test_files(self):
        """清理测试文件"""
        try:
            if os.path.exists(self.test_file):
                os.remove(self.test_file)
                print(f"🧹 清理测试文件: {self.test_file}")
        except Exception as e:
            print(f"⚠️  清理测试文件失败: {e}")


async def main():
    """主测试函数"""
    print("🚀 FileWriteServer modify_file 工具调用测试")
    print("=" * 60)
    
    # 解析命令行参数
    alias = "test_no_config"  # 默认别名
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--alias" and len(sys.argv) > 2:
            alias = sys.argv[2]
        elif len(sys.argv) > 1:
            alias = sys.argv[1]
    
    print(f"📝 使用别名: {alias}")
    
    # 创建测试器
    tester = ToolCallTester("file_write_server.py", alias)
    
    try:
        # 清理可能存在的测试文件
        tester.cleanup_test_files()
        
        # 测试工具信息获取
        print("\n🎯 测试 1: 工具信息获取")
        success1 = await tester.test_tool_info()
        
        # 测试 modify_file 工具操作
        print("\n🎯 测试 2: modify_file 工具操作")
        success2 = await tester.test_modify_file_operations()
        
        # 测试错误处理
        print("\n🎯 测试 3: 错误处理")
        success3 = await tester.test_error_handling()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 工具信息获取: {'通过' if success1 else '失败'}")
        print(f"✅ 工具操作测试: {'通过' if success2 else '失败'}")
        print(f"✅ 错误处理测试: {'通过' if success3 else '失败'}")
        
        if success1 and success2 and success3:
            print("\n🎉 所有 modify_file 工具测试通过！")
            result = 0
        else:
            print("\n❌ 部分 modify_file 工具测试失败")
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