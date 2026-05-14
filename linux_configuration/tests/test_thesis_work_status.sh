#!/bin/bash
# Regression tests for thesis_work_status.sh state-parsing helper behavior.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
TARGET_SCRIPT="$REPO_DIR/scripts/periodic_background/digital_wellbeing/thesis_work_status.sh"

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
mkdir -p "$WORKTREE/scripts/periodic_background/digital_wellbeing" "$BIN_DIR"
cp "$TARGET_SCRIPT" "$WORKTREE/scripts/periodic_background/digital_wellbeing/thesis_work_status.sh"

# sudo stub — passes through all commands
cat >"$BIN_DIR/sudo" <<'EOF'
#!/bin/bash
"$@"
EOF
chmod +x "$BIN_DIR/sudo"

# chattr stub
cat >"$BIN_DIR/chattr" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$BIN_DIR/chattr"

# grep stub — must NOT be called by state parsing
cat >"$BIN_DIR/grep" <<'EOF'
#!/bin/bash
printf 'grep should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/grep"

# cut stub — must NOT be called by state parsing
cat >"$BIN_DIR/cut" <<'EOF'
#!/bin/bash
printf 'cut should not be called\n' >&2
exit 1
EOF
chmod +x "$BIN_DIR/cut"

STATE_PATH="$TMP_DIR/work-time.state"
cat >"$STATE_PATH" <<'EOF'
# Thesis Work Tracker State File
TOTAL_WORK_SECONDS=3600
LAST_UPDATE_TIMESTAMP=1715400000
STEAM_ACCESS_GRANTED=1
LAST_WORK_SESSION_START=42
CURRENT_SESSION_SECONDS=90
EOF

printf 'Checking state parsing does not depend on grep/cut...\n'
# THESIS_STATUS_SKIP_SUDO=1 prevents exec sudo re-exec
# THESIS_STATUS_SKIP_OUTPUT=1 prevents display output; script returns after parsing
parsed_vals=$(PATH="$BIN_DIR:$PATH" THESIS_STATUS_SKIP_SUDO=1 THESIS_STATUS_SKIP_OUTPUT=1 \
  bash -lc \
  "STATE_FILE='$STATE_PATH'; \
   source '$WORKTREE/scripts/periodic_background/digital_wellbeing/thesis_work_status.sh'; \
   printf '%s|%s|%s|%s' \"\$TOTAL_WORK_SECONDS\" \"\$STEAM_ACCESS_GRANTED\" \"\$CURRENT_SESSION_SECONDS\" \"\$LAST_WORK_SESSION_START\"" \
  2>/dev/null)

assert_equals '3600|1|90|42' "$parsed_vals" \
  'thesis_work_status state parsing should work without grep/cut dependency'

printf 'thesis_work_status.sh regression checks passed.\n'
