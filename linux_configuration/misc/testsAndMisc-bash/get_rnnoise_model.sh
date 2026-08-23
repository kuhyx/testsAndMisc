#!/usr/bin/env bash

set -euo pipefail

# get_rnnoise_model.sh — fetch an RNNoise model into a local models dir
#
# Prefers known-good rnnoise-nu models. You can override with:
#   RN_URL, RN_TARGET_DIR, RN_TARGET_NAME
#
# Usage:
#   Bash/get_rnnoise_model.sh            # interactive download
#   RN_TARGET_DIR=./models Bash/get_rnnoise_model.sh --yes

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

YES=false
while [[ $# -gt 0 ]]; do
	case "$1" in
	-y | --yes)
		YES=true
		shift
		;;
	*)
		echo "Unknown option: $1" >&2
		exit 2
		;;
	esac
done

RN_TARGET_DIR=${RN_TARGET_DIR:-"$(dirname "$0")/models"}
RN_TARGET_NAME=${RN_TARGET_NAME:-"rnnoise_model.rnnn"}

mkdir -p "$RN_TARGET_DIR"
dest="$RN_TARGET_DIR/$RN_TARGET_NAME"

if [[ -f $dest ]]; then
	echo "Model already exists at: $dest"
	exit 0
fi

if ! $YES; then
	if ! ask_yes_no "Download RNNoise model to $dest?"; then
		echo "Aborted."
		exit 1
	fi
fi

if ! has_cmd curl && ! has_cmd wget; then
	echo "Error: Need curl or wget to download RNNoise model." >&2
	exit 3
fi

# Helper: try to download a URL to destination, exit 0 on success
# Usage: try_download_model URL DEST
try_download_model() {
	local url="$1"
	local dest="$2"
	local tmp
	tmp=$(mktemp)
	echo "Attempting to download RNNoise model from: $url" >&2
	if has_cmd curl; then
		curl -fsSL "$url" -o "$tmp" 2>/dev/null || true
	else
		wget -qO "$tmp" "$url" 2>/dev/null || true
	fi
	if [[ -s $tmp ]]; then
		mv "$tmp" "$dest"
		echo "Saved RNNoise model to: $dest" >&2
		exit 0
	fi
	rm -f "$tmp" || true
}

# Priority 1: explicit URL
if [[ -n ${RN_URL:-} ]]; then
	echo "Downloading RNNoise model from RN_URL: $RN_URL" >&2
	try_download_model "$RN_URL" "$dest"
	echo "Warning: RN_URL download failed; continuing to fallback sources." >&2
fi

# Priority 2: rnnoise-nu known models (GregorR)
NU_URLS=(
	"https://raw.githubusercontent.com/GregorR/rnnoise-nu/master/src/models/sh.rnnn"
	"https://raw.githubusercontent.com/GregorR/rnnoise-nu/master/src/models/lq.rnnn"
	"https://raw.githubusercontent.com/GregorR/rnnoise-nu/master/src/models/mp.rnnn"
	"https://raw.githubusercontent.com/GregorR/rnnoise-nu/master/src/models/bd.rnnn"
	"https://raw.githubusercontent.com/GregorR/rnnoise-nu/master/src/models/cb.rnnn"
)
for u in "${NU_URLS[@]}"; do
	try_download_model "$u" "$dest"
done

# Priority 2b: arnndn-models fallback (richardpl)
RNNDN_URLS=(
	"https://raw.githubusercontent.com/richardpl/arnndn-models/master/sh.rnnn"
)
for u in "${RNNDN_URLS[@]}"; do
	try_download_model "$u" "$dest"
done

# Priority 3: repo archives (rnnoise-nu and arnndn-models)
ARCHIVES=(
	"https://github.com/GregorR/rnnoise-nu/archive/refs/heads/master.zip"
	"https://github.com/richardpl/arnndn-models/archive/refs/heads/master.zip"
)
for aurl in "${ARCHIVES[@]}"; do
	echo "Attempting to download archive: $aurl" >&2
	tmpdir=$(mktemp -d)
	archive="$tmpdir/models.zip"
	set +e
	if has_cmd curl; then
		curl -fL "$aurl" -o "$archive"
	else
		wget -O "$archive" "$aurl"
	fi
	status=$?
	set -e
	if [[ $status -ne 0 ]]; then
		rm -rf "$tmpdir" || true
		continue
	fi
	if has_cmd bsdtar; then
		bsdtar -xf "$archive" -C "$tmpdir"
	elif has_cmd unzip; then
		unzip -q "$archive" -d "$tmpdir"
	else
		echo "Warning: Need bsdtar or unzip to extract archive; skipping archive method." >&2
		rm -rf "$tmpdir" || true
		continue
	fi
	mapfile -t nnfiles < <(bash -lc 'shopt -s globstar nullglob; for f in '"$tmpdir"'/**/*.rnnn '"$tmpdir"'/**/*.nn; do [[ -f "$f" ]] && echo "$f"; done')
	if [[ ${#nnfiles[@]} -gt 0 ]]; then
		cp -f "${nnfiles[0]}" "$dest"
		echo "Saved RNNoise model to: $dest (from archive)" >&2
		rm -rf "$tmpdir" || true
		exit 0
	fi
	rm -rf "$tmpdir" || true
done

# Priority 4: Arch-based AUR packages and search only .nn/.rnnn
if has_cmd yay; then
	echo "Attempting to install AUR packages that may include RNNoise models..." >&2
	set +e
	yay -S --noconfirm denoiseit-git 2>/dev/null
	yay -S --noconfirm speech-denoiser-git 2>/dev/null
	set -e
	mapfile -t found < <(bash -lc 'shopt -s globstar nullglob; for f in /usr/share/**/*.nn /usr/share/**/*.rnnn /usr/local/share/**/*.nn /usr/local/share/**/*.rnnn; do [[ -f "$f" ]] && echo "$f"; done' 2>/dev/null || true)
	if [[ ${#found[@]} -gt 0 ]]; then
		echo "Found candidate models:" >&2
		printf '  %s\n' "${found[@]}" >&2
		cp -f "${found[0]}" "$dest"
		echo "Copied model to: $dest" >&2
		exit 0
	fi
fi

echo "Error: Could not obtain an RNNoise model automatically." >&2
echo "Hint: Set RN_URL to a reachable model URL, or place a model file at: $dest" >&2
exit 5
