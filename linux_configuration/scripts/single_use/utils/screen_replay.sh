#!/usr/bin/env bash
# screen_replay.sh - Instant replay buffer for Linux (X11)
# Continuously records screen in segments; on hotkey, saves last 90 seconds
# and immediately plays it in mpv.

set -euo pipefail

REPLAY_DIR="${REPLAY_DIR:-/tmp/screen_replay}"
SAVE_DIR="${SAVE_DIR:-$HOME/Videos/replays}"
PID_FILE="$REPLAY_DIR/daemon.pid"
LOCK_FILE="$REPLAY_DIR/save.lock"
BUFFER_SECS="${BUFFER_SECS:-90}"
SEG_SECS=15
# segments needed: ceil(buffer/seg) + 1 for the one being written + 1 margin
SEG_WRAP=$(( (BUFFER_SECS / SEG_SECS) + 2 ))
FRAMERATE="${FRAMERATE:-30}"

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

FFMPEG="/usr/bin/ffmpeg"
FFPROBE="/usr/bin/ffprobe"

check_deps() {
    local missing=()
    [[ -x "$FFMPEG" ]]  || missing+=("ffmpeg")
    [[ -x "$FFPROBE" ]] || missing+=("ffprobe")
    for cmd in mpv xrandr; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    if (( ${#missing[@]} )); then
        die "Missing dependencies: ${missing[*]}"
    fi
}

is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

cmd_start() {
    check_deps
    mkdir -p "$REPLAY_DIR" "$SAVE_DIR"

    if is_running; then
        echo "Already running (PID: $(cat "$PID_FILE"))"
        return 0
    fi

    local display="${DISPLAY:-:0}"

    # Detect primary monitor geometry via xrandr
    local xrandr_line
    xrandr_line=$(xrandr | grep ' connected primary ' | head -1)
    [[ -n "$xrandr_line" ]] || die "Could not detect primary monitor (no 'primary' flag in xrandr)"

    local geometry
    geometry=$(printf '%s' "$xrandr_line" | grep -oP '\d+x\d+\+\d+\+\d+')
    [[ -n "$geometry" ]] || die "Could not parse primary monitor geometry"

    local resolution offset_x offset_y
    resolution=$(printf '%s' "$geometry" | grep -oP '^\d+x\d+')
    offset_x=$(printf '%s' "$geometry" | grep -oP '(?<=\+)\d+' | sed -n '1p')
    offset_y=$(printf '%s' "$geometry" | grep -oP '(?<=\+)\d+' | sed -n '2p')

    # Clean stale segments
    rm -f "$REPLAY_DIR"/seg*.mkv

    "$FFMPEG" -f x11grab -video_size "$resolution" -framerate "$FRAMERATE" \
        -i "${display}+${offset_x},${offset_y}" \
        -c:v libx264 -preset ultrafast -crf 23 \
        -g "$FRAMERATE" \
        -f segment -segment_time "$SEG_SECS" \
        -segment_wrap "$SEG_WRAP" \
        -reset_timestamps 1 \
        "$REPLAY_DIR/seg%02d.mkv" \
        </dev/null >"$REPLAY_DIR/ffmpeg.log" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"
    disown "$pid"

    # Give ffmpeg a moment to start (or fail)
    sleep 1
    if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$PID_FILE"
        echo "ffmpeg failed to start. Log:" >&2
        cat "$REPLAY_DIR/ffmpeg.log" >&2
        return 1
    fi

    echo "Replay daemon started (PID: $pid, buffer: ${BUFFER_SECS}s, segments: ${SEG_WRAP}x${SEG_SECS}s)"
}

cmd_save() {
    is_running || die "Daemon not running. Start with: $0 start"

    # Prevent concurrent saves
    exec 9>"$LOCK_FILE"
    flock -n 9 || die "Another save is already in progress"

    local timestamp output concat_file
    timestamp=$(date +%Y%m%d_%H%M%S)
    output="$SAVE_DIR/replay_${timestamp}.mp4"
    concat_file=$(mktemp /tmp/replay_concat.XXXXXX)

    # Collect segments sorted by modification time (oldest first)
    local -a segments=()
    while IFS=$'\t' read -r _ path; do
        segments+=("$path")
    done < <(find "$REPLAY_DIR" -maxdepth 1 -name 'seg*.mkv' -printf '%T@\t%p\n' 2>/dev/null | sort -n)

    (( ${#segments[@]} >= 1 )) || die "No recorded data yet"

    # The last segment is being actively written by ffmpeg.
    # Snapshot it so we capture everything up to this moment.
    local active_seg="${segments[-1]}"
    local snapshot="$REPLAY_DIR/_snapshot.mkv"
    cp -- "$active_seg" "$snapshot"

    # Use completed segments + snapshot of the active one
    local -a use_segments=()
    for seg in "${segments[@]:0:${#segments[@]}-1}"; do
        use_segments+=("$seg")
    done
    use_segments+=("$snapshot")

    # Build ffmpeg concat list
    for seg in "${use_segments[@]}"; do
        printf "file '%s'\n" "$seg"
    done > "$concat_file"

    # Concatenate with stream copy (near-instant)
    "$FFMPEG" -f concat -safe 0 -i "$concat_file" \
        -c copy -y "$output" 2>/dev/null

    # Trim to last BUFFER_SECS if the recording is longer
    local duration start
    duration=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$output")
    start=$(awk "BEGIN {v = $duration - $BUFFER_SECS; print (v > 0 ? v : 0)}")

    if awk "BEGIN {exit !($start > 1)}"; then
        local trimmed="${output%.mp4}_tmp.mp4"
        "$FFMPEG" -ss "$start" -i "$output" \
            -c copy -avoid_negative_ts make_zero \
            -y "$trimmed" 2>/dev/null
        mv -- "$trimmed" "$output"
    fi

    trap - EXIT
    rm -f "$concat_file" "$REPLAY_DIR/_snapshot.mkv"

    echo "Saved: $output"
    mpv --force-window=immediate "$output" &>/dev/null &
    disown
}

cmd_stop() {
    if is_running; then
        local pid
        pid=$(cat "$PID_FILE")
        kill -INT "$pid" 2>/dev/null || true
        for _ in {1..20}; do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.1
        done
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$PID_FILE" "$REPLAY_DIR"/seg*.mkv "$LOCK_FILE"
        echo "Daemon stopped"
    else
        echo "Not running"
        rm -f "$PID_FILE"
    fi
}

cmd_status() {
    if is_running; then
        echo "Running (PID: $(cat "$PID_FILE"))"
        local count size
        count=$(find "$REPLAY_DIR" -name 'seg*.mkv' 2>/dev/null | wc -l)
        size=$(du -sh "$REPLAY_DIR" 2>/dev/null | cut -f1)
        echo "Segments: $count/${SEG_WRAP}, Disk: $size"
    else
        echo "Not running"
    fi
}

usage() {
    cat <<EOF
Usage: $(basename "$0") {start|save|stop|status}

Instant screen replay buffer — records the last ${BUFFER_SECS}s of your screen.
Press your configured hotkey to save the buffer and play it back immediately.

Commands:
  start   Start the background recording daemon
  save    Save the last ${BUFFER_SECS}s and open in mpv
  stop    Stop the daemon and clean up temp files
  status  Show whether the daemon is running

Environment variables (override defaults):
  BUFFER_SECS  Replay buffer length in seconds  (default: 90)
  FRAMERATE    Recording frame rate              (default: 30)
  SAVE_DIR     Directory for saved replays       (default: ~/Videos/replays)
  DISPLAY      X11 display to capture            (default: :0)
EOF
}

case "${1:-help}" in
    start)  cmd_start ;;
    save)   cmd_save ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    *)      usage ;;
esac
