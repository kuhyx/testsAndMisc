---
name: code-quality-rules
description: 'Mandatory code quality, linting, and test coverage rules for ALL languages in this monorepo. Use BEFORE writing or modifying ANY code. Covers Python, C/C++, TypeScript, Dart/Flutter, and shell. Enforces 100% test coverage, zero lint suppressions, and pre-commit compliance.'
---

# Code Quality Rules — All Languages

**Every agent working in this repository MUST follow these rules.** Non-compliance causes pre-commit/pre-push hooks to fail and PRs to be rejected.

## Universal Rules (All Languages)

1. **100% test coverage** is required for every project in every language — no exceptions. Do not exclude packages, files, or lines from coverage.
2. **Zero lint suppressions** — never add `# noqa`, `# type: ignore`, `// ignore:`, `// ignore_for_file:`, `// NOLINT`, `@ts-ignore`, `eslint-disable`, or equivalent without explicit user approval. Fix the underlying issue instead.
3. **Pre-commit hooks must pass** — run `pre-commit run --files <changed-files>` after every change. Never use `--no-verify` on git commit or push.
4. **No binary files** in the workspace — move to `../testsAndMisc_binaries/`. See `scripts/check_no_binaries.sh`.
5. **No secrets in code** — patterns in `.secret-patterns` are scanned on every commit.

## Python (`python_pkg/`)

### Linters (ALL enabled, maximum strictness)

| Tool | Config | Key Settings |
|---|---|---|
| **ruff** | `pyproject.toml [tool.ruff]` | `select = ["ALL"]`, Google docstrings, `ban-relative-imports = "all"` |
| **mypy** | `pyproject.toml [tool.mypy]` | `strict = true`, all `disallow_*` and `warn_*` flags enabled |
| **pylint** | `pyproject.toml [tool.pylint]` | `enable = "all"`, `disable = []`, `fail-under = 8.0` |
| **bandit** | `pyproject.toml [tool.bandit]` | Security scanner, high severity, medium confidence |
| **ruff-format** | `pyproject.toml [tool.ruff.format]` | Double quotes, spaces, auto line endings |

### Ruff Rules

- **ALL rule categories enabled** — every ruff rule fires unless explicitly ignored in `pyproject.toml`.
- Only these rules are globally ignored (with justification):
  - `D203` (conflicts with `D211`), `D213` (conflicts with `D212`)
  - `COM812`, `ISC001` (formatter conflicts)
  - `S603` (subprocess false positives with validated input)
- Per-file ignores exist ONLY for test files and a handful of files with documented technical justifications (lazy imports, camelCase overrides, thesis scripts). Check `[tool.ruff.lint.per-file-ignores]` before adding any new ones.
- `fixable = ["ALL"]` — auto-fix is enabled for all rules.

### Mypy Rules

- `strict = true` mode with additional flags:
  - `disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_untyped_decorators`
  - `disallow_any_unimported`, `disallow_any_generics`, `disallow_subclassing_any`
  - `warn_return_any`, `warn_redundant_casts`, `warn_unused_ignores`, `warn_unreachable`
  - `strict_equality`, `extra_checks`, `no_implicit_optional`
- Type hints required on ALL functions.

### Pylint Rules

- **All checks enabled**, nothing disabled (`enable = "all"`, `disable = []`).
- `min-public-methods = 0`, `max-attributes = 10`, `max-module-lines = 1000`.

### Test Coverage

- **100% branch coverage** enforced via `[tool.coverage.report] fail_under = 100`.
- Branch coverage is mandatory (`branch = true`).
- Run: `python -m pytest python_pkg/<subpackage>/tests/ --cov=python_pkg.<subpackage> --cov-branch --cov-fail-under=100`
- The pre-push hook (`scripts/pytest_changed_packages.py`) runs tests only for changed subpackages.

### Style Requirements

- `from __future__ import annotations` in every file.
- Google docstring convention.
- Absolute imports only (`ban-relative-imports = "all"`).
- Double quotes everywhere.
- Private functions prefixed with `_`.

## C / C++ (`C/`, `CPP/`)

### Linters

| Tool | Trigger | Key Settings |
|---|---|---|
| **clang-format** | Pre-commit hook | Formatting enforced on all `.c`/`.cpp` files |
| **cppcheck** | Pre-commit hook | `--enable=warning,portability`, `--std=c11`, `--error-exitcode=1` |
| **flawfinder** | Pre-commit hook | `--error-level=5` — security scanner for C/C++ |
| **clang-tidy** | `C/lint_all.sh` | Uses `compile_commands.json` when available |

### Build Requirements

- Every C/C++ directory MUST have a `Makefile` and `run.sh` (enforced by `scripts/check_c_cpp_build_files.sh`).
- Exceptions: `CPP/mini_browser/` (CMake), `horatio/`.

### Test Coverage

- **100% line coverage** is required for all C/C++ projects.
- Use `gcov` + `lcov` to measure coverage. Compile with `-fprofile-arcs -ftest-coverage` (`--coverage` shorthand), run the test binary, then check coverage:
  ```bash
  gcc --coverage -o test_foo test_foo.c foo.c && ./test_foo
  lcov --capture --directory . --output-file coverage.info
  lcov --remove coverage.info '/usr/*' --output-file coverage.info
  genhtml coverage.info --output-directory coverage_html
  ```
- C projects under `C/tests/` and C++ projects under `CPP/tests/` — all tests must pass with 100% line coverage.
- When adding new C/C++ source files, add corresponding tests that cover every branch.

## TypeScript (`TS/`)

### Linters

| Tool | Config | Key Settings |
|---|---|---|
| **ESLint** | `eslint.config.mjs` | `eslint.configs.recommended` + `tseslint.configs.recommended` |
| **Prettier** | Pre-commit (push) | Formats YAML, JSON, Markdown |

### ESLint Rules

- TypeScript-ESLint recommended ruleset applied to all `TS/**/*.{ts,tsx}`.
- `@typescript-eslint/no-unused-vars` set to `"error"` (args/vars prefixed `_` are allowed).
- Ignores: `node_modules`, `dist`, `build`, `*.d.ts`, config files.

### Pre-commit Integration

- ESLint runs on every commit for `TS/` files: `npx eslint --no-warn-ignored`.

### Test Coverage

- **100% statement and branch coverage** is required for all TypeScript projects.
- Use a test runner (Jest, Vitest, or equivalent) with coverage enabled. Example with Vitest:
  ```bash
  npx vitest run --coverage --coverage.thresholds.statements=100 --coverage.thresholds.branches=100
  ```
- When adding new TS source files, add corresponding test files (`*.test.ts` / `*.spec.ts`) that cover every branch.
- Coverage reports must be generated and checked before considering work complete.

## Dart / Flutter

### Horatio (`horatio/`)

| Tool | Config | Enforcement |
|---|---|---|
| **dart analyze** | `horatio/analysis_options.yaml` | `--fatal-infos` — infos are errors |
| **dart format** | melos `format` script | `--set-exit-if-changed` |
| **flutter test** | `horatio/run.sh` | 100% line coverage enforced |

#### Analysis Rules

The `analysis_options.yaml` enables **strict everything**:
- `strict-casts: true`, `strict-inference: true`, `strict-raw-types: true`
- `missing_return: error`, `missing_required_param: error`
- **100+ individual lint rules** explicitly enabled (see file for full list)
- Key rules: `always_use_package_imports`, `avoid_dynamic_calls`, `type_annotate_public_apis`, `prefer_single_quotes`, `require_trailing_commas`, `avoid_print`

#### Test Coverage

- **100% coverage** enforced for both `horatio_core` and `horatio_app`.
- Generated files (`*.g.dart`, `tables/`) are filtered from coverage.
- Run: `cd horatio && bash run.sh test`
- Pre-push hook: `horatio-tests` runs `bash run.sh test`.

### Pomodoro App (`pomodoro_app/`)

- **Must match Horatio's strictness.** The `analysis_options.yaml` should be upgraded to the same level as `horatio/analysis_options.yaml`:
  - `strict-casts: true`, `strict-inference: true`, `strict-raw-types: true`
  - All 100+ lint rules from Horatio's config should be enabled
  - `flutter analyze --fatal-infos` — infos are treated as errors
- **100% test coverage** enforced, matching Horatio's standard.
- Pre-push hook: `flutter analyze && flutter test`.
- Current baseline (`package:flutter_lints/flutter.yaml`) is insufficient — any agent modifying `pomodoro_app/` should flag this gap and work toward parity with Horatio.

## Shell Scripts

### Linters

| Tool | Config | Key Settings |
|---|---|---|
| **ShellCheck** | Pre-commit hook | `--severity=warning` — all warnings and above are errors |

- All shell scripts are checked on every commit (except `pomodoro_app/`).
- Use `set -euo pipefail` in all bash scripts.

## Pre-Commit Hook Summary

### On Every Commit (fast, ~10s)

| Hook | Scope |
|---|---|
| trailing-whitespace, end-of-file-fixer | All files |
| check-yaml, check-json, check-toml, check-xml | Config files |
| check-merge-conflict, detect-private-key | All files |
| name-tests-test (`--pytest-test-first`) | Python tests |
| no-binaries | All files |
| no-noqa, no-ruff-noqa | Python — blocks ALL suppression comments |
| **ruff** (lint + fix) | Python |
| **ruff-format** | Python |
| **clang-format** | C/C++ |
| **cppcheck** | C/C++ |
| **flawfinder** | C/C++ |
| **eslint** | TypeScript |
| **shellcheck** | Shell scripts |
| **codespell** | All text files |
| check-c-cpp-build-files | C/C++ directories |
| check-python-location | Python must be under `python_pkg/` |
| check-no-secrets | All files |

### On Push Only (slow)

| Hook | Scope |
|---|---|
| **mypy** | Python (strict type checking) |
| **pylint** | Python (comprehensive linting) |
| **bandit** | Python (security scanning) |
| **pytest + 100% coverage** | Python (changed subpackages) |
| **prettier** | YAML, JSON, Markdown |
| **flutter analyze + test** | `pomodoro_app/` |
| **horatio run.sh test** | `horatio/` (100% coverage) |

## Verification Checklist

Before considering any code change complete:

1. [ ] `pre-commit run --files <changed-files>` passes
2. [ ] Tests pass with 100% branch coverage for the affected project
3. [ ] No new lint suppressions added without user approval
4. [ ] No binary files added to the workspace
5. [ ] Type hints on all new Python functions
6. [ ] Docstrings on all new public Python functions (Google convention)
