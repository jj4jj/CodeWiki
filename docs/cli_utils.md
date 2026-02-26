Documentation for the `cli_utils` module has been generated. Here's a summary of the created files:

## Generated Documentation Files

| File | Description |
|------|-------------|
| [cli_utils.md](cli_utils.md) | Main documentation with architecture overview, component descriptions, and integration points |
| [logging.md](logging.md) | Detailed documentation for `CLILogger` class including all methods and usage patterns |
| [progress.md](progress.md) | Detailed documentation for `ProgressTracker` and `ModuleProgressBar` classes |

## Documentation Highlights

**Architecture:**
- The cli_utils module provides logging and progress tracking utilities for the CLI
- Three main components: `CLILogger`, `ProgressTracker`, and `ModuleProgressBar`

**Key Features Covered:**
1. **CLILogger** - Colored console output with verbose mode support, timestamps, and different severity levels
2. **ProgressTracker** - 5-stage weighted progress tracking with ETA estimation
3. **ModuleProgressBar** - Visual progress bar for module-by-module generation

**Visual Diagrams:**
- Architecture graph showing component relationships
- Stage workflow state diagram showing the 5 documentation generation stages with weights
- Progress calculation diagram illustrating stage weighting

**Cross-References:**
- All files are properly cross-referenced with each other
- Links to related modules: cli_adapters, cli_config, and be_agent_orchestrator