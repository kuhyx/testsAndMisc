"""Trigger a knowledge-rag reindex safely from outside the MCP server.

Two guards wrap the reindex, both of which exist because this runs unattended
from a pacman hook:

* **Instance lock.** knowledge-rag's single-instance lock is taken only by its
  ``main()``. Importing the orchestrator directly bypasses it, so a reindex
  fired while a ``claude-archwiki`` session is live would have two processes
  writing one Chroma collection. The lock file is checked explicitly instead.
* **Machine load.** Embedding is CPU-bound -- knowledge-rag ships the CPU-only
  ``onnxruntime`` build, so despite the 3090 in this box the pass saturates
  roughly every core for minutes. If the machine is already working hard,
  defer rather than compete: the converted Markdown stays on disk and the next
  run picks up exactly where this one stopped.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from python_pkg.archwiki_rag.constants import (
    DATA_SUBDIR,
    KNOWLEDGE_RAG_PYTHON,
    LOAD_PER_CORE_THRESHOLD,
    LOADAVG_PATH,
    LOCK_FILENAME,
)

_ENTRY_MODULE = "python_pkg.archwiki_rag._reindex_entry"


def read_lock_pid(store_dir: Path) -> int | None:
    """Read the pid recorded in the knowledge-rag instance lock.

    Parameters:
    store_dir (Path): Root of the knowledge-rag store.

    Returns:
    int | None: The pid, or None when there is no readable lock file.
    """
    lock_path = store_dir / DATA_SUBDIR / LOCK_FILENAME
    try:
        first_line = lock_path.read_text(encoding="utf-8").strip().splitlines()[0]
        return int(first_line)
    except IndexError, OSError, ValueError:
        return None


def is_server_running(store_dir: Path) -> bool:
    """Report whether a knowledge-rag MCP server currently owns this store.

    Parameters:
    store_dir (Path): Root of the knowledge-rag store.

    Returns:
    bool: True when the lock names a live process. A lock left behind by a
        crashed server is treated as free.
    """
    pid = read_lock_pid(store_dir)
    return pid is not None and Path(f"/proc/{pid}").exists()


def load_per_core() -> float:
    """Current 1-minute load average, divided by the CPU count.

    A single read of ``/proc/loadavg`` -- no forks, per the repo's polling
    guidance.

    Returns:
    float: Load per core, or 0.0 when ``/proc/loadavg`` is unreadable (a
        machine that cannot report load is never treated as busy).
    """
    try:
        first_field = LOADAVG_PATH.read_text(encoding="utf-8").split(maxsplit=1)[0]
        load = float(first_field)
    except IndexError, OSError, ValueError:
        return 0.0
    return load / (os.cpu_count() or 1)


def blocking_reason(store_dir: Path, *, ignore_load: bool = False) -> str | None:
    """Explain why a reindex should not run right now.

    Parameters:
    store_dir (Path): Root of the knowledge-rag store.
    ignore_load (bool): Skip the load check, for an explicitly requested run.

    Returns:
    str | None: Human-readable reason to defer, or None when clear to proceed.
    """
    if is_server_running(store_dir):
        return "a knowledge-rag server is already using this store"
    if not ignore_load:
        load = load_per_core()
        if load > LOAD_PER_CORE_THRESHOLD:
            return (
                f"machine is busy (load {load:.2f}/core); deferring to avoid contention"
            )
    return None


def run_reindex(store_dir: Path) -> int:
    """Run the reindex under the knowledge-rag interpreter.

    Parameters:
    store_dir (Path): Root of the knowledge-rag store, passed through as
        ``KNOWLEDGE_RAG_DIR`` so the child targets the right corpus.

    Returns:
    int: Exit status of the child process; 127 when its interpreter is absent.
    """
    if not KNOWLEDGE_RAG_PYTHON.exists():
        return 127

    env = dict(os.environ)
    env["KNOWLEDGE_RAG_DIR"] = str(store_dir)
    # The entry module imports from python_pkg, which is not installed into the
    # knowledge-rag venv, so point that interpreter back at this repo.
    repo_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo_root), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])],
    )

    completed = subprocess.run(
        [str(KNOWLEDGE_RAG_PYTHON), "-m", _ENTRY_MODULE],
        env=env,
        check=False,
    )
    return completed.returncode
