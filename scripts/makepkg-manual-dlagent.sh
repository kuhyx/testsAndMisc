#!/usr/bin/env bash
# makepkg-manual-dlagent.sh — A makepkg download agent for the manual:// protocol.
#
# makepkg calls this as:  makepkg-manual-dlagent.sh <url> <output_file>
#
# For Unreal Engine URLs, it opens the Epic download page in your browser,
# watches ~/Downloads via inotifywait, and copies the finished file to the
# expected output path — making `yay -Sua` seamless.
#
# For any other manual:// URL, it prints the original "please download manually"
# message and watches ~/Downloads for a matching filename.
#
# Install:
#   1. Place this script somewhere on your PATH or a known location.
#   2. Add to ~/.makepkg.conf:
#        DLAGENTS+=('manual::/path/to/makepkg-manual-dlagent.sh %u %o')
#
# Dependencies: inotify-tools (inotifywait), xdg-open

set -euo pipefail

URL="$1"       # e.g. manual://Linux_Unreal_Engine_5.7.2.zip
OUTPUT="$2"    # e.g. /home/user/.cache/yay/unreal-engine-bin/Linux_Unreal_Engine_5.7.2.zip

DOWNLOAD_DIR="${XDG_DOWNLOAD_DIR:-$HOME/Downloads}"

# Strip the manual:// prefix to get the bare filename
FILENAME="${URL#manual://}"

# If the output file already exists, nothing to do
if [[ -f "$OUTPUT" ]]; then
    echo "  -> File already exists: $OUTPUT"
    exit 0
fi

# If already sitting in ~/Downloads, just copy it
if [[ -f "$DOWNLOAD_DIR/$FILENAME" ]]; then
    echo "  -> Found $FILENAME in $DOWNLOAD_DIR, copying..."
    cp -- "$DOWNLOAD_DIR/$FILENAME" "$OUTPUT"
    exit 0
fi

# Determine which browser page to open based on the filename
OPEN_URL=""
case "$FILENAME" in
    Linux_Unreal_Engine_*.zip)
        OPEN_URL="https://www.unrealengine.com/linux"
        ;;
esac

echo ""
echo "  ┌─────────────────────────────────────────────────────────────┐"
echo "  │  manual:// download agent                                   │"
echo "  │  File needed: $FILENAME"
echo "  │  Destination: $OUTPUT"
if [[ -n "$OPEN_URL" ]]; then
    echo "  │  Download from: $OPEN_URL"
fi
echo "  │                                                             │"
echo "  │  Download the file in your browser.                         │"
echo "  │  It will be detected automatically from ~/Downloads.        │"
echo "  │  Press Ctrl+C to abort.                                     │"
echo "  └─────────────────────────────────────────────────────────────┘"
echo ""

# Open browser if we have a URL
if [[ -n "$OPEN_URL" ]]; then
    xdg-open "$OPEN_URL" 2>/dev/null &
fi

# Escape dots in filename for inotifywait regex
FILENAME_ESCAPED="${FILENAME//./\\.}"

# Watch ~/Downloads for the file to appear
while true; do
    inotifywait -q -q -e close_write,moved_to \
        --include "${FILENAME_ESCAPED}$" \
        "$DOWNLOAD_DIR" 2>/dev/null || true

    if [[ -f "$DOWNLOAD_DIR/$FILENAME" ]]; then
        # Brief pause to ensure the file is fully flushed
        sleep 2
        echo "  -> Download complete: $DOWNLOAD_DIR/$FILENAME"
        cp -- "$DOWNLOAD_DIR/$FILENAME" "$OUTPUT"
        echo "  -> Copied to $OUTPUT"
        exit 0
    fi
done
