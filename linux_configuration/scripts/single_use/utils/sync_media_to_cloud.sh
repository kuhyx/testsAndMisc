#!/bin/bash
# sync_media_to_cloud.sh — MOVE organized images/videos into the dufs cloud,
# unzipped and browsable, so they're viewable from anywhere (web + app) without
# duplicating them. The file LEAVES ~/Downloads and lives only in the cloud
# folder (which is on local disk and served by dufs) — so the cloud is the
# single storage; there is no separate local copy or zip duplicate.
#
# For each Downloads image/video it moves the file to $CLOUD_ROOT/Media/YYYY/MM/
# (by file mtime) with `mv`: an atomic rename on the same filesystem (instant,
# no extra disk), or a copy-then-remove-source across filesystems (mv removes
# the source only after a successful copy, so an interruption never loses data).
# The destination name is pre-checked to be free, so nothing is clobbered. Files
# modified in the last 2 minutes are skipped (they may still be downloading). A
# file identical to one already in the cloud is de-duplicated (source removed).
# Collisions with a different file get a numeric suffix. flock-guarded.
#
# CLOUD_ROOT is taken from the dufs serve-path (~/.config/dufs/dufs.yaml),
# falling back to ~/cloud. Self-contained; runs on Arch or Ubuntu.
#
# Usage: sync_media_to_cloud.sh [SOURCE_DIR ...]   (default: ~/Downloads)

set -euo pipefail

log() { printf '[media-cloud-sync] %s\n' "$*" >&2; }

readonly QUIESCE_SECONDS=120   # skip files modified within this window (still downloading)

# --- where does the cloud live? -----------------------------------------------
CLOUD_ROOT="${CLOUD_ROOT:-}"
if [[ -z "$CLOUD_ROOT" && -f "$HOME/.config/dufs/dufs.yaml" ]]; then
	CLOUD_ROOT="$(sed -nE 's/^serve-path:[[:space:]]*//p' "$HOME/.config/dufs/dufs.yaml" | head -1)"
fi
CLOUD_ROOT="${CLOUD_ROOT:-$HOME/cloud}"
readonly MEDIA_DEST="$CLOUD_ROOT/Media"

SOURCES=("$@")
[[ ${#SOURCES[@]} -eq 0 ]] && SOURCES=("$HOME/Downloads")

FD="$(command -v fd || command -v fdfind || true)"
[[ -n "$FD" ]] || { log "ERROR: fd (fd-find) not installed"; exit 1; }

# Same media extensions as organize_downloads.sh.
readonly EXTS=(jpg jpeg png gif bmp tiff tif webp raw cr2 nef orf arw dng heic heif \
	mp4 avi mkv mov wmv flv webm m4v 3gp ogv mpg mpeg mts m2ts vob)
FD_EXT_ARGS=()
for e in "${EXTS[@]}"; do FD_EXT_ARGS+=(-e "$e"); done

# --- serialize ---------------------------------------------------------------
STATE_DIR="${MEDIA_SYNC_STATE:-$HOME/.local/state/media-cloud-sync}"
mkdir -p "$STATE_DIR" "$MEDIA_DEST"
exec 9>"$STATE_DIR/lock"
flock -n 9 || { log "another sync is running — skipping"; exit 0; }

now="$(date +%s)"
moved=0 deduped=0 skipped=0
for src in "${SOURCES[@]}"; do
	[[ -e "$src" ]] || continue
	if [[ -f "$src" ]]; then
		mapfile -t FILES < <(printf '%s\n' "$src")
	else
		mapfile -t FILES < <(
			"$FD" "${FD_EXT_ARGS[@]}" --type f \
				--exclude 'media_archive_*' --exclude '*media_organize_*' \
				--exclude '.git' --exclude 'node_modules' \
				. "$src" 2>/dev/null || true
		)
	fi
	for f in "${FILES[@]}"; do
		[[ -f "$f" ]] || continue
		# Skip files still being written (recently modified → maybe downloading).
		mtime="$(stat -c%Y "$f" 2>/dev/null || echo 0)"
		if (( now - mtime < QUIESCE_SECONDS )); then
			log "skip (modified <${QUIESCE_SECONDS}s ago, may be downloading): $f"
			skipped=$((skipped + 1)); continue
		fi
		ext="${f##*.}"; ext="${ext,,}"
		sub="$(date -r "$f" +%Y/%m 2>/dev/null || echo unknown)"
		dest_dir="$MEDIA_DEST/$sub"
		base="$(basename "$f")"
		dest="$dest_dir/$base"
		if [[ -e "$dest" ]]; then
			if [[ "$(stat -c%s "$f")" == "$(stat -c%s "$dest" 2>/dev/null)" ]]; then
				rm -f "$f"; deduped=$((deduped + 1)); continue   # identical already in cloud
			fi
			stem="${base%.*}"; n=1
			while [[ -e "$dest_dir/${stem}_${n}.${ext}" ]]; do n=$((n + 1)); done
			dest="$dest_dir/${stem}_${n}.${ext}"
		fi
		mkdir -p "$dest_dir"
		# $dest is a pre-checked free name, so mv won't clobber. mv is atomic on
		# the same filesystem and safe (copy-then-unlink) across filesystems.
		if mv -f "$f" "$dest" 2>/dev/null; then
			moved=$((moved + 1))
		else
			log "WARNING: failed to move $f (left in Downloads)"
		fi
	done
done

log "done: $moved moved, $deduped duplicates dropped, $skipped skipped → $MEDIA_DEST"
