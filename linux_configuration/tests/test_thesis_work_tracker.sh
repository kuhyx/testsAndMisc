#!/bin/bash
# Regression tests for thesis_work_tracker.sh helper behavior.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
TARGET_SCRIPT="$REPO_DIR/scripts/digital_wellbeing/thesis_work_tracker.sh"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_equals() {
  local expected="$1"
  local actual="$2"
  local context="$3"
  if [[ "$expected" != "$actual" ]]; then
    fail "$context (expected: '$expected', actual: '$actual')"
  fi
}

TMP_DIR=$(mktemp -d)
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

WORKTREE="$TMP_DIR/worktree"
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$WORKTREE/scripts/digital_wellbeing" "$BIN_DIR"
cp "$TARGET_SCRIPT" "$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh"

cat >"$BIN_DIR/xdotool" <<'EOF'
#!/bin/bash
case "$*" in
  'getactivewindow')
    printf '12345\n'
    ;;
  'getwindowpid 12345')
    printf '6789\n'
    ;;
  'getwindowname 12345')
    printf '%s\n' "${MOCK_WINDOW_TITLE:-Document - praca_magisterska - Visual Studio Code}"
    ;;
  *)
    printf 'unexpected xdotool args: %s\n' "$*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$BIN_DIR/xdotool"

cat >"$BIN_DIR/ps" <<'EOF'
#!/bin/bash
printf '%s\n' "${MOCK_PROCESS_NAME:-Code}"
EOF
chmod +x "$BIN_DIR/ps"

cat >"$BIN_DIR/pgrep" <<'EOF'
#!/bin/bash
exit 1
EOF
chmod +x "$BIN_DIR/pgrep"

cat >"$BIN_DIR/date" <<'EOF'
#!/bin/bash
printf 'date should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/date"

source_env() {
  PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; $1"
}

source_env_with_proc() {
  local proc_root="$1"
  local cmd="$2"
  PATH="$BIN_DIR:$PATH" PROC_ROOT="$proc_root" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; $cmd"
}

printf 'Checking helper output for VS Code on thesis repo...\n'
result=$(source_env 'get_active_window_info')
assert_equals 'Code|Document - praca_magisterska - Visual Studio Code' "$result" \
  'get_active_window_info should return process and title for VS Code'

printf 'Checking helper reads process name from /proc before ps...\n'
PROC_WINDOW_DIR="$TMP_DIR/proc-window"
mkdir -p "$PROC_WINDOW_DIR/6789"
printf 'Code\n' >"$PROC_WINDOW_DIR/6789/comm"
cat >"$BIN_DIR/ps" <<'EOF'
#!/bin/bash
printf 'ps should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/ps"

result_proc=$(MOCK_WINDOW_TITLE='Document - praca_magisterska - Visual Studio Code' \
  source_env_with_proc "$PROC_WINDOW_DIR" 'get_active_window_info')
assert_equals 'Code|Document - praca_magisterska - Visual Studio Code' "$result_proc" \
  'get_active_window_info should read process name from proc comm without ps fallback'

cat >"$BIN_DIR/ps" <<'EOF'
#!/bin/bash
printf '%s\n' "${MOCK_PROCESS_NAME:-Code}"
EOF
chmod +x "$BIN_DIR/ps"

printf 'Checking thesis detection for VS Code thesis repo...\n'
active=$(source_env 'is_thesis_work_active && printf yes || printf no')
assert_equals 'yes' "$active" 'thesis detection should accept VS Code on the thesis repo'

printf 'Checking thesis detection skips non-thesis VS Code windows...\n'
non_thesis=$(MOCK_WINDOW_TITLE='Document - notes - Visual Studio Code' source_env 'is_thesis_work_active && printf yes || printf no')
assert_equals 'no' "$non_thesis" 'thesis detection should reject VS Code outside the thesis repo'

printf 'Checking steam detection reads process state from /proc without pgrep...\n'
PROC_DIR="$TMP_DIR/proc"
mkdir -p "$PROC_DIR/999"
printf 'steam\n' >"$PROC_DIR/999/comm"
steam_running=$(source_env_with_proc "$PROC_DIR" 'is_steam_running && printf yes || printf no')
assert_equals 'yes' "$steam_running" 'is_steam_running should detect steam via proc comm files'

printf 'Checking logging path does not depend on tee...\n'
cat >"$BIN_DIR/tee" <<'EOF'
#!/bin/bash
printf 'tee should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/tee"

LOG_PATH="$TMP_DIR/tracker.log"
set +e
log_result=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; LOG_FILE='$LOG_PATH'; log_info 'logging regression test'; printf ok")
log_ec=$?
set -e
assert_equals '0' "$log_ec" 'log_info should not fail when tee is unavailable'
assert_equals 'ok' "$log_result" 'log_info should succeed without tee dependency'
grep -q 'logging regression test' "$LOG_PATH" \
  || fail 'log_info should append message to the log file'

printf 'Checking state loading does not depend on grep/cut...\n'
cat >"$BIN_DIR/sudo" <<'EOF'
#!/bin/bash
"$@"
EOF
chmod +x "$BIN_DIR/sudo"

cat >"$BIN_DIR/chattr" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$BIN_DIR/chattr"

cat >"$BIN_DIR/grep" <<'EOF'
#!/bin/bash
printf 'grep should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/grep"

cat >"$BIN_DIR/cut" <<'EOF'
#!/bin/bash
printf 'cut should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/cut"

STATE_PATH="$TMP_DIR/work-time.state"
cat >"$STATE_PATH" <<'EOF'
# Thesis Work Tracker State File
TOTAL_WORK_SECONDS=123
LAST_UPDATE_TIMESTAMP=1715400000
STEAM_ACCESS_GRANTED=1
LAST_WORK_SESSION_START=77
CURRENT_SESSION_SECONDS=15
EOF

loaded_state=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   STATE_FILE='$STATE_PATH'; \
   load_state; \
   printf '%s|%s|%s|%s' \"\$TOTAL_WORK_SECONDS\" \"\$STEAM_ACCESS_GRANTED\" \"\$CURRENT_SESSION_SECONDS\" \"\$LAST_WORK_SESSION_START\"")
assert_equals '123|1|15|77' "$loaded_state" 'load_state should parse values without grep/cut dependency'

printf 'Checking state saving does not depend on tee...\n'
set +e
save_state_result=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   STATE_FILE='$STATE_PATH'; \
   STATE_DIR='$(dirname "$STATE_PATH")'; \
   save_state 321 0 45 9; \
   printf ok")
save_state_ec=$?
set -e
assert_equals '0' "$save_state_ec" 'save_state should not fail when tee is unavailable'
assert_equals 'ok' "$save_state_result" 'save_state should complete successfully without tee dependency'

saved_state=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   STATE_FILE='$STATE_PATH'; \
   load_state; \
   printf '%s|%s|%s|%s' \"\$TOTAL_WORK_SECONDS\" \"\$STEAM_ACCESS_GRANTED\" \"\$CURRENT_SESSION_SECONDS\" \"\$LAST_WORK_SESSION_START\"")
assert_equals '321|0|45|9' "$saved_state" 'save_state should persist updated values without tee dependency'

printf 'Checking writable save path does not require mktemp...\n'
cat >"$BIN_DIR/mktemp" <<'EOF'
#!/bin/bash
printf 'mktemp should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/mktemp"

set +e
save_fast_result=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   STATE_FILE='$STATE_PATH'; \
   STATE_DIR='$(dirname "$STATE_PATH")'; \
   save_state 654 1 30 11; \
   printf ok")
save_fast_ec=$?
set -e
assert_equals '0' "$save_fast_ec" 'save_state should not require mktemp when state file is writable'
assert_equals 'ok' "$save_fast_result" 'save_state fast path should complete successfully'

saved_fast_state=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   STATE_FILE='$STATE_PATH'; \
   load_state; \
   printf '%s|%s|%s|%s' \"\$TOTAL_WORK_SECONDS\" \"\$STEAM_ACCESS_GRANTED\" \"\$CURRENT_SESSION_SECONDS\" \"\$LAST_WORK_SESSION_START\"")
assert_equals '654|1|30|11' "$saved_fast_state" 'save_state writable fast path should persist values'

printf 'Checking block_distractions does not depend on grep or tee...\n'
HOSTS_PATH="$TMP_DIR/hosts-block"
printf '# /etc/hosts baseline\n127.0.0.1 localhost\n' >"$HOSTS_PATH"

cat >"$BIN_DIR/grep" <<'EOF'
#!/bin/bash
printf 'grep should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/grep"

cat >"$BIN_DIR/tee" <<'EOF'
#!/bin/bash
printf 'tee should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/tee"

set +e
block_result=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   HOSTS_FILE='$HOSTS_PATH'; \
   block_distractions; \
   printf ok")
block_ec=$?
set -e
assert_equals '0' "$block_ec" 'block_distractions should succeed without grep/tee'
assert_equals 'ok' "$block_result" 'block_distractions should complete without grep/tee dependency'
grep -q '0.0.0.0 steampowered.com' "$HOSTS_PATH" \
  || fail 'block_distractions should add steampowered.com entry to hosts file'
grep -q '0.0.0.0 reddit.com' "$HOSTS_PATH" \
  || fail 'block_distractions should add reddit.com entry to hosts file'
grep -q 'localhost' "$HOSTS_PATH" \
  || fail 'block_distractions should preserve existing localhost entry'

printf 'Checking block_distractions is idempotent (no duplicate entries)...\n'
set +e
block_result2=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   HOSTS_FILE='$HOSTS_PATH'; \
   block_distractions; \
   printf ok")
block_ec2=$?
set -e
assert_equals '0' "$block_ec2" 'block_distractions second run should succeed'
assert_equals 'ok' "$block_result2" 'block_distractions idempotent run should complete successfully'
count=$(grep -c '0.0.0.0 steampowered.com' "$HOSTS_PATH" || true)
assert_equals '1' "$count" 'block_distractions should not add duplicate entries'

printf 'Checking unblock_distractions does not depend on sed or mktemp...\n'
HOSTS_UNBLOCK_PATH="$TMP_DIR/hosts-unblock"
printf '# /etc/hosts baseline\n127.0.0.1 localhost\n0.0.0.0 steampowered.com\n0.0.0.0 reddit.com\n0.0.0.0 youtube.com\n' >"$HOSTS_UNBLOCK_PATH"

cat >"$BIN_DIR/sed" <<'EOF'
#!/bin/bash
printf 'sed should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/sed"

cat >"$BIN_DIR/mktemp" <<'EOF'
#!/bin/bash
printf 'mktemp should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/mktemp"

set +e
unblock_result=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   HOSTS_FILE='$HOSTS_UNBLOCK_PATH'; \
   unblock_distractions; \
   printf ok")
unblock_ec=$?
set -e
assert_equals '0' "$unblock_ec" 'unblock_distractions should succeed without sed/mktemp'
assert_equals 'ok' "$unblock_result" 'unblock_distractions should complete without sed/mktemp dependency'
if grep -q '0.0.0.0 steampowered.com' "$HOSTS_UNBLOCK_PATH" 2>/dev/null; then
  fail 'unblock_distractions should remove steampowered.com entry'
fi
if grep -q '0.0.0.0 reddit.com' "$HOSTS_UNBLOCK_PATH" 2>/dev/null; then
  fail 'unblock_distractions should remove reddit.com entry'
fi
grep -q 'localhost' "$HOSTS_UNBLOCK_PATH" \
  || fail 'unblock_distractions should preserve localhost entry'

printf 'Checking init_state does not depend on tee...\n'
STATE_INIT_PATH="$TMP_DIR/init-state-file.state"
STATE_INIT_DIR="$TMP_DIR/init-state-dir"
mkdir -p "$STATE_INIT_DIR"

set +e
init_result=$(PATH="$BIN_DIR:$PATH" THESIS_WORK_TRACKER_SKIP_MAIN=1 bash -lc \
  "source '$WORKTREE/scripts/digital_wellbeing/thesis_work_tracker.sh'; \
   STATE_FILE='$STATE_INIT_PATH'; \
   STATE_DIR='$STATE_INIT_DIR'; \
   LOG_DIR='$TMP_DIR'; \
   LOG_FILE='$TMP_DIR/init-tracker.log'; \
   init_state; \
   printf ok")
init_ec=$?
set -e
assert_equals '0' "$init_ec" 'init_state should succeed without tee dependency'
assert_equals 'ok' "$init_result" 'init_state should complete without tee dependency'
grep -q 'TOTAL_WORK_SECONDS=0' "$STATE_INIT_PATH" \
  || fail 'init_state should write TOTAL_WORK_SECONDS=0 to state file'

printf 'thesis_work_tracker.sh regression checks passed.\n'
