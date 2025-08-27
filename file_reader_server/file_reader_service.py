#!/usr/bin/env python3
"""
文件读取服务模块
提供文件读取、搜索、批量处理等核心功能
"""

import os
import re
import json
import asyncio
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.qparser import QueryParser

# 导入文件监控模块
try:
    from file_monitor import RealTimeIndexMonitor
except ImportError:
    RealTimeIndexMonitor = None

logger = logging.getLogger("file_reader_service")


class FileReaderService:
    """文件读取服务类"""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        # 将索引目录放在服务启动目录的data目录下，使用项目文件夹名称区分
        service_root = Path(__file__).parent
        data_dir = service_root / "data"
        data_dir.mkdir(exist_ok=True)
        project_name = self.project_root.name
        self.index_dir = data_dir / f"whoosh_index_{project_name}"
        self.monitor = None  # 文件监控器

        # 支持的文本文件扩展名
        self.text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.htm', '.css', '.scss',
            '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.log',
            '.sql', '.sh', '.bat', '.ps1', '.php', '.rb', '.go', '.rs', '.cpp',
            '.c', '.h', '.hpp', '.java', '.kt', '.swift', '.dart', '.vue', '.jsx',
            '.tsx', '.svelte', '.astro', '.toml', '.env', '.gitignore', '.dockerfile',
            '.makefile', '.cmake', '.gradle', '.properties', '.csv', '.tsv'
        }

        # 默认忽略的目录
        self.ignore_dirs = {
            '.git', '.svn', '.hg', '__pycache__', 'node_modules', '.vscode',
            '.idea', 'dist', 'build', 'target', '.next', '.nuxt', 'coverage',
            '.pytest_cache', '.mypy_cache', 'venv', 'env', '.env', 'whoosh_index'
        }

        # 在初始化时创建索引
        self._ensure_index_exists()
        
        # 初始化监控器（如果可用）并默认启动
        if RealTimeIndexMonitor:
            self.monitor = RealTimeIndexMonitor(str(self.project_root), str(self.index_dir))
            # 默认启动文件监控
            try:
                self.monitor.start_monitoring()
                logger.info("文件监控已默认启动")
            except Exception as e:
                logger.error(f"启动文件监控失败: {e}")
        
        logger.info(f"File Reader Service initialized with project root: {self.project_root}")

    def _should_ignore_path(self, path: Path) -> bool:
        """检查路径是否应该被忽略"""
        # 检查路径中的任何部分是否在忽略列表中
        for part in path.parts:
            if part in self.ignore_dirs:
                return True
            # 特殊处理：忽略所有以whoosh_index开头的目录
            if part.startswith('whoosh_index'):
                return True
        return False

    def _resolve_file_path(self, file_path: str) -> Path:
        """解析文件路径，支持相对路径和绝对路径"""
        path = Path(file_path)
        if path.is_absolute():
            return path
        else:
            return self.project_root / path

    def _compress_content(self, content: str, show_line_numbers: bool = True) -> str:
        """压缩内容，去掉空行并显示行号"""
        lines = content.split('\n')
        result_lines = []

        for i, line in enumerate(lines, 1):
            if line.strip():  # 只保留非空行
                if show_line_numbers:
                    result_lines.append(f"{i}:{line}")
                else:
                    result_lines.append(line)

        return '\n'.join(result_lines)

    def _ensure_index_exists(self):
        """确保索引存在，如果不存在则创建"""
        if not self.index_dir.exists():
            self.index_dir.mkdir(parents=True)
            
        if not exists_in(str(self.index_dir)):
            logger.info("索引不存在，正在创建新索引...")
            self._create_or_update_index()
        else:
            logger.info("索引已存在")
    
    def _create_or_update_index(self):
        """创建或更新Whoosh索引"""
        schema = Schema(
            path=ID(stored=True, unique=True), 
            content=TEXT(stored=True),
            modified_time=DATETIME(stored=True),
            file_hash=ID(stored=True)
        )
        
        if not self.index_dir.exists():
            self.index_dir.mkdir(parents=True)
            
        if exists_in(str(self.index_dir)):
            ix = open_dir(str(self.index_dir))
        else:
            ix = create_in(str(self.index_dir), schema)
            
        writer = ix.writer()
        
        # 清空现有索引
        writer.delete_by_term('path', '*')
        
        for file_path in self.project_root.rglob('*'):
            if not file_path.is_file():
                continue
                
            # 检查是否应该忽略此路径
            relative_path = file_path.relative_to(self.project_root)
            if self._should_ignore_path(relative_path):
                continue
                
            # 只处理支持的文本文件
            if file_path.suffix in self.text_extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 计算文件哈希和修改时间
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                    
                    writer.add_document(
                        path=str(file_path), 
                        content=content,
                        modified_time=mtime,
                        file_hash=file_hash
                    )
                except (UnicodeDecodeError, PermissionError):
                    continue
                    
        writer.commit()
        logger.info("Whoosh索引构建完成")
        
    def _get_line_numbers(self, file_path: str, keyword: str, max_matches: int = 10):
        """从文件中提取匹配关键词的行号和内容，同时返回文件总行数"""
        matches = []
        total_lines = 0
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    total_lines = line_num  # 记录总行数
                    if pattern.search(line):
                        # 高亮行内容
                        highlighted_line = pattern.sub(lambda m: f"**{m.group(0)}**", line.strip())
                        matches.append({
                            "line_number": line_num,
                            "content": highlighted_line
                        })
                    if len(matches) >= max_matches:
                        # 即使找到足够的匹配，也要继续读取以获取总行数
                        for remaining_line in f:
                            total_lines += 1
                        break
        except Exception as e:
            logger.error(f"读取文件 {file_path} 出错: {e}")
            
        return matches, total_lines

    async def read_file_lines_stream(self, file_path: str, start_line: int, end_line: int) -> AsyncGenerator[str, None]:
        """流式读取文件指定行范围"""
        try:
            # 参数验证
            if not file_path:
                yield json.dumps({"error": "缺少必要参数 file_path"}, ensure_ascii=False)
                return

            if start_line < 1:
                yield json.dumps({"error": "start_line 必须是大于0的整数（1-based行号）"}, ensure_ascii=False)
                return

            if end_line < start_line:
                yield json.dumps({"error": "end_line 必须是大于等于 start_line 的整数"}, ensure_ascii=False)
                return

            # 解析文件路径
            resolved_path = self._resolve_file_path(file_path)

            if not resolved_path.exists():
                yield json.dumps({"error": f"文件不存在 {resolved_path}"}, ensure_ascii=False)
                return

            if not resolved_path.is_file():
                yield json.dumps({"error": f"路径不是文件 {resolved_path}"}, ensure_ascii=False)
                return

            # 先发送文件信息
            yield json.dumps({
                "type": "file_info",
                "file_path": str(resolved_path),
                "request_range": f"{start_line}-{end_line}"
            }, ensure_ascii=False)

            # 读取文件内容
            with open(resolved_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)

            # 调整行号范围
            actual_start = max(1, start_line)
            actual_end = min(total_lines, end_line)

            if actual_start > total_lines:
                yield json.dumps({
                    "error": f"起始行号 {start_line} 超出文件总行数 {total_lines}"
                }, ensure_ascii=False)
                return

            # 发送总行数信息
            yield json.dumps({
                "type": "meta",
                "total_lines": total_lines,
                "actual_range": f"{actual_start}-{actual_end}"
            }, ensure_ascii=False)

            # 流式输出内容
            for i in range(actual_start - 1, actual_end):
                line_content = all_lines[i].rstrip('\n')
                if line_content.strip():  # 只输出非空行
                    yield json.dumps({
                        "type": "content",
                        "line_number": i + 1,
                        "content": line_content
                    }, ensure_ascii=False)

                # 每10行暂停一下，允许其他任务执行
                if (i + 1) % 10 == 0:
                    await asyncio.sleep(0.01)

            # 发送完成信号
            yield json.dumps({
                "type": "complete",
                "message": f"成功读取文件 {file_path} 第 {actual_start}-{actual_end} 行"
            }, ensure_ascii=False)

        except UnicodeDecodeError:
            yield json.dumps({"error": f"文件编码不支持，无法读取 {file_path}"}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"读取文件时发生异常: {e}")
            yield json.dumps({"error": f"读取文件失败 - {str(e)}"}, ensure_ascii=False)

    async def search_files_by_content_stream(self, query_text: str, limit: int = 50,
                                             case_sensitive: bool = False, context_lines: int = 20,
                                             file_extensions: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        """使用Whoosh进行流式搜索文件内容，只返回文件地址和匹配行详情"""
        try:
            if not query_text:
                yield json.dumps({"error": "缺少搜索关键词"}, ensure_ascii=False)
                return

            # 发送搜索开始信号
            yield json.dumps({
                "type": "search_start",
                "query": query_text,
                "limit": limit,
                "case_sensitive": case_sensitive,
                "message": "开始搜索..."
            }, ensure_ascii=False)

            # 检查索引是否存在，如果不存在则创建
            if not exists_in(str(self.index_dir)):
                yield json.dumps({
                    "type": "index_creating",
                    "message": "索引不存在，正在创建索引..."
                }, ensure_ascii=False)
                self._create_or_update_index()
                await asyncio.sleep(0.01)  # 让出控制权
                
                yield json.dumps({
                    "type": "index_complete",
                    "message": "索引创建完成，开始搜索..."
                }, ensure_ascii=False)

            # 使用Whoosh进行搜索
            ix = open_dir(str(self.index_dir))
            results_count = 0
            max_lines_per_file = 10  # 每个文件最多返回的匹配行数

            with ix.searcher() as searcher:
                query = QueryParser("content", ix.schema).parse(query_text)
                results = searcher.search(query, limit=limit)

                for hit in results:
                    file_path = hit['path']
                    
                    # 获取匹配行的详细信息和文件总行数
                    line_matches, total_lines = self._get_line_numbers(file_path, query_text, max_matches=max_lines_per_file)
                    
                    # 计算相对路径
                    try:
                        relative_path = str(Path(file_path).relative_to(self.project_root))
                    except ValueError:
                        relative_path = file_path

                    # 流式输出匹配结果（包含文件地址、匹配行详情和文件总行数）
                    yield json.dumps({
                        "type": "match",
                        "file_path": relative_path,
                        "line_matches": line_matches,
                        "total_matches_in_file": len(line_matches),
                        "total_lines": total_lines
                    }, ensure_ascii=False)

                    results_count += 1
                    
                    # 每处理一个文件暂停一下
                    await asyncio.sleep(0.01)

            # 发送搜索完成信号
            if results_count == 0:
                yield json.dumps({
                    "type": "no_results",
                    "message": f"未找到包含 '{query_text}' 的文件"
                }, ensure_ascii=False)
            else:
                yield json.dumps({
                    "type": "search_complete",
                    "results_count": results_count,
                    "message": f"找到 {results_count} 个匹配文件"
                }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"搜索文件内容时发生异常: {e}")
            yield json.dumps({"error": f"搜索失败 - {str(e)}"}, ensure_ascii=False)

    async def get_files_content_stream(self, file_paths: List[str]) -> AsyncGenerator[str, None]:
        """流式批量读取文件内容"""
        try:
            if not file_paths:
                yield json.dumps({"error": "缺少文件路径列表"}, ensure_ascii=False)
                return

            # 发送开始信号
            yield json.dumps({
                "type": "batch_start",
                "total_files": len(file_paths)
            }, ensure_ascii=False)

            for i, file_path in enumerate(file_paths):
                # 发送当前处理的文件信息
                yield json.dumps({
                    "type": "file_start",
                    "index": i + 1,
                    "file_path": file_path
                }, ensure_ascii=False)

                resolved_path = self._resolve_file_path(file_path)

                if not resolved_path.exists():
                    yield json.dumps({
                        "type": "file_error",
                        "file_path": file_path,
                        "error": "文件不存在"
                    }, ensure_ascii=False)
                    continue

                if not resolved_path.is_file():
                    yield json.dumps({
                        "type": "file_error",
                        "file_path": file_path,
                        "error": "路径不是文件"
                    }, ensure_ascii=False)
                    continue

                try:
                    with open(resolved_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    compressed_content = self._compress_content(content)
                    total_lines = len(content.split('\n'))

                    # 流式输出文件内容
                    yield json.dumps({
                        "type": "file_content",
                        "file_path": file_path,
                        "total_lines": total_lines,
                        "content": compressed_content
                    }, ensure_ascii=False)

                except UnicodeDecodeError:
                    yield json.dumps({
                        "type": "file_error",
                        "file_path": file_path,
                        "error": "文件编码不支持"
                    }, ensure_ascii=False)
                except Exception as e:
                    yield json.dumps({
                        "type": "file_error",
                        "file_path": file_path,
                        "error": f"读取失败: {str(e)}"
                    }, ensure_ascii=False)

                # 每个文件处理完后暂停
                await asyncio.sleep(0.01)

            # 发送完成信号
            yield json.dumps({
                "type": "batch_complete",
                "message": f"批量读取完成，共处理 {len(file_paths)} 个文件"
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"批量读取文件时发生异常: {e}")
            yield json.dumps({"error": f"批量读取失败 - {str(e)}"}, ensure_ascii=False)

    async def get_project_structure_stream(self, max_depth: int = 10, include_hidden: bool = False) -> AsyncGenerator[
        str, None]:
        """流式获取项目结构"""
        try:
            # 发送开始信号
            yield json.dumps({
                "type": "structure_start",
                "project_root": str(self.project_root),
                "max_depth": max_depth
            }, ensure_ascii=False)

            async def build_tree_stream(path: Path, prefix: str = "", depth: int = 0):
                if depth > max_depth:
                    return

                try:
                    # 获取目录下的所有项目
                    entries = list(path.iterdir())

                    # 过滤隐藏文件和忽略的目录
                    if not include_hidden:
                        entries = [e for e in entries if not e.name.startswith('.')]

                    # 过滤忽略的目录
                    entries = [e for e in entries if not (e.is_dir() and e.name in self.ignore_dirs)]

                    # 排序：目录在前，文件在后
                    entries.sort(key=lambda x: (x.is_file(), x.name.lower()))

                    for i, entry in enumerate(entries):
                        is_last = i == len(entries) - 1
                        current_prefix = "└── " if is_last else "├── "
                        next_prefix = "    " if is_last else "│   "

                        if entry.is_dir():
                            yield json.dumps({
                                "type": "directory",
                                "path": str(entry.relative_to(self.project_root)),
                                "display": f"{prefix}{current_prefix}{entry.name}/",
                                "depth": depth
                            }, ensure_ascii=False)

                            # 递归处理子目录
                            async for child_item in build_tree_stream(entry, prefix + next_prefix, depth + 1):
                                yield child_item
                        else:
                            # 只对支持的文本文件计算行数
                            line_info = ""
                            if entry.suffix in self.text_extensions:
                                try:
                                    with open(entry, 'r', encoding='utf-8') as f:
                                        line_count = sum(1 for _ in f)
                                    line_info = f" ({line_count} lines)"
                                except (UnicodeDecodeError, PermissionError):
                                    line_info = " (no access)"
                                except Exception:
                                    line_info = ""

                            yield json.dumps({
                                "type": "file",
                                "path": str(entry.relative_to(self.project_root)),
                                "display": f"{prefix}{current_prefix}{entry.name}{line_info}",
                                "depth": depth
                            }, ensure_ascii=False)

                        # 每10个条目暂停一下
                        if (i + 1) % 10 == 0:
                            await asyncio.sleep(0.01)

                except PermissionError:
                    yield json.dumps({
                        "type": "error",
                        "path": str(path.relative_to(self.project_root)),
                        "display": f"{prefix}❌ Permission denied",
                        "depth": depth
                    }, ensure_ascii=False)

            # 输出根目录
            yield json.dumps({
                "type": "root",
                "display": f"🏗️ Project Structure: {self.project_root.name}"
            }, ensure_ascii=False)

            # 流式构建树结构
            async for item in build_tree_stream(self.project_root):
                yield item

            # 发送完成信号
            yield json.dumps({
                "type": "structure_complete",
                "message": "项目结构生成完成"
            }, ensure_ascii=False)

        except Exception as e:
            logger.info(f"获取项目结构时发生异常: {e}")
            yield json.dumps({"error": f"获取项目结构失败 - {str(e)}"}, ensure_ascii=False)

    def start_monitoring(self) -> Dict[str, Any]:
        """启动文件监控"""
        if not self.monitor:
            if RealTimeIndexMonitor:
                self.monitor = RealTimeIndexMonitor(str(self.project_root), str(self.index_dir))
            else:
                return {"error": "文件监控模块不可用"}
        
        if self.monitor.is_running():
            return {"message": "监控已经在运行中"}
        
        try:
            self.monitor.start_monitoring()
            return {"success": True, "message": "文件监控已启动"}
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}")
            return {"error": f"启动监控失败: {str(e)}"}
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """停止文件监控"""
        if not self.monitor:
            return {"message": "监控器未初始化"}
        
        if not self.monitor.is_running():
            return {"message": "监控未在运行"}
        
        try:
            self.monitor.stop_monitoring()
            return {"success": True, "message": "文件监控已停止"}
        except Exception as e:
            logger.error(f"停止文件监控失败: {e}")
            return {"error": f"停止监控失败: {str(e)}"}
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        if not self.monitor:
            return {
                "available": RealTimeIndexMonitor is not None,
                "running": False,
                "message": "监控器未初始化"
            }
        
        return {
            "available": True,
            "running": self.monitor.is_running(),
            "project_root": str(self.project_root),
            "index_dir": str(self.index_dir)
        }
    
    def update_project_root(self, new_project_root: str) -> Dict[str, Any]:
        """动态更新项目根目录"""
        try:
            # 停止当前监控（如果正在运行）
            if self.monitor and self.monitor.is_running():
                self.stop_monitoring()
            
            # 更新项目根目录
            old_root = str(self.project_root)
            self.project_root = Path(new_project_root) if new_project_root else Path.cwd()
            
            # 更新索引目录，放在服务启动目录的data目录下
            service_root = Path(__file__).parent
            data_dir = service_root / "data"
            data_dir.mkdir(exist_ok=True)
            project_name = self.project_root.name
            self.index_dir = data_dir / f"whoosh_index_{project_name}"
            
            # 重新创建索引
            self._ensure_index_exists()
            
            # 重新初始化监控器
            if RealTimeIndexMonitor:
                self.monitor = RealTimeIndexMonitor(str(self.project_root), str(self.index_dir))
            
            logger.info(f"Project root updated from {old_root} to {self.project_root}")
            
            return {
                "success": True,
                "message": f"项目根目录已更新为: {self.project_root}",
                "old_root": old_root,
                "new_root": str(self.project_root)
            }
            
        except Exception as e:
            logger.error(f"更新项目根目录失败: {e}")
            return {
                "error": f"更新失败: {str(e)}"
            }