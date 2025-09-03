#!/usr/bin/env python3
"""
任务管理服务模块
提供任务创建、查询、状态管理等核心功能
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, asdict

logger = logging.getLogger("task_manager_service")


@dataclass
class Task:
    """任务数据模型"""
    id: str
    task_title: str
    target_file: str
    operation: str
    specific_operations: str
    related: str
    dependencies: str
    conversation_id: str
    request_id: str
    status: str = "pending"  # pending, in_progress, completed
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class TaskManagerService:
    """任务管理服务类
    
    负责任务的创建、加载、保存、查询和状态管理。
    采用完全按需加载的方式，每次操作时直接从文件读取，不维护内存缓存。
    """
    
    def __init__(self, data_dir: str = "./task_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.auto_save = True
        
        logger.info(f"TaskManagerService initialized with data dir: {self.data_dir.absolute()}")
    
    def _get_data_file_path(self, conversation_id: str, request_id: str) -> Path:
        """获取数据文件路径"""
        filename = f"{conversation_id}_{request_id}.json"
        return self.data_dir / filename
    

    
    def _load_tasks_from_file(self, file_path: Path) -> Dict[str, Task]:
        """从指定文件加载任务数据"""
        tasks = {}
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = Task(**task_data)
                        tasks[task.id] = task

            except Exception as e:
                logger.error(f"加载任务数据失败 {file_path}: {e}")
        return tasks
    
    def _save_tasks_to_file(self, conversation_id: str, request_id: str, tasks: List[Task]):
        """保存任务数据到指定文件"""
        try:
            file_path = self._get_data_file_path(conversation_id, request_id)
            data = {
                'conversation_id': conversation_id,
                'request_id': request_id,
                'tasks': [asdict(task) for task in tasks],
                'updated_at': datetime.now().isoformat()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(tasks)} 个任务到 {file_path}")
        except Exception as e:
            logger.error(f"保存任务数据失败: {e}")
    
    def _get_task_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        # 遍历所有文件查找
        for data_file in self.data_dir.glob("*.json"):
            file_tasks = self._load_tasks_from_file(data_file)
            if task_id in file_tasks:
                return file_tasks[task_id]
        
        return None
    
    def _get_tasks_by_conversation_request(self, conversation_id: str, request_id: str) -> List[Task]:
        """获取指定会话和请求的任务"""
        file_path = self._get_data_file_path(conversation_id, request_id)
        file_tasks = self._load_tasks_from_file(file_path)
        return list(file_tasks.values())
    

    
    async def create_tasks_stream(self, tasks_data: List[Dict[str, Any]], 
                                conversation_id: str, request_id: str) -> AsyncGenerator[str, None]:
        """创建任务（流式输出）"""
        yield f"开始创建 {len(tasks_data)} 个任务...\n"
        
        created_tasks = []
        errors = []
        
        for i, task_data in enumerate(tasks_data):
            try:
                # 验证必需字段
                required_fields = [
                    'task_title', 'target_file', 'operation', 
                    'specific_operations', 'related', 'dependencies'
                ]
                
                missing_fields = [field for field in required_fields if field not in task_data]
                if missing_fields:
                    errors.append({
                        'index': i,
                        'error': f"缺少必需字段: {', '.join(missing_fields)}"
                    })
                    continue
                
                # 创建任务
                task_id = str(uuid.uuid4())
                task = Task(
                    id=task_id,
                    task_title=task_data['task_title'],
                    target_file=task_data['target_file'],
                    operation=task_data['operation'],
                    specific_operations=task_data['specific_operations'],
                    related=task_data['related'],
                    dependencies=task_data['dependencies'],
                    conversation_id=conversation_id,
                    request_id=request_id,
                    status=task_data.get('status', 'pending')
                )
                
                created_tasks.append(task)
                
                yield f"[{i+1}/{len(tasks_data)}] 创建任务: {task.task_title} (ID: {task_id})\n"
                
            except Exception as e:
                error_msg = f"[{i+1}/{len(tasks_data)}] 创建任务失败: {str(e)}\n"
                yield error_msg
                errors.append({
                    'index': i,
                    'error': str(e)
                })
        
        # 保存到文件
        if created_tasks:
            self._save_tasks_to_file(conversation_id, request_id, created_tasks)
            yield f"\n✅ 成功创建 {len(created_tasks)} 个任务并保存到文件: {conversation_id}_{request_id}.json\n"
        
        if errors:
            yield f"❌ 失败 {len(errors)} 个任务\n"
        
        yield f"\n📊 总结: 成功创建 {len(created_tasks)} 个任务，失败 {len(errors)} 个\n"
    
    async def get_next_executable_task_stream(self, conversation_id: str, request_id: str) -> AsyncGenerator[str, None]:
        """获取下一个可执行任务的流式版本 - 完全按需加载"""
        yield "🔍 正在查找下一个可执行任务...\n"
        
        # 从文件加载任务
        file_path = self._get_data_file_path(conversation_id, request_id)
        if not file_path.exists():
            yield "❌ 未找到任务文件\n"
            return
        
        tasks_dict = self._load_tasks_from_file(file_path)
        if not tasks_dict:
            yield "❌ 任务文件为空\n"
            return
        
        # 查找可执行任务
        executable_tasks = []
        for task in tasks_dict.values():
            if task.status == 'pending':
                # 检查依赖是否已完成
                dependencies_met = True
                if task.dependencies and task.dependencies != "无":
                    for dep_id in task.dependencies.split(','):
                        dep_id = dep_id.strip()
                        if dep_id and dep_id in tasks_dict and tasks_dict[dep_id].status != 'completed':
                            dependencies_met = False
                            break
                
                if dependencies_met:
                    executable_tasks.append(task)
        
        if not executable_tasks:
            yield "❌ 没有找到可执行的任务\n"
            return
        
        # 返回第一个可执行任务（按创建时间排序）
        next_task = min(executable_tasks, key=lambda t: t.created_at)
        
        # 更新任务状态
        next_task.status = 'in_progress'
        next_task.updated_at = datetime.now().isoformat()
        
        # 保存到文件
        tasks_to_save = list(tasks_dict.values())
        self._save_tasks_to_file(conversation_id, request_id, tasks_to_save)
        
        yield f"✅ 找到可执行任务: {next_task.task_title} (ID: {next_task.id})\n"
        yield f"📄 目标文件: {next_task.target_file}\n"
        yield f"🔧 操作类型: {next_task.operation}\n"
        yield f"📝 具体操作: {next_task.specific_operations}\n"
        yield f"🔗 相关信息: {next_task.related}\n"
        yield f"📊 依赖关系: {next_task.dependencies}\n"
        yield f"▶️ 任务已标记为进行中\n"
    
    async def complete_task_stream(self, task_id: str) -> AsyncGenerator[str, None]:
        """完成任务的流式版本 - 完全按需加载"""
        yield f"🔍 正在查找任务 {task_id}...\n"
        
        task_found = None
        conversation_id = None
        request_id = None
        file_path = None
        
        # 遍历所有任务文件查找任务
        for file in self.data_dir.glob("*.json"):
            if "_" in file.stem:
                try:
                    tasks_dict = self._load_tasks_from_file(file)
                    if task_id in tasks_dict:
                        task_found = tasks_dict[task_id]
                        parts = file.stem.split('_', 1)
                        conversation_id = parts[0]
                        request_id = parts[1]
                        file_path = file
                        break
                except Exception:
                    continue
        
        if not task_found:
            yield f"❌ 任务 {task_id} 不存在\n"
            return
        
        yield f"📋 找到任务: {task_found.task_title}\n"
        
        # 更新任务状态
        task_found.status = 'completed'
        task_found.updated_at = datetime.now().isoformat()
        
        # 重新加载所有任务并保存
        tasks_dict = self._load_tasks_from_file(file_path)
        tasks_dict[task_id] = task_found
        tasks_to_save = list(tasks_dict.values())
        
        self._save_tasks_to_file(conversation_id, request_id, tasks_to_save)
        yield f"✅ 任务 '{task_found.task_title}' 已标记为完成\n"
        yield f"💾 已保存到文件: {conversation_id}_{request_id}.json\n"
    
    async def get_task_stats_stream(self, conversation_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """获取任务统计的流式版本 - 完全按需加载"""
        yield "📊 正在统计任务信息...\n"
        
        # 收集所有任务
        all_tasks = []
        for file in self.data_dir.glob("*.json"):
            if "_" in file.stem:
                try:
                    tasks_dict = self._load_tasks_from_file(file)
                    for task in tasks_dict.values():
                        if conversation_id is None or task.conversation_id == conversation_id:
                            all_tasks.append(task)
                except Exception:
                    continue
        
        scope = f"会话 {conversation_id}" if conversation_id else "全部"
        yield f"🔍 统计范围: {scope}\n"
        
        if not all_tasks:
            yield f"ℹ️ {scope}没有任务\n"
            return
        
        stats = {
            'total': len(all_tasks),
            'pending': len([t for t in all_tasks if t.status == 'pending']),
            'in_progress': len([t for t in all_tasks if t.status == 'in_progress']),
            'completed': len([t for t in all_tasks if t.status == 'completed'])
        }
        
        yield f"📈 {scope}任务统计:\n"
        yield f"  📋 总计: {stats['total']} 个\n"
        yield f"  ⏳ 待执行: {stats['pending']} 个\n"
        yield f"  🔄 进行中: {stats['in_progress']} 个\n"
        yield f"  ✅ 已完成: {stats['completed']} 个\n"
        
        if all_tasks:
            yield "\n📝 任务列表:\n"
            for i, task in enumerate(all_tasks, 1):
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅'}.get(task.status, '❓')
                yield f"  {i}. {status_emoji} {task.task_title} (ID: {task.id})\n"
    
    async def query_tasks_stream(self, conversation_id: Optional[str] = None, status: Optional[str] = None, task_title: Optional[str] = None) -> AsyncGenerator[str, None]:
        """查询任务的流式版本 - 完全按需加载"""
        yield "🔍 正在查询任务...\n"
        
        # 显示查询条件
        filters = []
        if conversation_id:
            filters.append(f"会话ID: {conversation_id}")
        if status:
            filters.append(f"状态: {status}")
        if task_title:
            filters.append(f"标题关键词: {task_title}")
        
        if filters:
            yield f"📋 查询条件: {', '.join(filters)}\n"
        else:
            yield "📋 查询条件: 无（显示所有任务）\n"
        
        # 收集所有任务
        all_tasks = []
        for file in self.data_dir.glob("*.json"):
            if "_" in file.stem:
                try:
                    tasks_dict = self._load_tasks_from_file(file)
                    all_tasks.extend(tasks_dict.values())
                except Exception:
                    continue
        
        filtered_tasks = all_tasks
        
        # 按条件过滤
        if conversation_id:
            filtered_tasks = [t for t in filtered_tasks if t.conversation_id == conversation_id]
            yield f"  🔸 按会话ID过滤后: {len(filtered_tasks)} 个任务\n"
        
        if status:
            filtered_tasks = [t for t in filtered_tasks if t.status == status]
            yield f"  🔸 按状态过滤后: {len(filtered_tasks)} 个任务\n"
        
        if task_title:
            filtered_tasks = [t for t in filtered_tasks if task_title.lower() in t.task_title.lower()]
            yield f"  🔸 按标题关键词过滤后: {len(filtered_tasks)} 个任务\n"
        
        yield f"\n📊 找到 {len(filtered_tasks)} 个匹配的任务\n"
        
        if filtered_tasks:
            yield "\n📝 匹配的任务列表:\n"
            for i, task in enumerate(filtered_tasks, 1):
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅'}.get(task.status, '❓')
                yield f"  {i}. {status_emoji} {task.task_title}\n"
                yield f"     📁 文件: {task.target_file}\n"
                yield f"     🔧 操作: {task.operation}\n"
                yield f"     🆔 ID: {task.id}\n"
                yield f"     📅 创建时间: {task.created_at}\n\n"
                await asyncio.sleep(0.1)  # 模拟处理时间
        else:
            yield "ℹ️ 没有找到匹配的任务\n"
    

    
    def update_data_dir(self, new_data_dir: str) -> Dict[str, Any]:
        """更新数据目录"""
        try:
            old_dir = self.data_dir
            self.data_dir = Path(new_data_dir)
            self.data_dir.mkdir(exist_ok=True)
            

            
            logger.info(f"数据目录已更新: {old_dir} -> {self.data_dir}")
            return {
                'success': True,
                'message': f'数据目录已更新为: {self.data_dir.absolute()}',
                'old_dir': str(old_dir),
                'new_dir': str(self.data_dir)
            }
        except Exception as e:
            logger.error(f"更新数据目录失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    

    
    def set_auto_save(self, auto_save: bool):
        """设置自动保存"""
        self.auto_save = auto_save