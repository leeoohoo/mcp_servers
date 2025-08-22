import logging
import os
import subprocess
import threading
import time
from typing import Optional, List, Generator, Tuple
from terminal_manager_server.models.command import Command
from terminal_manager_server.models.output import Output
from terminal_manager_server.models.terminal import Terminal
from .process_manager import ProcessManager

class CommandService:
    """命令执行服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.process_manager = ProcessManager()
    
    def execute_command(self, terminal_id: str, command_text: str, 
                       command_type: str = 'normal') -> Optional[Command]:
        """执行命令"""
        try:
            # 验证终端
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                self.logger.error(f"终端不存在: {terminal_id}")
                raise ValueError("TERMINAL_NOT_FOUND")
            
            if terminal.status != 'active':
                self.logger.error(f"终端状态不可用: {terminal_id} - {terminal.status}")
                raise ValueError(f"TERMINAL_INACTIVE:{terminal.status}")
            
            # 检查是否有正在运行的命令
            running_command = Command.find_running_by_terminal_id(terminal_id)
            if running_command:
                self.logger.warning(f"终端有正在运行的命令: {terminal_id}")
                # 可以选择终止之前的命令或拒绝新命令
                # 这里选择拒绝新命令
                raise ValueError(f"TERMINAL_BUSY:{running_command.command_id}")
            
            # 创建命令记录
            command = Command(
                terminal_id=terminal_id,
                command=command_text.strip(),
                command_type=command_type,
                status='pending'
            )
            
            if not command.save():
                self.logger.error("保存命令记录失败")
                return None
            
            # 异步执行命令
            thread = threading.Thread(
                target=self._execute_command_async,
                args=(command, terminal.working_directory),
                daemon=True
            )
            thread.start()
            
            self.logger.info(f"开始执行命令: {command.command_id} - {command_text}")
            return command
            
        except ValueError:
            # 重新抛出ValueError，让路由层处理具体的错误类型
            raise
        except Exception as e:
            self.logger.error(f"执行命令异常: {e}")
            return None
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """获取命令信息"""
        try:
            return Command.find_by_id(command_id)
        except Exception as e:
            self.logger.error(f"获取命令异常: {e}")
            return None
    
    def get_command_output(self, command_id: str, limit: int = 100, 
                          output_type: str = 'all') -> List[Output]:
        """获取命令输出"""
        try:
            return Output.find_by_command_id(command_id, limit, output_type)
        except Exception as e:
            self.logger.error(f"获取命令输出异常: {e}")
            return []
    
    def get_command_output_stream(self, command_id: str) -> Generator[str, None, None]:
        """获取命令输出流（用于SSE）"""
        try:
            command = Command.find_by_id(command_id)
            if not command:
                yield f"data: {{\"error\": \"命令不存在\", \"command_id\": \"{command_id}\"}}\n\n"
                return
            
            # 发送命令开始信息
            yield f"data: {{\"type\": \"start\", \"command_id\": \"{command_id}\", \"command\": \"{command.command}\", \"status\": \"{command.status}\"}}\n\n"
            
            last_sequence = 0
            
            while True:
                # 获取新的输出
                outputs = Output.find_by_command_id_after_sequence(
                    command_id, 
                    last_sequence, 
                    50
                )
                
                for output in outputs:
                    yield f"data: {{\"type\": \"output\", \"output_type\": \"{output.output_type}\", \"content\": \"{self._escape_json_string(output.content)}\", \"timestamp\": \"{output.timestamp.isoformat()}\", \"sequence\": {output.sequence}}}\n\n"
                    last_sequence = max(last_sequence, output.sequence)
                
                # 检查命令状态
                command = Command.find_by_id(command_id)
                if not command:
                    break
                
                if command.status in ['completed', 'failed', 'killed']:
                    # 发送命令结束信息
                    yield f"data: {{\"type\": \"end\", \"command_id\": \"{command_id}\", \"status\": \"{command.status}\", \"exit_code\": {command.exit_code or 'null'}, \"duration\": {command.get_duration()}}}\n\n"
                    break
                
                time.sleep(0.1)  # 避免过于频繁的查询
                
        except Exception as e:
            self.logger.error(f"获取命令输出流异常: {e}")
            yield f"data: {{\"error\": \"获取输出流异常: {str(e)}\", \"command_id\": \"{command_id}\"}}\n\n"
    
    def kill_command(self, command_id: str) -> bool:
        """终止命令"""
        try:
            command = Command.find_by_id(command_id)
            if not command:
                self.logger.error(f"命令不存在: {command_id}")
                return False
            
            if command.status not in ['pending', 'running']:
                self.logger.warning(f"命令状态不允许终止: {command_id} - {command.status}")
                return False
            
            # 终止进程
            if command.pid:
                if self.process_manager.kill_process(command.pid):
                    self.logger.info(f"成功终止进程: {command.pid}")
                else:
                    self.logger.warning(f"终止进程失败: {command.pid}")
            
            # 更新命令状态
            command.update_status('killed')
            
            # 添加系统输出
            self._add_system_output(command_id, "命令被用户终止")
            
            self.logger.info(f"命令已终止: {command_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"终止命令异常: {e}")
            return False
    
    def get_running_commands(self, terminal_id: Optional[str] = None) -> List[Command]:
        """获取正在运行的命令"""
        try:
            if terminal_id:
                command = Command.find_running_by_terminal_id(terminal_id)
                return [command] if command else []
            else:
                # 这里需要扩展Command模型来支持查找所有运行中的命令
                # 暂时返回空列表
                return []
        except Exception as e:
            self.logger.error(f"获取运行中命令异常: {e}")
            return []
    
    def get_command_history(self, terminal_id: str, page: int = 1, 
                           per_page: int = 20) -> Tuple[List[Command], int]:
        """获取命令历史"""
        try:
            commands = Command.find_by_terminal_id(terminal_id, page, per_page)
            total = Command.count_by_terminal_id(terminal_id)
            return commands, total
        except Exception as e:
            self.logger.error(f"获取命令历史异常: {e}")
            return [], 0
    
    def get_recent_commands(self, terminal_id: str, limit: int = 5) -> Optional[dict]:
        """获取最近命令"""
        try:
            from models.terminal import Terminal
            
            # 检查终端是否存在
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                return None
            
            commands = Command.find_recent_by_terminal_id(terminal_id, limit)
            result = []
            
            for cmd in commands:
                cmd_data = {
                    'command_id': cmd.command_id,
                    'command': cmd.command,
                    'status': cmd.status,
                    'created_at': cmd.created_at.isoformat(),
                    'end_time': cmd.end_time.isoformat() if cmd.end_time else None,
                    'exit_code': cmd.exit_code,
                    'command_type': cmd.command_type,
                    'duration': cmd.get_duration()
                }
                result.append(cmd_data)
            
            return {
                'commands': result,
                'count': len(result)
            }
        except Exception as e:
            self.logger.error(f"获取最近命令异常: {e}")
            return None
    
    def get_terminal_commands(self, terminal_id: str, page: int = 1, limit: int = 10) -> Optional[dict]:
        """获取终端命令历史"""
        try:
            # 确保参数是整数类型
            page = int(page) if isinstance(page, str) else page
            limit = int(limit) if isinstance(limit, str) else limit
            
            from models.terminal import Terminal
            
            # 检查终端是否存在
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                return None
            
            commands, total = self.get_command_history(terminal_id, page, limit)
            result = []
            
            for cmd in commands:
                cmd_data = {
                    'command_id': cmd.command_id,
                    'command': cmd.command,
                    'status': cmd.status,
                    'created_at': cmd.created_at.isoformat(),
                    'end_time': cmd.end_time.isoformat() if cmd.end_time else None,
                    'exit_code': cmd.exit_code,
                    'command_type': cmd.command_type,
                    'duration': cmd.get_duration()
                }
                result.append(cmd_data)
            
            return {
                'commands': result,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
        except Exception as e:
            self.logger.error(f"获取终端命令历史异常: {e}")
            return None
    
    def _execute_command_async(self, command: Command, working_directory: str):
        """异步执行命令"""
        try:
            # 更新命令状态为运行中
            command.update_status('running')
            
            # 添加开始执行的系统输出
            self._add_system_output(command.command_id, f"开始执行命令: {command.command}")
            
            # 准备执行环境
            env = dict(os.environ)
            env.update({
                'TERM': 'xterm-256color',
                'COLUMNS': '80',
                'LINES': '24'
            })
            
            # 执行命令
            process = subprocess.Popen(
                command.command,
                shell=True,
                cwd=working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 保存进程ID
            command.set_pid(process.pid)
            
            # 注册进程到进程管理器
            self.process_manager.register_process(command.command_id, process)
            
            # 读取输出
            self._read_process_output(command.command_id, process)
            
            # 等待进程结束
            exit_code = process.wait()
            
            # 更新命令状态
            if exit_code == 0:
                command.update_status('completed')
                self._add_system_output(command.command_id, f"命令执行完成，退出码: {exit_code}")
            else:
                command.update_status('failed')
                self._add_system_output(command.command_id, f"命令执行失败，退出码: {exit_code}")
            
            # 设置退出码
            command.exit_code = exit_code
            command.save()
            
            # 从进程管理器中移除
            self.process_manager.unregister_process(command.command_id)
            
            self.logger.info(f"命令执行完成: {command.command_id} - 退出码: {exit_code}")
            
        except Exception as e:
            self.logger.error(f"执行命令异常: {command.command_id} - {e}")
            command.update_status('failed')
            self._add_system_output(command.command_id, f"命令执行异常: {str(e)}")
            
            # 从进程管理器中移除
            self.process_manager.unregister_process(command.command_id)
    
    def _read_process_output(self, command_id: str, process: subprocess.Popen):
        """读取进程输出"""
        def read_stdout():
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self._add_output(command_id, line.rstrip('\n'), 'stdout')
            except Exception as e:
                self.logger.error(f"读取stdout异常: {e}")
        
        def read_stderr():
            try:
                while True:
                    line = process.stderr.readline()
                    if not line:
                        break
                    self._add_output(command_id, line.rstrip('\n'), 'stderr')
            except Exception as e:
                self.logger.error(f"读取stderr异常: {e}")
        
        # 启动读取线程
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        
        stdout_thread.start()
        stderr_thread.start()
        
        # 等待读取完成，不设置超时
        stdout_thread.join()
        stderr_thread.join()
    
    def _add_output(self, command_id: str, content: str, output_type: str):
        """添加命令输出"""
        try:
            # 获取当前命令的输出数量作为序号
            current_count = Output.count_by_command_id(command_id)
            
            output = Output(
                command_id=command_id,
                content=content,
                output_type=output_type,
                sequence=current_count + 1
            )
            output.save()
            self.logger.info(f"保存输出成功 - 命令ID: {command_id}, 序号: {current_count + 1}, 类型: {output_type}, 内容: {content[:50]}...")
        except Exception as e:
            self.logger.error(f"保存输出异常: {e}")
    
    def _add_system_output(self, command_id: str, content: str):
        """添加系统输出"""
        self._add_output(command_id, content, 'system')
    
    def _escape_json_string(self, text: str) -> str:
        """转义JSON字符串"""
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')