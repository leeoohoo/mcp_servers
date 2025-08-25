import logging
import os
from datetime import datetime
from typing import Optional, List
from terminal_manager_server.models.terminal import Terminal
from terminal_manager_server.models.command import Command

class TerminalService:
    """终端管理服务"""
    
    def __init__(self, default_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.default_dir = default_dir
    
    def create_terminal(self, working_directory: str) -> Optional[Terminal]:
        """创建新终端或复用空闲终端"""
        try:
            # 验证工作目录
            if not self._validate_working_directory(working_directory):
                if self.default_dir:
                    error_msg = f"工作目录无效: {working_directory}。只允许在以下目录下创建终端: {self.default_dir}"
                else:
                    error_msg = f"工作目录无效: {working_directory}"
                self.logger.error(error_msg)
                raise ValueError(f"INVALID_WORKING_DIRECTORY:{self.default_dir if self.default_dir else '未配置'}")
            
            # 首先检查是否有空闲终端可以复用
            idle_terminal = Terminal.find_idle_terminal_by_directory(working_directory)
            if idle_terminal:
                self.logger.info(f"复用空闲终端: {idle_terminal.terminal_id} 在目录: {working_directory}")
                # 更新终端的最后活动时间
                idle_terminal.updated_at = datetime.utcnow()
                idle_terminal.save()
                return idle_terminal
            
            # 检查终端数量限制
            if not self.can_create_terminal():
                self.logger.error("已达到最大终端数量限制")
                return None
            
            # 创建新终端实例
            terminal = Terminal(
                working_directory=working_directory,
                status='active'
            )
            
            # 保存到数据库
            if terminal.save():
                self.logger.info(f"创建新终端成功: {terminal.terminal_id} 在目录: {working_directory}")
                return terminal
            else:
                self.logger.error("保存终端到数据库失败")
                return None
                
        except ValueError as ve:
            # 重新抛出ValueError，让路由层处理
            self.logger.error(f"创建终端异常: {ve}")
            raise
        except Exception as e:
            self.logger.error(f"创建终端异常: {e}")
            return None
    
    def get_terminal(self, terminal_id: str) -> Optional[Terminal]:
        """获取终端信息"""
        try:
            return Terminal.find_by_id(terminal_id)
        except Exception as e:
            self.logger.error(f"获取终端异常: {e}")
            return None
    
    def get_active_terminals(self) -> List[Terminal]:
        """获取所有活跃终端"""
        try:
            return Terminal.find_active_terminals()
        except Exception as e:
            self.logger.error(f"获取活跃终端异常: {e}")
            return []
    
    def update_terminal_status(self, terminal_id: str, status: str) -> bool:
        """更新终端状态"""
        try:
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                self.logger.error(f"终端不存在: {terminal_id}")
                return False
            
            if terminal.update_status(status):
                self.logger.info(f"更新终端状态成功: {terminal_id} -> {status}")
                return True
            else:
                self.logger.error(f"更新终端状态失败: {terminal_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"更新终端状态异常: {e}")
            return False
    
    def delete_terminal(self, terminal_id: str) -> bool:
        """删除终端及其相关数据"""
        try:
            self.logger.debug(f"开始删除终端: {terminal_id}")
            terminal = Terminal.find_by_id(terminal_id)
            self.logger.debug(f"查找终端结果: {terminal}")
            if not terminal:
                self.logger.error(f"终端不存在: {terminal_id}")
                return False
            
            # 检查是否有正在运行的命令
            running_command = Command.find_running_by_terminal_id(terminal_id)
            if running_command:
                self.logger.warning(f"终端有正在运行的命令，无法删除: {terminal_id}")
                raise ValueError(f"TERMINAL_BUSY:{running_command.command_id}")
            
            # 级联删除相关数据
            from models.output import Output
            
            # 1. 删除所有输出记录
            Output.delete_by_terminal_id(terminal_id)
            
            # 2. 删除所有命令记录
            Command.delete_by_terminal_id(terminal_id)
            
            # 3. 删除终端记录
            if terminal.delete():
                self.logger.info(f"删除终端成功: {terminal_id}")
                return True
            else:
                self.logger.error(f"删除终端失败: {terminal_id}")
                return False
                
        except ValueError as ve:
            # 重新抛出ValueError，让路由层处理
            self.logger.error(f"删除终端异常: {ve}")
            raise
        except Exception as e:
            self.logger.error(f"删除终端异常: {e}")
            return False
    
    def can_create_terminal(self) -> bool:
        """检查是否可以创建新终端"""
        try:
            active_count = Terminal.count_active_terminals()
            return active_count < 10  # 默认最大10个终端
        except Exception as e:
            self.logger.error(f"检查终端数量异常: {e}")
            return False
    
    def is_terminal_available(self, terminal_id: str) -> bool:
        """检查终端是否可用"""
        try:
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                return False
            
            # 检查终端状态
            if terminal.status != 'active':
                return False
            
            # 检查工作目录是否仍然有效
            if not terminal.is_directory_valid():
                # 工作目录无效，更新终端状态
                terminal.update_status('dead')
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查终端可用性异常: {e}")
            return False
    
    def is_terminal_busy(self, terminal_id: str) -> bool:
        """检查终端是否忙碌（有命令在执行）"""
        try:
            running_command = Command.find_running_by_terminal_id(terminal_id)
            return running_command is not None
        except Exception as e:
            self.logger.error(f"检查终端忙碌状态异常: {e}")
            return True  # 异常时认为忙碌，安全起见
    
    def get_terminal_stats(self, terminal_id: str) -> dict:
        """获取终端统计信息"""
        try:
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                return {}
            
            # 统计命令数量
            total_commands = Command.count_by_terminal_id(terminal_id)
            
            # 获取最近命令
            recent_commands = Command.find_recent_by_terminal_id(terminal_id, 5)
            
            # 检查是否有正在运行的命令
            running_command = Command.find_running_by_terminal_id(terminal_id)
            
            return {
                'terminal_id': terminal_id,
                'status': terminal.status,
                'working_directory': terminal.working_directory,
                'created_at': terminal.created_at.isoformat(),
                'total_commands': total_commands,
                'recent_commands_count': len(recent_commands),
                'has_running_command': running_command is not None,
                'running_command_id': running_command.command_id if running_command else None
            }
            
        except Exception as e:
            self.logger.error(f"获取终端统计信息异常: {e}")
            return {}
    
    def cleanup_inactive_terminals(self) -> int:
        """清理不活跃的终端"""
        try:
            terminals = Terminal.find_active_terminals()
            cleaned_count = 0
            
            for terminal in terminals:
                # 检查工作目录是否仍然有效
                if not terminal.is_directory_valid():
                    terminal.update_status('dead')
                    cleaned_count += 1
                    self.logger.info(f"标记终端为dead（目录无效）: {terminal.terminal_id}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"清理不活跃终端异常: {e}")
            return 0
    
    def get_terminal_info(self, terminal_id: str) -> Optional[dict]:
        """获取终端详细信息"""
        try:
            terminal = Terminal.find_by_id(terminal_id)
            if not terminal:
                return None
            
            stats = self.get_terminal_stats(terminal_id)
            return {
                'terminal_id': terminal.terminal_id,
                'working_directory': terminal.working_directory,
                'status': terminal.status,
                'created_at': terminal.created_at.isoformat(),
                'updated_at': terminal.updated_at.isoformat() if terminal.updated_at else None,
                'stats': stats
            }
        except Exception as e:
            self.logger.error(f"获取终端信息异常: {e}")
            return None
    
    def _validate_working_directory(self, directory: str) -> bool:
        """验证工作目录"""
        try:
            # 检查目录是否存在
            if not os.path.exists(directory):
                self.logger.error(f"工作目录不存在: {directory}")
                return False
            
            # 检查是否为目录
            if not os.path.isdir(directory):
                self.logger.error(f"路径不是目录: {directory}")
                return False
            
            # 检查权限
            if not os.access(directory, os.R_OK | os.X_OK):
                self.logger.error(f"工作目录权限不足: {directory}")
                return False
            
            # 检查路径安全性（防止路径遍历）
            normalized_path = os.path.normpath(directory)
            if '..' in normalized_path:
                self.logger.error(f"工作目录包含不安全路径: {directory}")
                return False
            
            # 如果配置了默认工作目录，检查是否在允许的目录下
            if self.default_dir:
                normalized_default = os.path.normpath(self.default_dir)
                normalized_requested = os.path.normpath(directory)
                
                # 检查请求的目录是否在默认目录下或就是默认目录
                if not (normalized_requested == normalized_default or 
                        normalized_requested.startswith(normalized_default + os.sep)):
                    self.logger.error(f"工作目录不在允许范围内。请求目录: {directory}, 允许的工作目录: {self.default_dir}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证工作目录异常: {e}")
            return False

# 创建全局终端服务实例
terminal_service = TerminalService()