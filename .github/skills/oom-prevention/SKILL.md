---
name: oom-prevention
description: "Prevent OOM freezes from pre-commit and pre-push hooks. Apply when modifying .git/hooks/, scripts/pytest_changed_packages.py, or any hook that runs pytest, mypy, or Node.js tools. The system has zram swap (4 GB compressed, stored IN RAM) — without MemorySwapMax=0 a memory-limited cgroup thrashes zram instead of dying cleanly, freezing the machine."
---

# OOM Prevention in Git Hooks

## Why This Matters

This machine uses **zram swap** (compressed RAM-backed swap, ~4 GB). Without swap
disabled in cgroup limits, a process that exceeds `MemoryMax` spills into zram instead
of being killed — the kernel thrashes zram, consuming MORE real RAM, and the machine
hard-freezes before the OOM killer fires.

**Symptom:** running `git push` or `git commit` freezes the entire machine for 5–10+
minutes.

## The Fix: `MemorySwapMax=0`

Every hook invocation that runs memory-heavy tools (pytest, mypy, pylint, Node.js/TS)
**must** be wrapped in a systemd scope with _both_ `MemoryMax` and `MemorySwapMax=0`:

```bash
systemd-run --user --scope \
  -p MemoryMax=4G \
  -p MemorySwapMax=0 \
  -- <command>
```

`MemorySwapMax=0` disables swap for the cgroup entirely. At `MemoryMax`, the process
is SIGKILL'd instantly rather than thrashing swap.

## Affected Files

### `.git/hooks/pre-commit`

Contains a `run_capped()` shell function:

```bash
run_capped() {
  if command -v systemd-run >/dev/null 2>&1; then
    systemd-run --user --scope \
      -p MemoryMax=4G \
      -p MemorySwapMax=0 \
      -- "$@"
  else
    "$@"
  fi
}
```

All heavy tool invocations go through `run_capped`. Also sets
`NODE_OPTIONS=--max-old-space-size=512` for TypeScript/ESLint tools.

### `.git/hooks/pre-push`

Same `run_capped()` pattern as pre-commit, with `MemoryMax=4G MemorySwapMax=0`.

### `scripts/pytest_changed_packages.py`

Runs each affected package's tests in a **nested** 2 GB cgroup to keep memory
bounded across sequential package runs:

```python
use_cgroup = shutil.which("systemd-run") is not None
cmd = [
    "systemd-run", "--user", "--scope",
    "-p", "MemoryMax=2G",
    "-p", "MemorySwapMax=0",
    *pytest_cmd,
]
```

Each package also gets its own `COVERAGE_FILE` env var pointing to a tmpfile,
so sequential runs don't corrupt each other's SQLite coverage DB:

```python
with tempfile.NamedTemporaryFile(
    prefix=f".coverage_{pkg}_", dir=".", delete=False
) as tmp:
    cov_file = tmp.name
env = {**os.environ, "COVERAGE_FILE": cov_file}
result = subprocess.run(cmd, check=False, env=env)
Path(cov_file).unlink(missing_ok=True)
```

## Coverage DB Corruption

When multiple pytest-cov processes run sequentially sharing the same `.coverage`
SQLite file, the second process finds the first's leftover `.coverage` and tries to
`combine()` it as a parallel data source — but the schema is incompatible, causing:

```
INTERNALERROR> coverage.exceptions.DataError:
    Couldn't use data file '.coverage': no such table: other_db.file
```

**Fix:** `COVERAGE_FILE=<unique-per-run-path>` so each subprocess writes to an
isolated DB, never seeing the prior run's file.

## Quick Reference

| Problem                                  | Root Cause                                 | Fix                                         |
| ---------------------------------------- | ------------------------------------------ | ------------------------------------------- |
| Machine freezes during `git push`        | zram swap absorbs cgroup-limited process   | `MemorySwapMax=0` in all cgroup scopes      |
| Machine freezes during `git commit`      | Same as above                              | `run_capped()` in `.git/hooks/pre-commit`   |
| pytest INTERNALERROR on coverage combine | Stale `.coverage` SQLite DB from prior run | `COVERAGE_FILE=<unique-tmp>` per subprocess |
| pytest OOM during per-package run        | Accumulated memory across package runs     | 2 GB nested cgroup per package              |

## Adding New Hooks

If you add a new pre-commit or pre-push hook that runs:

- `pytest` with coverage
- `mypy` or `pylint`
- `node` / `eslint` / TypeScript compilation

**Always wrap it in `run_capped()`** (in the shell hook) or the `systemd-run`
subprocess pattern (in Python scripts). Never call these tools naked.
