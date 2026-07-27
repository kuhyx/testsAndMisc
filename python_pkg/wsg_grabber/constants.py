"""Fixed configuration for the /wsg/ grabber.

Values here are deliberately plain data so the pure planning helpers in
:mod:`python_pkg.wsg_grabber.scanner` can be exercised without touching the
network, the filesystem or a display.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

BOARD: Final[str] = "wsg"
# The only board this tool targets.

API_HOST: Final[str] = "https://a.4cdn.org"
MEDIA_HOST: Final[str] = "https://i.4cdn.org"
BOARDS_URL: Final[str] = "https://boards.4chan.org/"

THREADS_URL: Final[str] = f"{API_HOST}/{BOARD}/threads.json"
ARCHIVE_URL: Final[str] = f"{API_HOST}/{BOARD}/archive.json"

VIDEO_EXTENSIONS: Final[frozenset[str]] = frozenset({".webm", ".mp4", ".gif"})
# /wsg/ serves all three. A live catalogue sample was 55% webm, 37% mp4, 8%
# gif, so filtering to {".webm", ".gif"} would silently drop a third of it.

# i.4cdn.org answers a bare request with 429 once it has seen a burst, so the
# session presents itself as a browser following a link from the board. The
# cookies 4chan sets in response (``__cf_bm``, ``_cfuvid``) are why a single
# long-lived Session is mandatory rather than merely efficient.
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
API_HEADERS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # Ask for no compression so a hostile or compromised host cannot turn a
        # few hundred KB on the wire into gigabytes of decoded JSON.
        "Accept-Encoding": "identity",
        "Referer": BOARDS_URL,
    },
)
MEDIA_HEADERS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "User-Agent": USER_AGENT,
        "Accept": "video/webm,video/mp4,image/gif,video/*;q=0.9,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
        # Never gzip a webm: it cannot compress and it breaks Range resumption.
        "Accept-Encoding": "identity",
        "Referer": BOARDS_URL,
        "Sec-Fetch-Dest": "video",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    },
)

MIN_REQUEST_INTERVAL_S: Final[float] = 1.0
# The 4chan API rules state at most one request per second.

BACKOFF_BASE_S: Final[float] = 2.0
BACKOFF_CAP_S: Final[float] = 120.0
MAX_ATTEMPTS: Final[int] = 3
# Download attempts before a file is written off as ``gone``.

CONNECT_TIMEOUT_S: Final[float] = 10.0
READ_TIMEOUT_S: Final[float] = 30.0
CHUNK_BYTES: Final[int] = 65536

# Refuse an API response larger than this; the real ones are ~300 KB.
MAX_JSON_BYTES: Final[int] = 32 * 1024 * 1024

# How far a download may exceed its advertised size before it is abandoned.
SIZE_SLACK_BYTES: Final[int] = 1024 * 1024

SCHEMA_VERSION: Final[int] = 3
DB_TIMEOUT_S: Final[float] = 30.0
DB_BUSY_TIMEOUT_MS: Final[int] = 5000

POLL_INTERVAL_MS: Final[int] = 150
# How often the Tk loop drains the downloader's event queue.

IDLE_POLL_S: Final[float] = 1.0
# How long the worker sleeps per tick once the board is exhausted.

IDLE_RESCAN_S: Final[float] = 60.0
# How long a finished sweep stays quiet before the board is walked again.

JOIN_TIMEOUT_S: Final[float] = 10.0
IPC_READY_TIMEOUT_S: Final[float] = 10.0

CONTROL_BAR_HEIGHT_PX: Final[int] = 96
WINDOW_WIDTH_PX: Final[int] = 1100
WINDOW_HEIGHT_PX: Final[int] = 800

KEEP_KEYS: Final[tuple[str, ...]] = ("<k>", "<Right>")
PASS_KEYS: Final[tuple[str, ...]] = ("<j>", "<space>", "<Left>")
UNDO_KEYS: Final[tuple[str, ...]] = ("<u>", "<BackSpace>")
QUIT_KEYS: Final[tuple[str, ...]] = ("<q>", "<Escape>")
