# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sz-python-tools is a collection of command-line utilities for the Senzing entity resolution platform (V4). This is a Senzing Garage project (experimental/tinkering), not production-ready software.

## Common Commands

```bash
# Setup development environment (one-time)
make dependencies-for-development

# Run all linters (pylint, mypy, bandit, black, flake8, isort)
make lint

# Run individual linters
make pylint
make mypy
make black
make flake8
make isort
make bandit

# Run tests
make test

# Run tests with coverage (opens HTML report)
make coverage

# Clean build artifacts
make clean

# Build documentation
make documentation

# Build wheel package
make package
```

To run a single test file:
```bash
source .venv/bin/activate
pytest tests/example_test.py
```

## Architecture

### Source Organization

All source code is in `sz_tools/` directory. Each tool is a standalone executable Python script (no .py extension):

**Interactive Shell Tools** (using Python's `cmd.Cmd`):
- `sz_command` - Main CLI shell for Senzing engine operations
- `sz_configtool` - Configuration management shell
- `sz_explorer` - Entity/database explorer with prettytable output

**Data Processing Tools**:
- `sz_file_loader` - Multi-threaded data file loading (JSON/JSONL)
- `sz_export` - Entity data export (CSV/JSONL)
- `sz_snapshot` - Database state snapshots with multi-process support
- `sz_audit` - Data comparison and auditing
- `sz_json_analyzer` - JSON/JSONL file analysis

**Project Management**:
- `sz_create_project` - Create new Senzing project instances
- `sz_update_project` - V3→V4 and V4→V4 project upgrades
- `sz_setup_config` - Initialize Senzing configuration

### Shared Modules

- `_tool_helpers.py` - Comprehensive utilities: color theming (Colors class with ANSI codes), engine configuration, JSON formatting, terminal I/O, concurrent execution
- `_project_helpers.py` - Project file management, version comparison (SzBuildDetails class), Senzing paths
- `_sz_database.py` - Database abstraction layer supporting SQLite, PostgreSQL, Oracle, MSSQL, DB2, MySQL

### Key Patterns

- Color output uses the `Colors` class with themes: DEFAULT, LIGHT, DARK, TERMINAL
- JSON parsing uses `orjson` if available, with fallback to standard `json`
- Configuration stored in `sz_engine_config.ini`
- Interactive shells provide command history via readline

## Code Style

- **Line length**: 120 characters (Black formatter)
- **Import sorting**: isort with "black" profile
- **Type hints**: Gradual typing (mypy configured with relaxed checking)
- Python 3.10+ required

## Dependencies

Core runtime dependencies:
- `senzing >= 4.0.2`
- `senzing-core >= 1.0.0`

Optional (with graceful fallbacks):
- `orjson` - Fast JSON parsing
- `prettytable` - ASCII table output
- `pyclip` - Clipboard integration
- `pygments` - Syntax highlighting

## Environment

The Senzing C library must be installed:
- `/opt/senzing/er/lib` - Shared objects
- `/opt/senzing/er/sdk/c` - SDK headers
- `/etc/opt/senzing` - Configuration
