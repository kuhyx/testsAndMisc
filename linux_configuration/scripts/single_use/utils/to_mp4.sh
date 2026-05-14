#!/usr/bin/env bash
# Wrapper for backward compatibility - converts to mp4
# See convert_video.sh for full options
exec "$(dirname "$(readlink -f "$0")")/convert_video.sh" -f mp4 "$@"
