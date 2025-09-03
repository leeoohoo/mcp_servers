#!/usr/bin/env python3
"""
任务管理器服务器使用示例（流式版本）

演示如何使用任务管理器服务器的各项流式功能：
1. 批量创建任务（流式输出）
2. 获取下一个可执行任务（流式输出）
3. 完成任务（流式输出）
4. 查询任务统计（流式输出）
5. 任务查询（流式输出）
"""

import asyncio
import json
from task_manager_server import TaskManagerServer


async def demo_streaming_output(generator, title):
    """演示流式输出"""
    print(f"\n{'='*50}")
    print(f"🎬 {title}")
    print("="*50)
    
    async for chunk in generator:
        print(chunk, end='', flush=True)
    
    print()  # 添加换行


async def demo_task_manager():
    """演示任务管理器流式功能"""
    print("🚀 启动任务管理器演示（流式版本）")
    print("📁 数据将存储在 task_data/ 目录下")
    
    # 创建服务器实例
    server = TaskManagerServer()
    await server.initialize()
    
    # 示例任务数据
    sample_tasks = [
        {
            "task_title": "删除用户缓存管理器备份文件",
            "target_file": "src/main/java/com/example/usermanagement/cache/UserCacheManager.java.backup",
            "operation": "Delete",
            "specific_operations": "直接删除备份文件，这是UserCacheManager.java的备份文件",
            "related": "无",
            "dependencies": "无"
        },
        {
            "task_title": "备份RoleController备份文件",
            "target_file": "src/main/java/com/example/usermanagement/controller/RoleController.java.backup",
            "operation": "Delete",
            "specific_operations": "直接删除备份文件，这是RoleController.java的备份文件",
            "related": "无",
            "dependencies": "无"
        },
        {
            "task_title": "备份EmailService备份文件",
            "target_file": "src/main/java/com/example/usermanagement/service/EmailService.java.backup.backup",
            "operation": "Delete",
            "specific_operations": "备份文件备份文件，这是EmailService的二级备份文件",
            "related": "无",
            "dependencies": "无"
        },
        {
            "task_title": "备份EmailServiceInterface备份文件",
            "target_file": "src/main/java/com/example/usermanagement/service/EmailServiceInterface.java.backup",
            "operation": "Delete",
            "specific_operations": "删除备份文件，这是EmailService接口的备份文件",
            "related": "无",
            "dependencies": "无"
        }
    ]
    
    # 1. 创建任务（流式输出）
    create_generator = server._tools["create_tasks"](
        conversation_id="demo_conv_001",
        request_id="demo_req_001",
        tasks=sample_tasks
    )
    await demo_streaming_output(create_generator, "📝 批量创建任务")
    
    # 2. 获取任务统计（流式输出）
    stats_generator = server._tools["get_task_stats"]()
    await demo_streaming_output(stats_generator, "📊 获取任务统计")
    
    # 3. 获取下一个可执行任务（流式输出）
    next_task_generator = server._tools["get_next_executable_task"]()
    await demo_streaming_output(next_task_generator, "▶️ 获取下一个可执行任务")
    
    # 4. 查询任务（流式输出）
    query_generator = server._tools["query_tasks"]()
    await demo_streaming_output(query_generator, "🔍 查询所有任务")
    
    # 5. 按状态查询任务（流式输出）
    pending_generator = server._tools["query_tasks"](status="pending")
    await demo_streaming_output(pending_generator, "⏳ 查询待执行任务")
    
    # 6. 按会话查询任务（流式输出）
    conv_generator = server._tools["query_tasks"](conversation_id="demo_conv_001")
    await demo_streaming_output(conv_generator, "🗣️ 查询特定会话任务")
    
    # 7. 完成一个任务（流式输出）
    # 首先获取一个进行中的任务ID
    in_progress_tasks = [task for task in server.tasks.values() if task.status == 'in_progress']
    if in_progress_tasks:
        task_to_complete = in_progress_tasks[0]
        complete_generator = server._tools["complete_task"](task_id=task_to_complete.id)
        await demo_streaming_output(complete_generator, f"✅ 完成任务: {task_to_complete.task_title}")
    
    # 8. 最终统计（流式输出）
    final_stats_generator = server._tools["get_task_stats"]()
    await demo_streaming_output(final_stats_generator, "📈 最终任务统计")
    
    print("\n" + "="*50)
    print("🎉 流式演示完成")
    print("="*50)
    print("💾 任务数据已保存到 task_data/demo_conv_001_demo_req_001.json")
    print("🔄 可以重新运行此脚本查看持久化效果")
    print("📁 查看 task_data/ 目录了解分布式存储结构")


if __name__ == "__main__":
    asyncio.run(demo_task_manager())