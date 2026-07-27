"""Tests for parsing the /wsg/ JSON payloads.

Fixtures mirror the shape of real responses captured from the live API,
including the fields that are simply absent on text-only posts.
"""

from __future__ import annotations

from python_pkg.wsg_grabber import catalog

_WEBM = "Nz9OEKdMuMZEdYE6eLTKmA=="
_MP4 = "b9EO3Kaq7PHBgc6kWmHgew=="


def _post(**overrides: object) -> dict[str, object]:
    """Build a post carrying a webm attachment.

    Args:
        **overrides: Fields to replace or, with a None value, remove.

    Returns:
        dict[str, object]: Post payload.
    """
    post: dict[str, object] = {
        "no": 6195878,
        "resto": 0,
        "tim": 1784059525831380,
        "ext": ".webm",
        "filename": "kino moment",
        "fsize": 1008689,
        "md5": _WEBM,
        "w": 480,
        "h": 360,
    }
    post.update(overrides)
    return {key: value for key, value in post.items() if value is not None}


def test_media_url_uses_tim_not_the_poster_filename() -> None:
    assert (
        catalog.media_url(1784059525831380, ".webm")
        == "https://i.4cdn.org/wsg/1784059525831380.webm"
    )


def test_parse_thread_list_flattens_every_page() -> None:
    payload = [
        {"page": 1, "threads": [{"no": 1, "last_modified": 100, "replies": 2}]},
        {"page": 2, "threads": [{"no": 2, "last_modified": 200, "replies": 5}]},
    ]
    refs = catalog.parse_thread_list(payload)
    assert [(ref.thread_no, ref.api_last_modified) for ref in refs] == [
        (1, 100),
        (2, 200),
    ]


def test_parse_thread_list_survives_malformed_payloads() -> None:
    assert catalog.parse_thread_list("not a list") == []
    assert catalog.parse_thread_list([{"threads": "nope"}]) == []
    assert catalog.parse_thread_list([{"threads": [{"no": None}]}]) == []
    assert catalog.parse_thread_list([{"threads": [{"no": True}]}]) == []
    refs = catalog.parse_thread_list([{"threads": [{"no": 5}]}])
    assert refs[0].api_last_modified == 0


def test_parse_archive_reads_bare_thread_numbers() -> None:
    refs = catalog.parse_archive([11, 22, "junk", None])
    assert [ref.thread_no for ref in refs] == [11, 22]
    assert refs[0].api_last_modified == 0


def test_parse_thread_keeps_all_three_video_extensions() -> None:
    payload = {
        "posts": [
            _post(ext=".webm", md5=_WEBM, no=1),
            _post(ext=".mp4", md5=_MP4, no=2),
            _post(ext=".gif", md5="c" * 22 + "==", no=3),
        ],
    }
    files = catalog.parse_thread(99, payload)
    assert [item.ext for item in files] == [".webm", ".mp4", ".gif"]
    assert all(item.thread_no == 99 for item in files)


def test_parse_thread_skips_images_and_text_posts() -> None:
    payload = {
        "posts": [
            {"no": 1, "com": "text only"},
            _post(ext=".jpg", no=2),
            _post(ext=".png", no=3),
            _post(no=4),
        ],
    }
    files = catalog.parse_thread(99, payload)
    assert len(files) == 1
    assert files[0].post_no == 4


def test_parse_thread_skips_deleted_attachments() -> None:
    payload = {"posts": [_post(filedeleted=1)]}
    assert catalog.parse_thread(99, payload) == []


def test_parse_thread_rejects_malformed_file_fields() -> None:
    cases = [
        _post(tim=None),
        _post(no=None),
        _post(md5=None),
        _post(md5="too-short"),
        _post(ext=12345),
    ]
    for post in cases:
        assert catalog.parse_thread(99, {"posts": [post]}) == []


def test_parse_thread_defaults_missing_optional_fields() -> None:
    payload = {"posts": [_post(filename=None, fsize=None, w=None, h=None)]}
    item = catalog.parse_thread(99, payload)[0]
    assert item.orig_name == str(item.tim)
    assert (item.fsize, item.width, item.height) == (0, 0, 0)


def test_parse_thread_survives_a_payload_that_is_not_a_dict() -> None:
    assert catalog.parse_thread(1, "nonsense") == []
    assert catalog.parse_thread(1, {"posts": "nonsense"}) == []
    assert catalog.parse_thread(1, {"posts": ["nonsense"]}) == []


def test_deleted_md5s_collects_removed_attachments() -> None:
    payload = {
        "posts": [
            _post(no=1, filedeleted=1),
            _post(no=2, md5=_MP4),
            _post(no=3, filedeleted=1, md5=None),
        ],
    }
    assert catalog.deleted_md5s(payload) == {_WEBM}


def test_new_files_drops_anything_already_indexed() -> None:
    parsed = catalog.parse_thread(
        1,
        {"posts": [_post(no=1), _post(no=2, md5=_MP4)]},
    )
    fresh = catalog.new_files(parsed, {_WEBM})
    assert [item.md5 for item in fresh] == [_MP4]


def test_new_files_dedupes_within_one_batch() -> None:
    """A file quoted twice in the same thread must only be queued once."""
    parsed = catalog.parse_thread(
        1,
        {"posts": [_post(no=1), _post(no=2, tim=999)]},
    )
    assert len(parsed) == 2
    assert len(catalog.new_files(parsed, set())) == 1


def test_a_hostile_md5_is_rejected_before_it_can_reach_a_filename() -> None:
    """The digest tail ends up in a filename; length alone is not enough."""
    for hostile in ("../.." + "x" * 18, "a" * 23 + "\x00", "/" * 24, "a" * 23 + "\n"):
        assert catalog.parse_thread(1, {"posts": [_post(md5=hostile)]}) == []
    assert catalog.parse_thread(1, {"posts": [_post(md5=_WEBM)]}) != []


def test_an_out_of_range_integer_is_rejected() -> None:
    """Wider than sqlite's signed 64-bit range kills the worker on insert."""
    assert catalog.parse_thread(1, {"posts": [_post(tim=2**63)]}) == []
    assert catalog.parse_thread(1, {"posts": [_post(no=-(2**63) - 1)]}) == []
    assert catalog.parse_thread(1, {"posts": [_post(tim=2**63 - 1)]}) != []
