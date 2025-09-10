#!/usr/bin/env python3
import os
import shutil
from typing import List, Dict, Union, Optional, AsyncGenerator
from pathlib import Path
import asyncio


class PreciseTextModifier:
    """精准文本修改器 - 基于行号的文本编辑工具"""
    
    def __init__(self, file_path: str, backup: bool = False):
        self.file_path = file_path
        self.original_content = None
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 创建备份
        if backup:
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()
            self.original_content = ''.join(self.lines)
    
    def modify_line(self, line_num: int, new_content: str) -> 'PreciseTextModifier':
        """修改单行"""
        if 1 <= line_num <= len(self.lines):
            self.lines[line_num - 1] = new_content + '\n' if not new_content.endswith('\n') else new_content
        else:
            raise IndexError(f"行号 {line_num} 超出范围 (1-{len(self.lines)})")
        return self
    
    def modify_range(self, start_line: int, end_line: int, new_content: Union[str, List[str]]) -> 'PreciseTextModifier':
        """修改行范围"""
        if start_line < 1 or end_line > len(self.lines) or start_line > end_line:
            raise IndexError(f"行号范围无效: {start_line}-{end_line}, 文件总行数: {len(self.lines)}")
        
        if isinstance(new_content, str):
            new_lines = [new_content + '\n'] if not new_content.endswith('\n') else [new_content]
        else:
            new_lines = [line + '\n' if not line.endswith('\n') else line for line in new_content]
        
        start_idx = start_line - 1
        end_idx = end_line
        self.lines = self.lines[:start_idx] + new_lines + self.lines[end_idx:]
        return self
    
    def insert_lines(self, line_num: int, content: Union[str, List[str]]) -> 'PreciseTextModifier':
        """在指定行号后插入内容"""
        if line_num < 0 or line_num > len(self.lines):
            raise IndexError(f"插入位置无效: {line_num}, 文件总行数: {len(self.lines)}")
        
        if isinstance(content, str):
            content = [content]
        
        insert_lines = [line + '\n' if not line.endswith('\n') else line for line in content]
        self.lines = self.lines[:line_num] + insert_lines + self.lines[line_num:]
        return self
    
    def delete_lines(self, start_line: int, end_line: int) -> 'PreciseTextModifier':
        """删除指定范围的行"""
        if start_line < 1 or end_line > len(self.lines) or start_line > end_line:
            raise IndexError(f"删除范围无效: {start_line}-{end_line}, 文件总行数: {len(self.lines)}")
        
        start_idx = start_line - 1
        end_idx = end_line
        self.lines = self.lines[:start_idx] + self.lines[end_idx:]
        return self
    
    def batch_modify(self, modifications: Dict[int, str]) -> 'PreciseTextModifier':
        """批量修改多行"""
        # 从后往前修改避免行号变化
        for line_num in sorted(modifications.keys(), reverse=True):
            self.modify_line(line_num, modifications[line_num])
        return self
    
    def get_lines(self, start_line: Optional[int] = None, end_line: Optional[int] = None) -> List[str]:
        """获取指定范围的行"""
        if start_line is None and end_line is None:
            return self.lines
        
        start_idx = (start_line - 1) if start_line else 0
        end_idx = end_line if end_line else len(self.lines)
        return self.lines[start_idx:end_idx]
    
    def save(self, output_path: Optional[str] = None) -> str:
        """保存文件"""
        path = output_path or self.file_path
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(self.lines)
        return path
    
    def get_content(self) -> str:
        """获取当前内容"""
        return ''.join(self.lines)
    
    def get_line_count(self) -> int:
        """获取总行数"""
        return len(self.lines)


def get_markdown_language(file_path: str) -> str:
    """根据文件扩展名获取markdown语言标识符"""
    extension = Path(file_path).suffix.lower()
    
    # 文件扩展名到markdown语言的映射
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.jsx': 'jsx',
        '.java': 'java',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.dart': 'dart',
        '.vue': 'vue',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        '.conf': 'ini',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.dockerfile': 'dockerfile',
        '.makefile': 'makefile',
        '.cmake': 'cmake',
        '.gradle': 'gradle',
        '.properties': 'properties',
        '.env': 'bash',
        '.gitignore': 'gitignore',
        '.md': 'markdown',
        '.txt': 'text',
        '.log': 'log',
        '.csv': 'csv',
        '.tsv': 'tsv'
    }
    
    return language_map.get(extension, 'text')


async def show_directory_structure(dir_path: str, max_depth: int = 10, include_hidden: bool = False) -> AsyncGenerator[str, None]:
    """递归展示文件夹结构"""
    
    # 忽略的目录
    ignore_dirs = {
        '__pycache__', '.git', '.svn', '.hg', 'node_modules', '.vscode', '.idea',
        'build', 'dist', '.pytest_cache', '.mypy_cache', '.tox', 'venv', 'env'
    }
    
    # 支持的文本文件扩展名
    text_extensions = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.kt', '.swift', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.go', '.rs', '.php', '.rb', '.dart', '.vue', '.html', '.htm', '.css', '.scss',
        '.sass', '.less', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        '.sql', '.sh', '.bash', '.zsh', '.fish', '.bat', '.ps1', '.dockerfile', '.makefile',
        '.cmake', '.gradle', '.properties', '.env', '.gitignore', '.md', '.txt', '.log'
    }
    
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
            entries = [e for e in entries if not (e.is_dir() and e.name in ignore_dirs)]
            
            # 排序：目录在前，文件在后
            entries.sort(key=lambda x: (x.is_file(), x.name.lower()))
            
            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                current_prefix = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   "
                
                if entry.is_dir():
                    yield f"{prefix}{current_prefix}{entry.name}/\n"
                    
                    # 递归处理子目录
                    async for child_item in build_tree_stream(entry, prefix + next_prefix, depth + 1):
                        yield child_item
                else:
                    # 只对支持的文本文件计算行数
                    line_info = ""
                    if entry.suffix.lower() in text_extensions:
                        try:
                            with open(entry, 'r', encoding='utf-8') as f:
                                line_count = sum(1 for _ in f)
                            line_info = f" ({line_count} lines)"
                        except (UnicodeDecodeError, PermissionError):
                            line_info = " (no access)"
                        except Exception:
                            line_info = ""
                    
                    yield f"{prefix}{current_prefix}{entry.name}{line_info}\n"
                
                # 每10个条目暂停一下
                if (i + 1) % 10 == 0:
                    await asyncio.sleep(0.01)
        
        except PermissionError:
            yield f"{prefix}❌ Permission denied\n"
    
    # 输出目录结构
    path = Path(dir_path)
    yield f"\n📁 目录结构: {path.name}\n\n```\n"
    
    # 流式构建树结构
    async for item in build_tree_stream(path):
        yield item
    
    # 结束代码块
    yield "```\n"


def validate_file_access(file_path: str, project_root: str = "", max_file_size_mb: int = 10, enable_hidden_files: bool = False, allow_nonexistent: bool = False) -> str:
    """验证文件或目录访问权限
    
    Args:
        file_path: 文件路径
        project_root: 项目根目录
        max_file_size_mb: 最大文件大小(MB)
        enable_hidden_files: 是否允许隐藏文件
        allow_nonexistent: 是否允许不存在的文件(用于create操作)
    """
    if not project_root:
        project_root = os.getcwd()
    
    # 规范化project_root路径
    project_root = os.path.abspath(project_root)
    
    # 处理相对路径
    if not os.path.isabs(file_path):
        # 清理路径前缀，移除 ./ 等
        clean_path = file_path.lstrip('./').lstrip('\\')
        file_path = os.path.join(project_root, clean_path)
    
    # 安全检查：确保文件路径在project_root下
    normalized_file_path = os.path.normpath(file_path)
    normalized_project_root = os.path.normpath(project_root)
    
    if not normalized_file_path.startswith(normalized_project_root):
        raise PermissionError(f"安全限制：只允许访问项目根目录 {project_root} 下的文件")
    
    # 检查文件或目录是否存在
    if not os.path.exists(file_path):
        if allow_nonexistent:
            # 对于create操作，验证目标目录是否存在且有权限
            target_dir = os.path.dirname(file_path)
            if target_dir and not os.path.exists(target_dir):
                # 检查父目录是否在project_root下
                normalized_target_dir = os.path.normpath(target_dir)
                if not normalized_target_dir.startswith(normalized_project_root):
                    raise PermissionError(f"安全限制：只允许在项目根目录 {project_root} 下创建文件")
            return file_path
        else:
            # 如果文件不存在，尝试将路径与project_root拼接
            alternative_path = os.path.join(project_root, os.path.basename(file_path))
            if os.path.exists(alternative_path):
                file_path = alternative_path
            else:
                raise FileNotFoundError(f"文件或目录不存在: {file_path}")
    
    # 检查是否为隐藏文件或目录
    if not enable_hidden_files and os.path.basename(file_path).startswith('.'):
        raise PermissionError("不允许访问隐藏文件或目录")
    
    # 只对文件检查大小限制，目录不检查
    if os.path.isfile(file_path):
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > max_file_size_mb:
            raise ValueError(f"文件大小 ({file_size_mb:.2f}MB) 超过限制 ({max_file_size_mb}MB)")
    
    return file_path