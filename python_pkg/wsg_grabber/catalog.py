"""Parsing of the /wsg/ JSON payloads. No network, no filesystem.

The API hands back loosely-typed JSON where file fields are simply absent on
posts without an attachment, so every accessor here treats a missing or
wrong-typed field as "not a video" rather than trusting the shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber._coerce import as_int, as_list, as_md5, get
from python_pkg.wsg_grabber.constants import MEDIA_HOST, VIDEO_EXTENSIONS
from python_pkg.wsg_grabber.models import RemoteFile, ThreadRef

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


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
    for page in as_list(payload):
        for entry in as_list(get(page, "threads")):
            thread_no = as_int(get(entry, "no"))
            if thread_no is None:
                continue
            refs.append(
                ThreadRef(
                    thread_no=thread_no,
                    api_last_modified=as_int(get(entry, "last_modified")) or 0,
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
    for entry in as_list(payload):
        thread_no = as_int(entry)
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
    for post in as_list(get(payload, "posts")):
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
    for post in as_list(get(payload, "posts")):
        if not as_int(get(post, "filedeleted")):
            continue
        digest = as_md5(get(post, "md5"))
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
    if as_int(get(post, "filedeleted")):
        return None
    tim = as_int(get(post, "tim"))
    ext = get(post, "ext")
    digest = as_md5(get(post, "md5"))
    post_no = as_int(get(post, "no"))
    if tim is None or post_no is None or digest is None:
        return None
    if not isinstance(ext, str) or ext not in VIDEO_EXTENSIONS:
        return None
    name = get(post, "filename")
    return RemoteFile(
        md5=digest,
        tim=tim,
        ext=ext,
        orig_name=name if isinstance(name, str) else str(tim),
        fsize=as_int(get(post, "fsize")) or 0,
        width=as_int(get(post, "w")) or 0,
        height=as_int(get(post, "h")) or 0,
        thread_no=thread_no,
        post_no=post_no,
    )
