#!/usr/bin/env python3
"""
本地 MCP 服务器批量构建脚本

这个脚本会自动发现项目中的所有 MCP 服务器并进行构建。
使用方法:
    python scripts/build_all.py
    python scripts/build_all.py --platform linux
    python scripts/build_all.py --clean
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.discover_servers import MCPServerDiscovery
except ImportError:
    print("❌ 无法导入服务器发现模块")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


def clean_dist_directory():
    """清理 dist 目录"""
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        print(f"🧹 清理 {dist_dir}...")
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(exist_ok=True)
    print("✅ dist 目录已清理")


def install_dependencies(servers):
    """安装所有服务器的依赖"""
    print("📦 安装依赖...")
    
    # 安装基础依赖
    base_requirements = project_root / "requirements.txt"
    if base_requirements.exists():
        print(f"安装基础依赖: {base_requirements}")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(base_requirements)], 
                         check=True, capture_output=True)
            print("✅ 基础依赖安装成功")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  基础依赖安装失败: {e}")
    
    # 安装各服务器特定依赖
    for server in servers:
        if server.get('requirements_file'):
            req_file = project_root / server['requirements_file']
            if req_file.exists():
                print(f"安装 {server['name']} 的依赖: {req_file}")
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(req_file)], 
                                 check=True, capture_output=True)
                    print(f"✅ {server['name']} 依赖安装成功")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  {server['name']} 依赖安装失败: {e}")


def build_server(server, platform, output_dir):
    """构建单个服务器"""
    server_name = server['name']
    script_path = project_root / server['script_path']
    
    print(f"\n{'='*60}")
    print(f"🔨 构建服务器: {server_name}")
    print(f"📄 脚本路径: {script_path}")
    print(f"🖥️  目标平台: {platform}")
    print(f"📁 输出目录: {output_dir}")
    print(f"{'='*60}")
    
    # 检查脚本文件是否存在
    if not script_path.exists():
        print(f"❌ 脚本文件不存在: {script_path}")
        return False
    
    # 创建服务器专用输出目录
    server_output_dir = output_dir / server_name
    server_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建命令
    build_cmd = [
        sys.executable, '-m', 'mcp_framework.build',
        '--platform', platform,
        '--server', str(script_path),
        '--output-dir', str(server_output_dir),
        '--no-test'
    ]
    
    try:
        print(f"执行构建命令: {' '.join(build_cmd)}")
        
        # 运行构建命令
        result = subprocess.run(build_cmd, check=True, capture_output=True, text=True)
        
        print(f"✅ {server_name} 构建成功")
        if result.stdout:
            print("构建输出:")
            print(result.stdout)
        
        # 查找生成的可执行文件
        executable_files = list(server_output_dir.glob(f"{server_name}*"))
        if not executable_files:
            # 尝试其他可能的文件名
            executable_files = list(server_output_dir.glob("*"))
            executable_files = [f for f in executable_files if f.is_file() and not f.name.endswith('.txt')]
        
        if executable_files:
            for exe_file in executable_files:
                if exe_file.is_file():
                    # 移动到主输出目录
                    final_path = output_dir / exe_file.name
                    if final_path.exists():
                        final_path.unlink()
                    shutil.move(str(exe_file), str(final_path))
                    print(f"📦 可执行文件: {final_path}")
            
            # 清理临时目录
            shutil.rmtree(server_output_dir)
        else:
            print(f"⚠️  没有找到生成的可执行文件")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {server_name} 构建失败")
        if e.stderr:
            print(f"错误输出: {e.stderr}")
        if e.stdout:
            print(f"标准输出: {e.stdout}")
        return False
    except Exception as e:
        print(f"❌ {server_name} 构建过程中出现异常: {e}")
        return False


def create_archive(output_dir, platform):
    """创建发布包"""
    print(f"\n📦 创建发布包...")
    
    # 查找所有可执行文件
    executable_files = []
    for file_path in output_dir.iterdir():
        if file_path.is_file() and not file_path.name.endswith('.txt'):
            executable_files.append(file_path)
    
    if not executable_files:
        print("❌ 没有找到可执行文件")
        return None
    
    # 创建归档文件
    import platform as platform_module
    system = platform_module.system().lower()
    machine = platform_module.machine().lower()
    
    if system == "darwin":
        if machine == "arm64":
            archive_name = f"mcp-servers-macos-apple-silicon-{platform}"
        else:
            archive_name = f"mcp-servers-macos-intel-{platform}"
    else:
        archive_name = f"mcp-servers-{system}-{machine}-{platform}"
    
    # 创建归档
    if system == "windows":
        archive_path = project_root / f"{archive_name}.zip"
        import zipfile
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for exe_file in executable_files:
                zipf.write(exe_file, exe_file.name)
    else:
        archive_path = project_root / f"{archive_name}.tar.gz"
        import tarfile
        with tarfile.open(archive_path, 'w:gz') as tar:
            for exe_file in executable_files:
                tar.add(exe_file, arcname=exe_file.name)
    
    print(f"✅ 发布包已创建: {archive_path}")
    print(f"📊 包含 {len(executable_files)} 个可执行文件")
    
    return archive_path


def main():
    parser = argparse.ArgumentParser(description='批量构建 MCP 服务器')
    parser.add_argument('--platform', '-p', 
                       default='native',
                       choices=['native', 'linux', 'windows', 'macos'],
                       help='构建平台 (默认: native)')
    parser.add_argument('--clean', '-c',
                       action='store_true',
                       help='构建前清理 dist 目录')
    parser.add_argument('--no-deps', 
                       action='store_true',
                       help='跳过依赖安装')
    parser.add_argument('--no-archive',
                       action='store_true', 
                       help='不创建归档文件')
    parser.add_argument('--output-dir', '-o',
                       help='输出目录 (默认: dist)')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='详细输出')
    
    args = parser.parse_args()
    
    print("🚀 MCP 服务器批量构建工具")
    print(f"📁 项目根目录: {project_root}")
    print(f"🖥️  目标平台: {args.platform}")
    
    # 设置输出目录
    output_dir = Path(args.output_dir) if args.output_dir else project_root / "dist"
    
    # 清理输出目录
    if args.clean:
        clean_dist_directory()
    else:
        output_dir.mkdir(exist_ok=True)
    
    # 发现服务器
    print("\n🔍 发现 MCP 服务器...")
    discovery = MCPServerDiscovery(project_root)
    servers = discovery.find_mcp_servers()
    
    if not servers:
        print("❌ 没有发现任何 MCP 服务器")
        print("\n💡 提示:")
        print("  - 确保您的 Python 文件包含 MCP 相关的导入")
        print("  - 检查文件名是否包含 'server' 关键词")
        print("  - 确保文件不是测试或示例文件")
        return 1
    
    print(f"✅ 发现 {len(servers)} 个 MCP 服务器:")
    for i, server in enumerate(servers, 1):
        print(f"  {i}. {server['name']} - {server['script_path']}")
    
    # 安装依赖
    if not args.no_deps:
        print("\n📦 安装依赖...")
        install_dependencies(servers)
    
    # 构建所有服务器
    print(f"\n🔨 开始构建 {len(servers)} 个服务器...")
    
    success_count = 0
    failed_servers = []
    
    for server in servers:
        success = build_server(server, args.platform, output_dir)
        if success:
            success_count += 1
        else:
            failed_servers.append(server['name'])
    
    # 构建摘要
    print(f"\n{'='*60}")
    print(f"📊 构建摘要: {success_count}/{len(servers)} 个服务器构建成功")
    if failed_servers:
        print(f"❌ 失败的服务器: {', '.join(failed_servers)}")
    print(f"{'='*60}")
    
    # 显示构建产物
    if success_count > 0:
        print("\n📦 构建产物:")
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                size = file_path.stat().st_size
                size_mb = size / (1024 * 1024)
                print(f"  - {file_path.name} ({size_mb:.1f} MB)")
        
        # 创建归档文件
        if not args.no_archive and success_count > 0:
            archive_path = create_archive(output_dir, args.platform)
            if archive_path:
                size = archive_path.stat().st_size
                size_mb = size / (1024 * 1024)
                print(f"\n📦 归档文件: {archive_path.name} ({size_mb:.1f} MB)")
    
    return 0 if success_count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())