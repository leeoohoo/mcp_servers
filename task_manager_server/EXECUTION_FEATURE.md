# 任务执行过程功能说明

## 概述

新增了任务执行过程记录功能，允许development角色在完成任务后保存执行过程，inspector角色可以查看这些执行过程。

## 新增功能

### 1. 数据模型

新增 `TaskExecution` 数据类：
- `task_id`: 任务ID
- `execution_process`: 执行过程描述
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. 存储结构

- 任务数据：存储在 `{data_dir}/{conversation_id}_{request_id}.json`
- 执行过程：存储在 `{data_dir}/executions/{task_id}_execution.json`
- 每个任务ID对应一个独立的执行过程文件

### 3. 新增工具

#### save_task_execution (development角色)

**描述**: 保存任务执行过程

**参数**:
- `task_id` (必需): 要保存执行过程的任务ID
- `execution_process` (必需): 详细的执行过程描述

**功能**:
- 验证任务是否存在
- 保存执行过程到独立文件
- 提供保存确认和统计信息

**使用场景**: development角色完成任务后记录执行过程

### 4. 增强功能

#### get_current_executing_task (inspector角色)

**新增功能**:
- 在显示当前执行任务信息时，自动查询并显示已保存的执行过程
- 如果存在执行过程记录，会显示：
  - 执行过程保存时间
  - 执行过程更新时间
  - 完整的执行过程内容
- 如果没有执行过程记录，会提示"该任务暂无执行过程记录"

## 使用流程

1. **创建任务** (planner角色)
   ```
   使用 create_tasks 工具创建任务
   ```

2. **获取任务** (development角色)
   ```
   使用 get_next_executable_task 工具获取可执行任务
   ```

3. **执行任务** (development角色)
   ```
   执行具体的开发工作
   ```

4. **记录执行过程** (development角色)
   ```
   使用 save_task_execution 工具保存执行过程
   参数：task_id, execution_process
   ```

5. **完成任务** (development角色)
   ```
   使用 complete_task 工具标记任务完成
   ```

6. **检查执行过程** (inspector角色)
   ```
   使用 get_current_executing_task 工具查看任务和执行过程
   ```

## 文件结构示例

```
task_data/
├── conv_123_req_456.json          # 任务数据文件
└── executions/                     # 执行过程目录
    ├── task_id_1_execution.json    # 任务1的执行过程
    ├── task_id_2_execution.json    # 任务2的执行过程
    └── task_id_3_execution.json    # 任务3的执行过程
```

## 注意事项

1. 执行过程文件按任务ID独立存储，便于管理和查询
2. 只有存在的任务才能保存执行过程
3. 执行过程可以多次保存，会覆盖之前的记录
4. inspector角色查看任务时会自动显示执行过程（如果存在）
5. 数据目录更新时会自动创建executions子目录