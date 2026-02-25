# CodeWiki - 全局项目上下文与开发者指南

CodeWiki 是一个用于评估和生成大型代码库全景文档的 AI 驱动框架。本项目通过**多语言代码解析**、**架构感知的模块划分**以及**多智能体（Multi-Agent）递归生成**，为代码库构建结构化的文本及可视化文档（如：Mermaid 架构图、数据流图等）。

本文档主要面向新接手参与此项目的 **AI Agent** 和 **人类开发者**，提供快速理解系统核心、项目架构、扩展方式与开发规范的全局上下文信息。

## 1. 核心技术栈与架构设计

- **主要语言**: Python 3.12+ 
- **核心依赖**:
  - `tree-sitter`: 提供7种主流语言的 AST 解析。
  - `pydantic` & `pydantic-ai`: 用于数据模型验证和 Agent 构建。
  - `litellm` & `openai`: 统一的 LLM 接口支持（Claude/GPT 等多模型调度）。
  - `click`: 强大而灵活的命令行界面构建。
  - `FastAPI`: 提供文档结果的展示后台与 Web 接口服务。
- **系统数据流架构**:
  `代码库树分析` -> `抽象语法树 AST 解析` -> `依赖关系图提取` -> `层次化聚类算法分解` -> `构建模块树` -> `递归 Agent 智能生成文档` -> `合成多维度全局文档 (Markdown + 交互视图)`

## 2. 项目核心模块与目录结构

```text
codewiki/
├── codewiki/                 # 核心代码包
│   ├── cli/                  # 命令行交互工具（CLI）
│   │   ├── commands/         # 子命令定义（config, generate）
│   │   ├── models/           # 配置相关的数据模型层
│   │   └── adapters/         # 外部服务集成适配
│   ├── src/                  # 系统核心业务逻辑
│   │   ├── be/               # 后端：依赖分析引擎与 Agent 编排系统
│   │   │   ├── dependency_analyzer/ # 多语言源代码 AST 解析器（BaseAnalyzer 及各语言子类）
│   │   │   ├── cluster_modules.py   # 基于功能与拓扑级联关系的模块聚类引擎
│   │   │   ├── agent_orchestrator.py# 中心化调度 Agent 工作流的编排核心
│   │   │   ├── agent_tools/         # 供 LLM Agent 调用的工具函数集合（如解析文件、读取节点等）
│   │   │   └── prompt_template.py   # LLM Prompt 系统提示词集中管理
│   │   └── fe/               # 前端：结果展示和 Web 服务后台
│   │       ├── web_app.py           # FastAPI 服务器核心逻辑
│   │       └── visualise_docs.py    # 文档数据可视化层
│   ├── templates/            # Web 端渲染交互组件的界面模板
│   └── run_web_app.py        # 独立启动 Web 服务的入口点
├── docs/                     # 生成完毕的文档目录示例及导出内容
├── docker/                   # 容器化部署方案配置
├── pyproject.toml            # Python 核心依赖及元数据定义文件
├── pytest.ini                # Pytest 测试框架配置参数
└── DEVELOPMENT.md            # 英文版的标准开发者指南
```

## 3. 关键设计模式与抽象机制

为了应对多语言代码的解析及其生成逻辑中的不确定性因素，项目抽象出以下几个关键性架构设计：

1. **策略模式与多态解析（Strategy Pattern）**:
   多语言的 AST 解析能力由 `src/be/dependency_analyzer/analyzers/base.py` 中定义的抽象基类 `BaseAnalyzer` 提供。每种受支持的编程语言都会通过继承该类来实现自身固有的语言树逻辑。相关注册点位于 `ast_parser.py` 的解析字典内，达成语言扩充与主流程的解耦化。
2. **层次化归并映射设计（Hierarchical Clustering）**:
   利用 `cluster_modules.py` 将大型代码库拆解成 LLM 当前 Context Window 易于理解的小型叶子节点（Leaf modules）。该分簇系统在兼顾 Token 管控上限的同时，能保持极强的项目上下游逻辑连贯性和层级结构。
3. **递归多智能体机制（Recursive Multi-Agent System）**:
   在核心编排引擎 `agent_orchestrator.py` 里，程序会动态评估各个解析模块的内部复杂度。当某功能节点体量异常时，主 Agent 程序会递归实例化和委派（Delegation） 子 Agents 进行处理，处理完毕后通过聚类整合返回结果。

## 4. 如何进行二次开发与扩展 (Extension Guide)

### 场景 A：添加新语言解析支持
系统天然内置良好的扩展闭环，如需注入新语言：
1. 前往 `codewiki/src/be/dependency_analyzer/analyzers` 新建新语言分析器（如 `php_analyzer.py`）。
2. 在该类体内继承 `BaseAnalyzer` 并实现两大核心方法：
   - `extract_dependencies(self, ast_node)`
   - `extract_components(self, ast_node)`
3. 跳转至 `src/be/dependency_analyzer/ast_parser.py` 中的 `LANGUAGE_ANALYZERS` 字典里，以键值对形式挂载新建的解析类。
4. （可选）在 `pyproject.toml` 的项目依赖表中加入新语言相应的 `tree-sitter-[lang]` 组件并更新环境。

### 场景 B：增加自定义的 CLI Agent 控制指令
1. 于 `cli/models/config.py` 中的 `AgentInstructions` `dataclass` 类型下添加对应功能所需的新变量字段。
2. 更新该配置结构的串行化生命周期方法（涉及 `to_dict` 与 `from_dict` 等）。
3. 前往 `cli/commands/generate.py` 使用 `@click.option` 将新功能暴露至终端环境。
4. 补齐消费侧逻辑：确保后方业务逻辑，或是系统提示词中正确响应新增加字段。

## 5. 项目开发规范 (Development Guidelines)

- **Python 代码风格风格**: 严格遵循 PEP-8；推荐集成并使用 `black` 自动化格式（`line-length = 100`）以及 `ruff` 代码 Linter。
- **类型提示 (Type Hints)**: 所有函数参数及返回值均推荐启用显式类型注解，通过 `mypy` 规避运行时动态错误。
- **文档维护**: 暴露在外的核心 Class 或 Utility 必须撰写包含输入输出详尽说明的 docstrings。
- **测试提交流程**: 集成了完善的单元测试套件，新分支提交必须确保所有 `pytest` 用例运行完毕且覆盖率未滑坡。

## 6. 构建与安装说明

### 环境准备工作
- 需准备 **Python 3.12** 及以上版本。
- 需具备 **Node.js** 的执行环境（>= 14.0，主要用于确保输出 Mermaid 解析图表的正确渲染核实）。

### 从源码安装调试
```bash
# 1. 下载源码并构建纯净的沙盒虚拟环境
git clone https://github.com/FSoft-AI4Code/CodeWiki.git
cd CodeWiki
python3.12 -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# 2. 安装库至 Editable（开发） 模式及拉取依赖
pip install -e .
pip install -r requirements.txt
```

## 7. 常用运行与测试使用方法

### 大模型及系统配置初始化
使用生成前需进行必要的 AI Model 及基准令牌（Token）的路由配置，目前兼容支持全部类 OpenAI 格式。
```bash
codewiki config set \
  --api-key YOUR_API_KEY \
  --base-url {LLM_PROVIDER_HOST} \
  --main-model claude-sonnet-4 \
  --cluster-model claude-sonnet-4 \
  --fallback-model glm-4p5
```

### 业务级文档一键分析生成
```bash
# 执行整个工程代码分析并创建含有交互页面的文档分支
codewiki generate --github-pages --create-branch
```

### 测试及日志追踪相关
如面临语法树解析报错、API 瓶颈挂起等行为，通过下方方式定位：
```bash
# 获取极其详细的 Debugging 分析流信息
codewiki generate --verbose
# （或）在终端定义变量全局生效
export CODEWIKI_LOG_LEVEL=DEBUG

# 验证代码稳定性，运行测试大盘
pytest -v --cov=codewiki --cov-report=term-missing
```

---

> 💡 **给新接手 AI Agent 的直接导览建议**: 
> 亲爱的 Agent 协作者，在探索此代码仓库时，强推荐您第一时间聚焦于 `src/be/agent_orchestrator.py` 的多 Agent 机制执行路线。如果你受到的指令涉及了上下文扩展、或是重组底层 Prompt 提示体系，请您深入解刨 `prompt_template.py` 内部封装的结构、以及它是如何协同 `ast_parser.py` 进行跨模块传递分工的。若要处理渲染方面的反馈，则直接调看前端业务域 `src/fe/` 以及 `templates/` 下相关的视图服务逻辑。
