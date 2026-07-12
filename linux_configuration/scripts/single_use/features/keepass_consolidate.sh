#!/bin/bash
# keepass_consolidate.sh — enforce "exactly one KeePass vault" on this device.
#
# Finds stray *.kdbx files scattered around your folders, merges each into the
# ONE canonical vault, and removes the stray — so you never again wonder which
# copy is current. It is deliberately conservative:
#   * a stray is only touched if it opens with the SAME master password
#     (different-password DBs are reported and left completely alone);
#   * the canonical vault AND every stray are backed up before any change;
#   * a stray is removed ONLY after its merge into the canonical succeeded.
#
# The master password is taken from KP_MASTER_PW (in memory, never stored) —
# normally supplied by keepass-open.sh, which already has it. Self-contained so
# it runs on both the Arch PC and the Ubuntu laptop.
#
# Usage: KP_MASTER_PW=… keepass_consolidate.sh [--canonical PATH] [--root DIR] [--dry-run]

set -euo pipefail

CANONICAL="${KP_CANONICAL:-$HOME/cloud/Keepass/Passwords.kdbx}"
SEARCH_ROOT="${KP_SEARCH_ROOT:-$HOME}"
DRY_RUN=0
STATE_DIR="${KP_STATE_DIR:-$HOME/.config/keepass-sync}"

EXCLUDE_ARGS=()
while [[ $# -gt 0 ]]; do
	case "$1" in
	--canonical) CANONICAL="$2"; shift 2 ;;
	--root) SEARCH_ROOT="$2"; shift 2 ;;
	--exclude) EXCLUDE_ARGS+=("$2"); shift 2 ;;
	--dry-run|-n) DRY_RUN=1; shift ;;
	*) echo "unknown arg: $1" >&2; exit 2 ;;
	esac
done

log() { printf '[keepass-consolidate] %s\n' "$*" >&2; }
die() { printf '[keepass-consolidate] ERROR: %s\n' "$*" >&2; exit 1; }

MASTER_PW="${KP_MASTER_PW:-}"
[[ -n "$MASTER_PW" ]] || die "KP_MASTER_PW not set (needed to open/merge vaults)"
command -v keepassxc-cli >/dev/null || die "keepassxc-cli not found"
# fd is 'fd' on Arch, 'fdfind' on Debian/Ubuntu.
FD="$(command -v fd || command -v fdfind || true)"
[[ -n "$FD" ]] || die "fd (fd-find) not found"

[[ -f "$CANONICAL" ]] || die "canonical vault not found: $CANONICAL"
opens() { printf '%s\n' "$MASTER_PW" | keepassxc-cli ls "$1" >/dev/null 2>&1; }
opens "$CANONICAL" || die "master password does not open the canonical vault — aborting"

backup() {  # backup <file> — copy into a timestamped sibling .backup_ dir
	local f="$1" bdir
	bdir="$(dirname "$f")/.backup_$(date +%Y%m%d_%H%M%S)_consolidate"
	mkdir -p "$bdir"; cp -f "$f" "$bdir/"
}

# --- exclude prefixes: dirs whose vaults are NOT strays -----------------------
# Critically the dufs serve-path: on the machine running dufs that directory IS
# the remote canonical store (e.g. ~/cloud/Keepass) — it must never be treated
# as a stray and removed. Plus any --exclude args and KP_EXCLUDE (colon-list).
EXCLUDES=()
_add_exclude() { local p; p="$(readlink -f "$1" 2>/dev/null || echo "$1")"; [[ -n "$p" ]] && EXCLUDES+=("$p"); }
_dufs_cfg="$HOME/.config/dufs/dufs.yaml"
if [[ -f "$_dufs_cfg" ]]; then
	_sp="$(sed -nE 's/^serve-path:[[:space:]]*//p' "$_dufs_cfg" | head -1)"
	[[ -n "$_sp" ]] && _add_exclude "$_sp"
fi
IFS=':' read -r -a _kp_excl <<<"${KP_EXCLUDE:-}"
for e in "${_kp_excl[@]}" "${EXCLUDE_ARGS[@]}"; do [[ -n "$e" ]] && _add_exclude "$e"; done

is_excluded() {  # is_excluded <abs-path> — under any excluded prefix?
	local p="$1" ex
	for ex in "${EXCLUDES[@]}"; do
		[[ "$p" == "$ex" || "$p" == "$ex"/* ]] && return 0
	done
	return 1
}
[[ ${#EXCLUDES[@]} -gt 0 ]] && log "excluding: ${EXCLUDES[*]}"

# --- locate strays -----------------------------------------------------------
# Absolute canonical path, so we can exclude it exactly.
CANON_ABS="$(readlink -f "$CANONICAL")"
mapfile -t CANDIDATES < <(
	"$FD" -e kdbx -u -a --exclude '.backup_*' --exclude 'node_modules' \
		--exclude '.git' --exclude '.cache' --exclude 'Trash' \
		--exclude 'snap' --exclude '.local/share/Trash' \
		. "$SEARCH_ROOT" 2>/dev/null || true
)

STRAYS=()
for f in "${CANDIDATES[@]}"; do
	[[ -f "$f" ]] || continue
	local_abs="$(readlink -f "$f")"
	[[ "$local_abs" == "$CANON_ABS" ]] && continue   # the canonical itself
	is_excluded "$local_abs" && continue             # dufs store / excluded dirs
	# Skip our own timestamped backups defensively (in case fd glob missed).
	[[ "$f" == *"/.backup_"* ]] && continue
	STRAYS+=("$f")
done

if [[ ${#STRAYS[@]} -eq 0 ]]; then
	log "no strays found — exactly one vault ($CANONICAL). Done."
	exit 0
fi

log "found ${#STRAYS[@]} candidate stray vault(s) under $SEARCH_ROOT"

mkdir -p "$STATE_DIR"
exec 9>"$STATE_DIR/consolidate.lock"
flock -n 9 || die "another consolidation is running"

merged=0 skipped=0
for stray in "${STRAYS[@]}"; do
	if ! opens "$stray"; then
		log "SKIP (different master password, left untouched): $stray"
		skipped=$((skipped + 1))
		continue
	fi
	if [[ "$DRY_RUN" -eq 1 ]]; then
		log "[dry-run] would merge + remove: $stray"
		merged=$((merged + 1))
		continue
	fi
	backup "$CANONICAL"
	backup "$stray"
	if printf '%s\n' "$MASTER_PW" | keepassxc-cli merge --same-credentials "$CANONICAL" "$stray" >/dev/null 2>&1; then
		rm -f "$stray"
		log "merged + removed stray: $stray"
		merged=$((merged + 1))
	else
		log "merge FAILED (stray kept): $stray"
		skipped=$((skipped + 1))
	fi
done

log "done: $merged merged, $skipped skipped. Canonical: $CANONICAL"
