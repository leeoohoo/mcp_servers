#!/usr/bin/env python3
"""
测试工具调用功能
使用 SimpleClient 验证 ExpertStreamServer 的 query_expert_stream 工具调用功能
"""

import asyncio
import sys
import os
from mcp_framework.client.simple import SimpleClient


class ToolCallTester:
    def __init__(self, server_script: str, alias: str = None):
        self.server_script = server_script
        self.alias = alias
    
    async def test_tool_info(self):
        """测试工具信息获取"""
        print("\n🧪 测试工具信息获取...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                
                # 检查是否有 query_expert_stream 工具
                has_tool = await client.has_tool("query_expert_stream")
                if not has_tool:
                    print("❌ query_expert_stream 工具不存在")
                    return False
                
                print("✅ 找到 query_expert_stream 工具")
                
                # 获取工具信息
                tool_info = await client.tool_info("query_expert_stream")
                
                if tool_info:
                    print("✅ 成功获取工具信息")
                    print(f"   工具名称: query_expert_stream")
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
    
    async def test_query_expert_stream_operations(self):
        """测试 query_expert_stream 工具的各种操作"""
        print("\n🧪 测试 query_expert_stream 工具操作...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                print("✅ 成功连接到服务器")
                
                # 1. 测试简单问题
                print("\n1. 测试简单问题...")
                try:
                    print("问题: 什么是Python?")
                    print("回答: ", end="", flush=True)
                    
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", 
                                                        question="什么是Python?"):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                    
                    print(f"\n✅ 简单问题测试成功，完整回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"\n❌ 简单问题测试失败: {e}")
                    return False
                
                # 2. 测试技术问题
                print("\n2. 测试技术问题...")
                try:
                    print("问题: 解释一下Python中的装饰器是什么，如何使用？")
                    print("回答: ", end="", flush=True)
                    
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", 
                                                        question="解释一下Python中的装饰器是什么，如何使用？"):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                    
                    print(f"\n✅ 技术问题测试成功，完整回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"\n❌ 技术问题测试失败: {e}")
                    return False
                
                # 3. 测试代码相关问题
                print("\n3. 测试代码相关问题...")
                try:
                    print("问题: 写一个Python函数来计算斐波那契数列")
                    print("回答: ", end="", flush=True)
                    
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", 
                                                        question="写一个Python函数来计算斐波那契数列"):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                    
                    print(f"\n✅ 代码问题测试成功，完整回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"\n❌ 代码问题测试失败: {e}")
                    return False
                
                # 4. 测试复杂任务
                print("\n4. 测试复杂任务...")
                try:
                    print("问题: 设计一个简单的Web应用架构，包括前端、后端和数据库")
                    print("回答: ", end="", flush=True)
                    
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", 
                                                        question="设计一个简单的Web应用架构，包括前端、后端和数据库"):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                    
                    print(f"\n✅ 复杂任务测试成功，完整回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"\n❌ 复杂任务测试失败: {e}")
                    return False
                
                # 5. 测试多轮对话
                print("\n5. 测试多轮对话...")
                try:
                    print("问题: 继续上一个问题，详细说明数据库设计")
                    print("回答: ", end="", flush=True)
                    
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", 
                                                        question="继续上一个问题，详细说明数据库设计"):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                    
                    print(f"\n✅ 多轮对话测试成功，完整回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"\n❌ 多轮对话测试失败: {e}")
                    return False
                
                return True
                
        except Exception as e:
            print(f"❌ query_expert_stream 操作测试失败: {e}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理"""
        print("\n🧪 测试错误处理...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                
                # 1. 测试空问题
                print("\n1. 测试空问题...")
                try:
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", question=""):
                        full_response += chunk
                    print(f"✅ 空问题处理成功，回答: {full_response[:100]}...")
                except Exception as e:
                    print(f"✅ 空问题正确抛出异常: {e}")
                
                # 2. 测试超长问题
                print("\n2. 测试超长问题...")
                try:
                    long_question = "这是一个非常长的问题。" * 1000
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", question=long_question):
                        full_response += chunk
                    print(f"✅ 超长问题处理成功，回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"✅ 超长问题正确抛出异常: {e}")
                
                # 3. 测试特殊字符
                print("\n3. 测试特殊字符...")
                try:
                    special_question = "测试特殊字符: @#$%^&*()_+{}|:<>?[]\\;'\",./"
                    full_response = ""
                    async for chunk in client.call_stream("query_expert_stream", question=special_question):
                        full_response += chunk
                    print(f"✅ 特殊字符处理成功，回答长度: {len(full_response)}")
                except Exception as e:
                    print(f"✅ 特殊字符正确抛出异常: {e}")
                
                return True
                
        except Exception as e:
            print(f"❌ 错误处理测试失败: {e}")
            return False
    
    async def test_streaming_response(self):
        """测试流式响应特性"""
        print("\n🧪 测试流式响应特性...")
        
        try:
            async with SimpleClient(self.server_script, alias=self.alias) as client:
                
                print("测试流式响应的实时性...")
                print("问题: 详细解释机器学习的基本概念和应用")
                print("回答: ", end="", flush=True)
                
                chunk_count = 0
                total_length = 0
                
                async for chunk in client.call_stream("query_expert_stream", 
                                                    question="详细解释机器学习的基本概念和应用"):
                    print(chunk, end="", flush=True)
                    chunk_count += 1
                    total_length += len(chunk)
                
                print(f"\n✅ 流式响应测试成功")
                print(f"   总块数: {chunk_count}")
                print(f"   总长度: {total_length}")
                print(f"   平均块大小: {total_length/chunk_count if chunk_count > 0 else 0:.1f}")
                
                return True
                
        except Exception as e:
            print(f"❌ 流式响应测试失败: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行 ExpertStreamServer 工具调用测试...")
        
        results = []
        
        # 运行各项测试
        results.append(await self.test_tool_info())
        results.append(await self.test_query_expert_stream_operations())
        results.append(await self.test_error_handling())
        results.append(await self.test_streaming_response())
        
        # 汇总结果
        passed = sum(results)
        total = len(results)
        
        print(f"\n📊 测试结果汇总:")
        print(f"   通过: {passed}/{total}")
        print(f"   成功率: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 所有测试通过！")
            return True
        else:
            print("❌ 部分测试失败")
            return False


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 ExpertStreamServer 工具调用功能")
    parser.add_argument("--alias", default="test_no_config", help="服务器别名")
    
    args = parser.parse_args()
    
    # 服务器脚本路径
    server_script = "expert_stream_server.py"
    
    # 创建测试器
    tester = ToolCallTester(server_script, alias=args.alias)
    
    # 运行测试
    success = await tester.run_all_tests()
    
    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())