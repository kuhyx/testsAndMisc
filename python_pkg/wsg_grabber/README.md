# wsg_grabber

Scrapes 4chan's /wsg/ board for videos, downloads every one it has not seen
before, and shows them one at a time for a keep/pass decision — mpv embedded in
a Tk window with the buttons directly underneath.

```bash
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber          # review
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber scrape   # no UI
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber stats
```

`k` / `→` keeps, `j` / `space` / `←` passes, `u` / `Backspace` undoes, `q` /
`Esc` quits. The buttons do the same thing for the mouse.

## Undo

Misclicked? `u` takes the last verdict back: the file returns from `keep/` or
`trash/` to `incoming/`, the index row goes back to _ready_, the counter is
corrected, and that video is on screen again. Whatever was showing when you hit
undo goes to the front of the queue, so nothing is skipped.

It steps back through **any number of verdicts, and survives quitting** — the
trail lives in the index, not in memory, so reopening the reviewer can still
undo what you decided yesterday. The status bar shows how many are left
(`u undoes (17)`), and the button greys out when there is nothing to take back.
If you cleared `trash/` by hand in the meantime, undo says so in the log and
drops that entry rather than failing on it repeatedly.

## Storage

```
~/.local/share/wsg_grabber/
├── index.db     sqlite, remembers every file ever seen
├── incoming/    downloaded, awaiting your verdict
├── keep/        you kept these
└── trash/       you passed on these — NOTHING here is ever removed automatically
```

**No downloaded video is ever deleted.** A pass moves the file into `trash/`;
emptying it is your call. `unlink` appears only on things that are not videos —
a corrupt or abandoned `.part`, and mpv's control socket — and `files.apply_move`
refuses to overwrite an existing destination, so a move can never destroy a
video you already decided on.

## Why it never shows you the same video twice

Every 4chan post that carries a file also carries `md5` — the base64 MD5 of the
whole file, published by the API before you fetch anything. That is the primary
key of the `files` table, so:

- a video you have already reviewed is never downloaded again, at a cost of
  zero bytes;
- the same clip reposted in another thread collapses onto the existing row,
  which on /wsg/ is the common case;
- a truncated or mangled download is caught, because the bytes are checked
  against that same value before the file is offered for review.

Verified against a live file during development: the API's
`Nz9OEKdMuMZEdYE6eLTKmA==` matched `base64(md5(bytes))` exactly.

## Being a good citizen

- One request per second to `a.4cdn.org`, which is what the API rules ask for.
- `If-Modified-Since` on every API request — thread bodies, `threads.json` and
  `archive.json` alike — plus a `last_modified` comparison against the stored
  value, so an unchanged thread costs a 304 and nothing else. A steady-state
  rescan is a couple of conditional requests that return 304.
- `Accept-Encoding: identity` on both hosts, and hard caps on response and
  download size. A compressed response is refused outright: a few hundred KB on
  the wire can decode to gigabytes, and the md5 check does not help when the
  same party publishes both the bytes and the digest.
- One long-lived `requests.Session`. This is required rather than merely tidy:
  `i.4cdn.org` answers with 429 under load and sets `__cf_bm` / `_cfuvid`
  cookies that have to persist across requests.
- 429 and 5xx back off exponentially, honouring `Retry-After`.

## Downloading is prioritised over indexing

While anything is queued the worker downloads rather than walking more threads.
That is deliberate: it is what puts a playable video on screen seconds after
launch instead of after the whole board has been catalogued. The consequence is
that `stats` shows the known-file count climbing in bursts rather than smoothly
— the board is fully indexed once downloads drain. A first full run is roughly
9,000 files and 20–25 GB, so expect a couple of hours; it is resumable and
restarting picks up mid-file via HTTP `Range`.

## Logs

Every run writes one JSON object per line to
`~/.local/share/wsg_grabber/logs/session-<time>-<pid>.jsonl`.

```bash
wsg-grabber logs                # where they are, plus a tally of the newest
wsg-grabber --log-level debug   # record every IPC command as well
wsg-grabber --echo-log          # mirror records to stderr while running
```

The point is after-the-fact diagnosis. If the reviewer ever looks stuck on one
video while the filenames keep advancing, one query settles whether mpv was
handed the new file and was actually decoding it:

```bash
LOG=$(ls -t ~/.local/share/wsg_grabber/logs/*.jsonl | head -1)
jq -r 'select(.event=="review.show")
       | "show \(.file)  mpv_was: \(.mpv_before.path) t=\(.mpv_before["playback-time"]) \(.mpv_before.width)x\(.mpv_before.height)"' "$LOG"
```

A healthy run shows `playback-time` advancing and the dimensions changing per
video. A frozen one shows them static, which points at the player rather than
at the queue. Other useful queries:

```bash
jq -c 'select(.level=="error")' "$LOG"                          # what went wrong
jq -r 'select(.event=="review.verdict")|"\(.choice) \(.on_file)"' "$LOG"
jq -c 'select(.event|startswith("player."))' "$LOG"
```

Field names are stable; every record carries `ts`, `seq`, `level`, `event` and
`thread`.

## Debugging without touching your queue

`paths` honours `XDG_DATA_HOME`, so a throwaway instance costs nothing and can
neither consume real videos nor record real verdicts:

```bash
XDG_DATA_HOME=/tmp/wsg-sandbox python3 -m python_pkg.wsg_grabber stats
```

## Layout

| Module              | Responsibility                                                    |
| ------------------- | ----------------------------------------------------------------- |
| `catalog.py`        | Parses the board's JSON. Pure.                                    |
| `scanner.py`        | Scheduling, backoff, resume decisions. Pure.                      |
| `review.py`         | Everything the reviewer does: queue, verdicts, status text. Pure. |
| `verdict.py`        | What keep/pass means, as a planned file move. Pure.               |
| `net.py`            | The only module that speaks HTTP.                                 |
| `db.py`             | sqlite schema, connection setup, migrations.                      |
| `store.py`          | The download lifecycle of a file.                                 |
| `store_threads.py`  | Which threads were visited, and their HTTP stamps.                |
| `store_verdicts.py` | The review trail that undo walks back.                            |
| `downloader.py`     | The background worker thread.                                     |
| `files.py`          | The only module that moves files.                                 |
| `player.py`         | mpv as a subprocess over its JSON IPC socket.                     |
| `ui.py`             | The only module that imports `tkinter`.                           |
| `logs.py`           | Structured JSONL event log.                                       |
| `app.py` / `cli.py` | Composition and argument parsing.                                 |

The split is what makes 100% branch coverage achievable: `ui.py` and
`player.py` are close to pure wiring, and every decision they would otherwise
make lives in a pure function tested from plain values with no display and no
network. Two decisions do remain in `ui.py`, both because a bug proved they had
to: the already-playing guard (without it `loadfile` fires every tick and the
video restarts continuously) and dropping an item whose file has vanished.

## mpv is a subprocess, not `python-mpv`

`python-mpv` resolves `libmpv` at _import_ time and raises `OSError` wherever it
is missing — including this repo's CI runner, so it would pass locally and fail
on push. Driving `mpv --wid=<frame> --input-ipc-server=<socket>` over a unix
socket needs only `subprocess`, `socket` and `json`.

**The socket must be drained.** mpv pushes an asynchronous event stream plus a
reply per command down the same connection. A client that only ever writes lets
that backlog fill the kernel buffer, at which point mpv's writer for that
connection blocks and it stops reading commands. Nothing errors: `sendall` still
succeeds, mpv stays alive and keeps playing whatever it had, so the reviewer
advances through filenames while the picture never changes. Measured: commands
were silently ignored from about the thirty-fifth video onwards, and the very
same command sent on a fresh connection worked instantly. `player.py` therefore
runs a reader thread whose only job is to drain — deleting it reintroduces the
freeze roughly half an hour into a session.

Two more mpv details worth knowing if you touch `ui.py`:

- `--wid` does not draw into your widget. mpv creates its own X window and
  reparents it onto the frame, covering it completely — which is why the
  control bar is packed _below_ the video rather than over it.
- `--input-vo-keyboard=no` is what lets the Tk key bindings fire at all. Without
  it mpv's child window takes keyboard focus and Tk never sees a keypress.

## Requirements

`mpv` and `tk` (system packages, installed by `install.sh`) and `requests`,
which the repo already declares. Nothing else.
