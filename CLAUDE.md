# Copilot Instructions for testsAndMisc

## Project Overview

A mixed-language monorepo containing Python packages, Bash scripts, and misc automation. Actively-developed
components span personal productivity tools: alarm/shutdown scheduling, screen locking, Linux system
configuration, and Android phone focus enforcement.

Steam backlog enforcer has been extracted to its own repo:
[`steam-backlog-enforcer`](https://github.com/kuhyx/steam-backlog-enforcer).

Archived / unmaintained projects live in the sibling repository
[`testsAndMisc-archive`](https://github.com/kuhyx/testsAndMisc-archive).

## Repository Layout

| Path                   | Description                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| `python_pkg/`          | Python packages — each maintained subpackage lives here                                       |
| `linux_configuration/` | Arch Linux setup, i3 config, system maintenance scripts                                       |
| `phone_focus_mode/`    | GPS-based Android focus enforcer (Bash, ADB, Magisk)                                          |
| `meta/`                | Repo-wide tooling: `pyproject.toml`, `requirements.txt`, `run.sh`, `lint_python.sh`, `.fvmrc` |
| `scripts/`             | Workspace-level helper scripts and pre-commit hooks (moved to `meta/scripts/`)                |
| `docs/`                | Reference docs; `docs/superpowers/` holds AI workflow artifacts                               |
| `third_party/`         | Vendored upstream skills/agents                                                               |

> **Note**: Root-level `pyproject.toml`, `requirements.txt`, `requirements.txt`, `run.sh`, and `.fvmrc`
> are symlinks into `meta/`. Edit files there, not the symlinks.

## Architecture

### Python Packages (`python_pkg/`)

- **screen_locker/** — Tkinter/systemd screen locker with workout tracking and sick-day management
  - `screen_lock.py` — main locker UI
  - `_early_bird.py` — early-bird workout check
  - `_sick_tracker.py` — sick-day tracker
  - `_shutdown.py` — scheduled shutdown integration
  - `_phone_verification.py` — phone check integration
  - `_ui_flows.py` / `_window_setup.py` — UI helpers
  - `_time_check.py` — time/schedule checks
  - `_log_integrity.py` — tamper-evident workout logs
  - `tests/` — 100% branch coverage enforced (300+ tests)

- **wake_alarm/** — Alarm + fan ramp + Tapo P110 smart plug control
  - `_alarm.py` — alarm logic
  - `_smart_plug.py` — Tapo P110 control
  - `_state.py` — alarm state persistence
  - `_constants.py` — timing/config constants
  - `wake_state.json` — persistent alarm state
  - `wake-alarm-fans.sh` — fan ramp script (requires sudo)
  - `wake-alarm.service` — systemd unit
  - `tests/` — pytest tests

- **brother_printer/** — Brother printer status checker via CUPS and USB/network query
  - `check_brother_printer.py` — main status check
  - `cups_queue.py` / `cups_service.py` — CUPS integration
  - `network_query.py` / `usb_query.py` — device discovery
  - `tests/` — pytest tests

- **screen_locker** and **wake_alarm** share the `midnight_shutdown` integration:
  on alarm nights the system hibernates instead of powering off.

- **shared/** — Shared utilities across python_pkg subpackages
- **random_jpg/** — Random JPEG downloader utility
- **geo_cache/** — Geographic coordinate cache helper

### Phone Focus Mode (`phone_focus_mode/`)

Location-based app restriction for rooted Android. Automatically disables non-whitelisted apps within
500 m of home using ADB + Magisk.

- `focus_ctl.sh` / `focus_daemon.sh` — focus enforcement scripts
- `dns_enforcer.sh` — DNS-level blocking (netd cache restart for YouTube)
- `hosts_enforcer.sh` — `/etc/hosts` manipulation
- `launcher_enforcer.sh` — launcher restriction
- `workout_detector.sh` — workout detection integration
- `magisk_service.sh` — Magisk module hook (prevents module self-disabling)
- `config.sh` — configuration constants
- `deploy.sh` — ADB deployment script
- `systemd/` — systemd units for scheduling
- `lib/` — shared shell library functions

### Linux Configuration (`linux_configuration/`)

Arch Linux setup and ongoing system automation.

```
linux_configuration/
├── install_core_system.sh          # Core system installer
├── scripts/
│   ├── single_use/                 # One-time setup scripts
│   │   ├── fresh-install/
│   │   ├── features/
│   │   ├── fixes/
│   │   └── misc/
│   └── periodic_background/        # Ongoing daemons / scheduled scripts
│       ├── digital_wellbeing/      # Compulsive-opening blocker, focus daemon, LeechBlock
│       ├── hosts/                  # DNS/hosts guard and generation
│       ├── i3-configuration/       # i3 window manager config
│       ├── system-maintenance/     # Usage reporting, system checks
│       └── utils/
├── tests/                          # Shell-based test harness
└── test_results.log
```

Key scripts:

- `scripts/periodic_background/digital_wellbeing/focus_mode_daemon.py` — Linux digital-wellbeing daemon
- `scripts/periodic_background/hosts/generate_hosts_file.sh` — Generates `/etc/hosts` blocklist
- `scripts/periodic_background/system-maintenance/bin/usage_report.py` — Daily usage report

### `meta/` — Repo-wide Tooling

All root-level config files are symlinks into `meta/`. Edit here:

- `meta/pyproject.toml` — ruff, mypy, pylint, bandit, pytest, coverage config
- `meta/requirements.txt` — runtime + dev dependencies
- `meta/run.sh` — usage report entrypoint + polling script profiler/diagnostics
- `meta/lint_python.sh` — manual lint helper
- `meta/scripts/` — pre-commit hook scripts (`check_no_binaries.sh`, `check_ai_evidence.sh`, etc.)

### `docs/superpowers/` — AI Workflow Artifacts

Pre-commit **requires** an evidence file for every commit that changes source code:

```
docs/superpowers/
├── evidence/         # ← Required: one JSON per commit touching code
│   └── template.json
├── contracts/        # Acceptance criteria / objective contracts per task
├── sessions/         # Append-only session logs (JSONL)
├── specs/            # Task specifications / design docs
├── plans/            # Implementation plans
├── memory/           # Persistent context (CONTEXT.md, etc.)
└── workflows/        # Agent workflow definitions
```

**Rule**: copy `docs/superpowers/evidence/template.json`, fill it in, and stage it with your code changes
before committing. The `ai-evidence-contract` hook will reject commits without it.

## Development Workflow

### Testing (Critical — 100% branch coverage enforced for all packages)

```bash
# Run all python_pkg tests with coverage
python -m pytest python_pkg/ --cov=python_pkg --cov-branch --cov-fail-under=100

# Run a single package
python -m pytest python_pkg/screen_locker/ --cov=python_pkg.screen_locker --cov-branch --cov-fail-under=100
python -m pytest python_pkg/wake_alarm/ --cov=python_pkg.wake_alarm --cov-branch --cov-fail-under=100
python -m pytest python_pkg/brother_printer/ --cov=python_pkg.brother_printer --cov-branch --cov-fail-under=100

# Quick run without coverage
python -m pytest python_pkg/ -x -v
```

### Pre-commit Hooks (Always run before commits)

```bash
pre-commit run --files <file1> <file2>  # Check specific files (recommended)
pre-commit run --all-files              # Full check (~10s linters)
pre-commit run --all-files --hook-stage pre-push  # Includes pytest + prettier
```

**Active hooks (commit-stage)**:

| Hook                                                             | Purpose                                                     |
| ---------------------------------------------------------------- | ----------------------------------------------------------- |
| trailing-whitespace, end-of-file-fixer, check-yaml/json/toml/xml | General formatting                                          |
| check-added-large-files (max 2 MB)                               | Prevent large files                                         |
| detect-private-key                                               | Secret detection                                            |
| no-binaries                                                      | Block binary/image files from being committed               |
| ai-evidence-contract                                             | Require `docs/superpowers/evidence/*.json` for code changes |
| ai-multifile-contract                                            | Require workflow contract for multi-file changes            |
| append-only-sessions                                             | Enforce append-only session logs                            |
| no-polling-antipatterns                                          | Block polling script fork-storm anti-patterns               |
| no-noqa / no-ruff-noqa                                           | Block lint suppression comments                             |
| ruff (lint+fix)                                                  | Python linting                                              |
| ruff-format                                                      | Python formatting                                           |
| mypy                                                             | Python type checking                                        |
| pylint                                                           | Python extended linting                                     |
| bandit                                                           | Python security checks                                      |
| codespell                                                        | Spell checking                                              |

**Push-stage only**: `pytest-coverage` + `prettier`

**CRITICAL: NEVER use `--no-verify`** on `git commit` or `git push`. Fix failures or ask — never bypass hooks.

### AI Evidence Requirement

For every commit that touches `.py`, `.sh`, `.c`, `.go`, `.ts`, etc.:

1. Copy `docs/superpowers/evidence/template.json` → `docs/superpowers/evidence/<task-slug>-<date>.json`
2. Fill in the fields (objective, steps taken, verification result)
3. Stage and include it with your code changes

### Linting Tools (configured in `meta/pyproject.toml`)

- **ruff**: `select = ["ALL"]` — all rules enabled, Google docstrings
- **mypy**: `strict = true` with full type checking
- **pylint**: all checks enabled
- **coverage**: `fail_under = 100`, branch coverage required

## Code Conventions

### Python Style

- Use `from __future__ import annotations` for forward references
- Google docstring convention
- Absolute imports only (`ban-relative-imports = "all"`)
- Type hints required on all functions
- Private functions/modules prefixed with `_` (e.g., `_smart_plug.py`, `_process_game_event`)

### Shell Style

- Always `set -euo pipefail`
- Double-quote all variable expansions
- Avoid fork-heavy patterns: prefer `/proc`, `/sys`, bash builtins over `$(...)` in hot paths
- Use `jq`/`yq` for JSON/YAML, not `grep`/`awk`

### Test Patterns

```python
# Type aliases for test dicts (keeps mypy happy)
Event = dict[str, Any]

# Mock external calls — never hit real APIs/filesystem
with patch("python_pkg.screen_locker.screen_lock.some_func") as mock:
    ...

# Use PropertyMock for property exceptions
type(mock_obj).property_name = PropertyMock(side_effect=TypeError())
```

### Branch Coverage Tips

- Use explicit `while True` + `try/except StopIteration` instead of `for` loops when iterator
  exhaustion needs coverage
- Mock threads/subprocesses to avoid slow tests
- Every `if`/`else` branch needs a corresponding test

## Key Files

- `meta/pyproject.toml` — All tool configs (ruff, mypy, pylint, pytest, coverage)
- `.pre-commit-config.yaml` — Pre-commit hook definitions
- `meta/requirements.txt` — Runtime + dev dependencies
- `.github/workflows/python-tests.yml` — CI: runs all pytest on `python_pkg/**` changes
- `.github/workflows/pre-commit.yml` — CI: runs pre-commit checks
- `docs/superpowers/evidence/template.json` — Template for AI evidence artifacts

## Per-File Ignores (in `meta/pyproject.toml`)

Test files allow: `S101` (assert), `PLR2004` (magic values), `S310`, `S607`, `PLC0415`
