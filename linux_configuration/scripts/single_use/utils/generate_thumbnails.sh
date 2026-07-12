#!/bin/bash
# generate_thumbnails.sh — make small preview thumbnails for the cloud media so
# the web gallery (cloud_gallery) loads fast instead of downloading full files.
#
# For every image/video under the dufs cloud it writes a ~400px JPEG to
#   $CLOUD_ROOT/.thumbs/<same-path>.jpg
# which the gallery requests as `/.thumbs/<path>.jpg`. Images are resized with
# ImageMagick; videos get a poster frame via ffmpeg. Idempotent: a thumbnail
# newer than its source is skipped. flock-guarded, self-contained.
#
# CLOUD_ROOT comes from the dufs serve-path (~/.config/dufs/dufs.yaml), else
# ~/cloud. Usage: generate_thumbnails.sh [ROOT_DIR]

set -euo pipefail

readonly THUMB_MAX=400

log() { printf '[thumbnails] %s\n' "$*" >&2; }

CLOUD_ROOT="${CLOUD_ROOT:-}"
if [[ -z "$CLOUD_ROOT" && -f "$HOME/.config/dufs/dufs.yaml" ]]; then
	CLOUD_ROOT="$(sed -nE 's/^serve-path:[[:space:]]*//p' "$HOME/.config/dufs/dufs.yaml" | head -1)"
fi
CLOUD_ROOT="${CLOUD_ROOT:-$HOME/cloud}"
ROOT="${1:-$CLOUD_ROOT}"
readonly THUMBS="$CLOUD_ROOT/.thumbs"

FD="$(command -v fd || command -v fdfind || true)"
[[ -n "$FD" ]] || { log "ERROR: fd (fd-find) not installed"; exit 1; }
command -v ffmpeg >/dev/null || { log "ERROR: ffmpeg not installed"; exit 1; }
MAGICK="$(command -v magick || command -v convert || true)"
[[ -n "$MAGICK" ]] || { log "ERROR: ImageMagick (magick/convert) not installed"; exit 1; }

readonly IMG_EXTS=(jpg jpeg png gif bmp tiff tif webp heic heif avif)
readonly VID_EXTS=(mp4 avi mkv mov wmv flv webm m4v 3gp ogv mpg mpeg mts m2ts vob)
FD_ARGS=()
for e in "${IMG_EXTS[@]}" "${VID_EXTS[@]}"; do FD_ARGS+=(-e "$e"); done

STATE_DIR="${THUMB_STATE:-$HOME/.local/state/media-cloud-sync}"
mkdir -p "$STATE_DIR" "$THUMBS"
exec 9>"$STATE_DIR/thumbs.lock"
flock -n 9 || { log "another thumbnail run is in progress — skipping"; exit 0; }

is_video() {
	local ext="${1##*.}"
	ext="${ext,,}"
	for v in "${VID_EXTS[@]}"; do [[ "$ext" == "$v" ]] && return 0; done
	return 1
}

made=0 skipped=0 failed=0
while IFS= read -r src; do
	[[ -f "$src" ]] || continue
	# Thumbnail path mirrors the file's path under the cloud root.
	rel="${src#"$CLOUD_ROOT"}"
	dst="$THUMBS${rel}.jpg"
	if [[ -f "$dst" && "$dst" -nt "$src" ]]; then
		skipped=$((skipped + 1)); continue
	fi
	mkdir -p "$(dirname "$dst")"
	if is_video "$src"; then
		if ffmpeg -y -loglevel error -ss 1 -i "$src" -frames:v 1 \
			-vf "scale=${THUMB_MAX}:-2:force_original_aspect_ratio=decrease" \
			"$dst" </dev/null 2>/dev/null; then
			made=$((made + 1))
		else
			# Fall back to the very first frame (videos shorter than 1s).
			if ffmpeg -y -loglevel error -i "$src" -frames:v 1 \
				-vf "scale=${THUMB_MAX}:-2" "$dst" </dev/null 2>/dev/null; then
				made=$((made + 1))
			else
				failed=$((failed + 1))
			fi
		fi
	else
		if "$MAGICK" "${src}[0]" -auto-orient -thumbnail "${THUMB_MAX}x${THUMB_MAX}>" \
			-strip "$dst" 2>/dev/null; then
			made=$((made + 1))
		else
			failed=$((failed + 1))
		fi
	fi
done < <("$FD" "${FD_ARGS[@]}" --type f --exclude '.thumbs' --exclude '_thumbs' . "$ROOT" 2>/dev/null || true)

log "done: $made made, $skipped current, $failed failed → $THUMBS"
