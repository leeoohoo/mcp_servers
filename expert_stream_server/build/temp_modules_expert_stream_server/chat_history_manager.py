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

        # 确保数据目录存在
        os.makedirs("data", exist_ok=True)

    async def initialize(self):
        """初始化存储"""
        if not self.enable_history:
            logger.info("📝 聊天记录功能已禁用")
            return

        if self.mongodb_url and PYMONGO_AVAILABLE:
            try:
                self.mongo_client = MongoClient(self.mongodb_url, serverSelectionTimeoutMS=5000)
                # 测试连接
                self.mongo_client.admin.command('ping')

                # 解析数据库名
                db_name = self.mongodb_url.split('/')[-1] or 'chat_history'
                self.db = self.mongo_client[db_name]
                self.collection = self.db.conversations

                # 创建索引
                self.collection.create_index("conversation_id")
                self.collection.create_index("timestamp")

                logger.info(f"📝 MongoDB聊天记录存储已连接: {db_name}")
                return
            except Exception as e:
                logger.warning(f"⚠️ MongoDB连接失败，将使用文件存储: {e}")
                self.mongo_client = None

        # 使用文件存储
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
        logger.info(f"📝 文件聊天记录存储已初始化: {self.file_path}")

    async def save_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None):
        """保存消息"""
        if not self.enable_history:
            return

        message = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }

        try:
            if self.collection:
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

        try:
            if self.collection:
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
