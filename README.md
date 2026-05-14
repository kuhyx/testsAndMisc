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

| Directory     | Description              |
| ------------- | ------------------------ |
| `Bash/`       | FFmpeg build scripts     |
| `C/`          | Small native helpers     |
| `python_pkg/` | Python package structure |

Archived / unmaintained projects live in the sibling repository
[`testsAndMisc-archive`](https://github.com/kuhyx/testsAndMisc-archive).

## Tooling

- **Python linting**: [Ruff](https://docs.astral.sh/ruff/) with all rules enabled (see `pyproject.toml`)
- **CI**: GitHub Actions — lint, build, and test on push
- **Testing**: pytest (Python), custom shell-based test harness for scripts
