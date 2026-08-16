# testsAndMisc

Mixed-language monorepo: Python packages, Bash automation, and several apps.

## Repository Layout

| Path                        | Description                                                                                               |
| --------------------------- | --------------------------------------------------------------------------------------------------------- |
| `python_pkg/`               | Python packages — every `.py` in the repo belongs here or in an allowlisted dir                           |
| `meta/`                     | Repo-wide tooling: `pyproject.toml`, `requirements.txt`, `run.sh`, `lint_python.sh`, `.fvmrc`, `scripts/` |
| `linux_configuration/`      | Arch setup, i3 config, system maintenance, and the tracked git hooks                                      |
| `phone_focus_mode/`         | GPS-based Android focus enforcer (Bash, ADB, Magisk)                                                      |
| `billsplit/`                | Receipt bill-splitting Flutter app (Dart)                                                                 |
| `reverse_survivors/`        | React/Vite game — you play the horde (TypeScript)                                                         |
| `poker-stakes/`             | Poker stakes trainer (TypeScript, Vite)                                                                   |
| `kcd2_dice_solver/`         | KCD2 dice solver                                                                                          |
| `focus_owner/`              | Android Device-Owner focus enforcer (Kotlin)                                                              |
| `bucket_catch/`, `bottles/` | Small standalone projects                                                                                 |
| `docs/`                     | Reference docs; `docs/superpowers/` holds AI workflow artifacts                                           |
| `third_party/`              | Vendored upstream skills/agents                                                                           |

Root `pyproject.toml`, `requirements.txt`, `run.sh`, `lint_python.sh` and
`.fvmrc` are **symlinks into `meta/`** — edit the files in `meta/`, not the
symlinks.

Extracted to their own repos: [`steam-backlog-enforcer`](https://github.com/kuhyx/steam-backlog-enforcer),
[`screen-locker`](https://github.com/kuhyx/screen-locker),
[`diet-guard`](https://github.com/kuhyx/diet-guard),
[`wake-alarm`](https://github.com/kuhyx/wake-alarm),
[`dufs-cloud`](https://github.com/kuhyx/dufs-cloud),
[`build-your-x`](https://github.com/kuhyx/build-your-x) (lives at `~/build_your_x`).
Archived work: [`testsAndMisc-archive`](https://github.com/kuhyx/testsAndMisc-archive).

## Adding a Flutter app

`billsplit/` is currently the only one, and the only place binaries are
committed. To add another, repeat **both** halves or the icons fail silently:

1. Add the icon globs to `.binary-allowlist`.
2. Add matching `!` overrides at the end of `.gitignore` — an ignored file
   fails silently on `git add` rather than erroring.

Icons come from the shared generator in `python_pkg/app_icons/`. Dart style is
gated by CI only (`.github/workflows/billsplit-ci.yml`), not by a local hook.
Keep app dirs free of Python: the `check-python-location` hook requires every
`.py` to sit under `python_pkg/` (or `linux_configuration/`, `phone_focus_mode/`,
`meta/scripts/`). `billsplit/`'s coverage gate therefore lives at
`python_pkg/billsplit_coverage/`.

## Git Workflow

Work directly on `main`; commit and push straight there.

`core.hooksPath` points at the tracked `linux_configuration/.githooks/`, so
hooks travel with the repo. `.git/hooks/` is unused — **never run
`pre-commit install`**.

- **pre-commit**: shfmt + shellcheck + jscpd (fails above 2% duplication),
  then `pre-commit run --hook-stage pre-commit`.
- **pre-push**: `pre-commit run --hook-stage pre-push` — `prettier` and
  `ci-mirror`. `ci-mirror` runs a clean-venv install, `pre-commit run` over all
  files, and pytest for changed packages.

Bootstrap a clone or new machine:

```bash
./meta/scripts/install_hooks.sh          # wire hooks + install missing tools
./meta/scripts/install_hooks.sh --check  # verify only; exit 1 if incomplete
```

Both hooks fail closed: every external binary is verified each run and
auto-installed via pacman where possible. A missing tool aborts the commit —
it never means "skip the check". Extend `REQUIRED_TOOLS` in
`linux_configuration/.githooks/lib/common.sh` when adding a `language: system`
hook. `common.sh` also warns when local shellcheck/prettier/shfmt/zsh drift
from the versions pinned in `.github/workflows/pre-commit.yml`.

## Development Workflow

- Do NOT run tests unless instructed, or before committing.
- If tests fail on the same issue twice in a row, STOP and ask.
- Confirm a change works by **running the program** and inspecting output —
  not by running tests. Then ask the user to confirm the behaviour.
- Fix coverage gaps; do not ignore them.

### AI evidence (enforced)

Every commit touching code needs an evidence artifact:

1. Copy `docs/superpowers/evidence/template.json` →
   `docs/superpowers/evidence/<task-slug>-<date>.json`.
2. Fill in intent, scope, changes, verification, risks, rollback.
3. Stage it with the code.

`validate_evidence.py` rejects empty `verification[]` and the phrases
"should work", "probably fine", "seems right".

**Staging ≥4 code files additionally requires a fresh
`docs/superpowers/contracts/*.json`** in the same commit.

Deletions in `docs/superpowers/sessions/*` abort the commit (append-only).

## Code Conventions

Anything already enforced by a hook is omitted here — run
`pre-commit run --all-files` and read `.pre-commit-config.yaml` for the
complete list. What follows is what a linter cannot check.

### Python

- `from __future__ import annotations` for forward references.
- Prefix private functions/modules with `_` (`_smart_plug.py`,
  `_process_game_event`).
- Mock external calls in tests; never hit real APIs or the filesystem.
- For branch coverage: prefer an explicit `while True` with
  `try`/`except StopIteration` over `for` when iterator exhaustion needs
  covering, and mock threads/subprocesses to keep tests fast.

Full linting/coverage configuration lives in `meta/pyproject.toml`
(ruff `select = ["ALL"]`, mypy, pylint `enable = "all"`, coverage
`fail_under = 100` with branch coverage). Note the mypy **hook** disables a
number of error codes, so it is weaker than the `strict = true` in the config.

### Shell

- `set -euo pipefail` in every script.
- Prefer `/proc`, `/sys` and bash builtins over `$(...)` in hot paths — see
  the `efficient-polling-scripts` skill. The `no-polling-antipatterns` hook
  only inspects functions named `*_loop`, `*_daemon` or `poll*`, so a fork
  storm elsewhere passes clean.
- Use `jq`/`yq` for JSON/YAML, not `grep`/`awk`.

## Key Files

- `meta/pyproject.toml` — all Python tool configs
- `.pre-commit-config.yaml` — hook definitions
- `linux_configuration/.githooks/` — the tracked git hooks
- `meta/requirements.txt` — runtime + dev dependencies
- `docs/superpowers/evidence/template.json` — evidence template
- `.github/workflows/` — `pre-commit`, `python-tests`, `shell-tests`, and one
  CI workflow per app
