#!/usr/bin/env python3
"""
测试 stdio MCP 服务器配置解析功能
"""

import asyncio
import logging
from expert_service import parse_stdio_mcp_servers_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestStdioConfig")

def test_parse_stdio_config():
    """测试 stdio 配置解析函数"""
    logger.info("🧪 开始测试 stdio 配置解析功能")
    
    # 测试用例1: 标准格式 name:script_path--alias
    test_config_1 = "file-manager:file_manager.py--file-mgr,task-runner:task_runner.js--task-mgr"
    result_1 = parse_stdio_mcp_servers_config(test_config_1)
    
    logger.info(f"测试用例1 - 输入: {test_config_1}")
    logger.info(f"测试用例1 - 输出: {result_1}")
    
    expected_1 = [
        {'name': 'file-manager', 'command': 'file_manager.py', 'alias': 'file-mgr'},
        {'name': 'task-runner', 'command': 'task_runner.js', 'alias': 'task-mgr'}
    ]
    
    assert result_1 == expected_1, f"测试用例1失败: 期望 {expected_1}, 实际 {result_1}"
    logger.info("✅ 测试用例1通过")
    
    # 测试用例2: 没有 alias 的格式
    test_config_2 = "simple-tool:simple.py,another-tool:another.js"
    result_2 = parse_stdio_mcp_servers_config(test_config_2)
    
    logger.info(f"测试用例2 - 输入: {test_config_2}")
    logger.info(f"测试用例2 - 输出: {result_2}")
    
    expected_2 = [
        {'name': 'simple-tool', 'command': 'simple.py', 'alias': 'simple-tool'},
        {'name': 'another-tool', 'command': 'another.js', 'alias': 'another-tool'}
    ]
    
    assert result_2 == expected_2, f"测试用例2失败: 期望 {expected_2}, 实际 {result_2}"
    logger.info("✅ 测试用例2通过")
    
    # 测试用例3: 空字符串
    test_config_3 = ""
    result_3 = parse_stdio_mcp_servers_config(test_config_3)
    
    logger.info(f"测试用例3 - 输入: '{test_config_3}'")
    logger.info(f"测试用例3 - 输出: {result_3}")
    
    expected_3 = []
    assert result_3 == expected_3, f"测试用例3失败: 期望 {expected_3}, 实际 {result_3}"
    logger.info("✅ 测试用例3通过")
    
    # 测试用例4: 混合格式
    test_config_4 = "tool1:script1.py--alias1,tool2:script2.py,tool3:script3.js--alias3"
    result_4 = parse_stdio_mcp_servers_config(test_config_4)
    
    logger.info(f"测试用例4 - 输入: {test_config_4}")
    logger.info(f"测试用例4 - 输出: {result_4}")
    
    expected_4 = [
        {'name': 'tool1', 'command': 'script1.py', 'alias': 'alias1'},
        {'name': 'tool2', 'command': 'script2.py', 'alias': 'tool2'},
        {'name': 'tool3', 'command': 'script3.js', 'alias': 'alias3'}
    ]
    
    assert result_4 == expected_4, f"测试用例4失败: 期望 {expected_4}, 实际 {result_4}"
    logger.info("✅ 测试用例4通过")
    
    # 测试用例5: 无效格式（应该被跳过）
    test_config_5 = "valid-tool:script.py--alias,invalid-format,another-valid:script2.py"
    result_5 = parse_stdio_mcp_servers_config(test_config_5)
    
    logger.info(f"测试用例5 - 输入: {test_config_5}")
    logger.info(f"测试用例5 - 输出: {result_5}")
    
    expected_5 = [
        {'name': 'valid-tool', 'command': 'script.py', 'alias': 'alias'},
        {'name': 'another-valid', 'command': 'script2.py', 'alias': 'another-valid'}
    ]
    
    assert result_5 == expected_5, f"测试用例5失败: 期望 {expected_5}, 实际 {result_5}"
    logger.info("✅ 测试用例5通过")
    
    logger.info("🎉 所有 stdio 配置解析测试通过！")

if __name__ == "__main__":
    test_parse_stdio_config()