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
    session_id: str
    status: str = "pending"  # pending, in_progress, completed
    created_at: str = None
    updated_at: str = None
    viewed_count: int = 0  # 记录任务被查看的次数
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


@dataclass
class TaskExecution:
    """任务执行过程数据模型"""
    task_id: str
    execution_process: str
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
        
        # 创建执行过程存储目录
        self.execution_dir = self.data_dir / "executions"
        self.execution_dir.mkdir(exist_ok=True)
        
        logger.info(f"TaskManagerService initialized with data dir: {self.data_dir.absolute()}")
    
    def _get_data_file_path(self, session_id: str) -> Path:
        """获取数据文件路径"""
        filename = f"{session_id}.json"
        return self.data_dir / filename
    
    def _get_execution_file_path(self, task_id: str) -> Path:
        """获取任务执行过程文件路径"""
        filename = f"{task_id}_execution.json"
        return self.execution_dir / filename
    

    
    def _load_tasks_from_file(self, file_path: Path) -> Dict[str, Task]:
        """从指定文件加载任务数据"""
        tasks = {}
        if file_path.exists():
            try:
                # 使用errors='replace'参数处理可能的编码错误
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        # 为旧数据提供 viewed_count 默认值
                        if 'viewed_count' not in task_data:
                            task_data['viewed_count'] = 0
                        task = Task(**task_data)
                        tasks[task.id] = task

            except Exception as e:
                logger.error(f"加载任务数据失败 {file_path}: {e}")
        return tasks
    
    def _save_tasks_to_file(self, session_id: str, tasks: List[Task]):
        """保存任务数据到指定文件"""
        try:
            file_path = self._get_data_file_path(session_id)
            data = {
                'session_id': session_id,
                'tasks': [asdict(task) for task in tasks],
                'updated_at': datetime.now().isoformat()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                # 设置ensure_ascii=True以避免UTF-8编码问题
                json.dump(data, f, ensure_ascii=True, indent=2)
            logger.info(f"已保存 {len(tasks)} 个任务到 {file_path}")
        except Exception as e:
            logger.error(f"保存任务数据失败: {e}")
    
    def _save_task_execution(self, task_execution: TaskExecution):
        """保存任务执行过程到文件"""
        try:
            file_path = self._get_execution_file_path(task_execution.task_id)
            data = asdict(task_execution)
            with open(file_path, 'w', encoding='utf-8') as f:
                # 设置ensure_ascii=True以避免UTF-8编码问题
                json.dump(data, f, ensure_ascii=True, indent=2)
            logger.info(f"已保存任务执行过程到 {file_path}")
        except Exception as e:
            logger.error(f"保存任务执行过程失败: {e}")
    
    def _load_task_execution(self, task_id: str) -> Optional[TaskExecution]:
        """从文件加载任务执行过程"""
        file_path = self._get_execution_file_path(task_id)
        if file_path.exists():
            try:
                # 使用errors='replace'参数处理可能的编码错误
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                    return TaskExecution(**data)
            except Exception as e:
                logger.error(f"加载任务执行过程失败 {file_path}: {e}")
        return None
    
    def _get_task_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        # 遍历所有文件查找
        for data_file in self.data_dir.glob("*.json"):
            file_tasks = self._load_tasks_from_file(data_file)
            if task_id in file_tasks:
                return file_tasks[task_id]
        
        return None
    
    def _get_tasks_by_session(self, session_id: str) -> List[Task]:
        """获取指定会话的任务"""
        file_path = self._get_data_file_path(session_id)
        file_tasks = self._load_tasks_from_file(file_path)
        return list(file_tasks.values())
    

    
    async def create_tasks_stream(self, tasks_data: List[Dict[str, Any]], 
                                session_id: str) -> AsyncGenerator[str, None]:
        """创建或修改任务（流式输出）
        
        如果session_id对应的文件已存在，则直接覆盖该文件中的任务
        """
        yield f"开始处理 {len(tasks_data)} 个任务...\n"
        
        created_tasks = []
        errors = []
        
        # 加载现有任务（仅用于日志记录）
        file_path = self._get_data_file_path(session_id)
        existing_tasks = {}
        
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
                
                # 直接创建新任务，不考虑修改现有任务
                # 如果提供了task_id，则使用提供的ID，否则生成新ID
                task_id = task_data.get('task_id', str(uuid.uuid4()))
                # 创建新任务
                task = Task(
                    id=task_id,
                    task_title=task_data['task_title'],
                    target_file=task_data['target_file'],
                    operation=task_data['operation'],
                    specific_operations=task_data['specific_operations'],
                    related=task_data['related'],
                    dependencies=task_data['dependencies'],
                    session_id=session_id,
                    status=task_data.get('status', 'pending')
                )
                
                created_tasks.append(task)
                yield f"[{i+1}/{len(tasks_data)}] 创建任务: {task.task_title} (ID: {task_id})\n"
                
            except Exception as e:
                error_msg = f"[{i+1}/{len(tasks_data)}] 处理任务失败: {str(e)}\n"
                yield error_msg
                errors.append({
                    'index': i,
                    'error': str(e)
                })
        
        # 直接保存到文件，覆盖原有内容
        tasks_to_save = created_tasks
        
        if tasks_to_save:
            self._save_tasks_to_file(session_id, tasks_to_save)
            yield f"\n✅ 成功创建 {len(created_tasks)} 个任务并保存到文件: {session_id}.json\n"
        
        if errors:
            yield f"❌ 失败 {len(errors)} 个任务\n"
        
        yield f"\n📊 总结: 成功创建 {len(created_tasks)} 个任务，失败 {len(errors)} 个\n"
    
    async def get_next_executable_task_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """获取下一个可执行任务的流式版本 - 完全按需加载
        
        修改逻辑：如果已有执行中的任务，则返回该任务而不是查找新任务
        """
        yield "🔍 正在查找可执行任务...\n"
        
        # 从文件加载任务
        file_path = self._get_data_file_path(session_id)
        if not file_path.exists():
            yield "❌ 未找到任务文件\n"
            return
        
        tasks_dict = self._load_tasks_from_file(file_path)
        if not tasks_dict:
            yield "❌ 任务文件为空\n"
            return
        
        # 首先检查是否已有执行中的任务
        in_progress_tasks = [task for task in tasks_dict.values() if task.status == 'in_progress']
        
        if in_progress_tasks:
            # 如果有执行中的任务，返回第一个（按创建时间排序）
            current_task = min(in_progress_tasks, key=lambda t: t.created_at)
            
            # 增加查看次数
            current_task.viewed_count += 1
            current_task.updated_at = datetime.now().isoformat()
            
            # 保存更新后的任务数据
            tasks_to_save = list(tasks_dict.values())
            self._save_tasks_to_file(session_id, tasks_to_save)
            
            # 根据查看次数给出不同的提示
            if current_task.viewed_count == 1:
                yield f"🔄 发现正在执行的任务: {current_task.task_title} (ID: {current_task.id})\n"
            else:
                yield f"🔄 这个任务你已经看过了！任务: {current_task.task_title} (ID: {current_task.id})\n"
                yield f"📊 查看次数: {current_task.viewed_count} 次\n"
                yield f"⚠️ 这是同一个任务，你之前已经查看过 {current_task.viewed_count - 1} 次\n"
            
            yield f"📄 目标文件: {current_task.target_file}\n"
            yield f"🔧 操作类型: {current_task.operation}\n"
            yield f"📝 具体操作: {current_task.specific_operations}\n"
            yield f"🔗 相关信息: {current_task.related}\n"
            yield f"📊 依赖关系: {current_task.dependencies}\n"
            yield f"⚠️ 请先完成当前任务再获取下一个任务\n"
            return
        
        # 如果没有执行中的任务，查找可执行任务
        executable_tasks = []
        for task in tasks_dict.values():
            if task.status == 'pending':
                # 检查依赖是否已完成（completed或dev_completed都算完成）
                dependencies_met = True
                if task.dependencies and task.dependencies != "无":
                    for dep_id in task.dependencies.split(','):
                        dep_id = dep_id.strip()
                        if dep_id and dep_id in tasks_dict and tasks_dict[dep_id].status not in ['completed', 'dev_completed']:
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
        self._save_tasks_to_file(session_id, tasks_to_save)
        
        yield f"✅ 找到新的可执行任务: {next_task.task_title} (ID: {next_task.id})\n"
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
        session_id = None
        file_path = None
        
        # 遍历所有任务文件查找任务
        for file in self.data_dir.glob("*.json"):
            try:
                tasks_dict = self._load_tasks_from_file(file)
                if task_id in tasks_dict:
                    task_found = tasks_dict[task_id]
                    session_id = file.stem
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
        
        self._save_tasks_to_file(session_id, tasks_to_save)
        yield f"✅ 任务 '{task_found.task_title}' 已标记为完成\n"
        yield f"💾 已保存到文件: {session_id}.json\n"
    
    async def get_task_stats_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """获取任务统计的流式版本 - 完全按需加载"""
        yield "📊 正在统计任务信息...\n"
        
        # 从指定会话文件加载任务
        file_path = self._get_data_file_path(session_id)
        if not file_path.exists():
            yield f"❌ 会话 {session_id} 的任务文件不存在\n"
            return
        
        tasks_dict = self._load_tasks_from_file(file_path)
        all_tasks = list(tasks_dict.values())
        
        scope = f"会话 {session_id}"
        yield f"🔍 统计范围: {scope}\n"
        
        if not all_tasks:
            yield f"ℹ️ {scope}没有任务\n"
            return
        
        stats = {
            'total': len(all_tasks),
            'pending': len([t for t in all_tasks if t.status == 'pending']),
            'in_progress': len([t for t in all_tasks if t.status == 'in_progress']),
            'dev_completed': len([t for t in all_tasks if t.status == 'dev_completed']),
            'completed': len([t for t in all_tasks if t.status == 'completed'])
        }
        
        yield f"📈 {scope}任务统计:\n"
        yield f"  📋 总计: {stats['total']} 个\n"
        yield f"  ⏳ 待执行: {stats['pending']} 个\n"
        yield f"  🔄 进行中: {stats['in_progress']} 个\n"
        yield f"  🚀 开发完成: {stats['dev_completed']} 个\n"
        yield f"  ✅ 已完成: {stats['completed']} 个\n"
        
        if all_tasks:
            yield "\n📝 任务列表:\n"
            for i, task in enumerate(all_tasks, 1):
                status_emoji = {
                    'pending': '⏳', 
                    'in_progress': '🔄', 
                    'dev_completed': '🚀',
                    'completed': '✅'
                }.get(task.status, '❓')
                yield f"  {i}. {status_emoji} {task.task_title} (ID: {task.id})\n"
    

    

    
    def update_data_dir(self, new_data_dir: str) -> Dict[str, Any]:
        """更新数据目录"""
        try:
            old_dir = self.data_dir
            self.data_dir = Path(new_data_dir)
            self.data_dir.mkdir(exist_ok=True)
            
            # 更新执行过程存储目录
            self.execution_dir = self.data_dir / "executions"
            self.execution_dir.mkdir(exist_ok=True)
            
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
    
    async def get_current_executing_task_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """获取当前正在执行或开发完成的任务的流式版本
        
        Args:
            session_id: 会话ID
            
        Yields:
            str: 流式输出的任务信息
        """
        yield "🔍 正在查找当前执行中或开发完成的任务...\n"
        
        # 从文件加载任务
        file_path = self._get_data_file_path(session_id)
        if not file_path.exists():
            yield "❌ 未找到任务文件\n"
            return
        
        tasks_dict = self._load_tasks_from_file(file_path)
        if not tasks_dict:
            yield "❌ 任务文件为空\n"
            return
        
        # 查找执行中或开发完成的任务
        active_tasks = [task for task in tasks_dict.values() if task.status in ['in_progress', 'dev_completed']]
        
        if not active_tasks:
            yield "ℹ️ 当前没有正在执行或开发完成的任务\n"
            return
        
        # 优先返回in_progress任务，如果没有则返回最新的dev_completed任务
        in_progress_tasks = [task for task in active_tasks if task.status == 'in_progress']
        dev_completed_tasks = [task for task in active_tasks if task.status == 'dev_completed']
        
        if in_progress_tasks:
            current_task = min(in_progress_tasks, key=lambda t: t.created_at)
            status_desc = "执行中"
        else:
            current_task = max(dev_completed_tasks, key=lambda t: t.updated_at)
            status_desc = "开发完成"
        
        yield f"✅ 找到当前{status_desc}的任务\n"
        yield f"📋 任务标题: {current_task.task_title}\n"
        yield f"🆔 任务ID: {current_task.id}\n"
        yield f"📊 任务状态: {current_task.status}\n"
        yield f"📄 目标文件: {current_task.target_file}\n"
        yield f"🔧 操作类型: {current_task.operation}\n"
        yield f"📝 具体操作: {current_task.specific_operations}\n"
        yield f"🔗 相关信息: {current_task.related}\n"
        yield f"📊 依赖关系: {current_task.dependencies}\n"
        yield f"📅 创建时间: {current_task.created_at}\n"
        yield f"🔄 更新时间: {current_task.updated_at}\n"
        yield f"👀 查看次数: {current_task.viewed_count}\n"
        
        # 查询任务执行过程
        task_execution = self._load_task_execution(current_task.id)
        if task_execution:
            yield f"\n📋 执行过程信息:\n"
            yield f"💾 保存时间: {task_execution.created_at}\n"
            yield f"🔄 更新时间: {task_execution.updated_at}\n"
            yield f"📝 执行过程:\n{task_execution.execution_process}\n"
        else:
            yield f"\n⚠️ 该任务暂无执行过程记录\n"
        
        if len(active_tasks) > 1:
            yield f"⚠️ 注意: 发现 {len(active_tasks)} 个活跃任务（{len(in_progress_tasks)}个执行中，{len(dev_completed_tasks)}个开发完成），显示优先级最高的任务\n"
    
    async def save_task_execution_stream(self, task_id: str, execution_process: str) -> AsyncGenerator[str, None]:
        """保存任务执行过程的流式版本，并将任务状态改为dev_completed"""
        yield f"💾 正在保存任务 {task_id} 的执行过程...\n"
        
        # 验证任务是否存在
        task = self._get_task_by_id(task_id)
        if not task:
            yield f"❌ 任务 {task_id} 不存在\n"
            return
        
        # 创建任务执行过程对象
        task_execution = TaskExecution(
            task_id=task_id,
            execution_process=execution_process
        )
        
        # 保存执行过程到文件
        self._save_task_execution(task_execution)
        
        # 更新任务状态为dev_completed
        original_status = task.status
        task.status = 'dev_completed'
        task.updated_at = datetime.now().isoformat()
        
        # 保存更新后的任务数据
        session_id = task.session_id
        file_path = self._get_data_file_path(session_id)
        tasks_dict = self._load_tasks_from_file(file_path)
        tasks_dict[task_id] = task
        tasks_to_save = list(tasks_dict.values())
        self._save_tasks_to_file(session_id, tasks_to_save)
        
        yield f"✅ 任务执行过程已保存\n"
        yield f"📋 任务标题: {task.task_title}\n"
        yield f"🆔 任务ID: {task_id}\n"
        yield f"📝 执行过程长度: {len(execution_process)} 字符\n"
        yield f"💾 保存时间: {task_execution.created_at}\n"
        yield f"🔄 任务状态: {original_status} → dev_completed\n"