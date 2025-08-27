#!/usr/bin/env python3
"""
文件监控模块
基于 watchdog 的实时文件监控功能，用于自动更新 Whoosh 索引
"""

import os
import re
import json
import hashlib
import time
import threading
import logging
from datetime import datetime
from queue import Queue, Empty
from pathlib import Path
from typing import Set, Dict, Any, Optional

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("file_monitor")


class SmartIndexManager:
    """智能索引管理器"""
    
    def __init__(self, root_dir: str, index_dir: str = None):
        self.root_dir = Path(root_dir)
        # 如果没有指定索引目录，使用服务启动目录下的data目录
        if index_dir is None:
            service_root = Path(__file__).parent
            data_dir = service_root / "data"
            data_dir.mkdir(exist_ok=True)
            project_name = self.root_dir.name
            self.index_dir = data_dir / f"whoosh_index_{project_name}"
        else:
            self.index_dir = Path(index_dir)
        self.supported_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.htm', '.css', '.scss',
            '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.log',
            '.sql', '.sh', '.bat', '.ps1', '.php', '.rb', '.go', '.rs', '.cpp',
            '.c', '.h', '.hpp', '.java', '.kt', '.swift', '.dart', '.vue', '.jsx',
            '.tsx', '.svelte', '.astro', '.toml', '.env', '.gitignore', '.dockerfile',
            '.makefile', '.cmake', '.gradle', '.properties', '.csv', '.tsv'
        }
        self.ignore_dirs = {
            '.git', '.svn', '.hg', '__pycache__', 'node_modules', '.vscode',
            '.idea', 'dist', 'build', 'target', '.next', '.nuxt', 'coverage',
            '.pytest_cache', '.mypy_cache', 'venv', 'env', '.env'
        }
        self.metadata_file = self.index_dir / "file_metadata.json"
        self.lock = threading.RLock()  # 线程安全锁
        
        # 创建schema
        self.schema = Schema(
            path=ID(stored=True, unique=True), 
            content=TEXT(stored=True),
            modified_time=DATETIME(stored=True),
            file_hash=ID(stored=True)
        )
        
        # 初始化索引
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """确保索引目录存在"""
        if not self.index_dir.exists():
            self.index_dir.mkdir(parents=True)
        
        if not exists_in(str(self.index_dir)):
            ix = create_in(str(self.index_dir), self.schema)
            logger.info("创建新索引...")
        else:
            logger.info("索引已存在")
    
    def _should_ignore_path(self, path: Path) -> bool:
        """检查路径是否应该被忽略"""
        for part in path.parts:
            if part in self.ignore_dirs:
                return True
            # 特殊处理：忽略所有以whoosh_index开头的目录
            if part.startswith('whoosh_index'):
                return True
        return False
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """计算文件内容的MD5哈希值"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return None
    
    def load_file_metadata(self) -> Dict[str, Any]:
        """加载文件元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")
        return {}
    
    def save_file_metadata(self, metadata: Dict[str, Any]):
        """保存文件元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
    
    def scan_current_files(self) -> Dict[str, Dict[str, Any]]:
        """扫描当前目录中的所有文件"""
        current_files = {}
        for file_path in self.root_dir.rglob('*'):
            if not file_path.is_file():
                continue
                
            # 检查是否应该忽略此路径
            relative_path = file_path.relative_to(self.root_dir)
            if self._should_ignore_path(relative_path):
                continue
                
            # 只处理支持的文本文件
            if file_path.suffix in self.supported_extensions:
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    file_hash = self.get_file_hash(file_path)
                    if file_hash:
                        current_files[str(file_path)] = {
                            'mtime': mtime,
                            'hash': file_hash
                        }
                except Exception as e:
                    logger.error(f"扫描文件 {file_path} 时出错: {e}")
        return current_files
    
    def update_single_file(self, file_path: str, action: str = "update"):
        """更新单个文件的索引"""
        with self.lock:
            try:
                ix = open_dir(str(self.index_dir))
                writer = ix.writer()
                
                if action == "delete":
                    logger.info(f"从索引中删除: {file_path}")
                    writer.delete_by_term('path', file_path)
                    
                    # 更新元数据
                    metadata = self.load_file_metadata()
                    if file_path in metadata:
                        del metadata[file_path]
                        self.save_file_metadata(metadata)
                
                elif action in ["create", "update"]:
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists() and file_path_obj.suffix in self.supported_extensions:
                        try:
                            # 检查是否应该忽略此路径
                            relative_path = file_path_obj.relative_to(self.root_dir)
                            if self._should_ignore_path(relative_path):
                                writer.commit()
                                return
                                
                            mtime = datetime.fromtimestamp(file_path_obj.stat().st_mtime)
                            file_hash = self.get_file_hash(file_path_obj)
                            
                            if file_hash:
                                # 检查是否真的需要更新
                                metadata = self.load_file_metadata()
                                old_info = metadata.get(file_path, {})
                                
                                if file_hash != old_info.get('hash', ''):
                                    logger.info(f"{'创建' if action == 'create' else '更新'}索引: {file_path}")
                                    
                                    # 删除旧文档（如果存在）
                                    writer.delete_by_term('path', file_path)
                                    
                                    # 读取文件内容
                                    with open(file_path_obj, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    
                                    # 添加新文档
                                    writer.add_document(
                                        path=file_path,
                                        content=content,
                                        modified_time=mtime,
                                        file_hash=file_hash
                                    )
                                    
                                    # 更新元数据
                                    metadata[file_path] = {
                                        'mtime': mtime,
                                        'hash': file_hash
                                    }
                                    self.save_file_metadata(metadata)
                                else:
                                    logger.debug(f"文件内容未变化，跳过: {file_path}")
                        
                        except Exception as e:
                            logger.error(f"处理文件 {file_path} 时出错: {e}")
                
                writer.commit()
                
            except Exception as e:
                logger.error(f"更新索引时出错: {e}")
    
    def full_index_update(self):
        """完整的增量索引更新"""
        with self.lock:
            logger.info("开始完整索引更新...")
            start_time = time.time()
            
            # 加载之前的文件元数据
            old_metadata = self.load_file_metadata()
            
            # 扫描当前文件
            current_files = self.scan_current_files()
            
            ix = open_dir(str(self.index_dir))
            writer = ix.writer()
            
            # 统计信息
            added_count = 0
            updated_count = 0
            deleted_count = 0
            
            try:
                # 1. 处理删除的文件
                for old_path in old_metadata.keys():
                    if old_path not in current_files:
                        logger.info(f"删除文件: {old_path}")
                        writer.delete_by_term('path', old_path)
                        deleted_count += 1
                
                # 2. 处理新增和修改的文件
                for file_path, file_info in current_files.items():
                    should_update = False
                    action = ""
                    
                    if file_path not in old_metadata:
                        # 新文件
                        should_update = True
                        action = "新增"
                        added_count += 1
                    else:
                        old_info = old_metadata[file_path]
                        # 检查文件是否有变化（通过哈希值比较）
                        if file_info['hash'] != old_info.get('hash', ''):
                            should_update = True
                            action = "更新"
                            updated_count += 1
                            # 删除旧文档
                            writer.delete_by_term('path', file_path)
                    
                    if should_update:
                        try:
                            logger.info(f"{action}文件: {file_path}")
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            writer.add_document(
                                path=file_path,
                                content=content,
                                modified_time=file_info['mtime'],
                                file_hash=file_info['hash']
                            )
                        except Exception as e:
                            logger.error(f"处理文件 {file_path} 时出错: {e}")
                
                # 提交更改
                writer.commit()
                
                # 保存新的元数据
                self.save_file_metadata(current_files)
                
                elapsed_time = time.time() - start_time
                logger.info(f"索引更新完成！耗时: {elapsed_time:.2f}秒")
                logger.info(f"新增: {added_count} 个文件")
                logger.info(f"更新: {updated_count} 个文件")
                logger.info(f"删除: {deleted_count} 个文件")
                
            except Exception as e:
                logger.error(f"更新索引时出错: {e}")
                writer.cancel()
    
    def get_index_stats(self) -> str:
        """获取索引统计信息"""
        if not exists_in(str(self.index_dir)):
            return "索引不存在"
        
        with self.lock:
            ix = open_dir(str(self.index_dir))
            with ix.searcher() as searcher:
                doc_count = searcher.doc_count()
                return f"索引包含 {doc_count} 个文档"


class FileWatchHandler(FileSystemEventHandler):
    """文件监控事件处理器"""
    
    def __init__(self, index_manager: SmartIndexManager, update_queue: Queue):
        self.index_manager = index_manager
        self.update_queue = update_queue
        self.supported_extensions = index_manager.supported_extensions
        self.last_events = {}  # 防止重复事件
        self.event_delay = 0.5  # 事件去重延迟
    
    def _should_process_file(self, file_path: str) -> bool:
        """判断是否应该处理这个文件"""
        file_path_obj = Path(file_path)
        return (not file_path_obj.name.startswith('.') and 
                file_path_obj.suffix in self.supported_extensions and
                str(self.index_manager.index_dir) not in file_path)
    
    def _debounce_event(self, event_type: str, file_path: str) -> bool:
        """事件去重，避免重复处理"""
        current_time = time.time()
        event_key = f"{event_type}:{file_path}"
        
        if event_key in self.last_events:
            if current_time - self.last_events[event_key] < self.event_delay:
                return False
        
        self.last_events[event_key] = current_time
        return True
    
    def on_created(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            if self._debounce_event("created", event.src_path):
                self.update_queue.put(("create", event.src_path))
    
    def on_modified(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            if self._debounce_event("modified", event.src_path):
                self.update_queue.put(("update", event.src_path))
    
    def on_deleted(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            if self._debounce_event("deleted", event.src_path):
                self.update_queue.put(("delete", event.src_path))
    
    def on_moved(self, event):
        if not event.is_directory:
            # 处理文件移动/重命名
            if self._should_process_file(event.src_path):
                self.update_queue.put(("delete", event.src_path))
            if self._should_process_file(event.dest_path):
                self.update_queue.put(("create", event.dest_path))


class RealTimeIndexMonitor:
    """实时索引监控器"""
    
    def __init__(self, root_dir: str, index_dir: str = None):
        self.root_dir = root_dir
        # 如果没有指定索引目录，使用服务启动目录下的data目录
        if index_dir is None:
            service_root = Path(__file__).parent
            data_dir = service_root / "data"
            data_dir.mkdir(exist_ok=True)
            project_name = Path(root_dir).name
            self.index_dir = str(data_dir / f"whoosh_index_{project_name}")
        else:
            self.index_dir = index_dir
        self.index_manager = SmartIndexManager(root_dir, self.index_dir)
        self.update_queue = Queue()
        self.observer = None
        self.update_thread = None
        self.running = False
        self.batch_update_delay = 1.0  # 批量更新延迟
    
    def _update_worker(self):
        """更新工作线程"""
        pending_updates = {}
        
        while self.running:
            try:
                # 收集一段时间内的所有更新
                try:
                    action, file_path = self.update_queue.get(timeout=0.1)
                    pending_updates[file_path] = action
                    
                    # 继续收集更多更新（批量处理）
                    start_time = time.time()
                    while time.time() - start_time < self.batch_update_delay:
                        try:
                            action, file_path = self.update_queue.get(timeout=0.1)
                            pending_updates[file_path] = action
                        except Empty:
                            break
                    
                    # 批量处理更新
                    if pending_updates:
                        logger.info(f"批量处理 {len(pending_updates)} 个文件更新...")
                        for file_path, action in pending_updates.items():
                            self.index_manager.update_single_file(file_path, action)
                        pending_updates.clear()
                        logger.info("批量更新完成")
                
                except Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"更新工作线程出错: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        logger.info(f"初始化索引...")
        self.index_manager.full_index_update()
        logger.info(self.index_manager.get_index_stats())
        
        # 启动文件监控
        event_handler = FileWatchHandler(self.index_manager, self.update_queue)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.root_dir, recursive=True)
        
        # 启动更新工作线程
        self.running = True
        self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self.update_thread.start()
        
        # 启动文件系统监控
        self.observer.start()
        
        logger.info(f"开始实时监控目录: {self.root_dir}")
        logger.info(f"支持的文件类型: {self.index_manager.supported_extensions}")
    
    def stop_monitoring(self):
        """停止监控"""
        logger.info("正在停止监控...")
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        if self.update_thread:
            self.update_thread.join(timeout=2)
        
        logger.info("监控已停止")
    
    def manual_update(self):
        """手动触发完整更新"""
        logger.info("手动触发完整索引更新...")
        self.index_manager.full_index_update()
        logger.info(self.index_manager.get_index_stats())
    
    def is_running(self) -> bool:
        """检查监控是否正在运行"""
        return self.running and self.observer and self.observer.is_alive()