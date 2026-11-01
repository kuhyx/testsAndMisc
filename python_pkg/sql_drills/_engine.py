"""Thin Docker wrapper around one long-lived ``mysql:8.0.33`` container.

The version is pinned on purpose (the one the judge documents); do not bump
it. The data dir is a tmpfs, so ``stop`` leaves nothing behind. Every call
here is short: ``start`` waits a bounded time and says "rerun" if MySQL is
still initialising, rather than blocking.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

IMAGE = "mysql:8.0.33"
CONTAINER = "sql-drills-mysql"
READY_TIMEOUT = 45.0
QUERY_TIMEOUT = 30.0
_DOCKER_TIMEOUT = 50.0
_MYSQL = ["mysql", "-uroot", "--default-character-set=utf8mb4", "-B", "-N"]


class EngineError(RuntimeError):
    """Docker or MySQL is unavailable or misbehaving."""


@dataclass(frozen=True)
class SqlResult:
    """Outcome of one ``mysql`` client invocation."""

    returncode: int
    stdout: str
    stderr: str


def _docker(
    *args: str, stdin: str | None = None, timeout: float = _DOCKER_TIMEOUT
) -> subprocess.CompletedProcess[str]:
    """Run ``docker <args>``; map a missing binary or a timeout to EngineError."""
    exe = shutil.which("docker")
    if exe is None:
        msg = "docker binary not found"
        raise EngineError(msg)
    try:
        return subprocess.run(
            [exe, *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"docker {args[0]} timed out after {timeout:.0f}s"
        raise EngineError(msg) from exc


def container_state() -> str:
    """``running``, ``exited``, ... or ``missing`` when no such container."""
    res = _docker("inspect", "-f", "{{.State.Status}}", CONTAINER)
    return res.stdout.strip() if res.returncode == 0 else "missing"


def is_ready() -> bool:
    """True once MySQL accepts TCP connections (the init server does not)."""
    res = _docker(
        "exec", CONTAINER, "mysqladmin", "ping", "-h127.0.0.1", "-uroot", "--silent"
    )
    return res.returncode == 0


def start(
    timeout: float = READY_TIMEOUT,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Create or resume the container and wait (bounded) until it is ready."""
    state = container_state()
    if state == "missing":
        res = _docker(
            "run", "-d", "--name", CONTAINER,
            "--tmpfs", "/var/lib/mysql:rw,size=512m",
            "--memory", "1500m",
            "-e", "MYSQL_ALLOW_EMPTY_PASSWORD=yes",
            IMAGE,
        )  # fmt: skip
    elif state != "running":
        res = _docker("start", CONTAINER)
    else:
        res = subprocess.CompletedProcess([], 0, "", "")
    if res.returncode != 0:
        msg = f"could not start container: {res.stderr.strip()}"
        raise EngineError(msg)
    deadline = clock() + timeout
    while not is_ready():
        if clock() >= deadline:
            msg = f"MySQL not ready after {timeout:.0f}s; rerun `start` to keep waiting"
            raise EngineError(msg)
        sleep(1.0)


def stop() -> None:
    """Remove the container (and its tmpfs data). Idempotent."""
    _docker("rm", "-f", CONTAINER)


def run_sql(
    sql: str, database: str | None = None, timeout: float = QUERY_TIMEOUT
) -> SqlResult:
    """Pipe ``sql`` into the mysql client, ``-B -N`` style."""
    argv = ["exec", "-i", CONTAINER, *_MYSQL]
    if database:
        argv.append(database)
    try:
        res = _docker(*argv, stdin=sql, timeout=timeout)
    except EngineError as exc:
        if "timed out" in str(exc):
            msg = f"query timed out after {timeout:.0f}s"
            raise EngineError(msg) from exc
        raise
    return SqlResult(res.returncode, res.stdout, res.stderr)
