import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class FileStorage:
    """基于文件的数据存储系统"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 为每个集合创建单独的文件
        self.terminals_file = self.data_dir / "terminals.json"
        self.commands_file = self.data_dir / "commands.json"
        self.outputs_file = self.data_dir / "outputs.json"
        
        # 线程锁，确保文件操作的线程安全
        self._lock = threading.RLock()
        
        # 初始化文件
        self._init_files()
    
    def _init_files(self):
        """初始化数据文件"""
        for file_path in [self.terminals_file, self.commands_file, self.outputs_file]:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
    
    def _read_file(self, file_path: Path) -> List[Dict]:
        """读取JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换datetime字符串回datetime对象
                return self._deserialize_datetime(data)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_file(self, file_path: Path, data: List[Dict]):
        """写入JSON文件"""
        # 序列化datetime对象为字符串
        serialized_data = self._serialize_datetime(data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(serialized_data, f, ensure_ascii=False, indent=2)
    
    def _serialize_datetime(self, data: Any) -> Any:
        """序列化datetime对象"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._serialize_datetime(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_datetime(item) for item in data]
        return data
    
    def _deserialize_datetime(self, data: Any) -> Any:
        """反序列化datetime对象"""
        if isinstance(data, str):
            # 尝试解析ISO格式的datetime字符串
            try:
                return datetime.fromisoformat(data.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return data
        elif isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k in ['created_at', 'updated_at', 'start_time', 'end_time', 'timestamp']:
                    result[k] = self._deserialize_datetime(v)
                else:
                    result[k] = self._deserialize_datetime(v) if isinstance(v, (dict, list)) else v
            return result
        elif isinstance(data, list):
            return [self._deserialize_datetime(item) for item in data]
        return data
    
    def get_collection(self, collection_name: str):
        """获取集合操作对象"""
        return FileCollection(self, collection_name)

class FileCollection:
    """文件集合操作类"""
    
    def __init__(self, storage: FileStorage, collection_name: str):
        self.storage = storage
        self.collection_name = collection_name
        
        # 映射集合名到文件路径
        self.file_map = {
            'terminals': storage.terminals_file,
            'commands': storage.commands_file,
            'outputs': storage.outputs_file
        }
        
        if collection_name not in self.file_map:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        self.file_path = self.file_map[collection_name]
    
    def find_one(self, query: Dict) -> Optional[Dict]:
        """查找单个文档"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            for item in data:
                if self._match_query(item, query):
                    return item
            return None
    
    def find(self, query: Dict = None) -> 'FileCursor':
        """查找多个文档"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            if query is None:
                filtered_data = data
            else:
                filtered_data = [item for item in data if self._match_query(item, query)]
            return FileCursor(filtered_data)
    
    def insert_one(self, document: Dict) -> 'InsertResult':
        """插入单个文档"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            data.append(document)
            self.storage._write_file(self.file_path, data)
            return InsertResult(True)
    
    def update_one(self, query: Dict, update: Dict, upsert: bool = False) -> 'UpdateResult':
        """更新单个文档"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            modified_count = 0
            
            for i, item in enumerate(data):
                if self._match_query(item, query):
                    if '$set' in update:
                        data[i].update(update['$set'])
                    modified_count = 1
                    break
            
            if modified_count == 0 and upsert:
                # 创建新文档
                new_doc = query.copy()
                if '$set' in update:
                    new_doc.update(update['$set'])
                data.append(new_doc)
                modified_count = 1
            
            if modified_count > 0:
                self.storage._write_file(self.file_path, data)
            
            return UpdateResult(modified_count > 0, modified_count)
    
    def delete_one(self, query: Dict) -> 'DeleteResult':
        """删除单个文档"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            for i, item in enumerate(data):
                if self._match_query(item, query):
                    del data[i]
                    self.storage._write_file(self.file_path, data)
                    return DeleteResult(1)
            return DeleteResult(0)
    
    def delete_many(self, query: Dict) -> 'DeleteResult':
        """删除多个文档"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            original_count = len(data)
            data = [item for item in data if not self._match_query(item, query)]
            deleted_count = original_count - len(data)
            
            if deleted_count > 0:
                self.storage._write_file(self.file_path, data)
            
            return DeleteResult(deleted_count)
    
    def count_documents(self, query: Dict = None) -> int:
        """统计文档数量"""
        with self.storage._lock:
            data = self.storage._read_file(self.file_path)
            if query is None:
                return len(data)
            return len([item for item in data if self._match_query(item, query)])
    
    def _match_query(self, document: Dict, query: Dict) -> bool:
        """检查文档是否匹配查询条件"""
        for key, value in query.items():
            if key not in document:
                return False
            
            if isinstance(value, dict):
                # 处理操作符查询
                if '$in' in value:
                    if document[key] not in value['$in']:
                        return False
                elif '$ne' in value:
                    if document[key] == value['$ne']:
                        return False
                elif '$gt' in value:
                    if document[key] <= value['$gt']:
                        return False
                elif '$lt' in value:
                    if document[key] >= value['$lt']:
                        return False
                elif '$gte' in value:
                    if document[key] < value['$gte']:
                        return False
                elif '$lte' in value:
                    if document[key] > value['$lte']:
                        return False
                else:
                    return False
            else:
                if document[key] != value:
                    return False
        return True

class InsertResult:
    """插入结果"""
    def __init__(self, acknowledged: bool):
        self.acknowledged = acknowledged

class UpdateResult:
    """更新结果"""
    def __init__(self, acknowledged: bool, modified_count: int = 0):
        self.acknowledged = acknowledged
        self.modified_count = modified_count

class DeleteResult:
    """删除结果"""
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.acknowledged = deleted_count > 0

class FileCursor:
    """文件游标类，模拟MongoDB游标"""
    def __init__(self, data: List[Dict]):
        self.data = data
        self._sort_key = None
        self._sort_direction = 1
    
    def sort(self, key: str, direction: int = 1) -> 'FileCursor':
        """排序"""
        self._sort_key = key
        self._sort_direction = direction
        return self
    
    def limit(self, count: int) -> 'FileCursor':
        """限制结果数量"""
        if self._sort_key:
            self._apply_sort()
        self.data = self.data[:count]
        return self
    
    def skip(self, count: int) -> 'FileCursor':
        """跳过指定数量"""
        if self._sort_key:
            self._apply_sort()
        self.data = self.data[count:]
        return self
    
    def _apply_sort(self):
        """应用排序"""
        if self._sort_key:
            reverse = self._sort_direction == -1
            try:
                self.data.sort(key=lambda x: x.get(self._sort_key, ''), reverse=reverse)
            except Exception:
                # 如果排序失败，保持原顺序
                pass
    
    def __iter__(self):
        """迭代器"""
        if self._sort_key:
            self._apply_sort()
        return iter(self.data)
    
    def __len__(self):
        """获取长度"""
        return len(self.data)
    
    def __getitem__(self, index):
        """索引访问"""
        if self._sort_key:
            self._apply_sort()
        return self.data[index]

# 创建全局文件存储实例
file_storage = FileStorage()