import os
import re
import uuid

def validate_directory(directory_path):
    """验证目录路径是否有效"""
    if not directory_path:
        return False
    
    try:
        # 检查路径是否存在且为目录
        if not os.path.exists(directory_path):
            return False
        
        if not os.path.isdir(directory_path):
            return False
        
        # 检查是否有读取权限
        if not os.access(directory_path, os.R_OK):
            return False
        
        # 检查是否有执行权限（进入目录）
        if not os.access(directory_path, os.X_OK):
            return False
        
        return True
        
    except Exception:
        return False

def validate_terminal_id(terminal_id):
    """验证终端ID格式"""
    if not terminal_id:
        return False
    
    try:
        # 检查是否为有效的UUID格式
        uuid.UUID(terminal_id)
        return True
    except ValueError:
        return False

def validate_command_id(command_id):
    """验证命令ID格式"""
    if not command_id:
        return False
    
    try:
        # 检查是否为有效的UUID格式
        uuid.UUID(command_id)
        return True
    except ValueError:
        return False

def validate_command(command):
    """验证命令内容"""
    if not command or not isinstance(command, str):
        return False
    
    # 去除首尾空格
    command = command.strip()
    
    if not command:
        return False
    
    # 检查命令长度
    if len(command) > 10000:  # 限制命令长度
        return False
    
    # 检查是否包含危险字符（可根据需要调整）
    dangerous_patterns = [
        r'\x00',  # null字符
        r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]',  # 控制字符
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            return False
    
    return True

def validate_pagination(page, limit):
    """验证分页参数"""
    try:
        page = int(page) if page else 1
        limit = int(limit) if limit else 10
        
        if page < 1:
            page = 1
        
        if limit < 1:
            limit = 1
        elif limit > 100:  # 限制最大页面大小
            limit = 100
        
        return page, limit
        
    except (ValueError, TypeError):
        return 1, 10

def validate_output_limit(limit):
    """验证输出限制参数"""
    try:
        limit = int(limit) if limit else None
        
        if limit is not None:
            if limit < 1:
                limit = 1
            elif limit > 10000:  # 限制最大输出行数
                limit = 10000
        
        return limit
        
    except (ValueError, TypeError):
        return None

def is_safe_path(path):
    """检查路径是否安全（防止路径遍历攻击）"""
    if not path:
        return False
    
    try:
        # 规范化路径
        normalized_path = os.path.normpath(path)
        
        # 检查是否包含路径遍历字符
        if '..' in normalized_path:
            return False
        
        # 检查是否为绝对路径
        if not os.path.isabs(normalized_path):
            return False
        
        return True
        
    except Exception:
        return False

def validate_working_directory(directory):
    """验证工作目录（结合安全性和有效性检查）"""
    if not is_safe_path(directory):
        return False
    
    return validate_directory(directory)