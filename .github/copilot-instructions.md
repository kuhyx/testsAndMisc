# Copilot Instructions for testsAndMisc

## Project Overview

A mixed-language monorepo containing Python packages, C programs, TypeScript apps, and misc scripts. The primary actively-developed component is `python_pkg/lichess_bot/` - a Lichess chess bot.

## Architecture

### Python Packages (`python_pkg/`)

- **lichess_bot/** - Main project: Lichess bot with 100% test coverage requirement
  - `main.py` - Bot entry point, game handling, event loop
  - `lichess_api.py` - Lichess API client (NDJSON streaming)
  - `engine.py` - Wraps C engine at `C/lichess_random_engine/`
  - `tests/` - Comprehensive pytest tests using `MagicMock`, `PropertyMock`, `patch`
- Other packages are standalone scripts (download_cats, screen_locker, etc.)

### Cross-Language Integration

- Python `engine.py` → calls C binary via `subprocess.Popen`
- Python `stockfish_analysis/` → post-game analysis subprocess

## Development Workflow

### Testing (Critical - 100% coverage enforced)

```bash
# Run lichess_bot tests with coverage
python -m pytest python_pkg/lichess_bot/tests/ --cov=python_pkg.lichess_bot --cov-branch --cov-fail-under=100

# Quick test run
python -m pytest python_pkg/lichess_bot/tests/ -x -v
```

### Pre-commit Hooks (Always run before commits)

```bash
pre-commit run --all-files  # Full check
pre-commit run --files <file1> <file2>  # Specific files
```

**Hook order**: ruff (lint+fix) → ruff-format → mypy → pylint → bandit

### Linting Tools Configured in `pyproject.toml`

- **ruff**: `select = ["ALL"]` - all rules enabled, Google docstrings
- **mypy**: `strict = true` with full type checking
- **pylint**: all checks enabled
- **coverage**: `fail_under = 100`, branch coverage required

## Code Conventions

### Python Style

- Use `from __future__ import annotations` for forward references
- Google docstring convention
- Absolute imports only (`ban-relative-imports = "all"`)
- Type hints required on all functions
- Private functions prefixed with `_` (e.g., `_process_game_event`)

### Test Patterns (`python_pkg/lichess_bot/tests/`)

```python
# Type aliases for test dicts (keeps mypy happy)
Event = dict[str, Any]
GameThreads = dict[str, threading.Thread]

# Mock external calls, never hit real APIs
with patch("python_pkg.lichess_bot.main.threading.Thread") as mock:
    ...

# Use PropertyMock for property exceptions
type(mock_obj).property_name = PropertyMock(side_effect=TypeError())
```

### Branch Coverage Tips

- Use explicit `while True` + `try/except StopIteration` instead of `for` loops when iterator exhaustion needs coverage
- Mock threads/subprocesses to avoid slow tests

## Key Files

- `pyproject.toml` - All tool configs (ruff, mypy, pylint, pytest, coverage)
- `.pre-commit-config.yaml` - Pre-commit hook definitions
- `requirements.txt` - Runtime dependencies
- `.github/workflows/python-tests.yml` - CI pipeline

## Per-File Ignores (in `pyproject.toml`)

Test files allow: `S101` (assert), `PLR2004` (magic values), `S310`, `S607`, `PLC0415`
