"""Import RunnerUp activity files into Endurain, exactly once each.

Run from a systemd user timer. Configuration comes from the environment:

    ENDURAIN_URL        base URL (default http://127.0.0.1:8085)
    ENDURAIN_API_KEY    API key with the activities:upload scope (required)
    ENDURAIN_INBOX      WebDAV inbox (default ~/cloud/RunnerUp)
    ENDURAIN_STATE      ledger directory (default ~/.local/state/endurain-import)
    ENDURAIN_BULK_DIR   bulk_import dir for files the server rejected
    ENDURAIN_NO_ADB     set to 1 to disable the phone fallback

Exit status is 0 only when every file was accounted for; anything left in an
ambiguous state exits non-zero so the timer surfaces it rather than logging
quietly and moving on.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import sys

import requests

from python_pkg.endurain_import.ledger import (
    Entry,
    Ledger,
    activity_key,
    file_digest,
    now_iso,
)
from python_pkg.endurain_import.sources import inbox_files, pull_from_phone
from python_pkg.endurain_import.upload import EndurainClient, Outcome, SupportsUpload

_logger = logging.getLogger("endurain_import")

_DEFAULT_URL = "http://127.0.0.1:8085"
_DEFAULT_INBOX = Path.home() / "cloud" / "RunnerUp"
_DEFAULT_STATE = Path.home() / ".local" / "state" / "endurain-import"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _require_api_key() -> str:
    key = os.environ.get("ENDURAIN_API_KEY", "").strip()
    if not key:
        _logger.error(
            "ENDURAIN_API_KEY is not set. Create one in Endurain under "
            "Settings -> Security -> API Keys with the activities:upload scope."
        )
        raise SystemExit(2)
    return key


def _route_rejected(path: Path, bulk_dir: Path | None) -> None:
    """Copy a server-rejected file into bulk_import for manual recovery.

    Only ever called for a definite 4xx. Ambiguous failures must not land here:
    Endurain would import them a second time if the first attempt had in fact
    been committed.
    """
    if bulk_dir is None:
        _logger.warning("no bulk_import dir configured; leaving %s", path.name)
        return
    try:
        bulk_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, bulk_dir / path.name)
        _logger.warning("copied %s to bulk_import for manual retry", path.name)
    except OSError:
        _logger.exception("could not stage %s for bulk import", path.name)


def _process(
    path: Path,
    client: SupportsUpload,
    ledger: Ledger,
    processed_dir: Path,
    bulk_dir: Path | None,
) -> str:
    """Import one file. Returns one of: skipped, imported, rejected, ambiguous."""
    digest = file_digest(path)
    key = activity_key(path)
    # Two independent dedupe checks. The digest catches the identical file
    # arriving twice; the activity key catches the SAME RUN arriving as both
    # .gpx and .tcx, whose bytes differ and which Endurain would otherwise
    # import as two separate activities.
    if digest in ledger or ledger.has_activity(key):
        processed_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(processed_dir / path.name))
        _logger.info("%s already imported; moved to processed/", path.name)
        return "skipped"

    result = client.upload(path)
    if result.outcome is Outcome.OK:
        ledger.record(Entry(digest, key, path.name, result.activity_id, now_iso()))
        processed_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(processed_dir / path.name))
        _logger.info("imported %s (activity_id=%s)", path.name, result.activity_id)
        return "imported"

    if result.outcome is Outcome.REJECTED:
        _logger.error("rejected %s -- %s", path.name, result.detail)
        _route_rejected(path, bulk_dir)
        return "rejected"

    # Ambiguous: leave the file exactly where it is and do NOT record it.
    _logger.error(
        "ambiguous outcome for %s -- %s. Left in the inbox; verify in Endurain "
        "before the next run to avoid a duplicate.",
        path.name,
        result.detail,
    )
    return "ambiguous"


def main() -> int:
    """Run one import pass. Returns the process exit status."""
    _configure_logging()
    api_key = _require_api_key()
    base_url = os.environ.get("ENDURAIN_URL", _DEFAULT_URL)
    inbox = Path(os.environ.get("ENDURAIN_INBOX", _DEFAULT_INBOX))
    state = Path(os.environ.get("ENDURAIN_STATE", _DEFAULT_STATE))
    bulk = os.environ.get("ENDURAIN_BULK_DIR")
    bulk_dir = Path(bulk) if bulk else None

    client = EndurainClient(base_url, api_key)
    try:
        client.about()
    # requests.RequestException covers the transport failures; OSError/ValueError
    # cover a malformed response body. ConnectionError subclasses OSError, so a
    # separate requests handler would be unreachable.
    except (OSError, ValueError, RuntimeError, requests.RequestException):
        _logger.exception("Endurain is not reachable at %s", base_url)
        return 1

    ledger = Ledger(state / "ledger.json")
    processed_dir = inbox / "processed"

    if os.environ.get("ENDURAIN_NO_ADB") != "1":
        pull_from_phone(inbox)

    # TCX carries more than GPX (laps, cadence, HR), so when a run is present
    # in both formats the TCX must be the one that wins the dedupe race.
    pending = sorted(inbox_files(inbox), key=lambda p: p.suffix.lower() != ".tcx")
    if not pending:
        _logger.info("nothing to import (ledger holds %d file(s))", len(ledger))
        return 0

    counts = {"skipped": 0, "imported": 0, "rejected": 0, "ambiguous": 0}
    for path in pending:
        counts[_process(path, client, ledger, processed_dir, bulk_dir)] += 1

    _logger.info(
        "done: %(imported)d imported, %(skipped)d already known, "
        "%(rejected)d rejected, %(ambiguous)d ambiguous",
        counts,
    )
    # Fail closed so the timer reports a problem instead of hiding it.
    return 1 if counts["ambiguous"] or counts["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main())
