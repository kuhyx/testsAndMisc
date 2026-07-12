#!/bin/bash
# import_media_archives.sh — extract media_archive_*.zip snapshots and MOVE their
# media into the self-hosted dufs cloud, deduplicating across the overlapping
# snapshots, then delete each zip once its media is safely in the cloud.
#
# These archives are incremental snapshots of ~/Downloads (each holds a top-level
# downloads/ dir) and contain only images/videos — so "media only" loses nothing.
#
# Per zip (safe + resumable):
#   1. extract into a staging dir on the cloud filesystem (so mv is a rename)
#   2. hand the staging dir to sync_media_to_cloud.sh, which MOVES media into
#      $CLOUD/Media/YYYY/MM (by mtime) and drops files already in the cloud
#   3. verify no media remains in staging (nothing failed to move)
#   4. delete the staging dir, then delete the zip
# A zip is deleted ONLY after its media is confirmed in the cloud; on any problem
# the zip is kept and the run continues.
#
# Usage: import_media_archives.sh [ARCHIVE_DIR]
#        (default ARCHIVE_DIR: ~/Downloads/media_archive_archive)

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
readonly HERE
readonly ORGANIZER="$HERE/sync_media_to_cloud.sh"
readonly ARCHIVE_DIR="${1:-$HOME/Downloads/media_archive_archive}"

log() { printf '[import-archives] %s\n' "$*" >&2; }
die() { printf '[import-archives] ERROR: %s\n' "$*" >&2; exit 1; }

# --- dependencies (self-installing on Arch) ----------------------------------
if ! command -v unzip >/dev/null; then
	if command -v pacman >/dev/null; then
		sudo pacman -S --needed --noconfirm unzip
	else
		die "unzip is required but not installed"
	fi
fi
[[ -x "$ORGANIZER" ]] || die "organizer script not found/executable: $ORGANIZER"
[[ -d "$ARCHIVE_DIR" ]] || die "archive directory not found: $ARCHIVE_DIR"

# Media extensions must match sync_media_to_cloud.sh — used only to verify that
# staging was fully drained before deleting a zip.
readonly MEDIA_RE='.*\.(jpg|jpeg|png|gif|bmp|tiff|tif|webp|raw|cr2|nef|orf|arw|dng|heic|heif|mp4|avi|mkv|mov|wmv|flv|webm|m4v|3gp|ogv|mpg|mpeg|mts|m2ts|vob)$'

# --- stage on the cloud filesystem so mv is an atomic rename -----------------
CLOUD_ROOT="${CLOUD_ROOT:-}"
if [[ -z "$CLOUD_ROOT" && -f "$HOME/.config/dufs/dufs.yaml" ]]; then
	CLOUD_ROOT="$(sed -nE 's/^serve-path:[[:space:]]*//p' "$HOME/.config/dufs/dufs.yaml" | head -1)"
fi
CLOUD_ROOT="${CLOUD_ROOT:-$HOME/cloud}"
STAGE_PARENT="$(dirname "$CLOUD_ROOT")"
readonly STAGE_PARENT

STAGING=""
cleanup() { [[ -n "$STAGING" && -d "$STAGING" ]] && rm -rf "$STAGING"; }
trap cleanup EXIT

count_media() {
	find "$1" -type f -regextype posix-extended -iregex "$MEDIA_RE" 2>/dev/null | wc -l
}

shopt -s nullglob
zips=("$ARCHIVE_DIR"/*.zip)
(( ${#zips[@]} )) || { log "no *.zip found in $ARCHIVE_DIR — nothing to do"; exit 0; }

readonly total=${#zips[@]}
i=0 deleted=0 kept=0
log "importing $total archive(s) from $ARCHIVE_DIR into $CLOUD_ROOT/Media"
for zip in "${zips[@]}"; do
	i=$((i + 1))
	log "[$i/$total] $(basename "$zip") ($(du -h "$zip" | cut -f1))"

	STAGING="$(mktemp -d "$STAGE_PARENT/.media-import.XXXXXX")"
	if ! unzip -q -o "$zip" -d "$STAGING"; then
		log "  unzip failed — keeping zip"; rm -rf "$STAGING"; STAGING=""; kept=$((kept + 1)); continue
	fi

	before="$(count_media "$STAGING")"
	if ! "$ORGANIZER" "$STAGING"; then
		log "  organizer failed — keeping zip"; rm -rf "$STAGING"; STAGING=""; kept=$((kept + 1)); continue
	fi

	after="$(count_media "$STAGING")"
	if (( after > 0 )); then
		log "  WARNING: $after/$before media file(s) not moved — keeping zip for safety"
		rm -rf "$STAGING"; STAGING=""; kept=$((kept + 1)); continue
	fi

	rm -rf "$STAGING"; STAGING=""
	if rm -f "$zip"; then
		deleted=$((deleted + 1))
		log "  ✓ $before media handled; zip deleted"
	else
		log "  media moved but zip delete failed: $zip"; kept=$((kept + 1))
	fi
done

log "done: $deleted zip(s) imported + deleted, $kept kept"
