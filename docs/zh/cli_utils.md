`cli_utils` 模块的文档已生成。以下是创建的文件摘要：

## 生成的文档文件

| 文件 | 描述 |
|------|-------------|
| [cli_utils.md](cli_utils.md) | 主文档，包含架构概述、组件描述和集成点 |
| [logging.md](logging.md) | `CLILogger` 类的详细文档，包括所有方法和使用模式 |
| [progress.md](progress.md) | `ProgressTracker` 和 `ModuleProgressBar` 类的详细文档 |

## 文档亮点

**架构：**
- cli_utils 模块为 CLI 提供日志记录和进度跟踪工具
- 三个主要组件：`CLILogger`、`ProgressTracker` 和 `ModuleProgressBar`

**主要功能：**
1. **CLILogger** - 带 verbose 模式支持、时间戳和不同严重级别的彩色控制台输出
2. **ProgressTracker** - 5 阶段加权进度跟踪，支持 ETA 估算
3. **ModuleProgressBar** - 模块化生成的视觉进度条

**可视化图表：**
- 显示组件关系的架构图
- 5 个文档生成阶段（带权重）的阶段工作流状态图
- 展示阶段加权的进度计算图

**交叉引用：**
- 所有文件均相互正确交叉引用
- 相关模块链接：cli_adapters、cli_config 和 be_agent_orchestrator
