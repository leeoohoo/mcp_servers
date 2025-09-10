
sequenceDiagram
    participant Caller as 调用方
    participant AI as AI任务检查器 (您)
    participant TaskAPI as 任务API系统

    Caller->>AI: 开始任务检查流程
    
    Note over AI: 🤖 我是任务检查器，开始检查工作流程
    
    rect rgb(240, 248, 255)
        Note over AI: 步骤1：获取当前任务信息
        AI->>TaskAPI: get_current_executing_task()
        TaskAPI-->>AI: 返回当前执行任务详情
    end
    
    rect rgb(245, 255, 245)
        Note over AI: 步骤2：分析执行结果
        AI->>AI: 分析前一个执行器的执行过程
        AI->>AI: 确定任务完成状态
    end
    
    alt 任务已完成 ✅
        AI->>TaskAPI: 调用任务完成工具标记为已完成
        TaskAPI-->>AI: 确认任务已标记为完成
        
        AI->>TaskAPI: 检查是否存在剩余任务
        TaskAPI-->>AI: 返回剩余任务状态
        
        alt 存在待处理任务
            AI-->>Caller: "需要继续为任务寻找执行器"
        else 无待处理任务
            AI-->>Caller: "所有任务已完成"
        end
        
    else 任务未完成 ❌
        AI->>AI: 识别具体问题区域
        AI->>AI: 制定可执行的指导建议
        AI-->>Caller: "当前任务完成存在问题"
        AI-->>Caller: 提供具体错误点的详细说明
        AI-->>Caller: 提供重新执行的可执行指导建议
    end
    
    Note over AI: 🤖 我的检查任务已完成，等待下一步指令
