#!/usr/bin/env bats
# game_rec_watch.sh: start a recording when a Steam game scope appears, stop
# it 30 s (here GAME_REC_AUTO_GRACE) after the last scope of that AppID goes,
# never touch a manual recording, adopt the one running at startup.
# The D-Bus side is a FIFO fed with the lines game_rec_scopes.py prints
# (format checked against the live helper on 2026-11-22: `new app-steam-
# app2708450-1226153.scope`, then `sync`); the recorder, xdotool
# and systemd-run are the stubs from game_rec_helpers.bash.

load game_rec_helpers

WATCH="$REPO_DIR/gaming/game_rec_watch.sh"
BLOCK="$REPO_DIR/i3blocks/game_rec.sh"
RAT_SCOPE=app-steam-app3347910-325827.scope
RAT_SCOPE2=app-steam-app3347910-400100.scope

setup() {
	setup_stubs
	PIDFILE="$XDG_RUNTIME_DIR/game-rec.pid"
	WATCH_LOG="$BATS_TEST_TMPDIR/watch.log"
	WATCH_PID=''
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_game_window 109051905 0 0 3840 2160
}

teardown() {
	stop_watcher
	teardown_stubs
}

# start_watcher GRACE: run the watcher on a fresh FIFO; fd 4 feeds it.
start_watcher() {
	local fifo="$BATS_TEST_TMPDIR/events.$RANDOM"
	mkfifo "$fifo"
	GAME_REC_EVENTS="$fifo" GAME_REC_AUTO_GRACE="${1:-1}" \
		bash "$WATCH" </dev/null >>"$WATCH_LOG" 2>&1 3>&- &
	WATCH_PID=$!
	# Read-write open never blocks, even if the watcher died at once.
	exec 4<>"$fifo"
}

stop_watcher() {
	exec 4>&-
	[[ -z $WATCH_PID ]] || kill "$WATCH_PID" 2>/dev/null || true
	[[ -z $WATCH_PID ]] || wait "$WATCH_PID" 2>/dev/null || true
	WATCH_PID=''
}

feed() {
	printf '%s\n' "$@" >&4
}

# wait_log LINE [N]: wait (max 5 s) until LINE is in the watcher log N times.
wait_log() {
	local n=${2:-1} _
	for _ in {1..50}; do
		(($(grep -cxF -- "$1" "$WATCH_LOG" 2>/dev/null) >= n)) && return 0
		sleep 0.1
	done
	printf 'no "%s" x%s in watcher log:\n' "$1" "$n" >&2
	cat "$WATCH_LOG" >&2
	return 1
}

recorders() { wc -l <"$STUB_DIR/gsr_pids"; }

@test "a new Steam scope starts an auto recording in its own scope" {
	start_watcher 1
	feed sync "new $RAT_SCOPE"
	wait_log 'start 3347910'
	assert_argv DP-2 60 rat-game 'Rat Game.exe'
	grep -q -- '--user --scope' "$STUB_DIR/systemd_run_calls"
	rec status
	[ "$status" -eq 0 ]
	[[ $output == *' auto=3347910' ]]
	run bash "$BLOCK"
	[ "$output" = $'●\n●\n#FF5555' ]
	grep -qxF -- '-RTMIN+12 -x i3blocks' "$STUB_DIR/pkill_calls"
}

@test "auto start adds the game track before the game opens audio" {
	printf 'vesktop\n' >"$STUB_DIR/apps"
	start_watcher 1
	feed sync "new $RAT_SCOPE"
	wait_log 'start 3347910'
	assert_argv DP-2 60 rat-game 'Rat Game.exe|app:Rat Game'
}

@test "auto start ignores the focused window and names a reaperless game by AppID" {
	rm "$STUB_DIR/game_win"
	set_active_window 88 3840 0 2560 1440
	start_watcher 1
	feed sync 'new app-steam-app123-1.scope'
	wait_log 'start 123'
	assert_argv DP-2 60 steam-123
}

@test "stop after grace: SIGINT, pidfile and auto mark cleared, bar refreshed" {
	start_watcher 2
	feed sync "new $RAT_SCOPE"
	wait_log 'start 3347910'
	wait_for_recorder
	pid=$(last_pid)
	feed "removed $RAT_SCOPE"
	wait_log 'grace 3347910'
	sleep 1
	kill -0 "$pid"
	[ ! -e "$STUB_DIR/signals.$pid" ]
	wait_log 'stop 3347910'
	[ "$(cat "$STUB_DIR/signals.$pid")" = INT ]
	[ ! -e "$PIDFILE" ]
	[ ! -e "$XDG_RUNTIME_DIR/game-rec.auto" ]
	[ "$(wc -l <"$STUB_DIR/pkill_calls")" -ge 2 ]
}

@test "relaunch within grace keeps the same recording and file" {
	start_watcher 2
	feed sync "new $RAT_SCOPE"
	wait_log 'start 3347910'
	wait_for_recorder
	pid=$(last_pid)
	out=$(sed -n 2p "$PIDFILE")
	feed "removed $RAT_SCOPE"
	wait_log 'grace 3347910'
	feed "new $RAT_SCOPE2"
	wait_log 'resume 3347910'
	sleep 3
	kill -0 "$pid"
	[ ! -e "$STUB_DIR/signals.$pid" ]
	[ "$(recorders)" -eq 1 ]
	[ "$(sed -n 2p "$PIDFILE")" = "$out" ]
	run ! grep -qx 'stop 3347910' "$WATCH_LOG"
}

@test "two scopes of one game: grace starts only when the last one goes" {
	start_watcher 1
	feed sync "new $RAT_SCOPE" "new $RAT_SCOPE2"
	wait_log 'start 3347910'
	wait_for_recorder
	pid=$(last_pid)
	feed "removed $RAT_SCOPE"
	sleep 2
	kill -0 "$pid"
	run ! grep -qx 'grace 3347910' "$WATCH_LOG"
	feed "removed $RAT_SCOPE2"
	wait_log 'stop 3347910'
	[ "$(cat "$STUB_DIR/signals.$pid")" = INT ]
}

@test "a manual recording is never stopped or doubled" {
	start_watcher 1
	feed sync
	wait_log sync
	rec start
	[ "$status" -eq 0 ]
	wait_for_recorder
	pid=$(last_pid)
	feed "new $RAT_SCOPE"
	wait_log 'busy 3347910'
	feed "removed $RAT_SCOPE"
	wait_log 'gone 3347910'
	sleep 2
	kill -0 "$pid"
	[ ! -e "$STUB_DIR/signals.$pid" ]
	[ "$(recorders)" -eq 1 ]
	rec stop --auto 3347910
	[ "$status" -ne 0 ]
	kill -0 "$pid"
	[ ! -e "$STUB_DIR/signals.$pid" ]
	rec status
	[[ $output != *auto* ]]
}

@test "adopts the recording running at startup, then stops it after the game" {
	rec start
	wait_for_recorder
	pid=$(last_pid)
	start_watcher 1
	feed "new $RAT_SCOPE" sync
	wait_log 'adopt 3347910'
	rec status
	[[ $output == *' auto=3347910' ]]
	[ "$(recorders)" -eq 1 ]
	feed "removed $RAT_SCOPE"
	wait_log 'stop 3347910'
	[ "$(cat "$STUB_DIR/signals.$pid")" = INT ]
	[ ! -e "$PIDFILE" ]
}

@test "no adoption without a live game scope" {
	rec start
	wait_for_recorder
	start_watcher 1
	feed sync
	wait_log sync
	rec status
	[[ $output != *auto* ]]
}

@test "auto off pauses starts across watcher restarts; auto on resumes" {
	rec auto off
	[ "$status" -eq 0 ]
	rec auto
	[ "$output" = off ]
	start_watcher 1
	feed sync "new $RAT_SCOPE"
	wait_log 'off 3347910'
	stop_watcher
	start_watcher 1
	feed sync "new $RAT_SCOPE"
	wait_log 'off 3347910' 2
	[ "$(recorders)" -eq 0 ]
	rec auto on
	[ "$status" -eq 0 ]
	rec auto
	[ "$output" = on ]
	feed "removed $RAT_SCOPE" "new $RAT_SCOPE2"
	wait_log 'start 3347910'
	wait_for_recorder
}

@test "auto off still stops the auto recording that is already running" {
	start_watcher 1
	feed sync "new $RAT_SCOPE"
	wait_log 'start 3347910'
	wait_for_recorder
	pid=$(last_pid)
	rec auto off
	feed "removed $RAT_SCOPE"
	wait_log 'stop 3347910'
	[ "$(cat "$STUB_DIR/signals.$pid")" = INT ]
}

@test "unrelated scopes are ignored" {
	start_watcher 1
	feed sync 'new app-firefox-12.scope' 'new app-steam-appx-1.scope' \
		'new run-u5.scope' 'removed app-firefox-12.scope' 'bogus line'
	wait_log 'ignore app-steam-appx-1.scope'
	wait_log 'ignore bogus line'
	[ "$(recorders)" -eq 0 ]
	[ ! -e "$STUB_DIR/systemd_run_calls" ]
}

@test "the watcher exits non-zero when the event stream ends" {
	start_watcher 1
	feed sync
	wait_log sync
	exec 4>&-
	rc=0
	wait "$WATCH_PID" || rc=$?
	WATCH_PID=''
	[ "$rc" -ne 0 ]
}

@test "auto start before audio names every spelling the game may use" {
	make_reaper 4044285 2708450 '/home/kuhy/.local/share/Steam/steamapps/common/Oh Deer/OhDeer.exe'
	printf 'vesktop\n' >"$STUB_DIR/apps"
	start_watcher 1
	feed sync 'new app-steam-app2708450-1226153.scope'
	wait_log 'start 2708450'
	assert_argv DP-2 60 ohdeer 'OhDeer.exe|app:OhDeer|app:Oh Deer'
}

@test "auto start retries without the game track if the recorder rejects it" {
	printf 'vesktop\n' >"$STUB_DIR/apps"
	export GSR_STUB_REJECT_APP=1 GAME_REC_START_GRACE=0.5
	start_watcher 1
	feed sync "new $RAT_SCOPE"
	wait_log 'start 3347910'
	wait_for_recorder 2
	assert_argv DP-2 60 rat-game
	rec status
	[[ $output == *' auto=3347910' ]]
}
