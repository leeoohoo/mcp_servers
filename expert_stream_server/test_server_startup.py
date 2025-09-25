#!/usr/bin/env python3
"""
测试服务器启动
"""
import asyncio
import os
import sys
import logging
import subprocess
import time

# 设置测试环境变量
os.environ["TESTING_MODE"] = "true"

# 配置日志
logging.basicConfig(level=logging.DEBUG)

async def test_server_startup():
    """测试服务器启动"""
    print("🧪 测试服务器启动...")
    
    try:
        # 启动服务器进程
        print("🚀 启动服务器进程...")
        process = subprocess.Popen(
            [sys.executable, "expert_stream_server.py", "stdio", "--alias", "test_startup"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/Users/lilei/project/learn/mcp_servers/expert_stream_server"
        )
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(3)
        
        # 检查进程状态
        if process.poll() is None:
            print("✅ 服务器进程正在运行")
            
            # 发送初始化请求
            print("📤 发送初始化请求...")
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {}
                }
            }
            
            import json
            request_str = json.dumps(init_request) + "\n"
            process.stdin.write(request_str)
            process.stdin.flush()
            
            # 读取响应
            print("📥 等待响应...")
            max_attempts = 10
            for attempt in range(max_attempts):
                response_line = process.stdout.readline()
                if not response_line:
                    print(f"❌ 第 {attempt + 1} 次尝试：没有收到响应")
                    continue
                    
                response_line = response_line.strip()
                print(f"📋 第 {attempt + 1} 次响应: {response_line}")
                
                # 跳过非JSON格式的输出行（如启动信息）
                if not response_line.startswith('{'):
                    continue
                
                try:
                    response = json.loads(response_line)
                    if "result" in response:
                        print("✅ 服务器初始化成功!")
                        return True
                    elif "error" in response:
                        print(f"❌ 服务器初始化失败: {response['error']}")
                        return False
                    else:
                        print(f"📋 收到响应: {response}")
                        continue
                except json.JSONDecodeError as e:
                    print(f"⚠️  跳过非JSON响应: {response_line[:50]}...")
                    continue
            
            print("❌ 未收到有效的JSON响应")
            return False
        else:
            print(f"❌ 服务器进程已退出，退出码: {process.returncode}")
            # 读取错误输出
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"错误输出: {stderr_output}")
            return False
            
    except Exception as e:
        print(f"❌ 测试服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理进程
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait()
            print("🧹 服务器进程已终止")

async def main():
    """主函数"""
    success = await test_server_startup()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))