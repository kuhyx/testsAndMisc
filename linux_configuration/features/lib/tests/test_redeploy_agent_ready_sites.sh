#!/usr/bin/env bash
# Tests for features/redeploy_agent_ready_sites.sh.
#
# The wrapper is copied next to stub setup_*.sh scripts (it resolves its
# siblings from its own path), HOME points at a temp dir holding a stub
# checker, and systemctl is stubbed on PATH. Nothing live is restarted or
# fetched; the real --verify-only run against the public sites is manual.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

readonly WRAP_DIR="$TEST_TMPDIR/features"
readonly WRAPPER="$WRAP_DIR/redeploy_agent_ready_sites.sh"
mkdir -p "$WRAP_DIR" "$TEST_TMPDIR/src/utils/agent_ready"
cp "$FEATURES_LIB_DIR/../redeploy_agent_ready_sites.sh" "$WRAPPER"

# A sibling setup script that records its argv and exits $FAKE_RC_<name>.
cat >"$WRAP_DIR/setup_personal_website.sh" <<'EOF'
#!/usr/bin/env bash
name="$(basename "$0" .sh)"
printf '%s %s\n' "$name" "$*" >>"$TEST_TMPDIR/calls.log"
rc_var="FAKE_RC_${name}"
exit "${!rc_var:-0}"
EOF
cp "$WRAP_DIR/setup_personal_website.sh" "$WRAP_DIR/setup_kcd2_dice_solver.sh"
_t_stub systemctl

# Checker stub: PASS for kuhy, FAIL lines for dice, unreachable for popes.
cat >"$TEST_TMPDIR/src/utils/agent_ready/check.sh" <<'EOF'
#!/usr/bin/env bash
printf 'check %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
case "$2" in
*//kuhy.*) exit "${FAKE_KUHY_RC:-0}" ;;
*//dice.*)
	printf 'PASS AR-READ-03 ok\nFAIL AR-READ-02 soft 404\nFAIL AR-FIND-04 no Link\nFAIL AR-READ-02 again\n'
	exit 1
	;;
*) exit 3 ;;
esac
EOF
chmod +x "$TEST_TMPDIR/src/utils/agent_ready/check.sh"

run_wrapper() {
	: >"$TEST_TMPDIR/calls.log"
	local rc=0
	HOME="$TEST_TMPDIR" bash "$WRAPPER" "$@" >"$TEST_TMPDIR/out" 2>&1 || rc=$?
	echo "$rc"
}

printf '== --verify-only restarts nothing\n'
_t_eq 1 "$(run_wrapper --verify-only)" "a failing site makes the run exit 1"
_t_eq 0 "$(grep -cE '^(setup_|systemctl)' "$TEST_TMPDIR/calls.log" || true)" "no serve and no restart"
_t_eq 3 "$(grep -c '^check url https://' "$TEST_TMPDIR/calls.log")" "all three sites checked"
out="$(cat "$TEST_TMPDIR/out")"
_t_has "$out" "PASS          https://kuhy.duckdns.org" "kuhy verdict"
_t_has "$out" "FAIL          https://dice.kuhy.duckdns.org (AR-FIND-04,AR-READ-02)" "dice verdict lists unique failing ids"
_t_has "$out" "UNDETERMINED  https://popes.kuhy.duckdns.org" "popes verdict on checker exit 3"
_t_eq 3 "$(wc -l <"$TEST_TMPDIR/out")" "one line per site"

printf '== full run\n'
_t_eq 1 "$(FAKE_RC_setup_kcd2_dice_solver=1 run_wrapper)" "full run exits 1"
_t_called "setup_personal_website serve" "website serve ran"
_t_called "setup_kcd2_dice_solver serve" "dice serve ran"
_t_called "systemctl --user restart signal-bot-popes-site.service" "popes unit restarted"
_t_has "$(cat "$TEST_TMPDIR/out")" "kcd2-dice                    FAILED (exit 1)" "a failed serve is reported"
_t_eq 3 "$(grep -c '^check url' "$TEST_TMPDIR/calls.log")" "a failed serve does not skip the checks"

printf '== exit codes\n'
_t_eq 2 "$(run_wrapper --bogus)" "unknown argument exits 2"
_t_has "$(bash "$WRAPPER" --help)" "--verify-only" "help documents --verify-only"

_t_report "redeploy agent-ready sites"
