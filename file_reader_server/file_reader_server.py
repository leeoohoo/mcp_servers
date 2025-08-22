#!/usr/bin/env python3
"""
File Reader MCP Server (注解版本)
基于 EnhancedMCPServer 和装饰器系统的文件读取服务器

主要功能:
1. read_file_lines - 读取文件指定行范围（流式输出）
2. search_files_by_content - 搜索文件内容（流式输出）  
3. get_files_content - 批量读取文件内容（流式输出）
4. get_project_structure - 获取项目结构（流式输出）
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator
from typing_extensions import Annotated

# 导入新的框架
from mcp_framework import (

    MCPHTTPServer,
    ConfigManager,
    setup_logging,
    check_dependencies
)
from mcp_framework.core import EnhancedMCPServer

# 导入装饰器
from mcp_framework.core.decorators import (
    Required as R,
    Optional as O,
    IntRange,
    ServerParam,
    StringParam,
    BooleanParam,
    PathParam
)

# 配置日志
logger = logging.getLogger("file_reader_server")


class FileReaderService:
    """文件读取服务类"""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()

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
            '.pytest_cache', '.mypy_cache', 'venv', 'env', '.env'
        }

        logger.info(f"File Reader Service initialized with project root: {self.project_root}")

    def _should_ignore_path(self, path: Path) -> bool:
        """检查路径是否应该被忽略"""
        # 检查路径中的任何部分是否在忽略列表中
        for part in path.parts:
            if part in self.ignore_dirs:
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
        """流式搜索文件内容"""
        try:
            if not query_text:
                yield json.dumps({"error": "缺少搜索关键词"}, ensure_ascii=False)
                return

            # 发送搜索开始信号
            yield json.dumps({
                "type": "search_start",
                "query": query_text,
                "limit": limit,
                "case_sensitive": case_sensitive
            }, ensure_ascii=False)

            results_count = 0
            search_pattern = re.compile(
                query_text if case_sensitive else query_text,
                0 if case_sensitive else re.IGNORECASE
            )

            # 默认搜索的文件扩展名
            if file_extensions is None:
                file_extensions = ['.py', '.kt', '.java', '.js', '.ts', '.cpp', '.c', '.h', '.txt', '.md']

            # 遍历项目目录搜索
            for file_path in self.project_root.rglob('*'):
                if not file_path.is_file():
                    continue

                # 检查是否应该忽略此路径
                relative_path = file_path.relative_to(self.project_root)
                if self._should_ignore_path(relative_path):
                    continue

                # 检查文件扩展名
                if file_extensions:
                    if file_path.suffix not in file_extensions:
                        continue
                else:
                    # 如果没有指定扩展名，只处理支持的文本文件
                    if file_path.suffix not in self.text_extensions:
                        continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    # 搜索匹配行
                    for line_num, line in enumerate(lines, 1):
                        if search_pattern.search(line):
                            # 获取上下文
                            start_context = max(0, line_num - context_lines - 1)
                            end_context = min(len(lines), line_num + context_lines)

                            context_lines_content = []
                            for i in range(start_context, end_context):
                                line_content = lines[i].rstrip('\n')
                                if line_content.strip():  # 只显示非空行
                                    marker = ">>> " if i == line_num - 1 else "    "
                                    context_lines_content.append(f"{marker}{i + 1}:{line_content}")

                            # 流式输出匹配结果
                            yield json.dumps({
                                "type": "match",
                                "file": str(file_path.relative_to(self.project_root)),
                                "line": line_num,
                                "context": '\n'.join(context_lines_content)
                            }, ensure_ascii=False)

                            results_count += 1
                            if results_count >= limit:
                                break

                        # 每20行暂停一下
                        if line_num % 20 == 0:
                            await asyncio.sleep(0.01)

                    if results_count >= limit:
                        break

                except (UnicodeDecodeError, PermissionError):
                    continue

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
                    "message": f"找到 {results_count} 个匹配结果"
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
            logger.error(f"获取项目结构时发生异常: {e}")
            yield json.dumps({"error": f"获取项目结构失败 - {str(e)}"}, ensure_ascii=False)


class FileReaderMCPServer(EnhancedMCPServer):
    """基于注解装饰器的文件读取MCP服务器"""

    def __init__(self):
        super().__init__(
            name="file-reader-server",
            version="1.0.0",
            description="文件读取MCP服务器，基于注解装饰器系统提供流式文件操作功能"
        )
        # 在构造函数中就初始化服务，使用默认值
        self.file_reader_service = FileReaderService()
        logger.info("FileReaderMCPServer initialized")

    @property
    def setup_tools(self):
        """设置工具装饰器"""

        @self.streaming_tool(description="📖 **File Line Range Reader** - 流式读取文件指定行范围")
        async def read_file_lines(
                file_path: Annotated[str, R("文件路径（支持相对和绝对路径）")],
                start_line: Annotated[int, IntRange("起始行号（1-based）", min_val=1)],
                end_line: Annotated[int, IntRange("结束行号（1-based，包含）", min_val=1)]
        ) -> AsyncGenerator[str, None]:
            """流式读取文件指定行范围"""
            async for chunk in self.file_reader_service.read_file_lines_stream(file_path, start_line, end_line):
                yield self._normalize_stream_chunk(chunk)

        @self.streaming_tool(description="🔍 **Content Search** - 流式搜索文件内容")
        async def search_files_by_content(
                query_text: Annotated[str, R("搜索关键词")],
                limit: Annotated[int, O("最大结果数量", default=50, minimum=1)] = 50,
                case_sensitive: Annotated[bool, O("是否区分大小写", default=False)] = False,
                context_lines: Annotated[int, O("上下文行数", default=20, minimum=0)] = 20,
                file_extensions: Annotated[Optional[List[str]], O("文件扩展名列表，如 ['.py', '.js']")] = None
        ) -> AsyncGenerator[str, None]:
            """流式搜索文件内容"""
            async for chunk in self.file_reader_service.search_files_by_content_stream(
                    query_text, limit, case_sensitive, context_lines, file_extensions
            ):
                yield self._normalize_stream_chunk(chunk)

        @self.streaming_tool(description="📄 **Batch File Reader** - 流式批量读取文件内容")
        async def get_files_content(
                file_paths: Annotated[List[str], R("要读取的文件路径列表")]
        ) -> AsyncGenerator[str, None]:
            """流式批量读取文件内容"""
            async for chunk in self.file_reader_service.get_files_content_stream(file_paths):
                yield self._normalize_stream_chunk(chunk)

        @self.streaming_tool(description="🏗️ **Project Structure** - 流式获取项目结构")
        async def get_project_structure(
                max_depth: Annotated[int, O("最大遍历深度", default=10, minimum=1)] = 10,
                include_hidden: Annotated[bool, O("是否包含隐藏文件", default=False)] = False
        ) -> AsyncGenerator[str, None]:
            """流式获取项目结构"""
            async for chunk in self.file_reader_service.get_project_structure_stream(max_depth, include_hidden):
                yield self._normalize_stream_chunk(chunk)

        @self.resource(uri="config://file-reader", name="文件读取器配置", description="当前文件读取器的配置信息")
        async def file_reader_config_resource(uri: str) -> Dict[str, Any]:
            """获取文件读取器配置信息"""
            config_info = {
                "project_root": str(self.file_reader_service.project_root),
                "supported_extensions": list(self.file_reader_service.text_extensions),
                "ignored_directories": list(self.file_reader_service.ignore_dirs),
                "server_config": getattr(self, 'server_config', {})
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(config_info, indent=2, ensure_ascii=False)
                    }
                ]
            }

        @self.resource(uri="stats://project", name="项目统计", description="项目文件和代码行数统计")
        async def project_stats_resource(uri: str) -> Dict[str, Any]:
            """获取项目统计信息"""
            # 计算项目统计信息
            total_files = 0
            total_lines = 0
            file_types = {}

            try:
                for file_path in self.file_reader_service.project_root.rglob('*'):
                    if not file_path.is_file():
                        continue

                    relative_path = file_path.relative_to(self.file_reader_service.project_root)
                    if self.file_reader_service._should_ignore_path(relative_path):
                        continue

                    total_files += 1
                    ext = file_path.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1

                    if ext in self.file_reader_service.text_extensions:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = sum(1 for _ in f)
                                total_lines += lines
                        except (UnicodeDecodeError, PermissionError):
                            pass

                stats_info = {
                    "project_root": str(self.file_reader_service.project_root),
                    "total_files": total_files,
                    "total_lines": total_lines,
                    "file_types": file_types,
                    "text_file_extensions": len(self.file_reader_service.text_extensions)
                }

            except Exception as e:
                stats_info = {"error": f"Failed to calculate stats: {str(e)}"}

            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(stats_info, indent=2, ensure_ascii=False)
                    }
                ]
            }

        return True

    @property
    def setup_server_params(self):
        """设置服务器参数装饰器"""

        @self.decorators.server_param("project_root")
        async def project_root_param(
                param: Annotated[str, PathParam(
                    display_name="项目根目录",
                    description="服务器操作的根目录路径，留空使用当前目录",
                    required=False,
                    placeholder="/path/to/project"
                )]
        ):
            """项目根目录参数"""
            pass

        @self.decorators.server_param("max_file_size")
        async def max_file_size_param(
                param: Annotated[int, ServerParam(
                    display_name="最大文件大小 (MB)",
                    description="允许读取的最大文件大小，单位MB",
                    param_type="integer",
                    default_value=10,
                    required=False
                )]
        ):
            """最大文件大小参数"""
            pass

        @self.decorators.server_param("enable_hidden_files")
        async def enable_hidden_files_param(
                param: Annotated[bool, BooleanParam(
                    display_name="启用隐藏文件",
                    description="是否允许访问以点(.)开头的隐藏文件",
                    default_value=False,
                    required=False
                )]
        ):
            """启用隐藏文件参数"""
            pass

        @self.decorators.server_param("search_limit")
        async def search_limit_param(
                param: Annotated[int, ServerParam(
                    display_name="搜索结果限制",
                    description="搜索操作返回的最大结果数量",
                    param_type="integer",
                    default_value=50,
                    required=False
                )]
        ):
            """搜索结果限制参数"""
            pass

        return True

    async def initialize(self) -> None:
        """初始化服务器（实现基类抽象方法）"""
        # 触发装饰器工具注册
        _ = self.setup_tools
        # 触发服务器参数注册
        _ = self.setup_server_params

        # 调用基类的初始化（如果存在）
        if hasattr(super(), 'initialize'):
            await super().initialize()

        # 获取配置参数并重新初始化服务（如果需要）
        try:
            project_root = self.get_config_value("project_root")
            if project_root and project_root.strip():
                # 如果配置了项目根目录，重新初始化服务
                self.file_reader_service = FileReaderService(project_root.strip())
                logger.info(f"Using configured project root: {project_root}")
            else:
                # 使用默认的当前目录
                logger.info("Using current directory as project root")
        except Exception as e:
            logger.warning(f"Failed to get config, using default: {e}")

        # 确保服务已初始化
        if self.file_reader_service is None:
            self.file_reader_service = FileReaderService()
            logger.info("Initialized file reader service with defaults")


async def main():
    """主函数"""
    # 检查依赖
    if not check_dependencies():
        return

    # 设置日志
    setup_logging(log_level=logging.INFO, log_file="file_reader_server.log")

    # 创建服务器实例
    mcp_server = FileReaderMCPServer()

    # 手动调用初始化
    try:
        await mcp_server.initialize()
        print(f"✅ 初始化成功，工具数量: {len(mcp_server.tools)}")
        print(f"✅ 资源数量: {len(mcp_server.resources)}")
        for tool in mcp_server.tools:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.load_config()

    # 创建 HTTP 服务器
    http_server = MCPHTTPServer(mcp_server, config)

    try:
        # 启动服务器
        runner = await http_server.start()

        print(f"🚀 文件读取 MCP 服务器已启动!")
        print(f"📍 服务器地址: http://localhost:{config.port}")
        print(f"🛠️  设置页面: http://localhost:{config.port}/setup")
        print(f"🧪 测试页面: http://localhost:{config.port}/test")
        print(f"⚙️  配置页面: http://localhost:{config.port}/config")
        print(f"💚 健康检查: http://localhost:{config.port}/health")
        print(f"🌊 流式API: http://localhost:{config.port}/api/streaming/")
        print()
        print("按 Ctrl+C 停止服务器")

        # 等待中断信号
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭服务器...")

    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        print(f"❌ 服务器启动失败: {e}")
    finally:
        # 清理资源
        try:
            await http_server.stop()
            print("✅ 服务器已安全关闭")
        except Exception as e:
            logger.error(f"关闭服务器时出错: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        print(f"❌ 程序异常退出: {e}")
        sys.exit(1)
