"""Parsing of the /wsg/ JSON payloads. No network, no filesystem.

The API hands back loosely-typed JSON where file fields are simply absent on
posts without an attachment, so every accessor here treats a missing or
wrong-typed field as "not a video" rather than trusting the shape.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from python_pkg.wsg_grabber.constants import MEDIA_HOST, VIDEO_EXTENSIONS
from python_pkg.wsg_grabber.models import RemoteFile, ThreadRef

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

# base64 of a 16-byte digest is always 22 characters plus "==". Matching the
# exact shape -- not merely the length -- is what keeps a NUL byte out of a
# filename: one such value poisons the index permanently, because the crash
# happens before the row can ever be marked gone.
_MD5_SHAPE = re.compile(r"[A-Za-z0-9+/]{22}==")

# sqlite stores signed 64-bit integers; anything wider raises OverflowError deep
# inside executemany, which used to take the worker thread down with it.
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


def media_url(tim: int, ext: str) -> str:
    """Return the CDN address of an attachment.

    Args:
        tim: The post's ``tim`` field, which is the CDN filename stem.
        ext: Extension including the leading dot.

    Returns:
        str: Absolute URL on the media host.
    """
    return f"{MEDIA_HOST}/wsg/{tim}{ext}"


def parse_thread_list(payload: object) -> list[ThreadRef]:
    """Flatten ``threads.json`` into thread references.

    Args:
        payload: Decoded JSON: a list of pages, each with a ``threads`` list.

    Returns:
        list[ThreadRef]: Every advertised thread, in page order.
    """
    refs: list[ThreadRef] = []
    for page in _as_list(payload):
        for entry in _as_list(_get(page, "threads")):
            thread_no = _as_int(_get(entry, "no"))
            if thread_no is None:
                continue
            refs.append(
                ThreadRef(
                    thread_no=thread_no,
                    api_last_modified=_as_int(_get(entry, "last_modified")) or 0,
                ),
            )
    return refs


def parse_archive(payload: object) -> list[ThreadRef]:
    """Turn ``archive.json`` into thread references.

    The archive is a bare list of thread numbers with no timestamps, so each
    gets a zero stamp; they are immutable anyway and only need fetching once.

    Args:
        payload: Decoded JSON list of integers.

    Returns:
        list[ThreadRef]: Archived threads.
    """
    refs: list[ThreadRef] = []
    for entry in _as_list(payload):
        thread_no = _as_int(entry)
        if thread_no is not None:
            refs.append(ThreadRef(thread_no=thread_no, api_last_modified=0))
    return refs


def parse_thread(thread_no: int, payload: object) -> list[RemoteFile]:
    """Extract every video attachment from one thread payload.

    Posts whose file was deleted upstream are skipped: there is nothing left to
    fetch, and they must not be recorded as pending work.

    Args:
        thread_no: The thread being parsed, used to stamp each file.
        payload: Decoded ``thread/<no>.json``.

    Returns:
        list[RemoteFile]: Attachments with a video extension.
    """
    files: list[RemoteFile] = []
    for post in _as_list(_get(payload, "posts")):
        parsed = _parse_post(thread_no, post)
        if parsed is not None:
            files.append(parsed)
    return files


def deleted_md5s(payload: object) -> set[str]:
    """Return md5s of posts whose attachment was removed upstream.

    Args:
        payload: Decoded ``thread/<no>.json``.

    Returns:
        set[str]: Identities that should be written off rather than retried.
    """
    gone: set[str] = set()
    for post in _as_list(_get(payload, "posts")):
        if not _as_int(_get(post, "filedeleted")):
            continue
        digest = _as_md5(_get(post, "md5"))
        if digest is not None:
            gone.add(digest)
    return gone


def new_files(
    parsed: Iterable[RemoteFile],
    known: Sequence[str] | set[str] | frozenset[str],
) -> list[RemoteFile]:
    """Drop attachments already present in the index.

    This is where "never download the same video twice" is enforced, and it
    happens before a single byte is transferred because the API supplies the
    md5 up front.

    Args:
        parsed: Candidates from a thread.
        known: md5s already recorded, in any state including terminal ones.

    Returns:
        list[RemoteFile]: Genuinely new attachments, deduped within the batch.
    """
    seen = set(known)
    fresh: list[RemoteFile] = []
    for item in parsed:
        if item.md5 in seen:
            continue
        seen.add(item.md5)
        fresh.append(item)
    return fresh


def _parse_post(thread_no: int, post: object) -> RemoteFile | None:
    """Turn one post into a RemoteFile when it carries a usable video.

    Args:
        thread_no: Owning thread.
        post: Decoded post object.

    Returns:
        RemoteFile | None: None when the post has no video attachment.
    """
    if _as_int(_get(post, "filedeleted")):
        return None
    tim = _as_int(_get(post, "tim"))
    ext = _get(post, "ext")
    digest = _as_md5(_get(post, "md5"))
    post_no = _as_int(_get(post, "no"))
    if tim is None or post_no is None or digest is None:
        return None
    if not isinstance(ext, str) or ext not in VIDEO_EXTENSIONS:
        return None
    name = _get(post, "filename")
    return RemoteFile(
        md5=digest,
        tim=tim,
        ext=ext,
        orig_name=name if isinstance(name, str) else str(tim),
        fsize=_as_int(_get(post, "fsize")) or 0,
        width=_as_int(_get(post, "w")) or 0,
        height=_as_int(_get(post, "h")) or 0,
        thread_no=thread_no,
        post_no=post_no,
    )


def _get(container: object, key: str) -> object:
    """Read *key* from *container* when it is a mapping.

    Args:
        container: Anything; only dicts yield a value.
        key: Key to read.

    Returns:
        object: The value, or None.
    """
    if isinstance(container, dict):
        return container.get(key)
    return None


def _as_list(value: object) -> list[Any]:
    """Return *value* when it is a list, else an empty list.

    Args:
        value: Candidate.

    Returns:
        list[Any]: Safe list to iterate.
    """
    return value if isinstance(value, list) else []


def _as_int(value: object) -> int | None:
    """Coerce *value* to int when it is a real integer.

    Booleans are rejected: ``True`` is an int in Python but never a valid post
    number or timestamp. Values outside sqlite's signed 64-bit range are
    rejected too -- they raise OverflowError on insert, which is not in the
    worker's recoverable set and would kill it silently.

    Args:
        value: Candidate.

    Returns:
        int | None: The integer, or None.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if _INT64_MIN <= value <= _INT64_MAX else None


def _as_md5(value: object) -> str | None:
    """Validate the API's base64 md5 field.

    The charset check is not decoration: the tail of this value ends up in a
    filename via ``store.local_name``, and it arrives from an anonymous
    imageboard. Length alone would let through a NUL byte, which raises deep
    inside the filesystem call instead of being rejected here.

    Args:
        value: Candidate.

    Returns:
        str | None: The 24-character digest, or None when malformed.
    """
    if not isinstance(value, str):
        return None
    return value if _MD5_SHAPE.fullmatch(value) else None
