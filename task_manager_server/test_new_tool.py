#!/usr/bin/env python3
"""
测试新添加的 get_current_executing_task 工具
"""

import asyncio
import json
from task_manager_service import TaskManagerService

async def test_get_current_executing_task():
    """测试获取当前执行任务的功能"""
    service = TaskManagerService()
    
    # 测试参数
    conversation_id = "test_conv_001"
    request_id = "test_req_001"
    
    print("🧪 测试获取当前执行任务功能")
    print("=" * 50)
    
    # 首先创建一些测试任务
    test_tasks = [
        {
            "task_title": "测试任务1",
            "target_file": "test1.py",
            "operation": "create",
            "specific_operations": "创建测试文件1",
            "related": "测试相关信息1",
            "dependencies": ""
        },
        {
            "task_title": "测试任务2",
            "target_file": "test2.py",
            "operation": "create",
            "specific_operations": "创建测试文件2",
            "related": "测试相关信息2",
            "dependencies": ""
        }
    ]
    
    print("📝 创建测试任务...")
    async for chunk in service.create_tasks_stream(test_tasks, conversation_id, request_id):
        print(chunk, end="")
    
    print("\n" + "=" * 50)
    print("🔍 测试获取当前执行任务（应该没有执行中的任务）...")
    async for chunk in service.get_current_executing_task_stream(conversation_id, request_id):
        print(chunk, end="")
    
    print("\n" + "=" * 50)
    print("▶️ 获取下一个可执行任务（这会将任务标记为执行中）...")
    async for chunk in service.get_next_executable_task_stream(conversation_id, request_id):
        print(chunk, end="")
    
    print("\n" + "=" * 50)
    print("🔍 再次测试获取当前执行任务（现在应该有执行中的任务）...")
    async for chunk in service.get_current_executing_task_stream(conversation_id, request_id):
        print(chunk, end="")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成！")

if __name__ == "__main__":
    asyncio.run(test_get_current_executing_task())