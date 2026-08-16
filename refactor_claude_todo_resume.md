# Resume: enforce the 250-line file cap

> **Paste this whole file to a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Continues `refactor_claude_todo.md`, which is still the
> spec — read it too, but the decisions below override it where they differ.

## Where things stand

**184 files** over 250 lines (was 198). All work so far is committed and pushed
to `main`; the tree is clean. The three unrelated edits an earlier handoff
warned about (`README.md`, the two `analysis_options.yaml`) are no longer
present.

Done already (do not redo):

| Commit    | What                                                                 |
| --------- | -------------------------------------------------------------------- |
| `~/utils` | `plans/` + `sessions/` exempted from the cap (`specs/` still capped) |
| `17b20e5` | New `no-inline-python` pre-commit hook + the one violation fixed     |
| `004b4b0` | `CLAUDE.md` 259 → 141 lines                                          |
| `72a5e28` | `poker-stakes/` tracked in git (58 files)                            |
| `73b85f5` | `poker-stakes/` 4 violations → 0                                     |
| `77c6d9f` | `wsg_grabber/catalog.py` 251 → 175                                   |
| `8ce4536` | `wsg_grabber/cli.py` 282 → 247                                       |
| `62ad148` | `wsg_grabber/review.py` 330 → 196                                    |
| `262ef38` | `wsg_grabber/net.py` 335 → 109                                       |
| `f58caea` | `wsg_grabber/store.py` 382 → 202                                     |
| `324ec0c` | `wsg_grabber/downloader.py` 420 → 238 (mixins)                       |
| `16c6266` | `wsg_grabber/player.py` 373 → 235                                    |
| `d86965f` | `wsg_grabber/ui.py` 398 → 242 (mixin)                                |

**Every `wsg_grabber` source file is now under the cap.** What remains in that
package is its 7 test files, which are the next thing to do — see the note on
shared fixtures under "Traps".

## The live worklist

Do not work from a list in this file — it goes stale. Run:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

Current distribution: `linux_configuration` 84, `python_pkg` 50,
`phone_focus_mode` 13, `kcd2_dice_solver` 12, `focus_owner` 11, `billsplit` 6,
`reverse_survivors`/`meta`/`docs` 4 each, `.github`/`bucket_catch` 2 each.
**48 of them are near-misses at 251–300 lines** — highest count-drop per unit
of effort, do these first.

## Decisions already made (do not re-ask)

1. **Full clearance** to `--all` exit 0. When context runs out, write a fresh
   handoff like this one rather than stopping mid-way.
2. **CI checks only files in the push/PR range**, not `--all`.
3. `docs/superpowers/plans/**` + `sessions/**` are exempt — already done.
4. `poker-stakes/` is tracked — already done.
5. For prose: automate what can be automated, delete the automated lines, keep
   only HOW, never WHY.
6. Shell verification is `bash -n` + `shellcheck` + `systemctl cat` path checks.
   **Never execute enforcement scripts that mutate the phone or the live system.**
7. One commit per logical unit.

## The constraint that will bite you

**Wire the file-length gate LAST**, only once `--all` already exits 0.

`meta/scripts/ci_mirror.sh:109` runs `pre-commit run --all-files` as a
**pre-push** hook, and `.github/workflows/pre-commit.yml:105` does the same in
CI. Registering the hook while violations remain makes **every `git push` fail**
until the last file is fixed. Do not scope around it with `exclude:`/`files:` —
that is the allowlist the spec forbids.

Final commit, once and only once the tree is clean:

```yaml
- id: file-length
  name: file length <= 250 lines
  entry: bash /home/kuhy/utils/scripts/check_file_length.sh
  language: system
```

Plus `.github/workflows/file-length.yml` modelled on
`~/todo/.github/workflows/file-length.yml` (checks out `kuhyx/utils` into
`.utils`), scoped to changed files. Then prove it fails: stage a deliberately
251-line file, confirm `git commit` aborts, delete it.

## The Python re-export form — settled empirically, do not re-derive

When a split moves a **public** name out of a module that callers/tests still
reach through the old path, the re-export must be marked with `__all__`:

```python
from python_pkg.pkg._new_module import show_logs, summarise

__all__ = ["build_parser", "main", ..., "show_logs", "summarise"]
```

The PEP 484 alias form `from x import y as y` **does not work here**: ruff
raises `PLC0414` (useless-import-alias), auto-fixes it away, and then removes
the now-"unused" import under `F401` — silently breaking `cli.summarise`.
Verified on `wsg_grabber/cli.py`; `__all__` passes ruff + mypy + pylint clean.

Splits that only move **private** helpers (leading `_`, no external caller)
need no shim at all — check with grep first, as in `catalog.py`.

`__all__` only needs the **re-exported** names, not every public name in the
module — names defined locally stay reachable either way. Verified against the
full gate on `store.py`.

**`__all__` does not save you from ruff's `TC001`.** It suppresses `F401`, but
a re-exported class used only in annotations gets rewritten into the
`TYPE_CHECKING` block, which lints perfectly and raises `AttributeError` at
import time. This nearly shipped a broken `ui.Callbacks` that `cli.py`
constructs. A class that must be reachable at runtime from module X stays
_defined_ in module X. **Always finish a re-export split with**

```bash
PYTHONPATH=. python3 -c "from python_pkg.pkg import mod; mod.TheName"
```

Two other things the gate will not catch for you:

- **Check what the tests patch before choosing a seam.** `test_ui.py` does
  `patch.object(ui, "tk", fake)`, so every line touching `tkinter` had to stay
  in `ui.py`; moving widget construction out errored 22 tests. Grep the test
  file for `patch.object(<module>` first and treat those names as pinned.
- **Tests that call private methods pin them too** — `test_player.py` calls
  `mpv._note_errors(...)`, so that method stayed as a one-line delegate to the
  moved implementation.

**Budget the new import block and `__all__` before deciding a two-way split is
enough.** Five splits so far landed 2–16 lines over the cap after the first cut
and needed a further seam; the header costs 10–20 lines that the arithmetic on
function sizes does not show.

Splitting a **class**: if tests call private methods as bound attributes
(`worker._fetch_thread(...)` — grep the tests first), module-level functions
will not do; use mixins. The shape that passes every gate with **no
suppression** (settled on `downloader.py`, do not re-derive):

```python
# _worker_base.py
class WorkerBase(ABC):
    _deps: WorkerDeps          # bare annotations for read-only attributes
    _downloaded: int = 0       # real default for any attribute the mixin ASSIGNS

    @abstractmethod
    def _publish(self, event: DownloadEvent) -> None:
        """Supplied by the concrete Worker."""
```

Both mixins inherit `WorkerBase`; `Worker(ScanMixin, DownloadMixin)`. Why not
the obvious alternatives:

- Naming a class `*Mixin` does **not** get you pylint's `no-member` exemption
  here — `ignored-checks-for-mixins` is not configured for it. Don't rely on it.
- `raise NotImplementedError` stub bodies are **uncovered lines** under the
  100% branch gate.
- `if TYPE_CHECKING: def _publish(...) -> None: ...` satisfies mypy but leaves
  pylint reporting `no-member`.
- A bare annotation (`_downloaded: int`) is not enough for an attribute the
  mixin assigns to (`+= 1`); pylint wants a real default.

Watch the MRO: `Worker(ScanMixin, DownloadMixin)` means ScanMixin wins any
name collision.

Coverage: `meta/pyproject.toml` sets `source = ["python_pkg"]`, so a new
sibling module is measured automatically. Confirmed: new modules show up in
the report at 100% rather than being silently skipped. Add no new branches
(no `if TYPE_CHECKING` guards beyond what moved, no defensive `try/except`).

## Split recipes

- **Shell** — extract into `lib/*.sh` sourced by a thin entry script,
  `set -euo pipefail` in each. Follow `phone_focus_mode/lib/` and
  `linux_configuration/scripts/lib/common.sh`.
- **Python** — extract cohesive helpers into sibling modules; keep the public
  API stable by re-exporting.
- **TS/Dart** — extract components; re-export from the original path so no
  importer changes.
- **Tests** — split by describe/test-group. Coverage must not drop.
  In `python_pkg`, `meta/pyproject.toml` omits `*/tests/*` from coverage **by
  path**, so a shared `<pkg>/tests/_helpers.py` is coverage-safe — the opposite
  of the `poker-stakes` trap below, where fixtures beside the source got counted
  as production code. Prefer one shared helper module over another `partN` file:
  the repo already carries `test_cups_service_part2/part3`,
  `test_consumables_part2` and `test_downloader_part2`, and every new `partN`
  that redeclares the same fixture scaffolding pushes jscpd toward its 2%
  duplication threshold, which only fires on the real `git commit`.

Never game the cap: no one-lining, no deleting tests, no moving code into an
exempt extension, no suppressions.

## Never edit files while a push is running

`git push` runs pre-commit, which **stashes unstaged changes and restores them
afterwards**. Editing a file in that window makes the restore fail with
`patch does not apply`, and the push aborts — _while `git push | tail` still
reports exit 0_, because the pipe masks it. This cost two silent failed pushes
and one silently reverted split.

Rules that follow:

- Stage (`git add`) before running `pre-commit run --files ...` on a
  work-in-progress tree, or the same stash cycle can revert the edit.
- Push only with a clean tree, and do not start other file edits until it
  returns.
- After any push, confirm with `git status --short --branch` that it does not
  still say `ahead N`. Never trust the exit code alone.

## Traps that cost time in the last session

- **Test fixtures and coverage.** When splitting a test file, shared helpers
  must go where the coverage config already excludes them (in `poker-stakes`
  that is `src/test/**`, matched **by path**). Putting them beside the source
  makes the coverage tool count them as production code and the 100% gate
  fails. Move the file; do **not** add a `coverage.exclude` entry.
- **`end-of-file-fixer` aborts commits.** Files built with `sed`/`cat` often
  lack a trailing newline. The hook fixes it and then fails the commit
  ("files were modified by this hook"). Just `git add` again and re-commit.
- **Formatters silently revert edits.** A PostToolUse formatter stripped an
  added import twice. After editing, `grep` the file to confirm the change
  survived before running anything.
- **Contracts.** Staging **≥4 code files** requires a _fresh_
  `docs/superpowers/contracts/*.json` in that same commit, on top of the
  per-commit `docs/superpowers/evidence/*.json`. Required keys: `title`,
  `objective`, `acceptance_criteria`, `out_of_scope`, `verifier`. Validate with
  `python3 meta/scripts/validate_contract.py <file>`.
- **`invariants.test.ts` in poker-stakes** flakes on its 5s timeout under
  parallel coverage load. It passes standalone in ~2.6s. Not a regression —
  do not "fix" it by weakening the test.
- **Long commands**: background anything over ~60s rather than blocking.

## `phone_focus_mode` — highest blast radius, do it LAST

Two silent failure modes:

1. **`deploy.sh` has a hardcoded flat push list** (search for `adb_cmd push`,
   around lines 374–383) with **no `lib/` subdirectory**. Every new split lib
   must be added there in the same commit, or the phone sources a missing file
   at runtime — gate green, tests green, device broken.
2. **`config.sh` (556 lines) is sourced by 11 scripts.** Keep `config.sh` as
   the entry point that re-sources its own parts, so all 11 callers keep
   working untouched.

Static check after each split: grep `deploy.sh`'s push list and every
`source`/`.` line in `phone_focus_mode/*.sh` and confirm each new lib appears.

## Suggested order

1. The 48 near-misses (251–300) — mechanical, biggest count drop.
2. `python_pkg` (50) — `pytest-coverage` gates each changed package on commit.
3. `linux_configuration` (84) — largest; check systemd unit paths still resolve.
4. `kcd2_dice_solver`, `focus_owner`, `billsplit`, the rest.
5. `phone_focus_mode` (13) — with the guard above.
6. Gate wiring + CI workflow — last.

## Done condition

```bash
cd ~/testsAndMisc && bash ~/utils/scripts/check_file_length.sh --all   # exit 0
pre-commit run --all-files                                             # passes
```

Plus: a staged 251-line file makes `git commit` fail.
