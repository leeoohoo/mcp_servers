# MCP Servers Project

一个基于 Model Context Protocol (MCP) 的多功能服务器集合项目，提供文件读取、终端管理和AI专家服务等功能。
使用框架mcp-framework: https://github.com/QuantGeekDev/mcp-framework

## 项目概述

本项目包含多个独立的MCP服务器，每个服务器都专注于特定的功能领域：

- **文件读取服务器** - 提供文件内容读取、搜索和项目结构分析
- **终端管理服务器** - 提供终端创建、命令执行和进程管理
- **AI专家服务器** - 提供AI对话和工具调用服务

## 项目结构

```
mcp_servers/
├── requirements.txt              # 项目依赖包
├── README.md                     # 项目说明文档
├── file_reader_server.py         # 文件读取服务器主文件
├── weather_server.py             # 天气服务器示例
├── test_server.py                # 测试服务器
├── expert_stream_server/         # AI专家服务器模块
│   ├── expert_MCP_server_annotated.py
│   ├── expert_service.py
│   ├── ai_client.py
│   ├── ai_request_handler.py
│   ├── chat_history_manager.py
│   └── mcp_tool_execute.py
├── terminal_manager_server/      # 终端管理服务器模块
│   ├── terminal_mcp_server.py
│   ├── terminal_stream_server.py
│   ├── models/                   # 数据模型
│   ├── services/                 # 业务服务
│   └── utils/                    # 工具函数
├── config/                       # 配置文件
├── data/                         # 数据文件
├── dist/                         # 构建产物
└── build/                        # 构建临时文件
```

## 功能特性

### 🗂️ 文件读取服务器

- **文件内容读取** - 支持按行范围读取文件内容
- **内容搜索** - 在项目中搜索指定文本内容
- **批量文件读取** - 同时读取多个文件的内容
- **项目结构分析** - 生成项目目录结构树
- **流式输出** - 支持大文件的流式处理

### 🖥️ 终端管理服务器

- **终端创建与管理** - 创建、删除和管理多个终端实例
- **命令执行** - 在指定终端中执行命令
- **实时输出** - 获取命令执行的实时输出
- **进程监控** - 监控和管理运行中的进程
- **命令历史** - 记录和查询命令执行历史
- **状态管理** - 跟踪终端和命令的状态

### 🤖 AI专家服务器

- **AI对话** - 与OpenAI模型进行智能对话
- **工具调用** - 支持MCP工具的动态调用
- **聊天历史** - 管理和持久化对话历史
- **流式响应** - 支持流式AI响应输出
- **多模型支持** - 支持不同的AI模型配置

## 安装和使用

### 环境要求

- Python 3.8+
- 支持的操作系统：macOS, Linux, Windows

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd mcp_servers

# 安装依赖包
pip install -r requirements.txt
```

### 运行服务器

#### 文件读取服务器

```bash
python file_reader_server.py
```

#### 终端管理服务器

```bash
cd terminal_manager_server
python terminal_stream_server.py
```

#### AI专家服务器

```bash
cd expert_stream_server
python expert_stream_server.py
```

### 配置说明

每个服务器都支持通过配置文件进行自定义设置：

- 服务器端口和地址
- 日志级别和输出路径
- 功能特性开关
- 外部服务集成（如OpenAI API）

配置文件位于 `config/` 目录下。

## 技术架构

### 核心框架

项目基于自定义的 `mcp_framework` 框架构建，提供：

- **EnhancedMCPServer** - 增强的MCP服务器基类
- **装饰器系统** - 简化工具定义和参数验证
- **流式处理** - 支持大数据量的流式输出
- **配置管理** - 统一的配置管理系统
- **日志系统** - 完整的日志记录和管理

### 主要依赖

- `aiohttp` - 异步HTTP客户端
- `openai` - OpenAI API客户端
- `pymongo` - MongoDB数据库驱动
- `psutil` - 系统进程监控
- `pydantic` - 数据验证和序列化
- `typing-extensions` - 类型注解扩展

## 开发指南

### 添加新的工具

1. 在相应的服务器类中定义新的工具方法
2. 使用装饰器系统定义参数和描述
3. 实现工具的具体逻辑
4. 更新配置和文档

### 构建和部署

项目支持使用 PyInstaller 构建独立的可执行文件：

```bash
# 构建文件读取服务器
pyinstaller build/spec_file_reader_server/file-reader-server.spec

# 构建终端管理服务器
pyinstaller terminal_manager_server/build/spec_terminal_stream_server/terminal-stream-server.spec

# 构建AI专家服务器
pyinstaller expert_stream_server/build/spec_expert_stream_server/expert-stream-server.spec
```

构建产物将生成在 `dist/` 目录下。

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至项目维护者

---

*本项目是一个学习和实验性质的MCP服务器实现，旨在探索和展示MCP协议的各种应用场景。*