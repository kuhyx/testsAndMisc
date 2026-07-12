#!/bin/bash
# keepass_sync.sh — bidirectional, merge-safe reconcile of the KeePass vault
# between this device's working copy and the canonical cloud copy.
#
# The vault is a single encrypted file that is NOT multi-writer safe, so a raw
# copy/PUT would clobber concurrent edits. Safety comes from `keepassxc-cli
# merge` (entry-level, timestamp-based, idempotent). This script:
#   1. reads the master password (+ dufs creds) from the OS keyring (secret-tool)
#   2. downloads the remote copy
#   3. backs up the local copy, then merges remote INTO local (local = union)
#   4. uploads the merged local back to remote, guarded by a hash compare-and-swap
#      so a concurrent remote change is never clobbered (it retries instead)
#
# It is self-contained (no repo lib deps) so it runs identically on the Arch PC
# and the Ubuntu work laptop. Triggered by keepass-sync.{path,timer}. Idempotent
# and flock-guarded — safe to run at any time, in parallel invocations queue.
#
# Config (non-secret) is read from $KP_SYNC_CONFIG (default ~/.config/keepass-sync/config.env):
#   LOCAL_DB=/home/<you>/Keepass/Passwords.kdbx
#   REMOTE_MODE=file|webdav
#   REMOTE_FILE=/home/<you>/cloud/Keepass/Passwords.kdbx   # file mode (the PC)
#   REMOTE_URL=https://host/Keepass/Passwords.kdbx          # webdav mode (laptop)
#   DUFS_USER=<user>                                        # webdav mode
# Secrets come from the keyring (service "keepass-sync"):
#   key=master   -> the vault master password
#   key=dufs     -> the dufs web password (webdav mode only)

set -euo pipefail

readonly KP_SYNC_CONFIG="${KP_SYNC_CONFIG:-$HOME/.config/keepass-sync/config.env}"
readonly KEYRING_SERVICE="${KP_KEYRING_SERVICE:-keepass-sync}"
readonly STATE_DIR="${KP_STATE_DIR:-$HOME/.config/keepass-sync}"
readonly LOCKFILE="$STATE_DIR/lock"
readonly MAX_CAS_RETRIES=3

log() { printf '[keepass-sync] %s\n' "$*" >&2; }
die() { printf '[keepass-sync] ERROR: %s\n' "$*" >&2; exit 1; }
# Clean, non-fatal skip (keyring locked / server down) — retried next cycle.
skip() { printf '[keepass-sync] skip: %s\n' "$*" >&2; exit 0; }

# --- load config -------------------------------------------------------------
[[ -f "$KP_SYNC_CONFIG" ]] || die "config not found: $KP_SYNC_CONFIG (run setup_keepass_sync.sh)"
# shellcheck source=/dev/null
source "$KP_SYNC_CONFIG"
: "${LOCAL_DB:?LOCAL_DB not set in config}"
: "${REMOTE_MODE:?REMOTE_MODE not set in config}"

TMPDIR_RUN=""
cleanup() { [[ -n "$TMPDIR_RUN" && -d "$TMPDIR_RUN" ]] && rm -rf "$TMPDIR_RUN"; }
trap cleanup EXIT

# --- secrets -----------------------------------------------------------------
# The vault master password is NEVER stored: the open-wrapper passes it in
# memory via KP_MASTER_PW for the duration of a KeePass session. (A keyring
# lookup is kept only as an optional fallback, off by default.)
MASTER_PW="${KP_MASTER_PW:-}"
if [[ -z "$MASTER_PW" ]]; then
	MASTER_PW="$(secret-tool lookup service "$KEYRING_SERVICE" key master 2>/dev/null || true)"
fi
[[ -n "$MASTER_PW" ]] || skip "no master password provided (KP_MASTER_PW unset, keyring empty)"

# The dufs *server* password (webdav transport only) is NOT the vault key, so it
# may be cached in the keyring; env var overrides.
DUFS_PASS=""
if [[ "$REMOTE_MODE" == "webdav" ]]; then
	: "${REMOTE_URL:?REMOTE_URL required for webdav mode}"
	: "${DUFS_USER:?DUFS_USER required for webdav mode}"
	DUFS_PASS="${KP_DUFS_PW:-$(secret-tool lookup service "$KEYRING_SERVICE" key dufs 2>/dev/null || true)}"
	[[ -n "$DUFS_PASS" ]] || skip "no dufs password (KP_DUFS_PW unset, keyring empty)"
fi

sha() { sha256sum "$1" | cut -d' ' -f1; }

# --- remote transport abstraction (file mode vs webdav mode) -----------------
# remote_get <dest>   -> 0 if fetched, 1 if remote does not exist yet
# remote_hash         -> prints remote sha256, or empty if remote missing
# remote_put <src>    -> upload src as the new remote (atomic where possible)
remote_get() {
	local dest="$1"
	case "$REMOTE_MODE" in
	file)
		[[ -f "$REMOTE_FILE" ]] || return 1
		cp -f "$REMOTE_FILE" "$dest" ;;
	webdav)
		curl -fsS -u "$DUFS_USER:$DUFS_PASS" -o "$dest" "$REMOTE_URL" 2>/dev/null || return 1 ;;
	*) die "unknown REMOTE_MODE: $REMOTE_MODE" ;;
	esac
}
remote_hash() {
	case "$REMOTE_MODE" in
	file)   [[ -f "$REMOTE_FILE" ]] && sha "$REMOTE_FILE" || true ;;
	webdav) curl -fsS -u "$DUFS_USER:$DUFS_PASS" "${REMOTE_URL}?hash" 2>/dev/null || true ;;
	esac
}
remote_put() {
	local src="$1"
	case "$REMOTE_MODE" in
	file)
		local dir; dir="$(dirname "$REMOTE_FILE")"
		mkdir -p "$dir"
		cp -f "$src" "$REMOTE_FILE.tmp.$$" && mv -f "$REMOTE_FILE.tmp.$$" "$REMOTE_FILE" ;;
	webdav)
		curl -fsS -u "$DUFS_USER:$DUFS_PASS" -T "$src" "$REMOTE_URL" -o /dev/null ;;
	esac
}

# --- validate the master password against the local DB before touching it ----
verify_pw() {
	printf '%s\n' "$MASTER_PW" | keepassxc-cli ls "$1" >/dev/null 2>&1
}

backup_local() {
	local bdir
	bdir="$(dirname "$LOCAL_DB")/.backup_$(date +%Y%m%d_%H%M%S)"
	mkdir -p "$bdir"
	cp -f "$LOCAL_DB" "$bdir/" && log "backed up local vault to $bdir"
}

# --- the reconcile, with bounded compare-and-swap retries --------------------
reconcile() {
	TMPDIR_RUN="$(mktemp -d)"
	local tmp_remote="$TMPDIR_RUN/remote.kdbx"

	# Bootstrap: if the local vault is missing, seed it from the remote.
	if [[ ! -f "$LOCAL_DB" ]]; then
		if remote_get "$tmp_remote"; then
			mkdir -p "$(dirname "$LOCAL_DB")"
			cp -f "$tmp_remote" "$LOCAL_DB"
			log "bootstrapped local vault from remote"
			return 0
		fi
		skip "no local vault and no remote vault yet — nothing to do"
	fi

	verify_pw "$LOCAL_DB" || die "master password from keyring does not open $LOCAL_DB — refusing to touch it"

	local attempt=0
	while (( attempt < MAX_CAS_RETRIES )); do
		attempt=$((attempt + 1))

		local remote_hash_before; remote_hash_before="$(remote_hash)"
		if [[ -z "$remote_hash_before" ]]; then
			# No remote yet — publish our local copy as the first version.
			remote_put "$LOCAL_DB" && log "published local vault to remote (first copy)"
			return 0
		fi

		local local_before; local_before="$(sha "$LOCAL_DB")"
		if [[ "$remote_hash_before" == "$local_before" ]]; then
			log "already in sync (hash $local_before)"
			return 0
		fi

		remote_get "$tmp_remote" || skip "remote unreachable"

		# Merge remote INTO local so local becomes the union. Back up first;
		# never proceed to upload if the merge fails.
		backup_local
		if ! printf '%s\n' "$MASTER_PW" | keepassxc-cli merge --same-credentials "$LOCAL_DB" "$tmp_remote" >/dev/null 2>&1; then
			die "keepassxc-cli merge failed — local vault left intact (see latest .backup_*)"
		fi

		local local_after; local_after="$(sha "$LOCAL_DB")"

		# Compare-and-swap: only upload if the remote hasn't changed since our
		# read; otherwise someone else wrote concurrently — retry the whole
		# reconcile with the new remote (merges are commutative, so it converges).
		local remote_hash_now; remote_hash_now="$(remote_hash)"
		if [[ "$remote_hash_now" != "$remote_hash_before" ]]; then
			log "remote changed during merge (CAS) — retrying ($attempt/$MAX_CAS_RETRIES)"
			continue
		fi

		if [[ "$local_after" != "$remote_hash_now" ]]; then
			remote_put "$LOCAL_DB" && log "uploaded merged vault to remote"
		fi
		log "reconcile complete (local $local_after)"
		return 0
	done
	die "gave up after $MAX_CAS_RETRIES CAS retries — remote is changing too fast; will retry next cycle"
}

# --- serialize: only one reconcile at a time ---------------------------------
mkdir -p "$STATE_DIR"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
	skip "another reconcile is running"
fi

reconcile
