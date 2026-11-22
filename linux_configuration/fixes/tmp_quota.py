#!/usr/bin/env python3
"""Get or set one user's block quota on a mounted filesystem via quotactl_fd.

Used by fix_tmp_space.sh to raise a logged-in user's cap on the /tmp tmpfs
live: systemd sets that cap only at login, and restarting
user-runtime-dir@<uid> to re-apply it would end the session.

    tmp_quota.py get --uid 1000 --mount /tmp
    tmp_quota.py set --uid 1000 --mount /tmp --limit-kib 25165824

Both print "<limit_kib> <used_kib>" (the limit after the change, for set).
A limit of 0 means "no limit". Exits 1 with one line on stderr on failure.
Only the block limits are written; inode limits and usage are left alone.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    Syscall = Callable[[int, int, int, int, int], int]

SYS_QUOTACTL_FD = 443  # x86_64 (asm/unistd_64.h)
Q_GETQUOTA = 0x800007
Q_SETQUOTA = 0x800008
USRQUOTA = 0
SUBCMDSHIFT = 8
QIF_BLIMITS = 1


class IfDqblk(ctypes.Structure):
    """``struct if_dqblk`` from linux/quota.h; limits in KiB, space in bytes."""

    _fields_ = (
        ("dqb_bhardlimit", ctypes.c_uint64),
        ("dqb_bsoftlimit", ctypes.c_uint64),
        ("dqb_curspace", ctypes.c_uint64),
        ("dqb_ihardlimit", ctypes.c_uint64),
        ("dqb_isoftlimit", ctypes.c_uint64),
        ("dqb_curinodes", ctypes.c_uint64),
        ("dqb_btime", ctypes.c_uint64),
        ("dqb_itime", ctypes.c_uint64),
        ("dqb_valid", ctypes.c_uint32),
    )


class QuotaError(Exception):
    """quotactl_fd failed, or the kernel did not keep the requested limit."""


@dataclass(frozen=True)
class Quota:
    """One user's block quota: hard limit and current use, both in KiB."""

    limit_kib: int
    used_kib: int


def qcmd(cmd: int) -> int:
    """Encode ``QCMD(cmd, USRQUOTA)``."""
    return (cmd << SUBCMDSHIFT) | USRQUOTA


def libc_syscall() -> ctypes._FuncPointer:
    """Return libc's ``syscall`` with explicit types (cmd exceeds INT_MAX)."""
    fn = ctypes.CDLL(None, use_errno=True).syscall
    fn.argtypes = [
        ctypes.c_long,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
    ]
    fn.restype = ctypes.c_long
    return fn


def _call(mount: str, cmd: int, uid: int, block: IfDqblk, syscall: Syscall) -> None:
    """Run one quotactl_fd command against ``mount`` for ``uid``."""
    try:
        fd = os.open(mount, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as exc:
        msg = f"cannot open {mount}: {exc.strerror}"
        raise QuotaError(msg) from exc
    try:
        if syscall(SYS_QUOTACTL_FD, fd, qcmd(cmd), uid, ctypes.addressof(block)):
            err = ctypes.get_errno()
            msg = f"quotactl_fd on {mount} for uid {uid}: {os.strerror(err)}"
            raise QuotaError(msg)
    finally:
        os.close(fd)


def get_quota(mount: str, uid: int, syscall: Syscall) -> Quota:
    """Read ``uid``'s block quota on ``mount``."""
    block = IfDqblk()
    _call(mount, Q_GETQUOTA, uid, block, syscall)
    return Quota(limit_kib=block.dqb_bhardlimit, used_kib=block.dqb_curspace // 1024)


def set_limit(mount: str, uid: int, limit_kib: int, syscall: Syscall) -> Quota:
    """Set soft = hard = ``limit_kib`` (as systemd does), then read it back."""
    block = IfDqblk(
        dqb_bhardlimit=limit_kib, dqb_bsoftlimit=limit_kib, dqb_valid=QIF_BLIMITS
    )
    _call(mount, Q_SETQUOTA, uid, block, syscall)
    quota = get_quota(mount, uid, syscall)
    if quota.limit_kib != limit_kib:
        msg = f"uid {uid} on {mount}: set {limit_kib} KiB, reads back {quota.limit_kib}"
        raise QuotaError(msg)
    return quota


def _non_negative(text: str) -> int:
    """Parse an argument that must be an integer >= 0."""
    value = int(text)
    if value < 0:
        msg = f"must be >= 0: {text}"
        raise argparse.ArgumentTypeError(msg)
    return value


def _parser() -> argparse.ArgumentParser:
    """Build the get/set command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("get", "set"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--uid", type=_non_negative, required=True)
        cmd.add_argument("--mount", required=True)
        if name == "set":
            cmd.add_argument("--limit-kib", type=_non_negative, required=True)
    return parser


def main(argv: Sequence[str] | None = None, syscall: Syscall | None = None) -> int:
    """Run the command line; return the exit code."""
    args = _parser().parse_args(argv)
    call = syscall if syscall is not None else libc_syscall()
    try:
        if args.action == "set":
            quota = set_limit(args.mount, args.uid, args.limit_kib, call)
        else:
            quota = get_quota(args.mount, args.uid, call)
    except QuotaError as exc:
        sys.stderr.write(f"tmp_quota: {exc}\n")
        return 1
    sys.stdout.write(f"{quota.limit_kib} {quota.used_kib}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
