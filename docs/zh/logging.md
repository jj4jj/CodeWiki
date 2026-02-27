# 日志子模块

日志子模块提供 `CLILogger` 类，用于不同严重级别的彩色控制台输出。

## 概述

日志子模块（`logging.py`）提供用户友好的彩色控制台输出，支持详细和正常两种输出模式，可对 CLI 操作期间显示的信息量进行细粒度控制。

## CLILogger 类

### 用途

`CLILogger` 为 CodeWiki CLI 提供标准化的日志接口，具有以下功能：
- 不同消息类型的彩色输出
- 可选的详细模式用于调试
- 操作计时的时间戳跟踪

### 类定义

```python
class CLILogger:
    """Logger for CLI with support for verbose and normal modes."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = datetime.now()
```

### 方法

#### `debug(message: str)`

仅在详细模式启用时记录调试消息。

```python
logger.debug("Analyzing file structure...")
# 仅在 verbose=True 时显示
```

#### `info(message: str)`

以默认终端颜色记录信息消息。

```python
logger.info("Processing module: core/utils")
# 输出: Processing module: core/utils
```

#### `success(message: str)`

以绿色记录成功消息，并带有勾选前缀。

```python
logger.success("Documentation generated successfully")
# 输出: ✓ Documentation generated successfully (绿色)
```

#### `warning(message: str)`

以黄色记录警告消息，并带有警告符号前缀。

```python
logger.warning("Module not found, skipping")
# 输出: ⚠️  Module not found, skipping (黄色)
```

#### `error(message: str)`

以红色记录错误消息，并带有 X 前缀，输出到 stderr。

```python
logger.error("Failed to parse file")
# 输出: ✗ Failed to parse file (红色，输出到 stderr)
```

#### `step(message: str, step: Optional[int] = None, total: Optional[int] = None)`

记录处理步骤，可选步骤编号。

```python
# 不带步骤编号
logger.step("Starting analysis")
# 输出: → Starting analysis (蓝色，粗体)

# 带步骤编号
logger.step("Analyzing dependencies", step=1, total=5)
# 输出: [1/5] Analyzing dependencies (蓝色，粗体)
```

#### `elapsed_time() -> str`

返回自日志记录器创建以来经过的时间。

```python
elapsed = logger.elapsed_time()
# 返回: "2m 30s" 或 "45s"，取决于经过的时间
```

## 工厂函数

### `create_logger(verbose: bool = False) -> CLILogger`

创建并返回一个配置好的 `CLILogger` 实例。

```python
from codewiki.cli.utils.logging import create_logger

logger = create_logger(verbose=True)
```

## 使用示例

```python
from codewiki.cli.utils.logging import create_logger

# 初始化日志记录器
logger = create_logger(verbose=True)

# 记录不同类型的消息
logger.info("Starting documentation generation")
logger.step("Phase 1: Analysis", step=1, total=4)

logger.debug("Scanning project structure...")
logger.success("Found 25 modules")

logger.warning("2 modules skipped due to errors")
logger.error("Failed to generate 1 module")

# 检查经过的时间
print(f"Total time: {logger.elapsed_time()}")
```

## 输出格式

CLILogger 使用 Click 的彩色输出函数：

| 方法 | 颜色 | 前缀 | 输出流 |
|--------|-------|--------|---------------|
| debug | 青色（暗淡） | 时间戳 | stdout |
| info | 默认 | 无 | stdout |
| success | 绿色 | ✓ | stdout |
| warning | 黄色 | ⚠️ | stdout |
| error | 红色 | ✗ | stderr |
| step | 蓝色（粗体） | [step/total] 或 → | stdout |

## 依赖项

- **click**: 用于彩色终端输出（`click.secho`、`click.echo`）
- **datetime**: 用于时间戳跟踪
- **typing**: 用于类型提示（`Optional`）
- **sys**: 用于 stderr 输出

## 集成

CLILogger 在整个 CLI 中用于提供一致的用户反馈：

- **[cli_adapters.md](cli_adapters.md)**: 记录文档生成和翻译进度
- **[cli_config.md](cli_config.md)**: 记录配置加载和 git 操作
- **[be_agent_orchestrator.md](be_agent_orchestrator.md)**: 记录代理执行和文档生成

## 错误处理

CLILogger 设计为具有容错性：
- 在不支持颜色的终端中静默失败
- 优雅处理缺失的 click 库
- 日志操作期间不抛出异常
