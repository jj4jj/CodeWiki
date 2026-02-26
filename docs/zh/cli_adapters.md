`cli_adapters` 模块的文档现已完整。以下是生成文件的摘要：

## 生成的文档文件

| 文件 | 描述 |
|------|-------------|
| `cli_adapters.md` | 包含架构概述、工作流程和集成点的核心文档 |
| `doc_generator.md` | `CLIDocumentationGenerator` 的详细文档，包含5阶段管道 |
| `translator.md` | `DocTranslator` 的详细文档，包含翻译级联说明 |
| `html_generator.md` | `HTMLGenerator` 的详细文档，包含GitHub Pages部署信息 |

## 文档亮点

**架构：**
- `cli_adapters` 模块桥接CLI命令与后端服务
- 三个主要组件：`CLIDocumentationGenerator`、`DocTranslator`、`HTMLGenerator`

**涵盖的主要功能：**
1. **CLIDocumentationGenerator** - 5阶段文档管道，支持进度跟踪
2. **DocTranslator** - 级联翻译（agent → 主模型 → 备用模型）
3. **HTMLGenerator** - 用于GitHub Pages的独立HTML查看器

**包含的图表：**
- 架构概述（图）
- 文档生成序列
- 翻译级联序列

文档参考了模块树中的其他模块（cli_config、cli_models、cli_utils、be_agent_orchestrator、dependency_analyzer）以提供跨模块上下文。
