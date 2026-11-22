#!/bin/bash

# ============================================================================
# game-rec indicator for i3blocks: one red dot while a game-rec recording
# runs, nothing (block hidden) otherwise. No text: the dot is the whole cue
# (shape + red). i3bar has no tooltips, so there is none.
#
# Signal-driven, zero forks: the block is `interval=once` + `signal=12` in the
# i3blocks config; gaming/game_rec.sh sends `pkill -RTMIN+12 -x i3blocks` on
# start, stop and when the recorder exits. Only builtins run here: the
# pidfile is read with `read` and the pid checked against /proc/<pid>/cmdline
# (gpu-screen-recorder writing the pidfile's output path), the same ownership
# rule game_rec.sh uses, so a stale pidfile or a reused pid shows nothing.
# ============================================================================

set -euo pipefail

readonly PIDFILE="${XDG_RUNTIME_DIR:-/run/user/$UID}/game-rec.pid"
readonly DOT='●'
readonly RED='#FF5555'

emit() {
	# full_text, short_text, color: the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$1" "$2"
}

recording() {
	local pid='' out='' arg prev='' is_gsr=0 writes_out=0
	local -a argv=()
	[[ -r $PIDFILE ]] || return 1
	{ read -r pid && read -r out; } <"$PIDFILE" || true
	[[ $pid =~ ^[0-9]+$ && -n $out ]] || return 1
	mapfile -d '' argv 2>/dev/null <"/proc/$pid/cmdline" || return 1
	for arg in "${argv[@]}"; do
		[[ ${arg##*/} == gpu-screen-recorder ]] && is_gsr=1
		[[ $prev == -o && $arg == "$out" ]] && writes_out=1
		prev=$arg
	done
	((is_gsr && writes_out))
}

if recording; then
	emit "$DOT" "$RED"
else
	emit '' ''
fi
