#!/bin/bash
# Fix executable stack flags on Source Engine .so files before launching.
# Usage: Set as Steam Launch Options:
#   ~/.local/bin/fix-execstack-launch.sh %command%
#
# Works for any Source Engine game that fails on modern kernels (6.x+)
# due to shared libraries requiring executable stack (RWE flag).

if [[ $# -eq 0 ]]; then
	echo "Usage: $0 <command> [args...]"
	echo "Set as Steam launch option: ~/.local/bin/fix-execstack-launch.sh %command%"
	exit 1
fi

# Steam wraps %command% as: reaper SteamLaunch ... -- /path/to/game/hl2.sh -game ...
# Find the game directory by looking for a path inside steamapps/common/ in the args.
GAME_DIR=""
for arg in "$@"; do
	if [[ "$arg" == */steamapps/common/* ]]; then
		resolved="$(readlink -f "$arg" 2>/dev/null)"
		if [[ -n "$resolved" ]]; then
			# Walk up to find the game root (directory directly under steamapps/common/)
			candidate="$resolved"
			while [[ "$candidate" == */steamapps/common/*/* ]]; do
				candidate="$(dirname "$candidate")"
			done
			GAME_DIR="$candidate"
			break
		fi
	fi
done

if [[ -z "$GAME_DIR" || ! -d "$GAME_DIR" ]]; then
	echo "[fix-execstack] Warning: Could not detect game directory, skipping patch."
else
	# Fast path: directly patch known Source Engine offenders without scanning.
	# patchelf --clear-execstack is a no-op if the flag is already cleared.
	for sofile in "$GAME_DIR"/bin/engine.so "$GAME_DIR"/bin/video_bink.so; do
		[[ -f "$sofile" ]] && patchelf --clear-execstack "$sofile" 2>/dev/null
	done
fi

# Launch the game
exec "$@"
