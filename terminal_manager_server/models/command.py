import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from .database import db

class Command:
    """命令数据模型"""
    
    def __init__(self, command_id: str = None, terminal_id: str = None, 
                 command: str = None, status: str = 'pending', 
                 start_time: datetime = None, end_time: datetime = None,
                 exit_code: int = None, pid: int = None, command_type: str = 'normal'):
        self.command_id = command_id or str(uuid.uuid4())
        self.terminal_id = terminal_id
        self.command = command
        self.status = status  # pending, running, completed, failed, killed
        self.start_time = start_time or datetime.utcnow()
        self.end_time = end_time
        self.exit_code = exit_code
        self.pid = pid
        self.command_type = command_type  # normal, service, interactive
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'command_id': self.command_id,
            'terminal_id': self.terminal_id,
            'command': self.command,
            'status': self.status,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'exit_code': self.exit_code,
            'pid': self.pid,
            'command_type': self.command_type,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Command':
        """从字典创建Command实例"""
        return cls(
            command_id=data.get('command_id'),
            terminal_id=data.get('terminal_id'),
            command=data.get('command'),
            status=data.get('status', 'pending'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            exit_code=data.get('exit_code'),
            pid=data.get('pid'),
            command_type=data.get('command_type', 'normal')
        )
    
    def save(self) -> bool:
        """保存命令到数据库"""
        try:
            collection = db.get_collection('commands')
            result = collection.update_one(
                {'command_id': self.command_id},
                {'$set': self.to_dict()},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            print(f"保存命令失败: {e}")
            return False
    
    @classmethod
    def find_by_id(cls, command_id: str) -> Optional['Command']:
        """根据ID查找命令"""
        try:
            collection = db.get_collection('commands')
            data = collection.find_one({'command_id': command_id})
            return cls.from_dict(data) if data else None
        except Exception as e:
            print(f"查找命令失败: {e}")
            return None
    
    @classmethod
    def find_by_terminal_id(cls, terminal_id: str, page: int = 1, limit: int = 10) -> List['Command']:
        """根据终端ID查找命令（分页）"""
        try:
            collection = db.get_collection('commands')
            skip = (page - 1) * limit
            cursor = collection.find({'terminal_id': terminal_id}).sort('start_time', -1).skip(skip).limit(limit)
            return [cls.from_dict(data) for data in cursor]
        except Exception as e:
            print(f"查找终端命令失败: {e}")
            return []
    
    @classmethod
    def find_recent_by_terminal_id(cls, terminal_id: str, limit: int = 5) -> List['Command']:
        """查找终端最近的命令"""
        try:
            collection = db.get_collection('commands')
            cursor = collection.find({'terminal_id': terminal_id}).sort('start_time', -1).limit(limit)
            return [cls.from_dict(data) for data in cursor]
        except Exception as e:
            print(f"查找最近命令失败: {e}")
            return []
    
    @classmethod
    def find_running_by_terminal_id(cls, terminal_id: str) -> Optional['Command']:
        """查找终端正在运行的命令"""
        try:
            collection = db.get_collection('commands')
            data = collection.find_one({
                'terminal_id': terminal_id,
                'status': {'$in': ['pending', 'running']}
            })
            return cls.from_dict(data) if data else None
        except Exception as e:
            print(f"查找运行中命令失败: {e}")
            return None
    
    @classmethod
    def count_by_terminal_id(cls, terminal_id: str) -> int:
        """统计终端命令数量"""
        try:
            collection = db.get_collection('commands')
            return collection.count_documents({'terminal_id': terminal_id})
        except Exception as e:
            print(f"统计命令数量失败: {e}")
            return 0
    
    def update_status(self, status: str, exit_code: int = None) -> bool:
        """更新命令状态"""
        try:
            self.status = status
            if status in ['completed', 'failed', 'killed']:
                self.end_time = datetime.utcnow()
            if exit_code is not None:
                self.exit_code = exit_code
            
            collection = db.get_collection('commands')
            update_data = {
                'status': self.status,
                'end_time': self.end_time,
                'exit_code': self.exit_code
            }
            
            result = collection.update_one(
                {'command_id': self.command_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"更新命令状态失败: {e}")
            return False
    
    def set_pid(self, pid: int) -> bool:
        """设置进程ID"""
        try:
            self.pid = pid
            collection = db.get_collection('commands')
            result = collection.update_one(
                {'command_id': self.command_id},
                {'$set': {'pid': pid}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"设置PID失败: {e}")
            return False
    
    def delete(self) -> bool:
        """删除命令"""
        try:
            collection = db.get_collection('commands')
            result = collection.delete_one({'command_id': self.command_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"删除命令失败: {e}")
            return False
    
    @classmethod
    def delete_by_terminal_id(cls, terminal_id: str) -> bool:
        """删除终端的所有命令"""
        try:
            collection = db.get_collection('commands')
            result = collection.delete_many({'terminal_id': terminal_id})
            return result.acknowledged
        except Exception as e:
            print(f"删除终端命令失败: {e}")
            return False
    
    def is_service_command(self) -> bool:
        """判断是否为服务类命令"""
        if not self.command:
            return False
        
        service_keywords = ['server', 'daemon', 'service', 'start', 'run', 'serve', 'listen']
        long_running_keywords = ['tail -f', 'watch', 'monitor', 'top', 'htop']
        
        command_lower = self.command.lower()
        
        # 检查服务关键词
        for keyword in service_keywords:
            if keyword in command_lower:
                return True
        
        # 检查长期运行关键词
        for keyword in long_running_keywords:
            if keyword in command_lower:
                return True
        
        return False
    
    def get_duration(self) -> Optional[float]:
        """获取命令执行时长（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return None