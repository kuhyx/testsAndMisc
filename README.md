# testsAndMisc

A collection of personal projects, scripts, and experiments — from a GPS-based phone focus tool to Linux/Arch automation, with CI, linting, and pre-commit hooks across the board.

## Highlights

### [Phone Focus Mode](phone_focus_mode/)

Location-based app restriction for rooted Android. Automatically disables non-whitelisted apps within 500 m of home using ADB + Magisk. Features Haversine distance calculation, hysteresis to prevent toggling, fail-safe unlock, and state persistence. **Bash, Android ADB.**

### [Linux Configuration](linux_configuration/)

Automated Arch Linux setup: fresh-install scripts, i3 window manager config, LaTeX environment, and system tests. Includes documentation and test result logging.

### [Scripts](scripts/)

Utility scripts for development workflows — build file validation, secret detection, and custom makepkg helpers.

## Repository Layout

| Path                   | Description                                                                                                                                                                                                |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python_pkg/`          | Python packages (each maintained subpackage lives here)                                                                                                                                                    |
| `linux_configuration/` | Arch Linux setup, i3 config, system maintenance scripts                                                                                                                                                    |
| `phone_focus_mode/`    | GPS-based Android focus enforcer                                                                                                                                                                           |
| `scripts/`             | Workspace-level helper scripts and pre-commit hooks                                                                                                                                                        |
| `docs/`                | Reference docs and historical reports                                                                                                                                                                      |
| `third_party/`         | Vendored upstream skills/agents                                                                                                                                                                            |
| `meta/`                | Repo-wide tooling: `pyproject.toml`, `requirements.txt`, `.pre-commit-config.yaml`, `run.sh`, `lint_python.sh`, `.fvmrc`. Symlinked into the repo root so tools that auto-discover from root keep working. |

Archived / unmaintained projects live in the sibling repository
[`testsAndMisc-archive`](https://github.com/kuhyx/testsAndMisc-archive).

## Tooling

- **Python linting**: [Ruff](https://docs.astral.sh/ruff/) with all rules enabled (see `meta/pyproject.toml`)
- **Dependencies**: `pip install -r meta/requirements.txt` (combined runtime + dev)
- **CI**: GitHub Actions — lint, build, and test on push
- **Testing**: pytest (Python), custom shell-based test harness for scripts
