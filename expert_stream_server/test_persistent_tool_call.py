#!/usr/bin/env python3
"""
测试工具调用功能 - 持久客户端版本
使用持久的 SimpleClient 验证 ExpertStreamServer 的 query_expert_stream 工具调用功能
避免每次测试都重新创建连接，提高测试效率
"""

import asyncio
import sys
import os
import time
from mcp_framework.client.simple import SimpleClient


class PersistentToolCallTester:
    def __init__(self, server_script: str, alias: str = None):
        self.server_script = server_script
        self.alias = alias or "test_working_alias"  # 使用一个工作正常的alias
        self.client = None
        self.config_dir = "/Users/lilei/project/config/test_mcp_server_config"
    
    async def setup_client(self):
        """初始化持久客户端"""
        print(f"🔧 初始化持久客户端 (alias: {self.alias})...")
        
        try:
            self.client = SimpleClient(
                self.server_script, 
                alias=self.alias, 
                config_dir=self.config_dir
            )
            await self.client.__aenter__()  # 手动进入异步上下文
            print(f"✅ 持久客户端创建成功")
            return True
        except Exception as e:
            print(f"❌ 持久客户端创建失败: {e}")
            return False
    
    async def cleanup_client(self):
        """清理客户端"""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)  # 手动退出异步上下文
                print("✅ 持久客户端清理完成")
            except Exception as e:
                print(f"⚠️  持久客户端清理时出错: {e}")
            finally:
                self.client = None
    
    async def test_tool_info(self):
        """测试工具信息获取 - 使用持久客户端"""
        print("\n🧪 测试工具信息获取 (持久客户端)...")
        
        try:
            if not self.client:
                print("❌ 客户端未初始化")
                return False
            
            # 检查是否有 query_expert_stream 工具
            has_tool = await self.client.has_tool("query_expert_stream")
            if not has_tool:
                print("❌ query_expert_stream 工具不存在")
                return False
            
            print("✅ 找到 query_expert_stream 工具")
            
            # 获取工具信息
            tool_info = await self.client.tool_info("query_expert_stream")
            
            if tool_info:
                print("✅ 成功获取工具信息")
                print(f"   工具名称: query_expert_stream")
                print(f"   工具描述: {tool_info.description}")
                
                if hasattr(tool_info, 'input_schema') and tool_info.input_schema:
                    properties = tool_info.input_schema.get('properties', {})
                    print(f"   参数数量: {len(properties)}")
                    
                    for param_name, param_info in properties.items():
                        param_type = param_info.get('type', '未知')
                        param_desc = param_info.get('description', '无描述')
                        is_required = param_name in tool_info.input_schema.get('required', [])
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
        """测试 query_expert_stream 工具的各种操作 - 使用持久客户端"""
        print("\n🧪 测试 query_expert_stream 工具操作 (持久客户端)...")
        
        try:
            if not self.client:
                print("❌ 客户端未初始化")
                return False
            
            print("✅ 使用持久客户端连接")
            
            # 测试用例列表
            test_cases = [
                {
                    "name": "简单问题",
                    "question": "你可以用工具 帮我看看这个项目是做什么的?"
                },
                {
                    "name": "技术问题",
                    "question": "解释一下Python中的装饰器是什么，如何使用？"
                },
                {
                    "name": "代码相关问题",
                    "question": "写一个Python函数来计算斐波那契数列"
                },
                {
                    "name": "复杂任务",
                    "question": "设计一个简单的Web应用架构，包括前端、后端和数据库"
                },
                {
                    "name": "多轮对话",
                    "question": "继续上一个问题，详细说明数据库设计"
                }
            ]
            
            success_count = 0
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n{i}. 测试{test_case['name']}...")
                try:
                    print(f"问题: {test_case['question']}")
                    print("回答: ", end="", flush=True)
                    
                    full_response = ""
                    chunk_count = 0
                    start_time = time.time()
                    
                    async for chunk in self.client.call_stream("query_expert_stream", 
                                                            question=test_case['question']):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                        chunk_count += 1
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    print(f"\n✅ {test_case['name']}测试成功")
                    print(f"   回答长度: {len(full_response)}")
                    print(f"   响应时间: {duration:.2f}s")
                    print(f"   流式块数: {chunk_count}")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"\n❌ {test_case['name']}测试失败: {e}")
            
            print(f"\n📊 操作测试结果: {success_count}/{len(test_cases)} 成功")
            return success_count == len(test_cases)
            
        except Exception as e:
            print(f"❌ query_expert_stream 操作测试失败: {e}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理 - 使用持久客户端"""
        print("\n🧪 测试错误处理 (持久客户端)...")
        
        try:
            if not self.client:
                print("❌ 客户端未初始化")
                return False
            
            error_test_cases = [
                {
                    "name": "空问题",
                    "question": "",
                    "expect_error": True
                },
                {
                    "name": "超长问题",
                    "question": "这是一个非常长的问题。" * 1000,
                    "expect_error": False  # 可能会被处理而不是报错
                },
                {
                    "name": "特殊字符",
                    "question": "测试特殊字符: @#$%^&*()_+{}|:<>?[]\\;'\",./ 🚀🎉✅❌",
                    "expect_error": False
                },
                {
                    "name": "多语言混合",
                    "question": "Hello 你好 こんにちは 안녕하세요 Bonjour Hola",
                    "expect_error": False
                }
            ]
            
            success_count = 0
            
            for i, test_case in enumerate(error_test_cases, 1):
                print(f"\n{i}. 测试{test_case['name']}...")
                try:
                    full_response = ""
                    async for chunk in self.client.call_stream("query_expert_stream", 
                                                            question=test_case['question']):
                        full_response += chunk
                    
                    if test_case['expect_error']:
                        print(f"⚠️  {test_case['name']}应该报错但成功了，回答: {full_response[:50]}...")
                    else:
                        print(f"✅ {test_case['name']}处理成功，回答长度: {len(full_response)}")
                        success_count += 1
                        
                except Exception as e:
                    if test_case['expect_error']:
                        print(f"✅ {test_case['name']}正确抛出异常: {e}")
                        success_count += 1
                    else:
                        print(f"❌ {test_case['name']}意外抛出异常: {e}")
            
            print(f"\n📊 错误处理测试结果: {success_count}/{len(error_test_cases)} 符合预期")
            return success_count >= len(error_test_cases) * 0.75  # 75% 通过率即可
            
        except Exception as e:
            print(f"❌ 错误处理测试失败: {e}")
            return False
    
    async def test_streaming_response(self):
        """测试流式响应特性 - 使用持久客户端"""
        print("\n🧪 测试流式响应特性 (持久客户端)...")
        
        try:
            if not self.client:
                print("❌ 客户端未初始化")
                return False
            
            print("测试流式响应的实时性...")
            print("问题: 详细解释机器学习的基本概念和应用")
            print("回答: ", end="", flush=True)
            
            chunk_count = 0
            total_length = 0
            chunk_times = []
            start_time = time.time()
            last_chunk_time = start_time
            
            async for chunk in self.client.call_stream("query_expert_stream", 
                                                    question="详细解释机器学习的基本概念和应用"):
                current_time = time.time()
                chunk_interval = current_time - last_chunk_time
                chunk_times.append(chunk_interval)
                last_chunk_time = current_time
                
                print(chunk, end="", flush=True)
                chunk_count += 1
                total_length += len(chunk)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            print(f"\n✅ 流式响应测试成功")
            print(f"   总块数: {chunk_count}")
            print(f"   总长度: {total_length}")
            print(f"   总耗时: {total_duration:.2f}s")
            print(f"   平均块大小: {total_length/chunk_count if chunk_count > 0 else 0:.1f}")
            print(f"   平均块间隔: {sum(chunk_times)/len(chunk_times) if chunk_times else 0:.3f}s")
            print(f"   响应速度: {total_length/total_duration:.1f} 字符/秒")
            
            return True
            
        except Exception as e:
            print(f"❌ 流式响应测试失败: {e}")
            return False
    
    async def test_concurrent_calls(self):
        """测试并发调用 - 使用持久客户端"""
        print("\n🧪 测试并发调用 (持久客户端)...")
        
        try:
            if not self.client:
                print("❌ 客户端未初始化")
                return False
            
            # 准备并发测试问题
            concurrent_questions = [
                "什么是Python？",
                "什么是JavaScript？",
                "什么是机器学习？",
                "什么是区块链？",
                "什么是云计算？"
            ]
            
            async def single_call(question, index):
                """单个并发调用"""
                try:
                    start_time = time.time()
                    full_response = ""
                    
                    async for chunk in self.client.call_stream("query_expert_stream", question=question):
                        full_response += chunk
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    return True, index, question, len(full_response), duration
                except Exception as e:
                    return False, index, question, 0, 0
            
            print(f"开始 {len(concurrent_questions)} 个并发调用...")
            start_time = time.time()
            
            # 执行并发调用
            tasks = [single_call(q, i) for i, q in enumerate(concurrent_questions)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 分析结果
            success_count = 0
            total_response_length = 0
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"   ❌ 并发调用异常: {result}")
                else:
                    success, index, question, length, duration = result
                    if success:
                        print(f"   ✅ 调用 {index+1}: {question[:20]}... (长度: {length}, 耗时: {duration:.2f}s)")
                        success_count += 1
                        total_response_length += length
                    else:
                        print(f"   ❌ 调用 {index+1}: {question[:20]}... 失败")
            
            print(f"\n📊 并发调用结果:")
            print(f"   成功率: {success_count}/{len(concurrent_questions)} ({success_count/len(concurrent_questions)*100:.1f}%)")
            print(f"   总耗时: {total_duration:.2f}s")
            print(f"   平均响应长度: {total_response_length/success_count if success_count > 0 else 0:.1f}")
            
            return success_count >= len(concurrent_questions) * 0.8  # 80% 成功率即可
            
        except Exception as e:
            print(f"❌ 并发调用测试失败: {e}")
            return False
    
    async def test_performance_comparison(self):
        """测试性能对比 - 持久客户端 vs 临时客户端"""
        print("\n🧪 测试性能对比...")
        
        test_question = "简单解释什么是人工智能？"
        test_rounds = 3
        
        # 测试持久客户端性能
        print(f"   测试持久客户端性能 ({test_rounds} 轮)...")
        persistent_times = []
        
        for i in range(test_rounds):
            start_time = time.time()
            full_response = ""
            async for chunk in self.client.call_stream("query_expert_stream", question=test_question):
                full_response += chunk
            end_time = time.time()
            
            duration = end_time - start_time
            persistent_times.append(duration)
            print(f"     轮次 {i+1}: {duration:.2f}s (响应长度: {len(full_response)})")
        
        avg_persistent_time = sum(persistent_times) / len(persistent_times)
        print(f"   持久客户端平均耗时: {avg_persistent_time:.2f}s")
        
        # 测试临时客户端性能
        print(f"   测试临时客户端性能 ({test_rounds} 轮)...")
        temporary_times = []
        
        for i in range(test_rounds):
            start_time = time.time()
            
            async with SimpleClient(self.server_script, alias=self.alias, config_dir=self.config_dir) as temp_client:
                full_response = ""
                async for chunk in temp_client.call_stream("query_expert_stream", question=test_question):
                    full_response += chunk
            
            end_time = time.time()
            duration = end_time - start_time
            temporary_times.append(duration)
            print(f"     轮次 {i+1}: {duration:.2f}s (响应长度: {len(full_response)})")
        
        avg_temporary_time = sum(temporary_times) / len(temporary_times)
        print(f"   临时客户端平均耗时: {avg_temporary_time:.2f}s")
        
        # 性能对比
        if avg_temporary_time > 0:
            improvement = ((avg_temporary_time - avg_persistent_time) / avg_temporary_time) * 100
            print(f"\n📊 性能对比结果:")
            print(f"   持久客户端: {avg_persistent_time:.2f}s")
            print(f"   临时客户端: {avg_temporary_time:.2f}s")
            print(f"   性能提升: {improvement:.1f}% (持久客户端{'更快' if improvement > 0 else '更慢'})")
            
            return True
        else:
            print("❌ 性能对比测试数据异常")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行 ExpertStreamServer 持久客户端工具调用测试...")
        
        # 初始化客户端
        if not await self.setup_client():
            return False
        
        try:
            # 测试列表
            tests = [
                ("工具信息获取", self.test_tool_info),
                ("工具操作测试", self.test_query_expert_stream_operations),
                ("错误处理测试", self.test_error_handling),
                ("流式响应测试", self.test_streaming_response),
                ("并发调用测试", self.test_concurrent_calls),
                ("性能对比测试", self.test_performance_comparison),
            ]
            
            results = []
            
            # 运行各项测试
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
            
            # 汇总结果
            passed = sum(1 for _, success in results if success)
            total = len(results)
            
            print(f"\n📊 测试结果汇总:")
            print("=" * 60)
            
            for test_name, success in results:
                status = "✅ 通过" if success else "❌ 失败"
                print(f"   {test_name}: {status}")
            
            print(f"\n总体结果: {passed}/{total} 测试通过")
            print(f"成功率: {passed/total*100:.1f}%")
            
            if passed == total:
                print("🎉 所有测试都通过了！持久客户端工具调用功能正常。")
                return True
            elif passed >= total * 0.8:
                print("✅ 大部分测试通过，持久客户端基本功能正常。")
                return True
            else:
                print("❌ 多项测试失败，请检查配置和服务器状态。")
                return False
                
        finally:
            # 清理客户端
            await self.cleanup_client()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 ExpertStreamServer 持久客户端工具调用功能")
    parser.add_argument("--alias", default="test_no_config1", help="服务器别名")
    parser.add_argument("--server", default="./dist/expert-stream-server/expert-stream-server", help="服务器脚本路径")
    
    args = parser.parse_args()
    
    # 注释掉 TESTING_MODE 设置，允许MCP工具初始化
    # os.environ["TESTING_MODE"] = "true"
    
    # 创建测试器
    tester = PersistentToolCallTester(args.server, alias=args.alias)
    
    # 运行测试
    success = await tester.run_all_tests()
    
    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())