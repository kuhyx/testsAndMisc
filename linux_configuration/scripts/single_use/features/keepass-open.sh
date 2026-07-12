#!/bin/bash
# keepass-open.sh — open the KeePass vault with sync, WITHOUT storing the master
# password anywhere. This is the laptop/remote-device entry point: you run this
# instead of clicking KeePassXC directly.
#
# Flow (the master password lives only in this process's memory):
#   1. prompt for the vault master password
#   2. consolidate any stray *.kdbx on this device into the one canonical vault
#   3. reconcile with the cloud (pull remote + merge + push local) — bidirectional
#   4. launch KeePassXC on the local vault and wait
#   5. on close, reconcile once more so this session's edits are published
#
# The dufs *server* password (transport only, not the vault key) comes from the
# keyring. Config is read from ~/.config/keepass-sync/config.env (written by
# setup_keepass_sync.sh). Self-contained; runs on Arch or Ubuntu.

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
readonly SYNC="$HERE/keepass_sync.sh"
readonly CONSOLIDATE="$HERE/keepass_consolidate.sh"
readonly CONFIG="${KP_SYNC_CONFIG:-$HOME/.config/keepass-sync/config.env}"

log() { printf '\033[1;34m[keepass-open]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[keepass-open] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f "$CONFIG" ]] || die "config $CONFIG missing — run setup_keepass_sync.sh first"
# shellcheck source=/dev/null
source "$CONFIG"
: "${LOCAL_DB:?LOCAL_DB not set in config}"
command -v keepassxc >/dev/null || die "keepassxc (GUI) not found"

# If KeePassXC is already running, our "wait then push on close" won't work
# (the new invocation just focuses the existing window and returns immediately).
if pgrep -x keepassxc >/dev/null 2>&1; then
	WARN() { printf '\033[1;33m[keepass-open] !\033[0m %s\n' "$*"; }
	WARN "KeePassXC is already running — close it first so edits publish on exit."
fi

# Prompt for the master password (never echoed, never written to disk).
read -r -s -p "KeePass master password: " KP_MASTER_PW; echo
[[ -n "$KP_MASTER_PW" ]] || die "no password entered"
export KP_MASTER_PW

# 2 + 3: consolidate strays, then reconcile with the cloud (pull+merge+push).
log "consolidating strays and syncing with the cloud…"
KP_CANONICAL="$LOCAL_DB" bash "$CONSOLIDATE" --canonical "$LOCAL_DB" || log "consolidation reported an issue (continuing)"
bash "$SYNC" || die "initial sync failed — NOT opening a possibly-stale vault"

# 4: open KeePassXC and wait until it is closed.
log "opening KeePassXC…"
keepassxc "$LOCAL_DB" || true

# 5: publish this session's edits.
log "closing — publishing your changes…"
bash "$SYNC" || log "final sync failed; changes will publish on next open"

unset KP_MASTER_PW
log "done."
