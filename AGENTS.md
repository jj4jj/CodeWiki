# AGENTS.md

本文件是为 AI Agent 与人类开发者协作维护 `CodeWiki/CodeDoc` 项目而写的工程指南。
优先级: 代码实现 > 本文件 > README/DEVELOPMENT 文档。

## 1. 项目目标与范围

CodeWiki 是一个“代码仓库 -> 结构化技术文档”的生成系统，核心能力包括:

1. 多语言源码分析与依赖图构建（AST + call graph）。
2. 基于 LLM 的模块聚类与分层文档生成。
3. CLI 生成流程（`codewiki generate`）与可选 CLI Agent 子进程模式（`--with-agent-cmd`）。
4. Web 服务（FastAPI）任务队列、缓存、文档浏览与管理接口。
5. 可选文档翻译（`--output-lang`）与 HTML 浏览页（`--github-pages` / `--index-page`）。

非目标:

1. 该仓库当前不包含稳定的单元测试套件。
2. 当前 lint 基线存在大量历史问题，不应把“全仓 lint 清零”作为默认改动目标。

## 2. 代码结构（以当前仓库为准）

### 2.1 顶层目录

1. `codewiki/`: 主 Python 包。
2. `docs/`: 文档产物/示例文档。
3. `docker/`: Dockerfile、compose 与容器运行说明。
4. `output/`: 运行时产物（缓存、临时克隆、生成文档）。
5. `pyproject.toml`: 打包、依赖、工具配置（black/mypy/ruff/pytest）。
6. `README.md`, `DEVELOPMENT.md`: 说明文档（部分内容与当前实现可能有偏差）。

### 2.2 包内核心模块

1. `codewiki/cli/`
2. `codewiki/cli/main.py`: CLI 根命令注册（`config`, `generate`）。
3. `codewiki/cli/commands/config.py`: 配置管理命令。
4. `codewiki/cli/commands/generate.py`: 文档生成命令入口。
5. `codewiki/cli/adapters/doc_generator.py`: CLI 到后端编排适配层。
6. `codewiki/cli/adapters/translator.py`: 翻译后处理。
7. `codewiki/src/be/`
8. `codewiki/src/be/documentation_generator.py`: 后端主编排（依赖分析、聚类、文档生成、overview）。
9. `codewiki/src/be/agent_orchestrator.py`: pydantic-ai 模式模块生成。
10. `codewiki/src/be/cmd_agent_orchestrator.py`: CLI Agent 子进程模式模块生成。
11. `codewiki/src/be/dependency_analyzer/`: 仓库结构分析、call graph、多语言 analyzer。
12. `codewiki/src/fe/`
13. `codewiki/src/fe/web_app.py`: FastAPI 应用入口。
14. `codewiki/src/fe/background_worker.py`: 队列执行器、克隆、任务状态、缓存。
15. `codewiki/src/fe/routes.py`: Web/API 路由与文档浏览逻辑。
16. `codewiki/src/fe/github_processor.py`: 仓库 URL 解析与 clone 工具。
17. `codewiki/templates/github_pages/`: 静态 HTML 模板。

## 3. 关键执行链路（必须理解）

### 3.1 CLI 生成链路

1. `codewiki generate`
2. 读取配置（env/config/keyring 优先级在 `ConfigManager` 中实现）。
3. 仓库校验（语言扫描、git 状态、输出目录可写）。
4. `DependencyGraphBuilder` 构建组件与叶子节点。
5. `cluster_modules` 进行层次模块聚类（可能走 API 或 agent_cmd）。
6. `DocumentationGenerator.generate_module_documentation`:
7. 并行叶模块。
8. 顺序父模块。
9. 最后生成 `overview.md`。
10. 可选 HTML 与翻译后处理。

### 3.2 Web 任务链路

1. FastAPI 接收任务（`/`, `/admin`, `/api/tasks`）。
2. `BackgroundWorker` 入队并串行处理。
3. clone 仓库到 `output/temp/<job_id>`。
4. 调用 `DocumentationGenerator.run()`。
5. 写缓存索引、任务状态、日志文件。
6. 提供 `/docs/{job_id}` 与 `/static-docs/...` 浏览。

## 4. 需求说明（改动时要守住的产品行为）

### 4.1 CLI 行为约束

1. `config set/show/validate/agent` 必须保持可用。
2. `generate` 支持以下关键参数:
3. `--output/-o`
4. `--github-pages`
5. `--index-page`
6. `--no-cache`
7. `--include/--exclude/--focus/--doc-type/--instructions`
8. `--max-tokens/--max-token-per-module/--max-token-per-leaf-module/--max-depth`
9. `--output-lang`
10. `--with-agent-cmd`
11. `--concurrency/-j`
12. 已有“断点续跑”行为依赖于输出目录中 `.md` 是否存在，避免破坏此逻辑。

### 4.2 输出产物契约

标准生成目录至少包含:

1. `overview.md`
2. `module_tree.json`
3. `first_module_tree.json`
4. `metadata.json`
5. 各模块 `*.md`

翻译目录契约:

1. 输出在 `<output-dir>/<lang>/`。
2. 非 markdown 关键文件（如 JSON）需复制到翻译目录。

### 4.3 Cmd Agent 模式协议（高优先级）

当使用 `--with-agent-cmd`:

1. 叶子/普通模块: agent stdout 必须是“纯 markdown 内容”，不能带额外解释。
2. 父模块/overview: 期望 `<OVERVIEW>...</OVERVIEW>` 包裹（代码有兜底提取，但不要依赖）。
3. 聚类: 期望 `<GROUPED_COMPONENTS>...</GROUPED_COMPONENTS>` 包裹 JSON 字典。

## 5. 环境与构建

### 5.1 本地开发环境

1. Python >= 3.12（`pyproject.toml` 要求）。
2. Node.js >= 14（Mermaid 校验依赖链需要）。
3. git。

推荐命令:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

可选打包构建:

```bash
python -m pip install build
python -m build
```

### 5.2 Docker

```bash
docker-compose -f docker/docker-compose.yml up -d --build
```

Web 默认端口 `8000`，容器入口为:

```bash
python codewiki/run_web_app.py --host 0.0.0.0 --port 8000
```

## 6. 运行与验证

### 6.1 最小烟雾测试（当前可执行）

```bash
./.venv/bin/codewiki --help
./.venv/bin/codewiki config --help
./.venv/bin/python -m compileall -q codewiki
```

### 6.2 配置校验

```bash
codewiki config validate --quick
```

需要连通性时去掉 `--quick`。

### 6.3 pytest 现状（重要）

当前仓库没有 `tests/` 目录；`pyproject.toml` 中 `pytest` 配置包含 `testpaths = ["tests"]` 与覆盖率参数。

已知问题:

1. 直接运行 `pytest` 会在 `tests/` 缺失时递归扫描整个仓库。
2. 会误收集 `output/temp/...` 下外部仓库测试，导致大量 collection error。
3. `pytest-cov` 在 0 tests 时通常以非 0 退出。

因此当前建议:

1. 不把“根目录直接 `pytest` 通过”作为默认验收标准。
2. 新增测试时先创建 `tests/`，再用 `pytest tests -q`。
3. 若仅做局部改动，优先执行“目标模块级烟雾验证 + compileall”。

## 7. 代码规范与提交规范

### 7.1 风格与工具

1. 行宽 100（black/ruff 配置一致）。
2. 目标 Python 版本 `py312`。
3. `mypy` 为宽松模式（未强制完全类型化）。

### 7.2 实操建议

1. 改动时优先保持兼容，不要重构无关文件。
2. 优先做“最小充分改动”，避免扩大影响面。
3. 对新增参数，需同步 CLI、配置模型、后端消费层。
4. 不要破坏已有 JSON/Markdown 产物格式。
5. 涉及并发（`concurrency`）时，确认串行路径仍可工作。

### 7.3 现有技术债说明

`ruff check codewiki` 当前存在大量历史问题（未使用变量、E402、E722 等）。
除非任务明确要求“全量治理 lint”，否则只要求:

1. 新增代码不引入明显同类问题。
2. 修改文件尽量不扩大已有问题数量。

## 8. 常见改动任务操作手册

### 8.1 新增 CLI 参数

1. 在 `codewiki/cli/commands/generate.py` 或 `config.py` 加 option。
2. 在 `codewiki/cli/models/config.py` 的 `AgentInstructions`/`Configuration` 扩展字段。
3. 在 `codewiki/cli/config_manager.py` 补充加载/保存/覆盖逻辑。
4. 在 `codewiki/src/config.py` 和消费方透传。
5. 更新 README/本文件相关命令说明。

### 8.2 新增语言分析支持

1. 在 `codewiki/src/be/dependency_analyzer/analyzers/` 新增 analyzer。
2. 在 `call_graph_analyzer.py` 增加语言路由。
3. 在 `patterns.py` 与语言扩展映射中登记后缀。
4. 检查 CLI `detect_supported_languages` 是否需要同步（当前与后端能力存在轻微不一致风险）。

### 8.3 修改 Web API 参数

1. 更新 `web_app.py` 路由函数签名。
2. 更新 `routes.py` 的 `create_task_api/admin_post` 解析逻辑。
3. 更新 `models.py` 的 `GenerationOptions`。
4. 更新 `background_worker.py` 的参数应用逻辑。

## 9. 变更验收清单（DoD）

提交前至少确认:

1. 目标功能路径可运行（CLI 或 Web）。
2. `python -m compileall -q codewiki` 通过。
3. 受影响命令 `--help`/参数解析无回归。
4. 输出目录关键文件契约未破坏（`overview.md`, `module_tree.json`, `metadata.json`）。
5. 若涉及 agent_cmd，输出协议符合约定（见 4.3）。
6. 文档与参数说明同步更新。

---

如果本文件与当前实现冲突，以代码为准，并在同一提交中修正本文件。
