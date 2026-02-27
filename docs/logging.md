# Logging Sub-Module

The logging sub-module provides the `CLILogger` class for colored console output with different severity levels.

## Overview

The logging sub-module (`logging.py`) delivers user-friendly console output with color coding and formatting. It supports both verbose and normal output modes, enabling granular control over the amount of information displayed during CLI operations.

## CLILogger Class

### Purpose

`CLILogger` provides a standardized logging interface for the CodeWiki CLI with:
- Colored output for different message types
- Optional verbose mode for detailed debugging
- Timestamp tracking for operation timing

### Class Definition

```python
class CLILogger:
    """Logger for CLI with support for verbose and normal modes."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = datetime.now()
```

### Methods

#### `debug(message: str)`

Logs a debug message only when verbose mode is enabled.

```python
logger.debug("Analyzing file structure...")
# Only displays if verbose=True
```

#### `info(message: str)`

Logs an informational message in default terminal color.

```python
logger.info("Processing module: core/utils")
# Output: Processing module: core/utils
```

#### `success(message: str)`

Logs a success message in green with a checkmark prefix.

```python
logger.success("Documentation generated successfully")
# Output: ✓ Documentation generated successfully (in green)
```

#### `warning(message: str)`

Logs a warning message in yellow with a warning symbol prefix.

```python
logger.warning("Module not found, skipping")
# Output: ⚠️  Module not found, skipping (in yellow)
```

#### `error(message: str)`

Logs an error message in red with an X prefix, output to stderr.

```python
logger.error("Failed to parse file")
# Output: ✗ Failed to parse file (in red, to stderr)
```

#### `step(message: str, step: Optional[int] = None, total: Optional[int] = None)`

Logs a processing step with optional step numbering.

```python
# Without step numbers
logger.step("Starting analysis")
# Output: → Starting analysis (in blue, bold)

# With step numbers
logger.step("Analyzing dependencies", step=1, total=5)
# Output: [1/5] Analyzing dependencies (in blue, bold)
```

#### `elapsed_time() -> str`

Returns the elapsed time since the logger was created.

```python
elapsed = logger.elapsed_time()
# Returns: "2m 30s" or "45s" depending on elapsed time
```

## Factory Function

### `create_logger(verbose: bool = False) -> CLILogger`

Creates and returns a configured `CLILogger` instance.

```python
from codewiki.cli.utils.logging import create_logger

logger = create_logger(verbose=True)
```

## Usage Example

```python
from codewiki.cli.utils.logging import create_logger

# Initialize logger
logger = create_logger(verbose=True)

# Log different message types
logger.info("Starting documentation generation")
logger.step("Phase 1: Analysis", step=1, total=4)

logger.debug("Scanning project structure...")
logger.success("Found 25 modules")

logger.warning("2 modules skipped due to errors")
logger.error("Failed to generate 1 module")

# Check elapsed time
print(f"Total time: {logger.elapsed_time()}")
```

## Output Formatting

The CLILogger uses Click's colored output functions:

| Method | Color | Prefix | Output Stream |
|--------|-------|--------|---------------|
| debug | cyan (dim) | timestamp | stdout |
| info | default | none | stdout |
| success | green | ✓ | stdout |
| warning | yellow | ⚠️ | stdout |
| error | red | ✗ | stderr |
| step | blue (bold) | [step/total] or → | stdout |

## Dependencies

- **click**: For colored terminal output (`click.secho`, `click.echo`)
- **datetime**: For timestamp tracking
- **typing**: For type hints (`Optional`)
- **sys**: For stderr output

## Integration

The CLILogger is used throughout the CLI to provide consistent user feedback:

- **[cli_adapters.md](cli_adapters.md)**: Logs documentation generation and translation progress
- **[cli_config.md](cli_config.md)**: Logs configuration loading and git operations
- **[be_agent_orchestrator.md](be_agent_orchestrator.md)**: Logs agent execution and documentation generation

## Error Handling

The CLILogger is designed to be resilient:
- Silent failures for color rendering in unsupported terminals
- Graceful handling of missing click library
- No exceptions raised during logging operations
