"""Scrape 4chan's /wsg/ board and triage its videos with a keep/pass reviewer.

The board exposes a read-only JSON API whose post records carry ``md5`` --
``base64(md5(file_bytes))`` over the whole file. That single field is why this
package can honour "never show me the same video twice" without spending a byte:
dedupe happens against the catalogue, before any download starts, and reposts of
an identical file across threads collapse onto one row for free.

Nothing here ever deletes a file. A "pass" verdict moves the video to
``trash/`` and leaves it for the user to clear by hand.
"""

from __future__ import annotations
