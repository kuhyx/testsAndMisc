#!/usr/bin/env bats
# game_rec.sh state: pidfile start/stop/stale, the free-space refusal, the
# bar refresh, and the rule that stop only ever signals its own recorder.

load game_rec_helpers

BLOCK="$REPO_DIR/i3blocks/game_rec.sh"

setup() {
	setup_stubs
	PIDFILE="$XDG_RUNTIME_DIR/game-rec.pid"
}

teardown() {
	teardown_stubs
}

# A stub recorder this script did NOT start (stands in for game-rec.service).
spawn_decoy() {
	"$BATS_TEST_TMPDIR/bin/gpu-screen-recorder" -o "$BATS_TEST_TMPDIR/other.mkv" \
		</dev/null >/dev/null 2>&1 3>&- &
	wait_for_recorder 1
	DECOY=$(last_pid)
}

@test "start writes the recorder's pid and output; status reports it" {
	rec start
	[ "$status" -eq 0 ]
	wait_for_recorder
	[ "$(sed -n 1p "$PIDFILE")" = "$(last_pid)" ]
	[ "$(sed -n 2p "$PIDFILE")" = "$(tail -n 1 <<<"$(last_argv)")" ]
	rec status
	[ "$status" -eq 0 ]
	[[ $output == *"$(sed -n 2p "$PIDFILE")"* ]]
}

@test "second start refuses while recording; one recorder only" {
	rec start
	wait_for_recorder
	rec start
	[ "$status" -ne 0 ]
	[ "$(wc -l <"$STUB_DIR/gsr_pids")" -eq 1 ]
}

@test "stop sends SIGINT to its own recorder and clears the pidfile" {
	rec start
	wait_for_recorder
	pid=$(last_pid)
	rec stop
	[ "$status" -eq 0 ]
	[ "$(cat "$STUB_DIR/signals.$pid")" = INT ]
	run kill -0 "$pid"
	[ "$status" -ne 0 ]
	[ ! -e "$PIDFILE" ]
	rec status
	[ "$status" -ne 0 ]
}

@test "a stale pidfile (dead pid) does not block start" {
	sleep 0 &
	dead=$!
	wait "$dead"
	printf '%s\n%s\n' "$dead" "$GAME_REC_DIR/old.mkv" >"$PIDFILE"
	rec status
	[ "$status" -ne 0 ]
	rec start
	[ "$status" -eq 0 ]
	wait_for_recorder
	[ "$(sed -n 1p "$PIDFILE")" = "$(last_pid)" ]
}

@test "stop never signals a recorder that is not its own" {
	spawn_decoy
	printf '%s\n%s\n' "$DECOY" "$GAME_REC_DIR/mine.mkv" >"$PIDFILE"
	rec stop
	[ "$status" -ne 0 ]
	kill -0 "$DECOY"
	[ ! -e "$STUB_DIR/signals.$DECOY" ]
	[ ! -e "$PIDFILE" ]
	rec status
	[ "$status" -ne 0 ]
}

@test "start ignores a foreign recorder and stop leaves it running" {
	spawn_decoy
	rec start
	[ "$status" -eq 0 ]
	wait_for_recorder 2
	rec stop
	[ "$status" -eq 0 ]
	kill -0 "$DECOY"
	[ ! -e "$STUB_DIR/signals.$DECOY" ]
}

@test "stop with nothing recording signals nothing" {
	spawn_decoy
	rec stop
	[ "$status" -ne 0 ]
	kill -0 "$DECOY"
	[ ! -e "$STUB_DIR/signals.$DECOY" ]
}

@test "refuses to start with less than 20 GB free" {
	printf '%s\n' $((20 * 1024 * 1024 * 1024 - 1)) >"$STUB_DIR/df_avail"
	rec start
	[ "$status" -ne 0 ]
	[[ $output == *refusing* ]]
	[ ! -s "$STUB_DIR/gsr_pids" ]
	[ ! -e "$PIDFILE" ]
}

@test "exactly 20 GB free is enough" {
	printf '%s\n' $((20 * 1024 * 1024 * 1024)) >"$STUB_DIR/df_avail"
	rec start
	[ "$status" -eq 0 ]
}

@test "toggle starts, then stops" {
	rec toggle
	[ "$status" -eq 0 ]
	wait_for_recorder
	pid=$(last_pid)
	rec toggle
	[ "$status" -eq 0 ]
	[ "$(cat "$STUB_DIR/signals.$pid")" = INT ]
	[ ! -e "$PIDFILE" ]
}

@test "start and stop refresh the bar with RTMIN+12" {
	rec start
	wait_for_recorder
	[ "$(cat "$STUB_DIR/pkill_calls")" = "-RTMIN+12 -x i3blocks" ]
	rec stop
	[ "$(wc -l <"$STUB_DIR/pkill_calls")" -ge 2 ]
	[ "$(sort -u "$STUB_DIR/pkill_calls")" = "-RTMIN+12 -x i3blocks" ]
}

@test "a recorder that dies on its own clears the pidfile" {
	rec start
	wait_for_recorder
	kill -TERM "$(last_pid)"
	for _ in {1..40}; do
		[ -e "$PIDFILE" ] || break
		sleep 0.1
	done
	[ ! -e "$PIDFILE" ]
}

@test "bar block: hidden idle, red dot while recording, hidden when stale" {
	run bash "$BLOCK"
	[ "$status" -eq 0 ]
	[ -z "${output//$'\n'/}" ]
	rec start
	wait_for_recorder
	run bash "$BLOCK"
	[ "$output" = $'●\n●\n#FF5555' ]
	kill -TERM "$(last_pid)"
	printf '999999999\n%s\n' "$GAME_REC_DIR/x.mkv" >"$PIDFILE"
	run bash "$BLOCK"
	[ -z "${output//$'\n'/}" ]
}

@test "through the ~/.local/bin/game-rec symlink it still finds its lib" {
	mkdir -p "$BATS_TEST_TMPDIR/link"
	ln -s "$SCRIPT" "$BATS_TEST_TMPDIR/link/game-rec"
	run "$BATS_TEST_TMPDIR/link/game-rec" --help
	[ "$status" -eq 0 ]
	[ "$output" = 'Usage: game-rec start|stop|toggle|status|auto [on|off]' ]
	run "$BATS_TEST_TMPDIR/link/game-rec" status
	[ "$status" -eq 1 ]
	[ "$output" = idle ]
}
