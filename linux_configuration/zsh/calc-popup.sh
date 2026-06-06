#!/usr/bin/env bash
# ============================================================================
# calc-popup.sh — launch the floating scratchpad calculator (i3: Mod+c)
# ----------------------------------------------------------------------------
# Opens a small, centered, floating terminator that runs a minimal zsh which
# loads only the live-calc widget. Type math, see results live, Ctrl-D to close.
#
# i3 matches the window by its X role ("calc"), set via terminator --role.
# -u (--no-dbus) forces a standalone process so it never folds into an existing
# terminator window as a tab.
# ============================================================================
set -euo pipefail

# Directory of this script (the repo zsh/ dir); scratchpad rc lives alongside.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRATCH_ZDOTDIR="${SCRIPT_DIR}/scratchpad"

if ! command -v terminator >/dev/null 2>&1; then
    echo "calc-popup: terminator not found" >&2
    exit 1
fi

# --geometry is in pixels for terminator; set the size here (reliably, before
# the window maps) so i3 only has to float + center it.
exec terminator -u --role=calc -T calc --geometry=820x220 \
    -e "env ZDOTDIR='${SCRATCH_ZDOTDIR}' zsh -i"
