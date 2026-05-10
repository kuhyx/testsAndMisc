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

printf 'Checking helper output for VS Code on thesis repo...\n'
result=$(source_env 'get_active_window_info')
assert_equals 'Code|Document - praca_magisterska - Visual Studio Code' "$result" \
  'get_active_window_info should return process and title for VS Code'

printf 'Checking thesis detection for VS Code thesis repo...\n'
active=$(source_env 'is_thesis_work_active && printf yes || printf no')
assert_equals 'yes' "$active" 'thesis detection should accept VS Code on the thesis repo'

printf 'Checking thesis detection skips non-thesis VS Code windows...\n'
non_thesis=$(MOCK_WINDOW_TITLE='Document - notes - Visual Studio Code' source_env 'is_thesis_work_active && printf yes || printf no')
assert_equals 'no' "$non_thesis" 'thesis detection should reject VS Code outside the thesis repo'

printf 'thesis_work_tracker.sh regression checks passed.\n'
