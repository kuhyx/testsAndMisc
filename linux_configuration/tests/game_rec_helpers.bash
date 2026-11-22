# Shared bats fixtures for gaming/game_rec.sh and i3blocks/game_rec.sh.
#
# Every external program the recorder touches is a stub on PATH that records
# what it was asked: gpu-screen-recorder (argv, one element per line, and the
# signals it got), xdotool, xrandr, df and pkill. Game detection reads a fake
# /proc tree (GAME_REC_PROC_ROOT), so the tests never see kuhy's real reaper,
# game window or live recording. The stub outputs copy the real formats
# captured on 2026-11-22 (xrandr --listmonitors, xdotool --shell, reaper argv).

REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SCRIPT="$REPO_DIR/gaming/game_rec.sh"
RAT_EXE='/home/kuhy/.local/share/Steam/steamapps/common/rat game/Rat Game.exe'

setup_stubs() {
	STUB_DIR="$BATS_TEST_TMPDIR/stub"
	local bin="$BATS_TEST_TMPDIR/bin"
	mkdir -p "$STUB_DIR" "$bin" "$BATS_TEST_TMPDIR/run" "$BATS_TEST_TMPDIR/proc"
	export STUB_DIR
	export XDG_RUNTIME_DIR="$BATS_TEST_TMPDIR/run"
	export GAME_REC_DIR="$BATS_TEST_TMPDIR/videos"
	export GAME_REC_PROC_ROOT="$BATS_TEST_TMPDIR/proc"
	export GAME_REC_START_GRACE=0 GAME_REC_STOP_TIMEOUT=5
	# Absolute path: a watcher that outlives the test finds no pkill at all
	# instead of falling back to the real one.
	export GAME_REC_PKILL="$bin/pkill"
	export PATH="$bin:$PATH"
	unset GAME_REC_MONITOR GAME_REC_FPS GAME_REC_MIN_FREE_GB GAME_REC_EVENTS
	unset GAME_REC_AUTO_GRACE GAME_REC_BIN

	cat >"$bin/gpu-screen-recorder" <<'EOF'
#!/bin/bash
set -euo pipefail
if [[ ${1:-} == --list-application-audio ]]; then
	cat "$STUB_DIR/apps"
	exit 0
fi
printf '%s\n' "$@" >"$STUB_DIR/argv.$$"
printf '%s\n' "$$" >>"$STUB_DIR/gsr_pids"
# GSR_STUB_REJECT_APP=1: die at once on any app: source (an unknown app name).
if [[ -n ${GSR_STUB_REJECT_APP:-} && " $* " == *' app:'* ]]; then
	exit 1
fi
child=0
on_signal() {
	printf '%s\n' "$1" >>"$STUB_DIR/signals.$$"
	kill "$child" 2>/dev/null || true
	exit 0
}
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM
sleep 300 &
child=$!
wait "$child"
EOF
	cat >"$bin/xdotool" <<'EOF'
#!/bin/bash
set -euo pipefail
printf '%s\n' "$*" >>"$STUB_DIR/xdotool_calls"
case $1 in
search) [[ -s $STUB_DIR/game_win ]] && cat "$STUB_DIR/game_win" || exit 1 ;;
getactivewindow) [[ -s $STUB_DIR/active_win ]] && cat "$STUB_DIR/active_win" || exit 1 ;;
getwindowgeometry) cat "$STUB_DIR/geom.$3" ;;
esac
EOF
	cat >"$bin/xrandr" <<'EOF'
#!/bin/bash
printf 'Monitors: 2\n'
printf ' 0: +*DP-2 3840/620x2160/340+0+0  DP-2\n'
printf ' 1: +HDMI-0 2560/698x1440/393+3840+0  HDMI-0\n'
EOF
	cat >"$bin/df" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >>"$STUB_DIR/df_calls"
printf '    Avail\n%s\n' "$(cat "$STUB_DIR/df_avail")"
EOF
	cat >"$bin/pkill" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >>"$STUB_DIR/pkill_calls"
EOF
	# systemd-run --user --scope ... -- CMD: record the options, run CMD in place.
	cat >"$bin/systemd-run" <<'EOF'
#!/bin/bash
opts=()
while (($#)) && [[ $1 != -- ]]; do opts+=("$1") && shift; done
printf '%s\n' "${opts[*]}" >>"$STUB_DIR/systemd_run_calls"
shift
exec "$@"
EOF
	chmod +x "$bin"/*
	printf '%s\n' vesktop 'Rat Game.exe' >"$STUB_DIR/apps"
	printf '%s\n' $((500 * 1024 * 1024 * 1024)) >"$STUB_DIR/df_avail"
	: >"$STUB_DIR/gsr_pids"
}

# Kill every stub recorder and decoy this test started (never anything else).
teardown_stubs() {
	local pid
	while read -r pid; do
		kill -TERM "$pid" 2>/dev/null || true
	done <"$STUB_DIR/gsr_pids"
}

# make_reaper PID APPID EXE: a Steam reaper as /proc shows it (NUL-split argv).
make_reaper() {
	local dir="$GAME_REC_PROC_ROOT/$1"
	mkdir -p "$dir"
	printf 'reaper\n' >"$dir/comm"
	printf '%s\0' /home/kuhy/.local/share/Steam/steamrt64/reaper SteamLaunch \
		"AppId=$2" -- \
		/home/kuhy/.local/share/Steam/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point \
		--verb=waitforexitandrun -- \
		'/home/kuhy/.local/share/Steam/steamapps/common/Proton - Experimental/proton' \
		waitforexitandrun "$3" >"$dir/cmdline"
}

# The launch client also carries "reaper SteamLaunch" in its argv; it must
# never count as the game.
make_launch_client() {
	local dir="$GAME_REC_PROC_ROOT/$1"
	mkdir -p "$dir"
	printf 'steam-runtime-l\n' >"$dir/comm"
	printf '%s\0' steam-runtime-launch-client -- /bin/sh -c \
		"reaper SteamLaunch AppId=99 -- $RAT_EXE" >"$dir/cmdline"
}

# set_geom ID X Y W H: what `xdotool getwindowgeometry --shell ID` prints.
set_geom() {
	printf 'WINDOW=%s\nX=%s\nY=%s\nWIDTH=%s\nHEIGHT=%s\nSCREEN=0\n' "$@" \
		>"$STUB_DIR/geom.$1"
}
set_game_window() {
	set_geom "$@"
	printf '%s\n' "$1" >"$STUB_DIR/game_win"
}
set_active_window() {
	set_geom "$@"
	printf '%s\n' "$1" >"$STUB_DIR/active_win"
}

# fd 3 closed: bats would otherwise wait for the detached recorder/watcher.
run_script() {
	bash "$SCRIPT" "$@" 3>&-
}
rec() {
	run run_script "$@"
}

# Wait (max 5 s) until the Nth stub recorder has written its argv.
wait_for_recorder() {
	local n=${1:-1} _
	for _ in {1..50}; do
		(($(wc -l <"$STUB_DIR/gsr_pids") >= n)) && return 0
		sleep 0.1
	done
	return 1
}

last_pid() { tail -n 1 "$STUB_DIR/gsr_pids"; }
last_argv() { cat "$STUB_DIR/argv.$(last_pid)"; }

# expected_argv MONITOR FPS [APP]: the exact argv minus the trailing path.
expected_argv() {
	printf '%s\n' -w "$1" -f "$2" -c mkv -k hevc -q high -ac opus -a default_input
	[[ -z ${3:-} ]] || printf '%s\n' -a "app:$3"
	printf '%s\n' -a default_output -o
}

# assert_argv MONITOR FPS SLUG [APP]
assert_argv() {
	local argv want n
	wait_for_recorder
	argv=$(last_argv)
	want=$(expected_argv "$1" "$2" "${4:-}")
	n=$(wc -l <<<"$want")
	[[ $(head -n "$n" <<<"$argv") == "$want" ]] || {
		printf 'argv:\n%s\nwant:\n%s\n' "$argv" "$want" >&2
		return 1
	}
	[[ $(wc -l <<<"$argv") -eq $((n + 1)) ]]
	[[ $(tail -n 1 <<<"$argv") =~ ^$GAME_REC_DIR/$3-[0-9]{8}-[0-9]{6}\.mkv$ ]]
}
