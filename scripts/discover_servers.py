#!/usr/bin/env python3
"""
MCP 服务器自动发现脚本

此脚本会自动扫描项目目录，发现所有的 MCP 服务器，并生成构建配置。
使用方法:
    python scripts/discover_servers.py
    python scripts/discover_servers.py --output servers.json
    python scripts/discover_servers.py --build-all
"""

import os
import json
import glob
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional


class MCPServerDiscovery:
    """MCP 服务器发现器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.servers = []
    
    def find_mcp_servers(self) -> List[Dict]:
        """自动发现项目中的 MCP 服务器"""
        print(f"🔍 在 {self.project_root} 中搜索 MCP 服务器...")
        
        # 搜索模式：寻找包含 MCP 服务器的 Python 文件
        search_patterns = [
            "*_server/*.py",
            "*_server.py", 
            "*-server/*.py",
            "*-server.py",
            "servers/*/*.py",
            "servers/*.py",
            "mcp_servers/*/*.py",
            "mcp_servers/*.py",
            "src/*_server/*.py",
            "src/*_server.py",
            "src/servers/*.py",
            "**/*_server.py",  # 递归搜索
            "**/server.py",    # 通用服务器文件名
        ]
        
        found_files = set()
        
        # 使用不同的搜索模式
        for pattern in search_patterns:
            pattern_path = self.project_root / pattern
            for file_path in glob.glob(str(pattern_path), recursive=True):
                if self.is_python_file(file_path):
                    found_files.add(Path(file_path))
        
        # 检查每个找到的文件是否是 MCP 服务器
        servers = []
        for file_path in found_files:
            if self.is_mcp_server(file_path):
                server_info = self.extract_server_info(file_path)
                if server_info:
                    servers.append(server_info)
                    print(f"  ✅ 发现: {server_info['name']} ({file_path})")
        
        self.servers = servers
        return servers
    
    def is_python_file(self, file_path: str) -> bool:
        """检查是否是 Python 文件"""
        return file_path.endswith('.py') and not file_path.endswith('__init__.py')
    
    def is_mcp_server(self, file_path: Path) -> bool:
        """检查文件是否是 MCP 服务器"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查是否包含 MCP 相关导入和关键词
                mcp_indicators = [
                    'from mcp',
                    'import mcp',
                    'FastMCP',
                    'mcp.server',
                    'mcp.types',
                    'mcp.Server',
                    '@app.tool',
                    'app = FastMCP',
                    'server = Server',
                    'StdioServerParameters',
                    'run_server',
                    'serve_stdio'
                ]
                
                # 至少需要匹配一个 MCP 指示器
                has_mcp = any(indicator in content for indicator in mcp_indicators)
                
                # 排除测试文件
                exclude_patterns = [
                    'test_',
                    '_test',
                    'demo_',
                    '_demo'
                ]
                
                filename = file_path.name.lower()
                is_excluded = any(pattern in filename for pattern in exclude_patterns)
                
                return has_mcp and not is_excluded
                
        except Exception as e:
            print(f"  ⚠️  读取文件失败 {file_path}: {e}")
            return False
    
    def extract_server_info(self, file_path: Path) -> Optional[Dict]:
        """提取服务器信息"""
        try:
            # 生成服务器名称
            if file_path.parent.name.endswith('_server'):
                server_name = file_path.parent.name.replace('_', '-')
            elif file_path.parent.name.endswith('-server'):
                server_name = file_path.parent.name
            elif file_path.stem.endswith('_server'):
                server_name = file_path.stem.replace('_', '-')
            elif file_path.stem.endswith('-server'):
                server_name = file_path.stem
            elif file_path.stem == 'server':
                server_name = file_path.parent.name.replace('_', '-')
            else:
                server_name = file_path.stem.replace('_', '-')
            
            # 确保名称以 -server 结尾
            if not server_name.endswith('-server'):
                server_name += '-server'
            
            # 查找依赖文件
            requirements_file = self.find_requirements_file(file_path)
            
            # 查找配置文件
            config_file = self.find_config_file(file_path)
            
            # 获取相对路径
            relative_path = file_path.relative_to(self.project_root)
            
            # 尝试提取服务器描述
            description = self.extract_description(file_path)
            
            return {
                'name': server_name,
                'script_path': str(relative_path),
                'absolute_path': str(file_path),
                'requirements_file': requirements_file,
                'config_file': config_file,
                'directory': str(file_path.parent),
                'description': description,
                'size': file_path.stat().st_size,
                'modified': file_path.stat().st_mtime
            }
            
        except Exception as e:
            print(f"  ⚠️  提取服务器信息失败 {file_path}: {e}")
            return None
    
    def find_requirements_file(self, file_path: Path) -> Optional[str]:
        """查找依赖文件"""
        possible_req_files = [
            file_path.parent / f"{file_path.stem}_requirements.txt",
            file_path.parent / "requirements.txt",
            file_path.parent.parent / f"{file_path.parent.name}_requirements.txt",
            file_path.parent.parent / "requirements.txt",
            self.project_root / "requirements.txt"
        ]
        
        for req_file in possible_req_files:
            if req_file.exists():
                return str(req_file.relative_to(self.project_root))
        
        return None
    
    def find_config_file(self, file_path: Path) -> Optional[str]:
        """查找配置文件"""
        possible_config_files = [
            file_path.parent / f"{file_path.stem}.json",
            file_path.parent / f"{file_path.stem}.yaml",
            file_path.parent / f"{file_path.stem}.yml",
            file_path.parent / "config.json",
            file_path.parent / "config.yaml",
            file_path.parent / "config.yml"
        ]
        
        for config_file in possible_config_files:
            if config_file.exists():
                return str(config_file.relative_to(self.project_root))
        
        return None
    
    def extract_description(self, file_path: Path) -> str:
        """从文件中提取描述信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找文档字符串
                lines = content.split('\n')
                in_docstring = False
                docstring_lines = []
                
                for line in lines[:50]:  # 只检查前50行
                    line = line.strip()
                    if line.startswith('"""') or line.startswith("'''"):
                        if in_docstring:
                            break
                        in_docstring = True
                        # 如果同一行包含完整的文档字符串
                        if line.count('"""') == 2 or line.count("'''") == 2:
                            return line.replace('"""', '').replace("'''", '').strip()
                        continue
                    elif in_docstring:
                        if line and not line.startswith('#'):
                            docstring_lines.append(line)
                
                if docstring_lines:
                    return ' '.join(docstring_lines[:3])  # 取前3行
                
                # 如果没有找到文档字符串，查找注释
                for line in lines[:20]:
                    line = line.strip()
                    if line.startswith('#') and len(line) > 10:
                        comment = line[1:].strip()
                        if not comment.startswith('!') and not comment.startswith('-*-'):
                            return comment
                
                return f"MCP Server: {file_path.stem}"
                
        except Exception:
            return f"MCP Server: {file_path.stem}"
    
    def save_to_file(self, output_file: str):
        """保存发现结果到文件"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'servers': self.servers,
                'count': len(self.servers),
                'project_root': str(self.project_root),
                'discovery_time': __import__('time').time()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"📄 发现结果已保存到: {output_path}")
    
    def generate_build_script(self, output_file: str = "build_all_servers.py"):
        """生成构建所有服务器的脚本"""
        script_content = f'''#!/usr/bin/env python3
"""
自动生成的 MCP 服务器构建脚本
发现了 {len(self.servers)} 个服务器
"""

import subprocess
import sys
import os
from pathlib import Path

def build_all_servers():
    """构建所有发现的 MCP 服务器"""
    servers = {json.dumps(self.servers, indent=4)}
    
    print(f"🔨 开始构建 {{len(servers)}} 个 MCP 服务器...")
    
    success_count = 0
    failed_servers = []
    
    for server in servers:
        server_name = server['name']
        script_path = server['script_path']
        
        print(f"\n{{'='*50}}")
        print(f"构建服务器: {{server_name}}")
        print(f"脚本路径: {{script_path}}")
        print(f"{{'='*50}}")
        
        # 检查脚本文件是否存在
        if not os.path.exists(script_path):
            print(f"❌ 脚本文件不存在: {{script_path}}")
            failed_servers.append(server_name)
            continue
        
        # 构建命令
        build_cmd = [
            sys.executable, '-m', 'mcp_framework.build',
            '--server', script_path,
            '--no-test'
        ]
        
        try:
            print(f"执行构建命令: {{' '.join(build_cmd)}}")
            result = subprocess.run(build_cmd, check=True)
            print(f"✅ {{server_name}} 构建成功")
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            print(f"❌ {{server_name}} 构建失败: {{e}}")
            failed_servers.append(server_name)
        except Exception as e:
            print(f"❌ {{server_name}} 构建过程中出现异常: {{e}}")
            failed_servers.append(server_name)
    
    print(f"\n{{'='*50}}")
    print(f"构建摘要: {{success_count}}/{{len(servers)}} 个服务器构建成功")
    if failed_servers:
        print(f"失败的服务器: {{', '.join(failed_servers)}}")
    print(f"{{'='*50}}")
    
    return success_count, failed_servers

if __name__ == "__main__":
    success_count, failed_servers = build_all_servers()
    if failed_servers:
        sys.exit(1)
'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置可执行权限
        os.chmod(output_file, 0o755)
        
        print(f"📄 构建脚本已生成: {output_file}")
    
    def build_all_servers(self, platform: str = "native"):
        """构建所有发现的服务器"""
        if not self.servers:
            print("❌ 没有发现任何 MCP 服务器")
            return False
        
        print(f"🔨 开始构建 {len(self.servers)} 个 MCP 服务器 (平台: {platform})...")
        
        success_count = 0
        failed_servers = []
        
        for server in self.servers:
            server_name = server['name']
            script_path = server['script_path']
            
            print(f"\n{'='*50}")
            print(f"构建服务器: {server_name}")
            print(f"脚本路径: {script_path}")
            print(f"{'='*50}")
            
            # 检查脚本文件是否存在
            if not os.path.exists(script_path):
                print(f"❌ 脚本文件不存在: {script_path}")
                failed_servers.append(server_name)
                continue
            
            # 构建命令
            build_cmd = [
                sys.executable, '-m', 'mcp_framework.build',
                '--platform', platform,
                '--server', script_path,
                '--no-test'
            ]
            
            try:
                print(f"执行构建命令: {' '.join(build_cmd)}")
                result = subprocess.run(build_cmd, check=True)
                print(f"✅ {server_name} 构建成功")
                success_count += 1
                
            except subprocess.CalledProcessError as e:
                print(f"❌ {server_name} 构建失败: {e}")
                failed_servers.append(server_name)
            except Exception as e:
                print(f"❌ {server_name} 构建过程中出现异常: {e}")
                failed_servers.append(server_name)
        
        print(f"\n{'='*50}")
        print(f"构建摘要: {success_count}/{len(self.servers)} 个服务器构建成功")
        if failed_servers:
            print(f"失败的服务器: {', '.join(failed_servers)}")
        print(f"{'='*50}")
        
        return success_count > 0


def main():
    parser = argparse.ArgumentParser(description='MCP 服务器自动发现工具')
    parser.add_argument('--project-root', '-r', 
                       help='项目根目录路径 (默认: 当前目录)')
    parser.add_argument('--output', '-o', 
                       default='discovered_servers.json',
                       help='输出文件路径 (默认: discovered_servers.json)')
    parser.add_argument('--build-all', '-b', 
                       action='store_true',
                       help='发现后立即构建所有服务器')
    parser.add_argument('--platform', '-p', 
                       default='native',
                       choices=['native', 'linux', 'windows', 'macos'],
                       help='构建平台 (默认: native)')
    parser.add_argument('--generate-script', '-g',
                       action='store_true',
                       help='生成构建脚本')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='详细输出')
    
    args = parser.parse_args()
    
    # 创建发现器
    discovery = MCPServerDiscovery(args.project_root)
    
    # 发现服务器
    servers = discovery.find_mcp_servers()
    
    if not servers:
        print("❌ 没有发现任何 MCP 服务器")
        print("\n💡 提示:")
        print("  - 确保您的 Python 文件包含 MCP 相关的导入")
        print("  - 检查文件名是否包含 'server' 关键词")
        print("  - 确保文件不是测试或示例文件")
        return 1
    
    print(f"\n✅ 总共发现 {len(servers)} 个 MCP 服务器:")
    for i, server in enumerate(servers, 1):
        print(f"  {i}. {server['name']}")
        print(f"     路径: {server['script_path']}")
        print(f"     描述: {server['description']}")
        if server['requirements_file']:
            print(f"     依赖: {server['requirements_file']}")
        print()
    
    # 保存发现结果
    discovery.save_to_file(args.output)
    
    # 生成构建脚本
    if args.generate_script:
        discovery.generate_build_script()
    
    # 构建所有服务器
    if args.build_all:
        success = discovery.build_all_servers(args.platform)
        return 0 if success else 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())