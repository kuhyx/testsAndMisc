"""Tests for linux_configuration/fixes/tmp_quota.py (quotactl_fd helper).

The kernel is never called: every test passes a fake ``syscall`` that reads
or fills the ``if_dqblk`` struct at the address it is given, the way
quotactl_fd(2) does.
"""

from __future__ import annotations

import ctypes
import errno
from typing import TYPE_CHECKING

import pytest
import tmp_quota as tq

if TYPE_CHECKING:
    from pathlib import Path

LIMIT_KIB = 25165824
USED_BYTES = 3 * 1024 * 1024
UID = 1000


class FakeKernel:
    """Holds one user's quota and answers Q_GETQUOTA / Q_SETQUOTA."""

    def __init__(self, limit_kib: int = 0, *, fail: int = 0) -> None:
        """Start with ``limit_kib`` and fail every call with ``fail`` if set."""
        self.limit_kib = limit_kib
        self.fail = fail
        self.ignore_set = False
        self.calls: list[tuple[int, int, int]] = []
        self.set_blocks: list[tq.IfDqblk] = []

    def __call__(self, nr: int, fd: int, cmd: int, qid: int, addr: int) -> int:
        """Act as syscall(2) for quotactl_fd."""
        assert fd >= 0
        self.calls.append((nr, cmd, qid))
        if self.fail:
            ctypes.set_errno(self.fail)
            return -1
        block = tq.IfDqblk.from_address(addr)
        if cmd == tq.qcmd(tq.Q_GETQUOTA):
            block.dqb_bhardlimit = self.limit_kib
            block.dqb_bsoftlimit = self.limit_kib
            block.dqb_curspace = USED_BYTES
            block.dqb_valid = 63
        else:
            copy = tq.IfDqblk.from_buffer_copy(block)
            self.set_blocks.append(copy)
            if not self.ignore_set:
                self.limit_kib = block.dqb_bhardlimit
        return 0


def test_qcmd_matches_the_kernel_encoding() -> None:
    """QCMD(Q_GETQUOTA, USRQUOTA) is 0x80000700."""
    assert tq.qcmd(tq.Q_GETQUOTA) == 0x80000700
    assert tq.qcmd(tq.Q_SETQUOTA) == 0x80000800


def test_get_reads_limit_and_use(tmp_path: Path) -> None:
    """GET returns the hard limit in KiB and the use converted to KiB."""
    kernel = FakeKernel(LIMIT_KIB)
    quota = tq.get_quota(str(tmp_path), UID, kernel)
    assert quota == tq.Quota(limit_kib=LIMIT_KIB, used_kib=3072)
    assert kernel.calls == [(443, 0x80000700, UID)]


def test_get_reports_the_kernel_error(tmp_path: Path) -> None:
    """A failing syscall becomes a QuotaError naming the mount, uid and errno."""
    kernel = FakeKernel(fail=errno.ESRCH)
    with pytest.raises(tq.QuotaError, match="No such process") as caught:
        tq.get_quota(str(tmp_path), UID, kernel)
    assert str(tmp_path) in str(caught.value)
    assert "uid 1000" in str(caught.value)


def test_get_reports_an_unopenable_mount(tmp_path: Path) -> None:
    """A mount point that cannot be opened is a QuotaError, not a traceback."""
    with pytest.raises(tq.QuotaError, match="cannot open"):
        tq.get_quota(str(tmp_path / "missing"), UID, FakeKernel())


def test_set_writes_only_the_block_limits(tmp_path: Path) -> None:
    """SET sends soft = hard = limit and QIF_BLIMITS, nothing else."""
    kernel = FakeKernel(1600201)
    quota = tq.set_limit(str(tmp_path), UID, LIMIT_KIB, kernel)
    (sent,) = kernel.set_blocks
    assert (sent.dqb_bhardlimit, sent.dqb_bsoftlimit) == (LIMIT_KIB, LIMIT_KIB)
    assert sent.dqb_valid == tq.QIF_BLIMITS
    assert quota.limit_kib == LIMIT_KIB


def test_set_fails_when_the_limit_does_not_stick(tmp_path: Path) -> None:
    """A read-back that differs from the request is a QuotaError."""
    kernel = FakeKernel(1600201)
    kernel.ignore_set = True
    with pytest.raises(tq.QuotaError, match="reads back 1600201"):
        tq.set_limit(str(tmp_path), UID, LIMIT_KIB, kernel)


def test_main_get_prints_two_numbers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``get`` prints "<limit_kib> <used_kib>" for the shell to read."""
    argv = ["get", "--uid", "1000", "--mount", str(tmp_path)]
    assert tq.main(argv, FakeKernel(LIMIT_KIB)) == 0
    assert capsys.readouterr().out == f"{LIMIT_KIB} 3072\n"


def test_main_set_prints_the_read_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``set`` prints the quota as the kernel reports it afterwards."""
    argv = ["set", "--uid", "1000", "--mount", str(tmp_path)]
    argv += ["--limit-kib", str(LIMIT_KIB)]
    assert tq.main(argv, FakeKernel(1)) == 0
    assert capsys.readouterr().out == f"{LIMIT_KIB} 3072\n"


def test_main_reports_failure_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A QuotaError exits 1 with one clear line on stderr."""
    argv = ["get", "--uid", "1000", "--mount", str(tmp_path)]
    assert tq.main(argv, FakeKernel(fail=errno.EPERM)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("tmp_quota: ")
    assert "Operation not permitted" in captured.err


def test_main_rejects_a_negative_limit(tmp_path: Path) -> None:
    """A negative limit is an argument error, never sent to the kernel."""
    kernel = FakeKernel()
    argv = ["set", "--uid", "1000", "--mount", str(tmp_path), "--limit-kib", "-1"]
    with pytest.raises(SystemExit) as caught:
        tq.main(argv, kernel)
    assert caught.value.code == 2
    assert kernel.calls == []


def test_libc_syscall_is_typed() -> None:
    """The real syscall entry point has explicit argument and return types."""
    fn = tq.libc_syscall()
    assert fn.restype is ctypes.c_long
    assert fn.argtypes == [
        ctypes.c_long,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
    ]
