# Python split recipes for the 250-line cap

Settled empirically while clearing `python_pkg/wsg_grabber`. Every rule here
cost at least one failed gate run or one revert to learn — do not re-derive
them. Referenced from `refactor_claude_todo_resume.md`.

## The re-export form

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

## `mock.patch` pins names to a module — run this grep FIRST

**This is the constraint that decides where a seam can go.** `patch("mod.name")`
rebinds an attribute on `mod`. If you move a function to `_new.py`, that
function resolves its collaborators through `_new`'s globals, and the patch on
`mod` no longer reaches it. Tests then fail with either
`<module> does not have the attribute 'x'` or, worse, a real call to the thing
that was supposed to be mocked.

Before choosing any seam, list every pinned name in the package:

```bash
grep -ohP 'patch\((?:f")?(?:\{MOD\}|"[\w.]+)\.\K[\w]+' <pkg>/tests/*.py | sort -u
```

Everything it prints — **including plain imports like `subprocess`, `shutil`,
`Path`, `time`, and collaborators imported from sibling modules** — must stay
resolvable in the module the test names. Two consequences:

- A function that _calls_ a patched collaborator has to stay in that module,
  or move together with it.
- `patch.object(mod, "tk", fake)` is the same rule in another spelling.
  `test_ui.py` uses it, which is why every `tkinter` line had to stay in
  `ui.py` — moving widget construction out errored 22 tests.

`brother_printer` is the extreme case: its test modules patch ~90 distinct
names across the package, including `estimate_consumable_life` on `display`.
An otherwise clean extraction of the page-count block was reverted because of
exactly that. Grep first, then pick the seam.

**Tests that call private methods pin them too** — `test_player.py` calls
`mpv._note_errors(...)`, so that method stayed as a one-line delegate to the
moved implementation. That is the escape hatch for a **one-off** pinned name:
leave a thin delegate behind. It does not scale — under `select = ["ALL"]`
every delegate needs a full docstring with `Args:`, so a 25-line function
leaves a 12-line stub. Eight of those to make a line count is the cap-gaming
the spec forbids.

### A mispointed patch can HANG rather than fail

In `brother_printer` a stale patch target raised `AttributeError` or made a
real `subprocess` call — loud, or at worst a side effect you could check for
afterwards. In `code_tutor` it **spins**: `_write_tests_first_flow` reads from
an `input_fn` in a retry loop, so an unintercepted `_collect_and_rate_tests`
ran the real interactive flow and the suite hung for two minutes with no
output. `ps` showed it `State: R`, not blocked on I/O.

Two consequences for any package whose code prompts, retries or shells out:

- **Run the suite under `timeout`.** A hang is indistinguishable from a slow
  run until you have waited longer than you should.
- **Assert the patch targets resolve before invoking pytest**, since a missing
  one is exactly what causes the hang:

```bash
PYTHONPATH=. python3 -c "
from python_pkg.pkg import mod_a as a, mod_b as b
for n in ('_helper', 'Thing'): assert hasattr(a, n), n
"
```

`code_tutor` also patches by **absolute string with no `MOD` constant**, so a
seam there costs one rewrite per patch string rather than one `sed`. Prefer
seams whose moved block has few patched names, even at slightly worse line
arithmetic. Watch out for a `sed` with escaped alternation silently matching
nothing — a no-op rewrite looks exactly like a successful one at the shell, so
`grep` the result before trusting it.

### You may edit the tests to follow the code (agreed 2026-08-16)

When a patch target moves, **update the patch target**. Bounded by:

- no assertion changed,
- no test deleted, skipped or weakened,
- the pass **count** identical before and after (record it in the evidence).

Updating `MOD = "python_pkg.pkg.display"` to the function's new home is
bookkeeping, not weakening. Do it **per patched name**, never as a blanket
swap: a name patched from two different test modules (`_display_report_header`
is patched by both `test_display.py` and `test_display_part2.py`) has to stay
reachable from both, so it belongs in whichever module keeps the shared entry
points.

The test modules are usually the best map of where the seam goes. In
`brother_printer`, `test_display.py` patches only USB-side helpers,
`test_display_part2.py` only network-side, and `test_display_part3.py` only the
page-count collaborators — three concerns in one 427-line module. Split the
source to match, and let each test module's `MOD` follow.

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
