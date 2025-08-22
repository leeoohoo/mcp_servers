import logging
import os
import signal
import subprocess
import threading
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class ProcessManager:
    """进程管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processes: Dict[str, subprocess.Popen] = {}  # command_id -> process
        self.process_lock = threading.Lock()
        
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_dead_processes, daemon=True)
        self.cleanup_thread.start()
    
    def register_process(self, command_id: str, process: subprocess.Popen):
        """注册进程"""
        with self.process_lock:
            self.processes[command_id] = process
            self.logger.info(f"注册进程: {command_id} -> PID {process.pid}")
    
    def unregister_process(self, command_id: str):
        """注销进程"""
        with self.process_lock:
            if command_id in self.processes:
                process = self.processes.pop(command_id)
                self.logger.info(f"注销进程: {command_id} -> PID {process.pid}")
    
    def get_process(self, command_id: str) -> Optional[subprocess.Popen]:
        """获取进程"""
        with self.process_lock:
            return self.processes.get(command_id)
    
    def kill_process(self, pid: int) -> bool:
        """终止进程"""
        try:
            # 检查进程是否存在
            if not self._is_process_running(pid):
                self.logger.warning(f"进程不存在或已结束: {pid}")
                return True
            
            # 尝试优雅终止
            try:
                os.kill(pid, signal.SIGTERM)
                self.logger.info(f"发送SIGTERM信号到进程: {pid}")
                
                # 等待进程结束
                for _ in range(30):  # 等待3秒
                    if not self._is_process_running(pid):
                        self.logger.info(f"进程已优雅结束: {pid}")
                        return True
                    time.sleep(0.1)
                
                # 如果进程仍在运行，强制终止
                self.logger.warning(f"进程未响应SIGTERM，发送SIGKILL: {pid}")
                os.kill(pid, signal.SIGKILL)
                
                # 再次等待
                for _ in range(10):  # 等待1秒
                    if not self._is_process_running(pid):
                        self.logger.info(f"进程已强制结束: {pid}")
                        return True
                    time.sleep(0.1)
                
                self.logger.error(f"无法终止进程: {pid}")
                return False
                
            except ProcessLookupError:
                # 进程已经不存在
                self.logger.info(f"进程已不存在: {pid}")
                return True
                
        except Exception as e:
            self.logger.error(f"终止进程异常: {pid} - {e}")
            return False
    
    def kill_process_by_command(self, command_id: str) -> bool:
        """根据命令ID终止进程"""
        process = self.get_process(command_id)
        if not process:
            self.logger.warning(f"未找到命令对应的进程: {command_id}")
            return False
        
        return self.kill_process(process.pid)
    
    def is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行"""
        return self._is_process_running(pid)
    
    def get_process_info(self, pid: int) -> Optional[dict]:
        """获取进程信息"""
        try:
            if not self._is_process_running(pid):
                return None
            
            # 尝试获取进程信息
            try:
                # 读取进程状态文件
                with open(f'/proc/{pid}/stat', 'r') as f:
                    stat_data = f.read().split()
                
                # 读取进程状态
                with open(f'/proc/{pid}/status', 'r') as f:
                    status_lines = f.readlines()
                
                status_dict = {}
                for line in status_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        status_dict[key.strip()] = value.strip()
                
                return {
                    'pid': pid,
                    'name': status_dict.get('Name', 'unknown'),
                    'state': stat_data[2] if len(stat_data) > 2 else 'unknown',
                    'ppid': int(stat_data[3]) if len(stat_data) > 3 else 0,
                    'memory': status_dict.get('VmRSS', '0 kB'),
                    'threads': int(status_dict.get('Threads', '0'))
                }
                
            except (FileNotFoundError, PermissionError, ValueError):
                # 在macOS上，/proc不存在，使用ps命令
                result = subprocess.run(
                    ['ps', '-p', str(pid), '-o', 'pid,ppid,state,comm,rss,nlwp'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        data = lines[1].split()
                        if len(data) >= 6:
                            return {
                                'pid': int(data[0]),
                                'ppid': int(data[1]),
                                'state': data[2],
                                'name': data[3],
                                'memory': f"{data[4]} KB",
                                'threads': int(data[5])
                            }
                
                return {'pid': pid, 'running': True}
                
        except Exception as e:
            self.logger.error(f"获取进程信息异常: {pid} - {e}")
            return None
    
    def get_all_managed_processes(self) -> Dict[str, dict]:
        """获取所有管理的进程信息"""
        result = {}
        with self.process_lock:
            for command_id, process in self.processes.items():
                info = self.get_process_info(process.pid)
                if info:
                    result[command_id] = {
                        'command_id': command_id,
                        'process_info': info,
                        'start_time': getattr(process, 'start_time', None)
                    }
        return result
    
    def cleanup_dead_processes(self) -> int:
        """清理已死亡的进程"""
        cleaned_count = 0
        with self.process_lock:
            dead_commands = []
            for command_id, process in self.processes.items():
                if process.poll() is not None:  # 进程已结束
                    dead_commands.append(command_id)
            
            for command_id in dead_commands:
                self.processes.pop(command_id)
                cleaned_count += 1
                self.logger.info(f"清理已结束进程: {command_id}")
        
        return cleaned_count
    
    def kill_all_processes(self) -> int:
        """终止所有管理的进程"""
        killed_count = 0
        with self.process_lock:
            for command_id, process in list(self.processes.items()):
                if self.kill_process(process.pid):
                    killed_count += 1
                self.processes.pop(command_id, None)
        
        self.logger.info(f"终止了 {killed_count} 个进程")
        return killed_count
    
    def get_process_count(self) -> int:
        """获取管理的进程数量"""
        with self.process_lock:
            return len(self.processes)
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行（内部方法）"""
        try:
            # 发送信号0来检查进程是否存在
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def _cleanup_dead_processes(self):
        """定期清理已死亡的进程（后台线程）"""
        while True:
            try:
                cleaned = self.cleanup_dead_processes()
                if cleaned > 0:
                    self.logger.info(f"定期清理了 {cleaned} 个已结束的进程")
                
                time.sleep(30)  # 每30秒清理一次
                
            except Exception as e:
                self.logger.error(f"定期清理进程异常: {e}")
                time.sleep(60)  # 出错时等待更长时间
    
    def shutdown(self):
        """关闭进程管理器"""
        self.logger.info("正在关闭进程管理器...")
        
        # 终止所有进程
        killed_count = self.kill_all_processes()
        
        self.logger.info(f"进程管理器已关闭，终止了 {killed_count} 个进程")