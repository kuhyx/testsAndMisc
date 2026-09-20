#!/usr/bin/env python3
"""Re-encrypt keyring-bound (v11) Chromium passwords as basic-store (v10).

Why: lightdm autologin leaves gnome-keyring locked, so a Chromium-family
browser that finds its "Safe Storage" key in the keyring prompts to unlock it
on every launch. Running Helium with ``--password-store=basic`` stops that,
but ``v11`` rows (encrypted with the keyring key) become unreadable — and
Chromium deletes undecryptable logins on read. This converts them first.

Linux os_crypt scheme (unchanged since Chromium 4x): key = PBKDF2-HMAC-SHA1
(secret, "saltysalt", 1 iter, 16 B); AES-128-CBC, IV = 16 spaces, PKCS#7;
``v11`` uses the keyring secret, ``v10`` uses the fixed string "peanuts".

Needs the keyring unlocked ONCE: it asks the Secret Service to unlock the
default collection, which pops the gcr dialog. Browser must be closed.
Never prints a secret.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import secretstorage

DEFAULT_PROFILE = Path.home() / ".config" / "net.imput.helium" / "Default"
KEYRING_SCHEMA = "chrome_libsecret_os_crypt_password_v2"
SALT = b"saltysalt"
IV = b" " * 16
KEY_LEN = 16
BASIC_SECRET = b"peanuts"
V10 = b"v10"
V11 = b"v11"
# Anchored: a shell whose argv merely mentions the path must not match.
HELIUM_PROCESS_MARK = "^/opt/helium-browser-bin/"
FLAGS_FILE = Path.home() / ".config" / "helium-browser-flags.conf"
BASIC_FLAG = "--password-store=basic"


def say(msg: str, *, err: bool = False) -> None:
    """Write one line to stdout (or stderr); explicit so lint autofix cannot drop it."""
    (sys.stderr if err else sys.stdout).write(msg + "\n")


def derive_key(secret: bytes) -> bytes:
    """Chromium's os_crypt Linux KDF."""
    return hashlib.pbkdf2_hmac("sha1", secret, SALT, 1, KEY_LEN)


def decrypt(key: bytes, blob: bytes) -> bytes:
    """AES-128-CBC + PKCS#7 strip; ``blob`` is the payload after the 3-byte tag."""
    dec = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    padded = dec.update(blob) + dec.finalize()
    unpad = padding.PKCS7(algorithms.AES.block_size).unpadder()
    return unpad.update(padded) + unpad.finalize()


def encrypt(key: bytes, plain: bytes) -> bytes:
    """Inverse of :func:`decrypt`, without the tag."""
    pad = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = pad.update(plain) + pad.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor()
    return enc.update(padded) + enc.finalize()


def keyring_secret(application: str) -> bytes:
    """Unlock the default keyring (this pops the gcr dialog) and read the key.

    One D-Bus connection for the whole exchange: Secret Service prompt objects
    live only as long as the connection that created them, which is why a
    `secret-tool`/`busctl` sequence of separate processes can never work.
    """
    conn = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(conn)
    if collection.is_locked():
        say("keyring is locked — answer the unlock dialog on screen")
        if collection.unlock():  # True means the dialog was dismissed
            msg = "unlock dialog dismissed; keyring still locked"
            raise SystemExit(msg)
    for attrs in (
        {"xdg:schema": KEYRING_SCHEMA, "application": application},
        {"xdg:schema": KEYRING_SCHEMA},
    ):
        items = list(collection.search_items(attrs))
        if items:
            return items[0].get_secret()
    msg = f"no {KEYRING_SCHEMA} item in the default keyring"
    raise SystemExit(msg)


def browser_running() -> bool:
    """SQLite writes under a live browser are lost or corrupt the DB."""
    res = subprocess.run(
        ["/usr/bin/pgrep", "-f", HELIUM_PROCESS_MARK], capture_output=True, check=False
    )
    return res.returncode == 0


def migrate(
    db: Path, ring_key: bytes, basic_key: bytes, *, dry_run: bool
) -> tuple[int, int]:
    """Rewrite every v11 row in ``logins`` as v10; return (converted, already_v10)."""
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("SELECT id, password_value FROM logins").fetchall()
        converted = already = 0
        for row_id, blob in rows:
            if blob[:3] == V10:
                already += 1
                continue
            if blob[:3] != V11:
                say(f"  row {row_id}: unknown tag {blob[:3]!r}, left alone", err=True)
                continue
            plain = decrypt(ring_key, blob[3:])
            new_blob = V10 + encrypt(basic_key, plain)
            if decrypt(basic_key, new_blob[3:]) != plain:
                msg = f"row {row_id}: round-trip mismatch, aborting before any write"
                raise SystemExit(msg)
            if not dry_run:
                conn.execute(
                    "UPDATE logins SET password_value = ? WHERE id = ?",
                    (new_blob, row_id),
                )
            converted += 1
        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return converted, already


def enable_basic_store() -> None:
    """Append the flag Helium's wrapper reads — only after the rows are converted.

    Written here rather than by the installer so a restart can never happen
    between "flag on" and "rows converted": with the flag on and v11 rows
    still present, Chromium would treat them as undecryptable and delete them.
    """
    existing = FLAGS_FILE.read_text() if FLAGS_FILE.exists() else ""
    if BASIC_FLAG in existing.split():
        return
    with FLAGS_FILE.open("a") as fh:
        fh.write(f"{BASIC_FLAG}\n")
    say(f"added {BASIC_FLAG} to {FLAGS_FILE}")


def parse_args() -> argparse.Namespace:
    """CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="profile dir holding 'Login Data'",
    )
    parser.add_argument(
        "--application",
        default="chromium",
        help="keyring item's 'application' attribute",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="decrypt + verify only, write nothing"
    )
    return parser.parse_args()


def main() -> int:
    """Back up, convert, report counts."""
    args = parse_args()
    db = args.profile / "Login Data"
    if not db.is_file():
        say(f"no such file: {db}", err=True)
        return 2
    if browser_running():
        say("Helium is running — close it first, then rerun.", err=True)
        return 3
    ring_key = derive_key(keyring_secret(args.application))
    basic_key = derive_key(BASIC_SECRET)
    if not args.dry_run:
        backup = db.with_name(f"Login Data.pre-basic-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(db, backup)
        say(f"backup: {backup}")
    converted, already = migrate(db, ring_key, basic_key, dry_run=args.dry_run)
    verb = "would convert" if args.dry_run else "converted"
    say(f"{verb} {converted} v11 -> v10 rows; {already} already v10")
    if not args.dry_run:
        enable_basic_store()
    return 0


if __name__ == "__main__":
    sys.exit(main())
