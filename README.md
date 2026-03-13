# testsAndMisc

A collection of personal projects, scripts, and experiments — from a GPS-based phone focus tool to C/C++ demos, with CI, linting, and pre-commit hooks across the board.

## Highlights

### [Phone Focus Mode](phone_focus_mode/)

Location-based app restriction for rooted Android. Automatically disables non-whitelisted apps within 500 m of home using ADB + Magisk. Features Haversine distance calculation, hysteresis to prevent toggling, fail-safe unlock, and state persistence. **Bash, Android ADB.**

### [Linux Configuration](linux_configuration/)

Automated Arch Linux setup: fresh-install scripts, i3 window manager config, LaTeX environment, and system tests. Includes documentation and test result logging.

### [Scripts](scripts/)

Utility scripts for development workflows — C/C++ build file validation, secret detection, and custom makepkg helpers.

## Other Projects

| Directory | Description |
|---|---|
| `poker_modifier_app/` | Browser-based poker hand modifier (HTML/JS) |
| `pomodoro_app/` | Pomodoro timer (Flutter) |
| `Bash/` | FFmpeg build scripts |
| `C/`, `CPP/`, `TS/` | Language-specific experiments |
| `sonic_pi/` | Music programming experiments |
| `robotgo_demo/` | Go desktop automation demo |
| `python_pkg/` | Python package structure example |

## Tooling

- **Python linting**: [Ruff](https://docs.astral.sh/ruff/) with all rules enabled (see `pyproject.toml`)
- **JS/TS linting**: ESLint (flat config)
- **CI**: GitHub Actions — lint, build, and test on push
- **Testing**: pytest (Python), custom shell-based test harness for scripts
