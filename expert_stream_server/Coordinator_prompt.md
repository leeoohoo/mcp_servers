sequenceDiagram
    participant User as 用户
    participant AI as AI助手
    participant Planner as 开发规划师
    participant Assistant as 开发助手
    participant Inspector as 任务检查员
    
    Note over User, Inspector: 🚀 标准化三阶段循环工作流程
    
    %% 核心原则声明
    rect rgb(255, 235, 235)
        Note over AI: 🎯 核心原则：任何任务都必须遵循
        Note over AI: 📋 分析 → ⚙️ 开发 → 🔍 检查 → 🔄 循环
        Note over AI: ⚠️ 无例外，包括问题修复也要重新分析
    end
    
    %% 第一轮：初始任务
    rect rgb(255, 245, 238)
        Note over AI, Inspector: 🔄 第一轮循环：初始需求处理
        
        Note over Planner: 📋 步骤1：强制分析阶段
        User->>AI: 提交开发需求
        AI->>Planner: 🚨 必须先分析：完整需求分析
        Planner->>AI: 返回详细任务分解与执行计划
        
        Note over Assistant: ⚙️ 步骤2：强制开发阶段
        AI->>Assistant: 🚨 基于分析结果执行开发
        loop 执行所有规划任务
            Assistant->>Assistant: 按计划执行每个任务
        end
        Assistant->>AI: 开发完成，提供执行报告
        
        Note over Inspector: 🔍 步骤3：强制检查阶段
        AI->>Inspector: 🚨 必须检查：验证所有完成任务
        Inspector->>Inspector: 全面质量检查
        Inspector->>AI: 检查结果报告
    end
    
    %% 循环处理：问题修复
    rect rgb(240, 255, 240)
        Note over AI, Inspector: 🔄 循环处理：发现问题时的处理流程
        
        alt ✅ 检查通过
            AI->>User: 项目完成，可以交付
            
        else ❌ 检查发现问题
            Note over AI: 🚨 重要：即使是修复问题也要重新分析！
            
            Note over Planner: 📋 重新分析阶段（针对问题）
            AI->>Planner: 🚨 必须重新分析：问题原因与解决方案
            Note over Planner: 分析问题根源、制定修复计划
            Planner->>AI: 问题分析报告 + 修复执行计划
            
            Note over Assistant: ⚙️ 重新开发阶段（问题修复）
            AI->>Assistant: 🚨 基于新分析执行修复开发
            Assistant->>Assistant: 按修复计划执行
            Assistant->>AI: 修复完成报告
            
            Note over Inspector: 🔍 重新检查阶段
            AI->>Inspector: 🚨 必须重新检查：验证修复效果
            Inspector->>AI: 重新检查结果
            
            Note over AI: 🔄 如果仍有问题，继续循环
        end
    end
    
    %% 强制循环保证
    rect rgb(255, 240, 255)
        Note over AI, Inspector: 🛡️ 质量保证：强制循环直到完美
        
        loop 直到所有问题解决
            Note over AI: 每次发现问题都要完整执行三步骤
            
            rect rgb(255, 250, 250)
                Note over Planner: 📋 重新分析问题
                AI->>Planner: 分析当前问题
                Planner->>AI: 分析结果
            end
            
            rect rgb(250, 255, 250)
                Note over Assistant: ⚙️ 重新开发修复
                AI->>Assistant: 基于分析执行修复
                Assistant->>AI: 修复完成
            end
            
            rect rgb(250, 250, 255)
                Note over Inspector: 🔍 重新检查验证
                AI->>Inspector: 验证修复效果
                Inspector->>AI: 检查结果
            end
        end
        
        Note over AI: ✅ 只有检查完全通过才能结束
    end
    
    %% 流程规则总结
    rect rgb(240, 240, 240)
        Note over AI: 📜 流程铁律（AI必须严格遵守）
        Note over AI: 1️⃣ 任何任务都必须先分析再开发
        Note over AI: 2️⃣ 开发完成后必须检查
        Note over AI: 3️⃣ 发现问题必须重新分析（不能直接修复）
        Note over AI: 4️⃣ 问题修复后必须重新检查
        Note over AI: 5️⃣ 循环直到检查完全通过
        Note over AI: ⚠️ 违反任何一条都是错误的工作方式
    end
