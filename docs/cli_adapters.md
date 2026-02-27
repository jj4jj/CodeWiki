The documentation for the `cli_adapters` module is now complete. Here's a summary of the generated files:

## Generated Documentation Files

| File | Description |
|------|-------------|
| `cli_adapters.md` | Main documentation with architecture overview, workflows, and integration points |
| `doc_generator.md` | Detailed documentation for `CLIDocumentationGenerator` including 5-stage pipeline |
| `translator.md` | Detailed documentation for `DocTranslator` with translation cascade explanation |
| `html_generator.md` | Detailed documentation for `HTMLGenerator` with GitHub Pages deployment info |

## Documentation Highlights

**Architecture:**
- The cli_adapters module bridges CLI commands with backend services
- Three main components: `CLIDocumentationGenerator`, `DocTranslator`, `HTMLGenerator`

**Key Features Covered:**
1. **CLIDocumentationGenerator** - 5-stage documentation pipeline with progress tracking
2. **DocTranslator** - Cascading translation (agent → main model → fallback models)
3. **HTMLGenerator** - Self-contained HTML viewer for GitHub Pages

**Diagrams Included:**
- Architecture overview (graph)
- Documentation generation sequence
- Translation cascade sequence

The documentation references other modules in the module tree (cli_config, cli_models, cli_utils, be_agent_orchestrator, dependency_analyzer) for cross-module context.