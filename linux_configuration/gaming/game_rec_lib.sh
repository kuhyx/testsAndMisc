#!/bin/bash
# ============================================================================
# game_rec_lib.sh: what game_rec.sh knows without touching the recorder.
# Sourced (never run) by game_rec.sh from its resolved dir.
#   - state files: the pidfile (recorder pid + output path), its removal
#     with the auto mark (game_rec.sh reads and writes the mark itself), and
#     the ownership rule that stops game-rec from ever signalling a
#     gpu-screen-recorder it did not start;
#   - game detection from the Steam reaper's NUL-split /proc argv;
#   - the game's monitor (xdotool window centre -> xrandr monitor);
#   - app-audio matching (--list-application-audio name, or the guessed names
#     while the game has no stream yet) and the output-file slug.
# Owns the globals below; game_rec.sh reads them after each call.
# ============================================================================

readonly GSR=gpu-screen-recorder
readonly DEFAULT_MONITOR=DP-2
readonly PROC_ROOT="${GAME_REC_PROC_ROOT:-/proc}"
readonly STATE_DIR="${XDG_RUNTIME_DIR:-/run/user/$UID}"
readonly PIDFILE="$STATE_DIR/game-rec.pid"
readonly AUTO_MARK="$STATE_DIR/game-rec.auto"

REC_PID='' REC_OUT='' GAME_APPID='' GAME_EXE='' GAME_DIR=''

read_pidfile() {
	REC_PID='' REC_OUT=''
	[[ -r $PIDFILE ]] || return 1
	{ read -r REC_PID && read -r REC_OUT; } <"$PIDFILE" || true
	[[ $REC_PID =~ ^[0-9]+$ && -n $REC_OUT ]]
}

# owns PID OUT: PID is a live gpu-screen-recorder writing exactly OUT.
owns() {
	local arg prev='' is_gsr=0 writes_out=0
	local -a argv=()
	[[ $1 =~ ^[0-9]+$ ]] || return 1
	mapfile -d '' argv 2>/dev/null <"/proc/$1/cmdline" || return 1
	for arg in "${argv[@]}"; do
		[[ ${arg##*/} == "$GSR" ]] && is_gsr=1
		[[ $prev == -o && $arg == "$2" ]] && writes_out=1
		prev=$arg
	done
	((is_gsr && writes_out))
}

recording() {
	read_pidfile && owns "$REC_PID" "$REC_OUT"
}

clear_state() {
	rm -f "$PIDFILE" "$AUTO_MARK"
}

# detect_game [APPID]: sets GAME_APPID and GAME_EXE (basename) from the Steam
# reaper, if any; with APPID only that game's reaper counts.
detect_game() {
	local want=${1:-} comm_file comm arg appid exe dir
	local -a argv
	for comm_file in "$PROC_ROOT"/[0-9]*/comm; do
		read -r comm 2>/dev/null <"$comm_file" || continue
		[[ $comm == reaper ]] || continue
		mapfile -d '' argv 2>/dev/null <"${comm_file%/comm}/cmdline" || continue
		[[ ${argv[1]:-} == SteamLaunch ]] || continue
		appid='' exe='' dir=''
		for arg in "${argv[@]}"; do
			[[ $arg == AppId=* ]] && appid=${arg#AppId=}
			if [[ ${arg,,} == *.exe ]]; then
				exe=${arg##*/}
				# steamapps/common/<game dir>/...: PipeWire often names the
				# game after it instead of the exe (Oh Deer -> "OhDeer").
				[[ $arg == */steamapps/common/*/* ]] && dir=${arg#*/steamapps/common/} dir=${dir%%/*}
			fi
		done
		[[ -z $want || $appid == "$want" ]] || continue
		[[ -n $exe ]] && GAME_APPID=$appid GAME_EXE=$exe GAME_DIR=$dir
	done
	[[ -z $want ]] || GAME_APPID=$want
	return 0
}

# monitor_at X Y: the xrandr monitor containing that point.
monitor_at() {
	local line name mw mh mx my
	local re='^ *[0-9]+: +[+*]*([^ ]+) +([0-9]+)/[0-9]+x([0-9]+)/[0-9]+\+([0-9]+)\+([0-9]+)'
	while IFS= read -r line; do
		[[ $line =~ $re ]] || continue
		name=${BASH_REMATCH[1]} mw=${BASH_REMATCH[2]} mh=${BASH_REMATCH[3]}
		mx=${BASH_REMATCH[4]} my=${BASH_REMATCH[5]}
		if (($1 >= mx && $1 < mx + mw && $2 >= my && $2 < my + mh)); then
			printf '%s\n' "$name"
			return 0
		fi
	done < <(xrandr --listmonitors 2>/dev/null)
	return 1
}

# monitor_of_window WIN: the monitor holding the window's centre.
monitor_of_window() {
	local key value
	local -A g=()
	[[ -n $1 ]] || return 1
	while IFS='=' read -r key value; do g[$key]=$value; done \
		< <(xdotool getwindowgeometry --shell "$1" 2>/dev/null)
	[[ -n ${g[X]:-} && -n ${g[Y]:-} && -n ${g[WIDTH]:-} && -n ${g[HEIGHT]:-} ]] || return 1
	monitor_at $((g[X] + g[WIDTH] / 2)) $((g[Y] + g[HEIGHT] / 2))
}

# detect_monitor [auto]: an auto start runs while the game is still loading,
# when the focused window is Steam's, so it skips that fallback.
detect_monitor() {
	local win
	if [[ -n $GAME_APPID ]]; then
		win=$(xdotool search --onlyvisible --class "^steam_app_${GAME_APPID}\$" 2>/dev/null |
			head -n 1) || win=''
		monitor_of_window "$win" && return 0
	fi
	if [[ -n $GAME_EXE && -z ${1:-} ]]; then
		win=$(xdotool getactivewindow 2>/dev/null) || win=''
		monitor_of_window "$win" && return 0
	fi
	printf '%s\n' "$DEFAULT_MONITOR"
}

# app_key NAME: NAME lowercased, minus a .exe suffix and every non-alphanumeric
# ("Oh Deer", "OhDeer.exe" and "ohdeer" all give "ohdeer").
app_key() {
	local s=${1,,}
	s=${s%.exe}
	printf '%s\n' "${s//[^a-z0-9]/}"
}

# match_app_audio NAME...: the --list-application-audio entry whose app_key
# equals any NAME's (the exe basename, the Steam game dir), in its spelling.
match_app_audio() {
	local app name key
	local -A want=()
	for name in "$@"; do
		[[ -n $name ]] || continue
		key=$(app_key "$name")
		[[ -z $key ]] || want[$key]=1
	done
	((${#want[@]})) || return 0
	while IFS= read -r app; do
		key=$(app_key "$app")
		[[ -n $key && -n ${want[$key]:-} ]] && printf '%s\n' "$app" && return 0
	done < <(timeout 5 "$GSR" --list-application-audio 2>/dev/null)
	return 0
}

# app_candidates: before the game opens audio its PipeWire name is unknown, so
# name every spelling it may use (exe, exe minus .exe, Steam dir), merged into
# one track; gpu-screen-recorder links app:<name> (any case) when the stream
# appears. Prints `A|app:B|app:C` (the caller adds the first `app:`).
app_candidates() {
	local name joined=''
	local -A seen=()
	for name in "$GAME_EXE" "${GAME_EXE%.[eE][xX][eE]}" "$GAME_DIR"; do
		[[ -n $name && -z ${seen[${name,,}]:-} ]] || continue
		seen[${name,,}]=1
		joined+="${joined:+|app:}$name"
	done
	printf '%s\n' "$joined"
}

slugify() {
	local s=${1,,}
	s=${s%.exe}
	s=${s//[^a-z0-9]/-}
	while [[ $s == *--* ]]; do s=${s//--/-}; done
	s=${s#-}
	printf '%s\n' "${s%-}"
}
