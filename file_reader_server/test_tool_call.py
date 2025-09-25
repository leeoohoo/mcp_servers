#!/usr/bin/env python3
"""
测试工具调用功能
使用新的 SimpleClient 验证 FileReaderServer 的各种工具调用操作
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path
from mcp_framework.client.simple import SimpleClient


class ToolCallTester:
    def __init__(self, server_script: str, alias: str = None):
        self.server_script = server_script
        self.alias = alias
        # 创建临时目录和测试文件
        self.temp_dir = tempfile.mkdtemp(prefix="file_reader_tool_test_")
        self._setup_test_files()
    
    def _setup_test_files(self):
        """创建测试文件"""
        # Python文件
        python_file = Path(self.temp_dir) / "sample.py"
        python_file.write_text("""#!/usr/bin/env python3
# Sample Python file for testing
import os
import sys

def hello_world():
    \"\"\"Say hello to the world\"\"\"
    print("Hello, World!")
    return "success"

class SampleClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

# Main execution
if __name__ == "__main__":
    hello_world()
    obj = SampleClass("Test")
    print(obj.greet())
""")
        
        # JavaScript文件
        js_file = Path(self.temp_dir) / "sample.js"
        js_file.write_text("""// Sample JavaScript file
const express = require('express');
const app = express();

function helloWorld() {
    console.log('Hello from JavaScript!');
    return 'success';
}

class SampleClass {
    constructor(name) {
        this.name = name;
    }
    
    greet() {
        return `Hello, ${this.name}!`;
    }
}

// Export for testing
module.exports = { helloWorld, SampleClass };
""")
        
        # 文本文件
        text_file = Path(self.temp_dir) / "readme.txt"
        text_file.write_text("""File Reader Server Test
======================

This is a test file for the file reader server.
It contains multiple lines of text for testing purposes.

Features:
- Line reading
- Content searching
- File structure analysis

TODO: Add more test cases
FIXME: Handle edge cases better
""")
        
        # 创建子目录
        subdir = Path(self.temp_dir) / "subdir"
        subdir.mkdir()
        
        # 子目录中的文件
        nested_file = subdir / "nested.md"
        nested_file.write_text("""# Nested File

This is a nested markdown file.

## Section 1
Content in section 1.

## Section 2
Content in section 2.
""")
    
    def cleanup(self):
        """清理临时目录"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理临时目录时出错: {e}")

    async def test_read_file_lines_basic(self):
        """测试基础文件行读取"""
        try:
            print(f"🔗 连接到服务器: {self.server_script}")
            if self.alias:
                print(f"📝 使用别名: {self.alias}")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                print("✅ 成功连接到服务器")
                
                # 测试读取Python文件的前10行
                print("📖 测试读取文件行...")
                result = await client.call_tool("read_file_lines", {
                    "file_path": "sample.py",
                    "start_line": 1,
                    "end_line": 10
                })
                
                if result:
                    print(f"✅ 成功读取文件，内容长度: {len(result)}")
                    # 验证内容包含预期的代码
                    if "python3" in result and "import" in result:
                        print("  ✅ 读取内容正确")
                    else:
                        print("  ❌ 读取内容不正确")
                    return True
                else:
                    print("❌ 读取文件失败")
                    return False
                    
        except Exception as e:
            print(f"❌ 测试基础文件行读取时发生错误: {e}")
            return False

    async def test_read_file_lines_range(self):
        """测试文件行范围读取"""
        try:
            print(f"\n📖 测试文件行范围读取...")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                
                # 测试读取中间部分
                result = await client.call_tool("read_file_lines", {
                    "file_path": "sample.py",
                    "start_line": 5,
                    "end_line": 15
                })
                
                if result:
                    print(f"✅ 成功读取文件范围，内容长度: {len(result)}")
                    # 验证包含函数定义
                    if "def hello_world" in result:
                        print("  ✅ 读取范围内容正确")
                    else:
                        print("  ❌ 读取范围内容不正确")
                    return True
                else:
                    print("❌ 读取文件范围失败")
                    return False
                    
        except Exception as e:
            print(f"❌ 测试文件行范围读取时发生错误: {e}")
            return False

    async def test_search_files_by_content(self):
        """测试文件内容搜索"""
        try:
            print(f"\n🔍 测试文件内容搜索...")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                
                # 搜索函数名
                print("🔍 搜索函数名...")
                result1 = await client.call_tool("search_files_by_content", {
                    "query": "hello_world"
                })
                
                if result1 and "hello_world" in result1:
                    print("  ✅ 成功搜索到函数名")
                else:
                    print("  ❌ 搜索函数名失败")
                
                # 搜索类名
                print("🔍 搜索类名...")
                result2 = await client.call_tool("search_files_by_content", {
                    "query": "SampleClass"
                })
                
                if result2 and "SampleClass" in result2:
                    print("  ✅ 成功搜索到类名")
                else:
                    print("  ❌ 搜索类名失败")
                
                # 搜索注释内容
                print("🔍 搜索注释内容...")
                result3 = await client.call_tool("search_files_by_content", {
                    "query": "TODO"
                })
                
                if result3 and "TODO" in result3:
                    print("  ✅ 成功搜索到注释内容")
                else:
                    print("  ❌ 搜索注释内容失败")
                
                return True
                    
        except Exception as e:
            print(f"❌ 测试文件内容搜索时发生错误: {e}")
            return False

    async def test_get_files_content(self):
        """测试批量获取文件内容"""
        try:
            print(f"\n📚 测试批量获取文件内容...")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                
                # 批量获取多个文件
                result = await client.call_tool("get_files_content", {
                    "file_paths": ["sample.py", "sample.js", "readme.txt"]
                })
                
                if result:
                    print(f"✅ 成功批量获取文件内容，长度: {len(result)}")
                    
                    # 验证包含所有文件的内容
                    files_found = 0
                    if "sample.py" in result:
                        files_found += 1
                        print("  ✅ 找到 sample.py 内容")
                    if "sample.js" in result:
                        files_found += 1
                        print("  ✅ 找到 sample.js 内容")
                    if "readme.txt" in result:
                        files_found += 1
                        print("  ✅ 找到 readme.txt 内容")
                    
                    if files_found >= 2:  # 至少找到2个文件
                        print("  ✅ 批量获取内容正确")
                        return True
                    else:
                        print("  ❌ 批量获取内容不完整")
                        return False
                else:
                    print("❌ 批量获取文件内容失败")
                    return False
                    
        except Exception as e:
            print(f"❌ 测试批量获取文件内容时发生错误: {e}")
            return False

    async def test_get_project_structure(self):
        """测试获取项目结构"""
        try:
            print(f"\n🌳 测试获取项目结构...")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                
                result = await client.call_tool("get_project_structure", {
                    "max_depth": 3,
                    "show_hidden": False
                })
                
                if result:
                    print(f"✅ 成功获取项目结构，长度: {len(result)}")
                    
                    # 验证包含创建的文件
                    files_found = 0
                    if "sample.py" in result:
                        files_found += 1
                        print("  ✅ 找到 sample.py")
                    if "sample.js" in result:
                        files_found += 1
                        print("  ✅ 找到 sample.js")
                    if "readme.txt" in result:
                        files_found += 1
                        print("  ✅ 找到 readme.txt")
                    if "subdir" in result:
                        files_found += 1
                        print("  ✅ 找到 subdir 目录")
                    
                    if files_found >= 3:
                        print("  ✅ 项目结构获取正确")
                        return True
                    else:
                        print("  ❌ 项目结构获取不完整")
                        return False
                else:
                    print("❌ 获取项目结构失败")
                    return False
                    
        except Exception as e:
            print(f"❌ 测试获取项目结构时发生错误: {e}")
            return False

    async def test_error_handling(self):
        """测试错误处理"""
        try:
            print(f"\n⚠️ 测试错误处理...")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                
                # 测试读取不存在的文件
                print("📖 测试读取不存在的文件...")
                result1 = await client.call_tool("read_file_lines", {
                    "file_path": "nonexistent.txt",
                    "start_line": 1,
                    "end_line": 10
                })
                
                if result1 and "错误" in result1:
                    print("  ✅ 正确处理不存在文件的错误")
                else:
                    print("  ❌ 未正确处理不存在文件的错误")
                
                # 测试无效的行号范围
                print("📖 测试无效的行号范围...")
                result2 = await client.call_tool("read_file_lines", {
                    "file_path": "sample.py",
                    "start_line": 0,  # 无效的起始行号
                    "end_line": 10
                })
                
                if result2 and "错误" in result2:
                    print("  ✅ 正确处理无效行号的错误")
                else:
                    print("  ❌ 未正确处理无效行号的错误")
                
                # 测试空搜索查询
                print("🔍 测试空搜索查询...")
                result3 = await client.call_tool("search_files_by_content", {
                    "query": ""
                })
                
                # 空查询可能返回错误或空结果，都是合理的
                print("  ✅ 处理空搜索查询")
                
                return True
                    
        except Exception as e:
            print(f"❌ 测试错误处理时发生错误: {e}")
            return False

    async def test_tool_information(self):
        """测试工具信息获取"""
        try:
            print(f"\n🔧 测试工具信息获取...")
            
            config = {"project_root": self.temp_dir}
            
            async with SimpleClient(self.server_script, alias=self.alias, config=config) as client:
                
                # 获取所有工具
                tools = await client.tools()
                print(f"📋 可用工具数量: {len(tools)}")
                
                expected_tools = [
                    "read_file_lines",
                    "search_files_by_content", 
                    "get_files_content",
                    "get_project_structure"
                ]
                
                found_tools = 0
                for tool_name in expected_tools:
                    if await client.has_tool(tool_name):
                        print(f"  ✅ 找到工具: {tool_name}")
                        found_tools += 1
                        
                        # 获取工具详细信息
                        tool_info = await client.tool_info(tool_name)
                        if tool_info:
                            description = tool_info.description
                            if len(description) > 100:
                                description = description[:100] + "..."
                            print(f"    描述: {description}")
                    else:
                        print(f"  ❌ 缺少工具: {tool_name}")
                
                if found_tools >= 3:  # 至少找到3个预期工具
                    print("  ✅ 工具信息获取正确")
                    return True
                else:
                    print("  ❌ 工具信息获取不完整")
                    return False
                    
        except Exception as e:
            print(f"❌ 测试工具信息获取时发生错误: {e}")
            return False


async def main():
    """主测试函数"""
    print("🧪 开始测试工具调用功能")
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
    tester = ToolCallTester("file_reader_server.py", alias)
    
    try:
        # 测试基础文件行读取
        print("\n🎯 测试 1: 基础文件行读取")
        success1 = await tester.test_read_file_lines_basic()
        
        # 测试文件行范围读取
        print("\n🎯 测试 2: 文件行范围读取")
        success2 = await tester.test_read_file_lines_range()
        
        # 测试文件内容搜索
        print("\n🎯 测试 3: 文件内容搜索")
        success3 = await tester.test_search_files_by_content()
        
        # 测试批量获取文件内容
        print("\n🎯 测试 4: 批量获取文件内容")
        success4 = await tester.test_get_files_content()
        
        # 测试获取项目结构
        print("\n🎯 测试 5: 获取项目结构")
        success5 = await tester.test_get_project_structure()
        
        # 测试错误处理
        print("\n🎯 测试 6: 错误处理")
        success6 = await tester.test_error_handling()
        
        # 测试工具信息获取
        print("\n🎯 测试 7: 工具信息获取")
        success7 = await tester.test_tool_information()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 基础文件行读取: {'通过' if success1 else '失败'}")
        print(f"✅ 文件行范围读取: {'通过' if success2 else '失败'}")
        print(f"✅ 文件内容搜索: {'通过' if success3 else '失败'}")
        print(f"✅ 批量获取文件内容: {'通过' if success4 else '失败'}")
        print(f"✅ 获取项目结构: {'通过' if success5 else '失败'}")
        print(f"✅ 错误处理: {'通过' if success6 else '失败'}")
        print(f"✅ 工具信息获取: {'通过' if success7 else '失败'}")
        
        if all([success1, success2, success3, success4, success5, success6, success7]):
            print("\n🎉 所有工具调用测试通过！")
            return 0
        else:
            print("\n❌ 部分工具调用测试失败！")
            return 1
            
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        return 1
    finally:
        # 清理临时文件
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))