#!/bin/bash
# Regression tests for setup_dns_blocker.sh (LAN DNS blocker).
#
# Covers the pure, root-free logic:
#   - command dispatch (help lists all subcommands, unknown -> exit 1)
#   - firewall_is_loaded: the pipefail/SIGPIPE regression -- 'nft | grep -q'
#     used to false-negative under 'set -o pipefail' because grep closed the
#     pipe early and nft died on SIGPIPE. Detection must survive large output.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
TARGET_SCRIPT="$REPO_DIR/scripts/single_use/features/setup_dns_blocker.sh"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

TMP_DIR=$(mktemp -d)
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# --- Dispatch tests (real script, no root needed) --------------------------
help_out=$("$TARGET_SCRIPT" help)
for cmd in setup status refresh dhcp dhcp-off; do
  [[ "$help_out" == *"$cmd"* ]] || fail "help output missing '$cmd' subcommand"
done

# Unknown command must exit non-zero.
if "$TARGET_SCRIPT" bogus-cmd >/dev/null 2>&1; then
  fail "unknown command should exit non-zero"
fi

# --- firewall_is_loaded regression (pipefail/SIGPIPE) ----------------------
# Mock 'nft' so the function runs without root. Emit a LARGE ruleset so that a
# reintroduced 'grep -q' pipe would SIGPIPE nft and false-negative under pipefail.
make_nft() {
  local mode="$1" # drop | accept
  cat >"$BIN_DIR/nft" <<EOF
#!/bin/bash
# Large output to stress the early-close case.
echo "table inet filter {"
echo "  chain input {"
echo "    type filter hook input priority filter; policy ${mode};"
for i in \$(seq 1 500); do echo "    ip saddr 10.0.0.\$i tcp dport 22 accept"; done
echo "  }"
echo "}"
EOF
  chmod +x "$BIN_DIR/nft"
}

# Source the target with main() suppressed so we can call its functions.
run_fw_check() {
  local mode="$1"
  make_nft "$mode"
  PATH="$BIN_DIR:$PATH" SETUP_DNS_BLOCKER_SKIP_MAIN=1 bash -c '
    set -euo pipefail
    source "$1"
    if firewall_is_loaded; then echo LOADED; else echo NOT_LOADED; fi
  ' _ "$TARGET_SCRIPT"
}

got=$(run_fw_check drop)
[[ "$got" == "LOADED" ]] || fail "firewall_is_loaded should be true for a policy-drop chain (got: $got)"

got=$(run_fw_check accept)
[[ "$got" == "NOT_LOADED" ]] || fail "firewall_is_loaded should be false for a policy-accept chain (got: $got)"

printf 'PASS: %s\n' "$(basename "$0")"
