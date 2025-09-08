#!/usr/bin/env python3
"""
测试工具描述配置化功能
"""

import json
import os
from expert_MCP_server_annotated import ExpertMCPServerAnnotated

def test_tool_descriptions():
    """测试工具描述配置加载"""
    print("=== 测试工具描述配置化功能 ===")
    
    # 创建服务器实例
    server = ExpertMCPServerAnnotated()
    
    # 测试配置加载
    print("\n1. 测试配置文件加载:")
    print(f"配置文件路径: {os.path.join(os.path.dirname(__file__), 'tool_descriptions.json')}")
    print(f"配置加载状态: {'成功' if server.tool_descriptions else '失败'}")
    
    if server.tool_descriptions:
        print(f"可用工具模式: {list(server.tool_descriptions.get('query_expert_stream', {}).keys())}")
    
    # 测试不同模式的配置获取
    print("\n2. 测试不同模式的工具配置:")
    modes = ['development_assistant', 'development_planner', 'task_inspector']
    
    for mode in modes:
        config = server._get_tool_config('query_expert_stream', mode)
        print(f"\n模式: {mode}")
        if config:
            print(f"  描述长度: {len(config.get('description', ''))} 字符")
            print(f"  参数描述长度: {len(config.get('parameter_description', ''))} 字符")
            print(f"  描述开头: {config.get('description', '')[:50]}...")
        else:
            print("  配置未找到")
    
    # 测试装饰器参数设置
    print("\n3. 测试装饰器参数设置:")
    print(f"当前工具模式: {getattr(server, '_tool_mode', '未设置')}")
    
    # 模拟设置不同的工具模式
    for mode in modes:
        server._tool_mode = mode
        config = server._get_tool_config('query_expert_stream', mode)
        print(f"\n设置模式为 {mode}:")
        if config:
            print(f"  获取到配置: 是")
            print(f"  描述开头: {config.get('description', '')[:30]}...")
        else:
            print(f"  获取到配置: 否")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_tool_descriptions()