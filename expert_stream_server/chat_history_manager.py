import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
# 配置日志
logger = logging.getLogger("ChatHistoryManager")


class ChatHistoryManager:
    """聊天记录管理器，支持MongoDB和文件存储"""

    def __init__(self, mongodb_url: str = "", history_limit: int = 10, enable_history: bool = True):
        self.mongodb_url = mongodb_url
        self.history_limit = history_limit
        self.enable_history = enable_history
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.file_path = "data/chat_history.json"
        self.initialized = False
        self.use_mongo = False
        self._init_lock = asyncio.Lock()

        # 确保数据目录存在
        os.makedirs("data", exist_ok=True)

    async def initialize(self):
        """初始化存储（异步探查MongoDB，短超时，失败降级到文件）"""
        if not self.enable_history:
            logger.info("📝 聊天记录功能已禁用")
            return

        # 先确保文件存储可用，作为兜底
        self._init_file_storage_if_needed()

        # 检查测试模式与依赖可用性
        import os
        testing_mode = os.environ.get("TESTING_MODE", "false").lower() == "true"

        if testing_mode:
            logger.info("🧪 测试模式：跳过MongoDB连接，使用文件存储")
            async with self._init_lock:
                self.initialized = True
                self.use_mongo = False
            return

        # 异步短超时探查 MongoDB，成功则切换到 mongo
        if self.mongodb_url and PYMONGO_AVAILABLE:
            try:
                await asyncio.wait_for(self._try_init_mongo(), timeout=2.0)
                async with self._init_lock:
                    self.initialized = True
                    self.use_mongo = True
                logger.info("📝 MongoDB聊天记录存储已连接并启用")
                return
            except Exception as e:
                logger.warning(f"⚠️ MongoDB探查失败，使用文件存储: {e}")

        # 使用文件存储
        async with self._init_lock:
            self.initialized = True
            self.use_mongo = False
        logger.info(f"📝 文件聊天记录存储已初始化: {self.file_path}")

    async def save_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None):
        """保存消息"""
        if not self.enable_history:
            return

        # 确保已初始化（懒探查，短超时，不阻塞主流程）
        try:
            await asyncio.wait_for(self._ensure_initialized(), timeout=1.5)
        except Exception:
            # 初始化失败或超时，继续使用文件存储兜底
            pass

        message = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }

        try:
            if self.collection and self.use_mongo:
                # MongoDB存储
                await asyncio.get_event_loop().run_in_executor(
                    None, self.collection.insert_one, message
                )
            else:
                # 文件存储
                await self._save_to_file(message)

            # 记录保存的消息类型
            msg_type = metadata.get('type', 'normal') if metadata else 'normal'
            logger.debug(f"📝 已保存消息: role={role}, type={msg_type}, content_len={len(content)}")

        except Exception as e:
            logger.error(f"❌ 保存聊天记录失败: {e}")

    async def get_history(self, conversation_id: str, limit: int = None) -> List[Dict]:
        """获取历史记录"""
        if not self.enable_history:
            return []

        limit = limit or self.history_limit

        # 确保已初始化（懒探查，短超时，不阻塞主流程）
        try:
            await asyncio.wait_for(self._ensure_initialized(), timeout=1.5)
        except Exception:
            pass

        try:
            if self.collection and self.use_mongo:
                # MongoDB查询
                cursor = self.collection.find(
                    {"conversation_id": conversation_id}
                ).sort("timestamp", -1).limit(limit)

                messages = await asyncio.get_event_loop().run_in_executor(
                    None, list, cursor
                )
                # 转换ObjectId为字符串并反转顺序
                for msg in messages:
                    msg["_id"] = str(msg["_id"])
                    msg["timestamp"] = msg["timestamp"].isoformat()
                return list(reversed(messages))
            else:
                # 文件查询
                return await self._get_from_file(conversation_id, limit)
        except Exception as e:
            logger.error(f"❌ 获取聊天记录失败: {e}")
            return []

    async def _ensure_initialized(self):
        """懒初始化：必要时异步探查MongoDB，失败则使用文件存储"""
        if self.initialized:
            return
        if not self.enable_history:
            return

        async with self._init_lock:
            if self.initialized:
                return

            # 兜底先准备文件存储
            self._init_file_storage_if_needed()

            # 检查测试模式
            import os
            testing_mode = os.environ.get("TESTING_MODE", "false").lower() == "true"
            if testing_mode:
                self.initialized = True
                self.use_mongo = False
                return

            if self.mongodb_url and PYMONGO_AVAILABLE:
                try:
                    await asyncio.wait_for(self._try_init_mongo(), timeout=2.0)
                    self.initialized = True
                    self.use_mongo = True
                    logger.info("📝 懒初始化：MongoDB已连接")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ 懒初始化：MongoDB探查失败，使用文件存储: {e}")

            # 最终使用文件存储
            self.initialized = True
            self.use_mongo = False

    def _init_file_storage_if_needed(self):
        """确保文件存储准备就绪"""
        try:
            if not os.path.exists(self.file_path):
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
        except Exception as e:
            logger.warning(f"⚠️ 初始化文件存储失败（将在写入时重试）: {e}")

    async def _try_init_mongo(self):
        """在线程池中探查并初始化Mongo连接与集合（可能阻塞）"""

        def _blocking_connect():
            client = MongoClient(self.mongodb_url, serverSelectionTimeoutMS=2000)
            # 测试连接
            client.admin.command('ping')

            # 解析数据库名
            db_name = self.mongodb_url.split('/')[-1] or 'chat_history'
            db = client[db_name]
            collection = db.conversations

            # 创建索引（若失败不影响使用）
            try:
                collection.create_index("conversation_id")
                collection.create_index("timestamp")
            except Exception:
                pass

            return client, db, collection

        client, db, collection = await asyncio.get_event_loop().run_in_executor(None, _blocking_connect)
        # 设置到实例
        self.mongo_client = client
        self.db = db
        self.collection = collection

    async def _save_to_file(self, message: Dict):
        """保存到文件"""
        # 转换datetime为字符串
        message["timestamp"] = message["timestamp"].isoformat()

        def _write_file():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []

            data.append(message)

            # 保持文件大小合理，只保留最近的1000条记录
            if len(data) > 1000:
                data = data[-1000:]

            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        await asyncio.get_event_loop().run_in_executor(None, _write_file)

    async def _get_from_file(self, conversation_id: str, limit: int) -> List[Dict]:
        """从文件获取记录"""

        def _read_file():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 筛选对话ID并按时间排序
                conversation_messages = [
                    msg for msg in data
                    if msg.get("conversation_id") == conversation_id
                ]

                # 按时间戳排序并取最近的记录
                conversation_messages.sort(key=lambda x: x.get("timestamp", ""))
                return conversation_messages[-limit:] if limit else conversation_messages
            except (FileNotFoundError, json.JSONDecodeError):
                return []

        return await asyncio.get_event_loop().run_in_executor(None, _read_file)

    def close(self):
        """关闭连接"""
        if self.mongo_client:
            self.mongo_client.close()
