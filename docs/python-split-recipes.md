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
