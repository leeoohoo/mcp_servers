#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终端清理服务
定时清理长时间未使用的终端
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List

from terminal_manager_server.models.terminal import Terminal
from terminal_manager_server.models.command import Command
from terminal_manager_server.models.output import Output
from terminal_manager_server.services.terminal_service import terminal_service

class CleanupService:
    """终端清理服务"""
    
    def __init__(self, inactive_threshold_minutes: int = 20, check_interval_seconds: int = 300):
        """
        初始化清理服务
        
        Args:
            inactive_threshold_minutes: 终端非活跃阈值（分钟），默认20分钟
            check_interval_seconds: 检查间隔（秒），默认5分钟
        """
        self.inactive_threshold_minutes = inactive_threshold_minutes
        self.check_interval_seconds = check_interval_seconds
        self.logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()
        self._cleanup_thread = None
        self._running = False
    
    def start(self):
        """启动清理服务"""
        if self._running:
            self.logger.warning("清理服务已经在运行中")
            return
        
        self.logger.info(f"启动终端清理服务 - 非活跃阈值: {self.inactive_threshold_minutes}分钟, 检查间隔: {self.check_interval_seconds}秒")
        self._stop_event.clear()
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def stop(self):
        """停止清理服务"""
        if not self._running:
            self.logger.warning("清理服务未在运行")
            return
        
        self.logger.info("停止终端清理服务")
        self._stop_event.set()
        self._running = False
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
    
    def _cleanup_loop(self):
        """清理循环"""
        while not self._stop_event.is_set():
            try:
                self._perform_cleanup()
            except Exception as e:
                self.logger.error(f"清理过程中发生异常: {e}")
            
            # 等待下次检查
            self._stop_event.wait(self.check_interval_seconds)
    
    def _perform_cleanup(self):
        """执行清理操作"""
        self.logger.debug("开始检查需要清理的终端")
        
        try:
            # 获取所有活跃终端
            active_terminals = Terminal.find_active_terminals()
            
            if not active_terminals:
                self.logger.debug("没有找到活跃终端")
                return
            
            self.logger.debug(f"找到 {len(active_terminals)} 个活跃终端")
            
            # 检查每个终端的最后活动时间
            inactive_terminals = []
            current_time = datetime.now()
            threshold_time = current_time - timedelta(minutes=self.inactive_threshold_minutes)
            
            for terminal in active_terminals:
                last_activity_time = self._get_terminal_last_activity_time(terminal)
                
                if last_activity_time and last_activity_time < threshold_time:
                    # 检查是否有正在运行的命令
                    running_command = Command.find_running_by_terminal_id(terminal.terminal_id)
                    if not running_command:
                        inactive_terminals.append(terminal)
                        self.logger.info(f"发现非活跃终端: {terminal.terminal_id}, 最后活动时间: {last_activity_time}")
                    else:
                        self.logger.debug(f"终端 {terminal.terminal_id} 有正在运行的命令，跳过清理")
            
            # 清理非活跃终端
            if inactive_terminals:
                self.logger.info(f"开始清理 {len(inactive_terminals)} 个非活跃终端")
                for terminal in inactive_terminals:
                    self._cleanup_terminal(terminal)
            else:
                self.logger.debug("没有找到需要清理的非活跃终端")
                
        except Exception as e:
            self.logger.error(f"清理检查过程中发生异常: {e}")
    
    def _get_terminal_last_activity_time(self, terminal: Terminal) -> datetime:
        """获取终端最后活动时间"""
        try:
            # 获取终端最近的命令
            recent_commands = Command.find_recent_by_terminal_id(terminal.terminal_id, 1)
            
            if recent_commands:
                # 使用最近命令的结束时间或开始时间
                last_command = recent_commands[0]
                if last_command.end_time:
                    return last_command.end_time
                elif last_command.start_time:
                    return last_command.start_time
            
            # 如果没有命令记录，使用终端的更新时间或创建时间
            if terminal.updated_at:
                return terminal.updated_at
            else:
                return terminal.created_at
                
        except Exception as e:
            self.logger.error(f"获取终端 {terminal.terminal_id} 最后活动时间失败: {e}")
            # 如果获取失败，返回创建时间作为保守估计
            return terminal.created_at
    
    def _cleanup_terminal(self, terminal: Terminal):
        """清理指定终端"""
        try:
            self.logger.info(f"开始清理终端: {terminal.terminal_id}")
            
            # 使用终端服务删除终端（包括级联删除相关数据）
            success = terminal_service.delete_terminal(terminal.terminal_id)
            
            if success:
                self.logger.info(f"成功清理终端: {terminal.terminal_id}")
            else:
                self.logger.warning(f"清理终端失败: {terminal.terminal_id}")
                
        except Exception as e:
            self.logger.error(f"清理终端 {terminal.terminal_id} 时发生异常: {e}")
    
    def force_cleanup_all_inactive(self):
        """强制清理所有非活跃终端（手动触发）"""
        self.logger.info("手动触发强制清理所有非活跃终端")
        self._perform_cleanup()
    
    def get_cleanup_stats(self) -> dict:
        """获取清理统计信息"""
        try:
            active_terminals = Terminal.find_active_terminals()
            current_time = datetime.now()
            threshold_time = current_time - timedelta(minutes=self.inactive_threshold_minutes)
            
            total_terminals = len(active_terminals)
            inactive_count = 0
            active_with_commands = 0
            
            for terminal in active_terminals:
                last_activity_time = self._get_terminal_last_activity_time(terminal)
                
                if last_activity_time and last_activity_time < threshold_time:
                    running_command = Command.find_running_by_terminal_id(terminal.terminal_id)
                    if not running_command:
                        inactive_count += 1
                    else:
                        active_with_commands += 1
            
            return {
                'total_terminals': total_terminals,
                'inactive_terminals': inactive_count,
                'active_with_commands': active_with_commands,
                'threshold_minutes': self.inactive_threshold_minutes,
                'check_interval_seconds': self.check_interval_seconds,
                'service_running': self._running
            }
            
        except Exception as e:
            self.logger.error(f"获取清理统计信息失败: {e}")
            return {
                'error': str(e),
                'service_running': self._running
            }

# 创建全局清理服务实例
cleanup_service = CleanupService(
    inactive_threshold_minutes=20,  # 默认20分钟
    check_interval_seconds=300      # 默认5分钟检查一次
)