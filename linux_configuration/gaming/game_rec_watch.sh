#!/bin/bash
# ============================================================================
# game-rec auto watcher (the game-rec-auto user service): record every Steam
# game automatically.
#
# Events come from game_rec_scopes.py, one line each: `new <unit>`,
# `removed <unit>` for Steam's app-steam-app<AppID>-<pid>.scope units, and
# one `sync` after the scopes already running at startup. Zero polling: the
# loop blocks in `read`; the 30 s exit grace is the `read -t` timeout, so
# nothing wakes while no game starts or stops, and only bash builtins run per
# event until there is something to do.
#
# - new scope, nothing recording, `game-rec auto` on: `game-rec start --auto
#   <AppID>`, inside its own transient scope (systemd-run --scope), so a
#   watcher restart never kills the recording.
# - last scope of that AppID gone: after GRACE s `game-rec stop --auto <AppID>`
#   (SIGINT, finalises the file). A scope of the same AppID within the grace
#   keeps the same recording. game-rec refuses to stop anything not marked
#   auto, so manual (hotkey) recordings are never stopped.
# - sync: a recording already running while a game runs is adopted (marked
#   auto for that game); an auto recording whose game is gone gets the grace.
# - `auto off` blocks new starts only; a running auto recording still stops
#   with its game. A different game during the grace is started after the
#   stop.
# - The event stream ending (helper died) exits 1; systemd restarts us.
# Overrides: GAME_REC_AUTO_GRACE (s), GAME_REC_EVENTS (read this file or FIFO
# instead of running the helper), GAME_REC_BIN (game_rec.sh to call).
# ============================================================================

set -euo pipefail

SELF_DIR=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")
readonly SELF_DIR
readonly GAME_REC="${GAME_REC_BIN:-$SELF_DIR/game_rec.sh}"
readonly HELPER="$SELF_DIR/game_rec_scopes.py"
readonly GRACE="${GAME_REC_AUTO_GRACE:-30}"
readonly EVENTS="${GAME_REC_EVENTS:-}"
readonly AUTO_OFF="${XDG_RUNTIME_DIR:-/run/user/$UID}/game-rec.auto-off"
readonly SCOPE_RE='^app-steam-app([0-9]+)-[0-9]+\.scope$'
readonly AUTO_RE=' auto=([0-9]+)$'

declare -A LIVE=()     # unit -> AppID, for every live Steam scope
declare -A DEADLINE=() # AppID -> epoch second its grace ends
SYNCED=0
REC_STATUS='' # last `game-rec status` line ('' = not recording)

log() {
	printf '%s\n' "$*"
}

game_rec() {
	"$BASH" "$GAME_REC" "$@"
}

# refresh_status: REC_STATUS = `game-rec status`, '' when idle.
refresh_status() {
	REC_STATUS=$(game_rec status 2>/dev/null) || REC_STATUS=''
}

# app_live APPID: some live scope belongs to APPID.
app_live() {
	local unit
	for unit in "${!LIVE[@]}"; do
		[[ ${LIVE[$unit]} == "$1" ]] && return 0
	done
	return 1
}

maybe_start() {
	local appid=$1
	if [[ -e $AUTO_OFF ]]; then
		log "off $appid"
		return 0
	fi
	refresh_status
	if [[ -n $REC_STATUS ]]; then
		log "busy $appid"
		return 0
	fi
	if systemd-run --user --scope --collect --quiet -- \
		"$BASH" "$GAME_REC" start --auto "$appid" >/dev/null; then
		log "start $appid"
	else
		log "start failed $appid"
	fi
}

on_new() {
	local unit=$1 appid
	if [[ ! $unit =~ $SCOPE_RE ]]; then
		log "ignore $unit"
		return 0
	fi
	appid=${BASH_REMATCH[1]}
	LIVE[$unit]=$appid
	if [[ -n ${DEADLINE[$appid]:-} ]]; then
		unset "DEADLINE[$appid]"
		log "resume $appid"
		return 0
	fi
	((SYNCED)) || return 0
	app_live_others "$unit" "$appid" || maybe_start "$appid"
}

# app_live_others UNIT APPID: APPID has a live scope other than UNIT.
app_live_others() {
	local other
	for other in "${!LIVE[@]}"; do
		[[ $other != "$1" && ${LIVE[$other]} == "$2" ]] && return 0
	done
	return 1
}

# grace_if_auto APPID: start the grace if the recording is auto for APPID.
grace_if_auto() {
	refresh_status
	[[ $REC_STATUS =~ $AUTO_RE && ${BASH_REMATCH[1]} == "$1" ]] || return 0
	DEADLINE[$1]=$((EPOCHSECONDS + GRACE))
	log "grace $1"
}

on_removed() {
	local unit=$1 appid
	if [[ ! $unit =~ $SCOPE_RE ]]; then
		log "ignore $unit"
		return 0
	fi
	appid=${LIVE[$unit]:-}
	[[ -n $appid ]] || return 0
	unset "LIVE[$unit]"
	app_live "$appid" && return 0
	log "gone $appid"
	grace_if_auto "$appid"
}

on_sync() {
	local unit appid
	SYNCED=1
	log sync
	refresh_status
	[[ -n $REC_STATUS ]] || return 0
	if [[ $REC_STATUS =~ $AUTO_RE ]]; then
		appid=${BASH_REMATCH[1]}
		app_live "$appid" || grace_if_auto "$appid"
		return 0
	fi
	for unit in "${!LIVE[@]}"; do
		appid=${LIVE[$unit]}
		game_rec adopt "$appid" >/dev/null && log "adopt $appid"
		return 0
	done
}

# expire: stop every recording whose grace has ended, then start a game that
# is still running (a different AppID that came up during the grace).
expire() {
	local appid unit
	for appid in "${!DEADLINE[@]}"; do
		((DEADLINE[$appid] <= EPOCHSECONDS)) || continue
		unset "DEADLINE[$appid]"
		if game_rec stop --auto "$appid" >/dev/null; then
			log "stop $appid"
		else
			log "stop skipped $appid"
		fi
		for unit in "${!LIVE[@]}"; do
			maybe_start "${LIVE[$unit]}"
			break
		done
	done
}

# next_wait: WAIT = seconds until the earliest grace ends ('' = none).
next_wait() {
	local appid
	WAIT=''
	for appid in "${!DEADLINE[@]}"; do
		if [[ -z $WAIT ]] || ((DEADLINE[$appid] - EPOCHSECONDS < WAIT)); then
			WAIT=$((DEADLINE[$appid] - EPOCHSECONDS))
		fi
	done
}

handle() {
	local verb=${1%% *} arg=${1#* }
	case $verb in
	new) on_new "$arg" ;;
	removed) on_removed "$arg" ;;
	sync) on_sync ;;
	*) log "ignore $1" ;;
	esac
}

watch_events() {
	local fd=$1 line rc WAIT
	while :; do
		next_wait
		if [[ -z $WAIT ]]; then
			IFS= read -r line <&"$fd" || return 1
			handle "$line"
		elif ((WAIT <= 0)); then
			expire
		elif IFS= read -r -t "$WAIT" line <&"$fd"; then
			handle "$line"
		else
			rc=$?
			((rc > 128)) || return 1
			expire
		fi
	done
}

main() {
	local fd
	if [[ -n $EVENTS ]]; then
		exec {fd}<"$EVENTS"
	else
		exec {fd}< <(exec /usr/bin/python3 "$HELPER")
	fi
	if ! watch_events "$fd"; then
		log 'event stream ended'
		exit 1
	fi
}

main "$@"
