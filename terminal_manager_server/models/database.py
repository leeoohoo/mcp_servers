import logging
from terminal_manager_server.models.file_storage import file_storage

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None
    ASCENDING = 1
    DESCENDING = -1
    ConnectionFailure = Exception
    ServerSelectionTimeoutError = Exception

# 默认配置值
DEFAULT_CONFIG = {
    'storage_type': 'file',
    'mongodb_uri': 'mongodb://admin:password@localhost:27017/terminal_manager?authSource=admin',
    'mongodb_db': 'terminal_manager',
    'data_dir': 'data'
}

class Database:
    _instance = None
    _client = None
    _db = None
    _storage_type = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 使用默认配置，可以通过 configure 方法更新
        if self._config is None:
            self._config = DEFAULT_CONFIG.copy()
        self._storage_type = self._config.get('storage_type', 'file')
        if self._storage_type == 'mongodb' and self._client is None:
            self.connect()
    
    def configure(self, config_dict):
        """配置数据库参数"""
        if self._config is None:
            self._config = DEFAULT_CONFIG.copy()
        
        # 更新配置
        self._config.update(config_dict)
        
        # 如果存储类型改变，需要重新连接
        old_storage_type = self._storage_type
        self._storage_type = self._config.get('storage_type', 'file')
        
        if old_storage_type != self._storage_type:
            if old_storage_type == 'mongodb':
                self.close()
            if self._storage_type == 'mongodb':
                self.connect()
    
    def connect(self):
        """连接到MongoDB数据库"""
        if not PYMONGO_AVAILABLE:
            logging.warning("PyMongo不可用，跳过MongoDB连接")
            return
            
        try:
            mongodb_uri = self._config.get('mongodb_uri', DEFAULT_CONFIG['mongodb_uri'])
            mongodb_db = self._config.get('mongodb_db', DEFAULT_CONFIG['mongodb_db'])
            
            self._client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5秒超时
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # 测试连接
            self._client.admin.command('ping')
            self._db = self._client[mongodb_db]
            
            # 创建索引
            self._create_indexes()
            
            logging.info(f"成功连接到MongoDB数据库: {mongodb_db}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logging.error(f"MongoDB连接失败: {e}")
            raise
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # Terminal集合索引
            self._db.terminals.create_index([("terminal_id", ASCENDING)], unique=True)
            self._db.terminals.create_index([("status", ASCENDING)])
            self._db.terminals.create_index([("created_at", DESCENDING)])
            
            # Command集合索引
            self._db.commands.create_index([("command_id", ASCENDING)], unique=True)
            self._db.commands.create_index([("terminal_id", ASCENDING)])
            self._db.commands.create_index([("status", ASCENDING)])
            self._db.commands.create_index([("start_time", DESCENDING)])
            self._db.commands.create_index([("terminal_id", ASCENDING), ("start_time", DESCENDING)])
            
            # Output集合索引
            self._db.outputs.create_index([("command_id", ASCENDING)])
            self._db.outputs.create_index([("timestamp", ASCENDING)])
            self._db.outputs.create_index([("command_id", ASCENDING), ("timestamp", ASCENDING)])
            
            logging.info("数据库索引创建完成")
            
        except Exception as e:
            logging.error(f"创建索引失败: {e}")
    
    def get_db(self):
        """获取数据库实例"""
        if self._db is None:
            self.connect()
        return self._db
    
    def get_collection(self, collection_name):
        """获取指定集合"""
        if self._storage_type == 'file':
            return file_storage.get_collection(collection_name)
        else:
            return self.get_db()[collection_name]
    
    def close(self):
        """关闭数据库连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logging.info("MongoDB连接已关闭")
    
    def is_connected(self):
        """检查数据库连接状态"""
        if self._storage_type == 'file':
            # 文件存储模式，总是返回True
            return True
        
        try:
            if self._client:
                self._client.admin.command('ping')
                return True
        except Exception:
            pass
        return False

# 全局数据库实例
db = Database()