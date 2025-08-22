import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from .database import db

class Terminal:
    """终端数据模型"""
    
    def __init__(self, terminal_id: str = None, working_directory: str = None, 
                 status: str = 'active', created_at: datetime = None):
        self.terminal_id = terminal_id or str(uuid.uuid4())
        self.working_directory = working_directory or os.getcwd()
        self.status = status  # active, inactive, dead
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'terminal_id': self.terminal_id,
            'working_directory': self.working_directory,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Terminal':
        """从字典创建Terminal实例"""
        return cls(
            terminal_id=data.get('terminal_id'),
            working_directory=data.get('working_directory'),
            status=data.get('status', 'active'),
            created_at=data.get('created_at')
        )
    
    def save(self) -> bool:
        """保存终端到数据库"""
        try:
            collection = db.get_collection('terminals')
            self.updated_at = datetime.utcnow()
            
            result = collection.update_one(
                {'terminal_id': self.terminal_id},
                {'$set': self.to_dict()},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            print(f"保存终端失败: {e}")
            return False
    
    @classmethod
    def find_by_id(cls, terminal_id: str) -> Optional['Terminal']:
        """根据ID查找终端"""
        try:
            collection = db.get_collection('terminals')
            print(f"查找终端 - terminal_id: {terminal_id}")
            data = collection.find_one({'terminal_id': terminal_id})
            print(f"数据库查询结果: {data}")
            result = cls.from_dict(data) if data else None
            print(f"最终返回结果: {result}")
            return result
        except Exception as e:
            print(f"查找终端失败: {e}")
            return None
    
    @classmethod
    def find_active_terminals(cls) -> List['Terminal']:
        """查找所有活跃终端"""
        try:
            collection = db.get_collection('terminals')
            cursor = collection.find({'status': 'active'}).sort('created_at', -1)
            return [cls.from_dict(data) for data in cursor]
        except Exception as e:
            print(f"查找活跃终端失败: {e}")
            return []
    
    @classmethod
    def count_active_terminals(cls) -> int:
        """统计活跃终端数量"""
        try:
            collection = db.get_collection('terminals')
            return collection.count_documents({'status': 'active'})
        except Exception as e:
            print(f"统计活跃终端失败: {e}")
            return 0
    
    def update_status(self, status: str) -> bool:
        """更新终端状态"""
        try:
            self.status = status
            self.updated_at = datetime.utcnow()
            
            collection = db.get_collection('terminals')
            result = collection.update_one(
                {'terminal_id': self.terminal_id},
                {'$set': {'status': status, 'updated_at': self.updated_at}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"更新终端状态失败: {e}")
            return False
    
    def delete(self) -> bool:
        """删除终端"""
        try:
            collection = db.get_collection('terminals')
            result = collection.delete_one({'terminal_id': self.terminal_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"删除终端失败: {e}")
            return False
    
    def is_directory_valid(self) -> bool:
        """检查工作目录是否有效"""
        return os.path.isdir(self.working_directory) and os.access(self.working_directory, os.R_OK)