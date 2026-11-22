#!/bin/bash
# ============================================================================
# game-rec start|stop|toggle|status|auto [on|off]: NVENC recording
# (gpu-screen-recorder) of the monitor the Steam game is on (window class
# steam_app_<AppId>, else the focused window, else DP-2) with three opus
# tracks in order: mic, the game only (the --list-application-audio entry that
# matches the exe or Steam dir name, ignoring case, spaces, punctuation and
# .exe), everything. The game comes from the Steam reaper's NUL-split /proc
# argv (paths with spaces).
# State: $XDG_RUNTIME_DIR/game-rec.pid = recorder pid + output path. stop and
# status act only on a pid whose cmdline is gpu-screen-recorder with that
# exact `-o <path>`; anything else (e.g. a systemd unit's recorder) is never
# signalled and its pidfile is stale. stop = SIGINT (finalises the file).
# Never deletes recordings. Refreshes the i3blocks block (signal 12) on
# start/stop and, via the detached `_watch` helper, when the recorder dies.
#
# Auto mode (gaming/game_rec_watch.sh, the game-rec-auto user service):
# `start --auto APPID` records that AppID's game, `stop --auto APPID` stops a
# recording only if it is marked auto for that AppID, `adopt APPID` marks the
# running recording auto. The mark is $XDG_RUNTIME_DIR/game-rec.auto (pid,
# output, AppID); it counts only while pid + output match the pidfile, so a
# manual (hotkey) recording is never stopped by the watcher. `auto off`
# pauses new auto starts until `auto on` or the next login.
# Overrides: GAME_REC_{DIR,MONITOR,FPS,MIN_FREE_GB,PROC_ROOT,START_GRACE,
# STOP_TIMEOUT,BAR_SIGNAL (0 = off),PKILL}.
# State-file, detection and app-audio helpers: gaming/game_rec_lib.sh.
# ============================================================================

set -euo pipefail

readonly SELF="${BASH_SOURCE[0]}"
SELF_DIR=$(dirname -- "$(readlink -f -- "$SELF")")
readonly SELF_DIR
readonly REC_DIR="${GAME_REC_DIR:-$HOME/Videos/recordings}"
readonly FPS="${GAME_REC_FPS:-60}"
readonly MIN_FREE_GB="${GAME_REC_MIN_FREE_GB:-20}"
readonly START_GRACE="${GAME_REC_START_GRACE:-1}"
readonly STOP_TIMEOUT="${GAME_REC_STOP_TIMEOUT:-15}"
readonly BAR_SIGNAL="${GAME_REC_BAR_SIGNAL:-12}"
readonly PKILL="${GAME_REC_PKILL:-pkill}"

# State files, game/monitor detection, app-audio matching; sets STATE_DIR,
# PIDFILE, GSR and the REC_*/GAME_* globals.
# shellcheck source=game_rec_lib.sh
source "$SELF_DIR/game_rec_lib.sh"

readonly AUTO_OFF="$STATE_DIR/game-rec.auto-off"
readonly LOG="$STATE_DIR/game-rec.log"

MARK_APPID=''

# auto_marked: the current recording (read_pidfile first) carries an auto
# mark; sets MARK_APPID.
auto_marked() {
	local pid='' out='' appid=''
	MARK_APPID=''
	[[ -r $AUTO_MARK ]] || return 1
	{ read -r pid && read -r out && read -r appid; } <"$AUTO_MARK" || true
	[[ $pid == "$REC_PID" && $out == "$REC_OUT" && $appid =~ ^[0-9]+$ ]] || return 1
	MARK_APPID=$appid
}

# write_mark APPID: mark the current recording auto (atomic replace).
write_mark() {
	printf '%s\n%s\n%s\n' "$REC_PID" "$REC_OUT" "$1" >"$AUTO_MARK.$$"
	mv -f "$AUTO_MARK.$$" "$AUTO_MARK"
}

usage() {
	printf 'Usage: %s start|stop|toggle|status|auto [on|off]\n' "${SELF##*/}"
}

die() {
	printf 'game-rec: %s\n' "$1" >&2
	exit 1
}

require_tools() {
	local tool
	for tool in "$GSR" xdotool xrandr setsid tail timeout df; do
		command -v "$tool" >/dev/null 2>&1 ||
			die "$tool missing: run linux_configuration/features/setup_game_rec.sh"
	done
}

refresh_bar() {
	((BAR_SIGNAL > 0)) || return 0
	"$PKILL" "-RTMIN+$BAR_SIGNAL" -x i3blocks >/dev/null 2>&1 || true
}

check_free_space() {
	local -a lines
	mapfile -t lines < <(df --output=avail -B1 -- "$REC_DIR")
	local avail=${lines[1]:-}
	avail=${avail// /}
	[[ $avail =~ ^[0-9]+$ ]] || die "cannot read free space of $REC_DIR"
	if ((avail < MIN_FREE_GB * 1024 * 1024 * 1024)); then
		printf 'game-rec: refusing, %d GB free in %s, need %d GB\n' \
			$((avail / 1024 / 1024 / 1024)) "$REC_DIR" "$MIN_FREE_GB" >&2
		return 1
	fi
}

# spawn_recorder MONITOR APP OUT [APPID]: start gpu-screen-recorder, write the
# pidfile (and the auto mark), and succeed if it is still up after the grace.
spawn_recorder() {
	local monitor=$1 app=$2 out=$3 auto=${4:-} pid
	local -a args=(-w "$monitor" -f "$FPS" -c mkv -k hevc -q high -ac opus -a default_input)
	[[ -z $app ]] || args+=(-a "app:$app")
	args+=(-a default_output -o "$out")
	# setsid execs (no fork) here, so $! is the recorder's own pid; env resets
	# SIGINT, which bash leaves ignored for background jobs.
	setsid env --default-signal=INT "$GSR" "${args[@]}" </dev/null >"$LOG" 2>&1 &
	pid=$!
	printf '%s\n%s\n' "$pid" "$out" >"$PIDFILE"
	REC_PID=$pid REC_OUT=$out
	[[ -z $auto ]] || write_mark "$auto"
	sleep "$START_GRACE"
	kill -0 "$pid" 2>/dev/null && return 0
	clear_state
	tail -n 5 "$LOG" >&2 || true
	return 1
}

# cmd_start [APPID]: with APPID it is an auto start for that Steam game.
cmd_start() {
	local auto=${1:-} monitor=${GAME_REC_MONITOR:-} app='' guessed='' slug=desktop stamp out
	recording && die "already recording: $REC_OUT"
	clear_state
	mkdir -p "$REC_DIR" "$STATE_DIR"
	check_free_space || return 1
	detect_game "$auto"
	[[ -n $monitor ]] || monitor=$(detect_monitor "$auto")
	if [[ -n $GAME_EXE ]]; then
		slug=$(slugify "$GAME_EXE")
		app=$(match_app_audio "$GAME_EXE" "$GAME_DIR")
		# No stream yet: an auto start runs while the game is still loading,
		# and a hotkey start may come right after launch.
		if [[ -z $app ]]; then
			app=$(app_candidates)
			guessed=1
		fi
	elif [[ -n $auto ]]; then
		slug="steam-$auto"
	fi
	printf -v stamp '%(%Y%m%d-%H%M%S)T' -1
	out="$REC_DIR/${slug:-game}-$stamp.mkv"
	[[ ! -e $out ]] || out="$REC_DIR/${slug:-game}-$stamp-$$.mkv"
	if ! spawn_recorder "$monitor" "$app" "$out" "$auto"; then
		# Guessed names are unproven: a recording without the game track
		# beats no recording.
		[[ -n $guessed ]] || die "recorder exited at once (log: $LOG)"
		printf 'game-rec: recorder refused app:%s, retrying without it\n' "$app" >&2
		spawn_recorder "$monitor" '' "$out" "$auto" ||
			die "recorder exited at once (log: $LOG)"
	fi
	setsid "$BASH" "$SELF" _watch "$REC_PID" </dev/null >/dev/null 2>&1 &
	refresh_bar
	printf '%s\n' "$out"
}

# cmd_stop [APPID]: with APPID, stop only an auto recording of that game.
cmd_stop() {
	read_pidfile || die 'not recording'
	if ! owns "$REC_PID" "$REC_OUT"; then
		clear_state
		refresh_bar
		die 'stale pidfile removed, nothing signalled'
	fi
	if [[ -n ${1:-} ]] && ! { auto_marked && [[ $MARK_APPID == "$1" ]]; }; then
		die "not an auto recording of $1, left running"
	fi
	kill -INT "$REC_PID"
	# Still finalising after the timeout: keep the pidfile, _watch clears it.
	timeout "$STOP_TIMEOUT" tail --pid="$REC_PID" -f /dev/null ||
		die "recorder $REC_PID still finalising $REC_OUT"
	clear_state
	refresh_bar
	printf '%s\n' "$REC_OUT"
}

# cmd_adopt APPID: mark the running recording auto, so it stops with the game.
cmd_adopt() {
	[[ $1 =~ ^[0-9]+$ ]] || die "bad AppID: $1"
	recording || die 'not recording'
	write_mark "$1"
	printf 'adopted %s for %s\n' "$REC_OUT" "$1"
}

cmd_status() {
	recording || { printf 'idle\n' && return 1; }
	if auto_marked; then
		printf 'recording pid=%s %s auto=%s\n' "$REC_PID" "$REC_OUT" "$MARK_APPID"
	else
		printf 'recording pid=%s %s\n' "$REC_PID" "$REC_OUT"
	fi
}

cmd_auto() {
	case ${1:-} in
	on) rm -f "$AUTO_OFF" ;;
	off) mkdir -p "$STATE_DIR" && : >"$AUTO_OFF" ;;
	'') if [[ -e $AUTO_OFF ]]; then printf 'off\n'; else printf 'on\n'; fi ;;
	*) usage >&2 && exit 2 ;;
	esac
}

# _watch PID: wait for the recorder to exit, then clear its pidfile and mark.
cmd_watch() {
	tail --pid="$1" -f /dev/null 2>/dev/null || true
	if read_pidfile && [[ $REC_PID == "$1" ]]; then
		clear_state
	fi
	refresh_bar
}

# auto_arg FLAG APPID: the AppID after --auto, or nothing without the flag.
auto_arg() {
	[[ -n ${1:-} ]] || return 0
	[[ $1 == --auto && ${2:-} =~ ^[0-9]+$ ]] || die 'usage: --auto APPID'
	printf '%s\n' "$2"
}

main() {
	local appid
	case ${1:-} in
	start) appid=$(auto_arg "${2:-}" "${3:-}") && require_tools && cmd_start "$appid" ;;
	stop) appid=$(auto_arg "${2:-}" "${3:-}") && cmd_stop "$appid" ;;
	toggle) if recording; then cmd_stop; else require_tools && cmd_start; fi ;;
	status) cmd_status ;;
	auto) cmd_auto "${2:-}" ;;
	adopt) cmd_adopt "${2:?appid}" ;;
	_watch) cmd_watch "${2:?pid}" ;;
	-h | --help) usage ;;
	*) usage >&2 && exit 2 ;;
	esac
}

main "$@"
