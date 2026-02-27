`be_agent_orchestrator` 模块的文档现已生成完成。以下是生成文件的摘要：

## 生成的文档文件

| 文件 | 描述 |
|------|-------------|
| `be_agent_orchestrator.md` | 主文档，包含架构概览、工作流程和集成点 |
| `documentation_generator.md` | `DocumentationGenerator` 的详细文档，包括管道阶段和并行处理 |
| `agent_orchestrator.md` | `AgentOrchestrator` 的详细文档，包含 pydantic-ai 代理创建和工具配置 |
| `cmd_agent_orchestrator.md` | `CmdAgentOrchestrator` 的详细文档，包含 CLI 子进程协议以及与 API 模式的对比 |

## 文档亮点

**架构：**
- be_agent_orchestrator 模块是 AI 驱动文档生成的核心编排层
- 三个主要组件：`DocumentationGenerator`、`AgentOrchestrator`、`CmdAgentOrchestrator`

**主要功能涵盖：**
1. **DocumentationGenerator** - 主管道协调器，包含依赖图构建、模块聚类、并行叶子处理和父级概览生成
2. **AgentOrchestrator** - 创建基于复杂度的工具配置的 pydantic-ai 代理（叶子模块 vs 复杂模块）
3. **CmdAgentOrchestrator** - 基于 CLI 的即插即用替代方案，使用子进程通信绕过 API 上下文限制

**包含的图表：**
- 架构概览（图）
- 文档生成序列
- 处理顺序流程图（并行叶子 → 顺序父级 → 概览）

文档参考了模块树中的其他模块（dependency_analyzer、be_agent_tools、cli_models、cli_utils）以提供跨模块上下文。
