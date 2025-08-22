import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from .database import db

class Output:
    """命令输出数据模型"""
    
    def __init__(self, output_id: str = None, command_id: str = None, 
                 content: str = None, output_type: str = 'stdout', 
                 timestamp: datetime = None, sequence: int = 0):
        self.output_id = output_id or str(uuid.uuid4())
        self.command_id = command_id
        self.content = content or ''
        self.output_type = output_type  # stdout, stderr, system
        self.timestamp = timestamp or datetime.utcnow()
        self.sequence = sequence  # 输出序号，用于排序
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'output_id': self.output_id,
            'command_id': self.command_id,
            'content': self.content,
            'output_type': self.output_type,
            'timestamp': self.timestamp,
            'sequence': self.sequence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Output':
        """从字典创建Output实例"""
        return cls(
            output_id=data.get('output_id'),
            command_id=data.get('command_id'),
            content=data.get('content'),
            output_type=data.get('output_type', 'stdout'),
            timestamp=data.get('timestamp'),
            sequence=data.get('sequence', 0)
        )
    
    def save(self) -> bool:
        """保存输出到数据库"""
        try:
            collection = db.get_collection('outputs')
            result = collection.insert_one(self.to_dict())
            return result.acknowledged
        except Exception as e:
            print(f"保存输出失败: {e}")
            return False
    
    @classmethod
    def save_batch(cls, outputs: List['Output']) -> bool:
        """批量保存输出"""
        try:
            if not outputs:
                return True
            
            collection = db.get_collection('outputs')
            documents = [output.to_dict() for output in outputs]
            result = collection.insert_many(documents)
            return result.acknowledged
        except Exception as e:
            print(f"批量保存输出失败: {e}")
            return False
    
    @classmethod
    def find_by_command_id(cls, command_id: str, limit: int = None) -> List['Output']:
        """根据命令ID查找输出"""
        try:
            collection = db.get_collection('outputs')
            query = {'command_id': command_id}
            cursor = collection.find(query).sort('sequence', 1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            return [cls.from_dict(data) for data in cursor]
        except Exception as e:
            print(f"查找命令输出失败: {e}")
            return []
    
    @classmethod
    def find_recent_by_command_id(cls, command_id: str, limit: int = 100) -> List['Output']:
        """查找命令最近的输出"""
        try:
            collection = db.get_collection('outputs')
            cursor = collection.find({'command_id': command_id}).sort('sequence', -1).limit(limit)
            outputs = [cls.from_dict(data) for data in cursor]
            # 返回时按正序排列
            return list(reversed(outputs))
        except Exception as e:
            print(f"查找最近输出失败: {e}")
            return []
    
    @classmethod
    def find_by_command_id_after_sequence(cls, command_id: str, last_sequence: int, limit: int = 100) -> List['Output']:
        """查找指定序号之后的输出"""
        try:
            collection = db.get_collection('outputs')
            query = {
                'command_id': command_id,
                'sequence': {'$gt': last_sequence}
            }
            cursor = collection.find(query).sort('sequence', 1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            return [cls.from_dict(data) for data in cursor]
        except Exception as e:
            print(f"查找新输出失败: {e}")
            return []
    
    @classmethod
    def get_next_sequence(cls, command_id: str) -> int:
        """获取下一个序号"""
        try:
            collection = db.get_collection('outputs')
            result = collection.find_one(
                {'command_id': command_id},
                sort=[('sequence', -1)]
            )
            return (result['sequence'] + 1) if result else 0
        except Exception as e:
            print(f"获取序号失败: {e}")
            return 0
    
    @classmethod
    def count_by_command_id(cls, command_id: str) -> int:
        """统计命令输出数量"""
        try:
            collection = db.get_collection('outputs')
            return collection.count_documents({'command_id': command_id})
        except Exception as e:
            print(f"统计输出数量失败: {e}")
            return 0
    
    @classmethod
    def delete_by_command_id(cls, command_id: str) -> bool:
        """删除命令的所有输出"""
        try:
            collection = db.get_collection('outputs')
            result = collection.delete_many({'command_id': command_id})
            return result.acknowledged
        except Exception as e:
            print(f"删除命令输出失败: {e}")
            return False
    
    @classmethod
    def delete_by_terminal_id(cls, terminal_id: str) -> bool:
        """删除终端的所有输出记录"""
        try:
            from .command import Command
            
            # 获取终端的所有命令ID
            collection = db.get_collection('commands')
            command_cursor = collection.find({'terminal_id': terminal_id}, {'command_id': 1})
            command_ids = [cmd['command_id'] for cmd in command_cursor]
            
            if not command_ids:
                return True
            
            # 删除所有相关的输出记录
            output_collection = db.get_collection('outputs')
            result = output_collection.delete_many({'command_id': {'$in': command_ids}})
            return result.acknowledged
        except Exception as e:
            print(f"删除终端输出失败: {e}")
            return False
    
    @classmethod
    def cleanup_old_outputs(cls, command_id: str, keep_count: int = 1000) -> bool:
        """清理旧的输出，只保留最新的N条"""
        try:
            collection = db.get_collection('outputs')
            
            # 获取总数
            total_count = collection.count_documents({'command_id': command_id})
            
            if total_count <= keep_count:
                return True
            
            # 找到要保留的最小序号
            skip_count = total_count - keep_count
            result = collection.find_one(
                {'command_id': command_id},
                sort=[('sequence', 1)],
                skip=skip_count
            )
            
            if result:
                min_sequence_to_keep = result['sequence']
                # 删除旧的输出
                delete_result = collection.delete_many({
                    'command_id': command_id,
                    'sequence': {'$lt': min_sequence_to_keep}
                })
                return delete_result.acknowledged
            
            return True
        except Exception as e:
            print(f"清理旧输出失败: {e}")
            return False
    
    @classmethod
    def get_combined_output(cls, command_id: str, limit: int = None) -> str:
        """获取合并的输出内容"""
        try:
            outputs = cls.find_by_command_id(command_id, limit)
            return ''.join([output.content for output in outputs])
        except Exception as e:
            print(f"获取合并输出失败: {e}")
            return ''
    
    def get_size(self) -> int:
        """获取输出内容大小（字节）"""
        return len(self.content.encode('utf-8')) if self.content else 0