# Next session: three explicit asks, then keep splitting

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

Over-cap: **37 → 24** (20 shell, 2 kotlin, 1 dart, 1 markdown — this file).
17 commits pushed. **Python is done**: every `.py` is under the cap at 100%
line+branch coverage where the gate measures it.

The user has given three direct instructions. Do them in this order, each as
its own commit. They are already decided — do **not** re-litigate them.

---

## 1. Fix the `_VENDOR_KW` Intel bug

`python_pkg/vscode_optimizer/_hardware.py:22`:

```python
_VENDOR_KW = {"nvidia": "NVIDIA", "amd": "AMD", "ati": "AMD", "intel": "Intel"}
```

`_detect_gpu` does `for kw, vendor in _VENDOR_KW.items(): if kw in low:`.
Every real `lspci` display line contains **"VGA comp*ati*ble controller"**, so
`"ati"` matches unconditionally and `"intel"` is unreachable. **Intel iGPUs are
reported as AMD**, which switches on the GPU-accelerated terminal and AMD-only
Electron flags. This machine is unaffected only because `"nvidia"` is checked
first.

**Do:**

- Fix it so vendor detection keys on the device description rather than the
  whole line — the text after the last `:` is already extracted into
  `hw.gpu_model` one line above. Match against that, not `low`.
- Delete the `strict=True` xfail `test_detect_gpu_should_recognise_an_intel_igpu`
  in `python_pkg/vscode_optimizer/tests/test_gpu_disk.py` and make it a normal
  passing test. **The xfail is `strict=True`, so a fix without removing the
  marker fails the suite** — that is deliberate.
- The parametrised `test_detect_gpu_maps_each_vendor_keyword` currently
  _characterises_ the bug: two of its cases assert `"AMD"` for an Intel line and
  for an unknown vendor. Update both to the correct expectations.
- Verify with a real run: `python3 -m python_pkg.vscode_optimizer --dry-run`
  must still detect this machine's RTX 3090 as NVIDIA and propose the same
  **18 changes**. Then confirm the repo gate: bare `pytest` (memory-capped)
  at 100%.

## 2. Split the `phone_focus_mode` scripts anyway

The user has accepted the deployment risk. **This does not mean skip the copy
lists** — it means proceed with the splits, doing them correctly.

`deploy.sh` has **two** hardcoded per-file lists and never deploys `lib/`:

- an `adb_cmd push "$DEPLOY_DIR/<f>" "/data/local/tmp/focus_stage/<f>"` (~line 381)
- an `adb_root "cp /data/local/tmp/focus_stage/<f> $REMOTE_DIR/<f>"` (~line 497)

**Every new sibling must be added to BOTH, in the same commit.** Missing the
push leaves the copy pointing at a file that was never staged. Use a **sibling
file** beside the entry script, never a `lib/` member — these scripts source
`"$SCRIPT_DIR/<name>.sh"` and `lib/` does not exist on the phone.

`tether_enforcer.sh` was done last session and is the worked example — read that
commit before starting.

Targets, cheapest first, with what can verify each:

| file                 | lines | verifiable by                                                                        |
| -------------------- | ----- | ------------------------------------------------------------------------------------ |
| `dns_enforcer.sh`    | 325   | `lib/tests/test_dns_enforcer.sh` — **runnable**                                      |
| `phone_backup.sh`    | 333   | no test; not in deploy.sh's lists at all                                             |
| `curfew_enforcer.sh` | 367   | no test                                                                              |
| `hosts_enforcer.sh`  | 421   | no test                                                                              |
| `lib/monitor.sh`     | 449   | `lib/tests/test_monitor.sh` — **runnable**; already a lib, not deployed by deploy.sh |
| `focus_daemon.sh`    | 543   | no test                                                                              |
| `config.sh`          | 571   | **`python_pkg/focus_policy/loader.py` parses it** — see below                        |
| `deploy.sh`          | 835   | not deployed itself; entry+`lib/` IS safe here                                       |
| `focus_ctl.sh`       | 1091  | no test                                                                              |

Start with `dns_enforcer.sh` and `lib/monitor.sh`: both have real test scripts,
so you can prove the split the way `tether_enforcer` was proved (run the test
before and after; the count must match exactly).

**`config.sh` is special.** `python_pkg/focus_policy/loader.py` is a
mini-interpreter that parses it as the live source of truth. Splitting it breaks
that loader unless the parser follows. `focus_policy` has 100% tests that will
catch it — run them. Plan the two changes together, or do `config.sh` last.

## 3. Restructure the three parked files

Last session parked these because a verbatim function move cannot get them under
the cap. The user has authorised restructuring. **Restructuring means the
verbatim harness no longer applies, so each one needs a test or a real run
instead** — say plainly which you used.

- **`install_plagiarism_tools.sh` (534, only 3 tiny functions).** ~500 lines of
  top-level code. Wrap coherent stages in functions, then move those. This is
  the most mechanical of the three; do it first.
- **`libre_translate.sh` (488, 18 funcs).** After the clean seams are taken,
  `parse_args` (111 lines), `write_env_file`, `detect_container_user` and `main`
  all assign **and** read the same configuration globals. Four attempts were
  spent relocating them; that does not work. Restructure `parse_args` — e.g.
  split the case body into per-flag helpers, or move the whole config-globals
  cluster into one lib that owns both writes and reads.
- **`diagnose_pacman_hook_stall.sh` (493, 15 funcs).** Same shape: `run_one`
  writes `LAST_ELAPSED`, `main` reads it. Also emits **SC2153**
  (`PACMAN_BIN` vs `PACMAN_PID`) once split — that is a real shellcheck finding
  to resolve, not to suppress.

---

## Tooling — use it, don't rebuild it

**`meta/scripts/extract_shell_functions.py`** — moves functions into a library.
Walks brace-by-brace and lifts only function blocks. **Never slice by line
range**: these scripts interleave top-level commands between function
definitions, and a range slice sweeps those into the library where they run at
source time and out of order. It refuses to guess when there is no `set -e`
anchor (as in the `#!/system/bin/sh` phone scripts) — place the source line by
hand there, after the existing `. "$SCRIPT_DIR/config.sh"`.

```bash
python3 meta/scripts/extract_shell_functions.py <script> <lib> \
  --functions name1,name2 --header '#!/usr/bin/env bash
# What this library is for.'
```

**`meta/scripts/verify_shell_split.sh`** — proves a move was verbatim by
normalising each function through `shfmt -mn` and comparing hashes. Sees through
reformatting, catches a one-character logic change, names the function.

```bash
bash meta/scripts/verify_shell_split.sh HEAD <old-path> <new-path>...
```

**Re-run it after pre-commit autofixes** — it caught `export` edits that lint had
accepted but that changed two function bodies. It does **not** apply to task 3,
where the code is deliberately being restructured.

## The rule that decides where a shell seam can fall

**A file must not assign a global it never reads.** That is SC2034; the repo
forbids suppressions; the pre-commit hook runs `shellcheck` with **no `-x`**, so
a `# shellcheck source=` directive will not make it follow the link. Each file
stands alone — check with `shellcheck <lib>` before committing.

The precedent at `install_pacman_wrapper.sh:29` is about _definitions-only_ libs.
It does **not** mean "assignments stay in the entry script" — it means writer and
readers must sit in the same file. `steam_compatibility.sh` split cleanly only
once `detect_system` moved next to `score_game` and `load_cache_map` next to
`main`. This is the shell analogue of the `monkeypatch.setattr` target trap.

## Still-live deployment trap (task 2 does not cancel this)

**`install_leechblock.sh` (485)** and **`block_compulsive_opening.sh` (705)** are
copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed copy
on **every pacman invocation**. Split them naively and every `pacman -S` on this
machine fails. Teach the installer to deploy the directory first, in its own
commit, then re-baseline, then split. **Do these last.** Note you cannot run
`sudo pacman -S` from the Bash tool — it deadlocks on `db.lck`; hand the user a
`! pacman -S <pkg>` line and state the expected output.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, `# type: ignore`, `# shellcheck
disable`, no lowered coverage threshold. Every time this came up last session
  the seam was wrong, not the linter.
- **Run the actual thing.** `steam_compatibility.sh --help` exiting 0 is what
  proved four source lines resolved. For scripts too dangerous to run
  (`main.sh` installs packages; `setup_passwordless_system.sh` writes sudoers),
  say so and rely on `bash -n` plus sourcing each library in a subshell to prove
  it has no side effects.
- **Check `check_file_length.sh --all` _before_ committing** — a split that fixes
  one file while pushing a new library over the cap is a net zero. It happened
  twice last session.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (copy `template.json`). Staging
  **≥4 code files also needs** a fresh `docs/superpowers/contracts/*.json`.
  Validate with `meta/scripts/validate_{evidence,contract}.py`.
- New sourced libs need a shebang **and** the executable bit. The
  `check-shebang-scripts-are-executable` hook reads the **git index** — stage the
  mode with `git add --chmod=+x`.
- `pre-commit run --files <changed>` before committing. **`prettier` and
  `ci-mirror` run on pre-push, not pre-commit.** `npx prettier --write` any `.md`
  you touch, including this one.
- Work directly on `main`. `git stash` and branch creation are blocked by hooks.
  Verify a push landed with `git status -sb` showing no `[ahead N]`.
- **Do not wire the file-length pre-commit hook.** It lands last, once
  `check_file_length.sh --all` exits 0. 24 files are still over.
- Cap pytest memory:
  `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0`.

## Known pre-existing state — not yours, do not fix silently

- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with
  `❌ FAIL: Compulsive block wrappers installed`. Belongs to
  `block_compulsive_opening.sh`.
- **`bucket_catch/packages/frontend` has 4 eslint errors**, documented with
  measured reasoning in
  `docs/superpowers/evidence/bucket-catch-eslint-2026-08-17.json`.
  `usePuzzleGameLoop.ts:129`'s `Map.get(...)!` cannot be fixed with
  `?? Infinity` — tried, measured at 99.54%, because the default side is
  unreachable. `npm run coverage` is green: 145 tests, 100%.
- Repo-wide `jscpd` reports ~2.5% from the working tree but 1.47% at HEAD in a
  clean worktree — the excess is vendored `.venv` site-packages. Don't chase it.
- The `tether_enforcer.sh` split is **unverified on the phone**. Its test passes
  (17/17), and both `deploy.sh` lists were updated, but no deploy has run. If
  tether enforcement misbehaves after the next deploy, look there first.

## Testing notes specific to this repo

- `linux_configuration/tests` **is** in CI, but never by name: `pyproject.toml`
  sets `testpaths`, so bare `pytest` collects it. Behaviour is gated; coverage is
  not (`--cov=python_pkg` only).
- **Non-`python_pkg` modules are tested via `linux_configuration/tests/`**, whose
  `conftest.py` puts standalone script dirs on `sys.path`. Add a directory there
  rather than moving code into `python_pkg/` — that move drags the file under a
  `fail_under = 100` gate and breaks any by-path caller.
- `name-tests-test` requires every `.py` under `tests/` to be `test_*.py`. Shared
  helpers go in `conftest.py` as **fixtures** — `conftest` is not importable by
  module name.
- For a **test-file** split the discriminating check is the test **count**, not a
  green run: a file outside the runner's glob is silently never collected. That
  caught a real breakage last session.
- `phone_focus_mode`'s shell tests are **not** in CI — `shell-tests.yml` uses an
  explicit list covering `linux_configuration/tests/` only. Run them by hand.
- `focus_owner` gradle needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and
  `--rerun-tasks`; a plain `gradlew test` reports `UP-TO-DATE` and proves nothing.
