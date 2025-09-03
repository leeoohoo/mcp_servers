# Task Manager Server（流式版本）

任务管理器 MCP 服务器 - 基于 MCP Framework 构建的任务管理系统，支持流式输出和分布式存储

## 🚀 功能特性

### 核心功能
- **流式输出**: 所有工具都支持流式输出，提供实时处理反馈
- **批量创建任务**: 支持一次性创建多个任务，流式显示创建进度
- **任务执行管理**: 获取下一个可执行任务，自动更新任务状态
- **任务状态跟踪**: 支持 pending、in_progress、completed 三种状态
- **会话隔离**: 支持按会话ID管理任务
- **分布式存储**: 按 `conversation_id_request_id` 格式分别存储任务文件
- **数据持久化**: 任务数据自动保存到对应的JSON文件

### 任务字段
每个任务包含以下字段：
- `task_title`: 任务标题
- `target_file`: 目标文件
- `operation`: 操作类型
- `specific_operations`: 具体操作描述
- `related`: 相关信息
- `dependencies`: 依赖关系
- `conversation_id`: 会话ID
- `request_id`: 请求ID
- `status`: 任务状态 (pending/in_progress/completed)
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 📦 安装和运行

### 1. 安装依赖

```bash
cd task_manager_server
pip install -r task_manager_server_requirements.txt
```

### 2. 启动服务器

```bash
python task_manager_server.py --port 8090
```

服务器将在 `http://localhost:8090` 启动。

## 🛠️ 可用工具（流式版本）

### 1. create_tasks (流式)
创建任务（支持批量创建）- 流式输出创建进度

**参数:**
- `conversation_id` (必需): 会话ID
- `request_id` (必需): 请求ID  
- `tasks` (必需): 任务列表，每个任务包含以下字段：
  - `task_title`: 任务标题
  - `target_file`: 目标文件
  - `operation`: 操作类型
  - `specific_operations`: 具体操作
  - `related`: 相关信息
  - `dependencies`: 依赖关系

**流式输出示例:**
```
开始创建 3 个任务...
[1/3] 创建任务: 删除用户缓存文件 (ID: abc123)
[2/3] 创建任务: 备份控制器文件 (ID: def456)
[3/3] 创建任务: 清理邮件服务 (ID: ghi789)

✅ 成功创建 3 个任务并保存到文件: conv123_req456.json
📊 总结: 成功创建 3 个任务，失败 0 个
```

### 2. get_next_executable_task (流式)
获取下一个可执行任务 - 流式输出查找和任务详情

**参数:**
- `conversation_id` (可选): 会话ID，用于过滤特定会话的任务

**流式输出示例:**
```
🔍 正在查找下一个可执行任务...
📋 找到待执行任务: 删除用户缓存文件
▶️ 任务已标记为进行中
📄 任务详情:
  - ID: abc123
  - 标题: 删除用户缓存文件
  - 目标文件: /path/to/cache/file
  - 操作: Delete
  ...
```

### 3. complete_task (流式)
标记任务为已完成 - 流式输出处理过程

**参数:**
- `task_id` (必需): 任务ID

**流式输出示例:**
```
🔍 正在查找任务 abc123...
📋 找到任务: 删除用户缓存文件
✅ 任务 '删除用户缓存文件' 已标记为完成
💾 已保存到文件: conv123_req456.json
```

### 4. get_task_stats (流式)
获取任务统计信息 - 流式输出统计结果

**参数:**
- `conversation_id` (可选): 会话ID，用于过滤特定会话的任务

**流式输出示例:**
```
📊 正在统计任务信息...
🔍 统计范围: 会话 conv123
📈 会话 conv123 任务统计:
  📋 总计: 5 个
  ⏳ 待执行: 2 个
  🔄 进行中: 1 个
  ✅ 已完成: 2 个

📝 任务列表:
  1. ⏳ 备份控制器文件 (ID: def456)
  2. 🔄 删除用户缓存文件 (ID: abc123)
  ...
```

### 5. query_tasks (流式)
根据条件查询任务 - 流式输出查询过程和结果

**参数:**
- `conversation_id` (可选): 会话ID
- `status` (可选): 任务状态 (pending, in_progress, completed)
- `task_title` (可选): 任务标题关键词

**流式输出示例:**
```
🔍 正在查询任务...
📋 查询条件: 会话ID: conv123, 状态: pending
  🔸 按会话ID过滤后: 5 个任务
  🔸 按状态过滤后: 2 个任务

📊 找到 2 个匹配的任务

📝 匹配的任务列表:
  1. ⏳ 备份控制器文件
     📁 文件: /path/to/controller.java
     🔧 操作: Backup
     🆔 ID: def456
     📅 创建时间: 2024-01-01T10:00:00
  ...
```

## 📊 使用流程

### 典型工作流程

1. **创建任务**: 使用 `create_tasks` 批量创建任务
2. **执行任务**: 使用 `get_next_executable_task` 获取下一个任务
3. **完成任务**: 使用 `complete_task` 标记任务完成
4. **查看进度**: 使用 `get_task_stats` 查看整体进度

### 示例场景

```python
# 1. 创建一批开发任务
tasks = [
    {
        "task_title": "设计数据库表结构",
        "target_file": "database/schema.sql",
        "operation": "Create",
        "specific_operations": "设计用户、订单、产品表",
        "related": "数据库设计",
        "dependencies": "需求分析"
    },
    {
        "task_title": "实现用户API",
        "target_file": "api/user.py",
        "operation": "Create",
        "specific_operations": "CRUD操作接口",
        "related": "后端API",
        "dependencies": "数据库表结构"
    }
]

# 2. 循环执行任务
while True:
    next_task = get_next_executable_task(conversation_id="project_123")
    if not next_task["has_task"]:
        print("所有任务已完成！")
        break
    
    # 执行任务逻辑...
    print(f"正在执行: {next_task['task']['task_title']}")
    
    # 完成任务
    complete_task(next_task["task"]["id"])
```

## 💾 数据存储（分布式存储）

任务数据按 `conversation_id_request_id` 格式分别存储在 `task_data/` 目录下的独立 JSON 文件中：

### 存储结构
```
task_data/
├── conv123_req456.json
├── conv123_req789.json
├── conv456_req123.json
└── ...
```

### 文件格式
每个文件包含以下结构：

```json
{
  "conversation_id": "conv123",
  "request_id": "req456",
  "tasks": [
    {
      "id": "task_uuid",
      "task_title": "任务标题",
      "target_file": "目标文件路径",
      "operation": "操作类型",
      "specific_operations": "具体操作描述",
      "related": "相关信息",
      "dependencies": "依赖关系",
      "conversation_id": "conv123",
      "request_id": "req456",
      "status": "pending|in_progress|completed",
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T10:00:00"
    }
  ],
  "updated_at": "2024-01-01T10:00:00"
}
```

### 存储优势
- **会话隔离**: 每个会话的任务独立存储，便于管理
- **并发安全**: 不同会话的操作不会相互影响
- **数据恢复**: 可以单独恢复特定会话的任务数据
- **性能优化**: 只加载需要的任务数据，提高性能

## 🔧 配置选项

服务器支持以下启动参数：
- `--port`: 服务器端口 (默认: 8090)
- `--host`: 服务器主机 (默认: localhost)

## 📝 注意事项

1. **任务ID唯一性**: 每个任务都有唯一的UUID
2. **状态管理**: 任务状态自动管理，无需手动设置
3. **数据持久化**: 所有操作都会自动保存到文件
4. **会话隔离**: 支持多个会话同时管理不同的任务集合
5. **错误处理**: 完善的错误处理和验证机制

## 🚀 扩展功能

未来可以扩展的功能：
- 任务优先级管理
- 任务截止时间
- 任务分配给特定用户
- 任务进度百分比
- 任务评论和附件
- 任务模板功能