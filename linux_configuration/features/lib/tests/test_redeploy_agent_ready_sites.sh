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

# Barrier: `barrier.sh <group> <member>` marks <member> as started and waits
# up to 3 s for all three members of <group>. A sequential caller can never
# have all three running at once, so it logs SERIAL instead: a deterministic
# concurrency check with no timing threshold to flake on.
cat >"$TEST_TMPDIR/barrier.sh" <<'EOF'
#!/usr/bin/env bash
mkdir -p "$TEST_TMPDIR/barrier/$1"
: >"$TEST_TMPDIR/barrier/$1/$2"
for _ in $(seq 30); do
	n="$(find "$TEST_TMPDIR/barrier/$1" -type f | wc -l)"
	[[ $n -ge 3 ]] && exit 0
	sleep 0.1
done
printf 'SERIAL %s %s\n' "$1" "$2" >>"$TEST_TMPDIR/calls.log"
EOF
chmod +x "$TEST_TMPDIR/barrier.sh"

# A sibling setup script that records its argv, joins the redeploy barrier,
# sleeps $FAKE_SLEEP and exits $FAKE_RC_<name>.
cat >"$WRAP_DIR/setup_personal_website.sh" <<'EOF'
#!/usr/bin/env bash
name="$(basename "$0" .sh)"
printf '%s %s\n' "$name" "$*" >>"$TEST_TMPDIR/calls.log"
"$TEST_TMPDIR/barrier.sh" redeploy "$name"
sleep "${FAKE_SLEEP:-0}"
rc_var="FAKE_RC_${name}"
exit "${!rc_var:-0}"
EOF
cp "$WRAP_DIR/setup_personal_website.sh" "$WRAP_DIR/setup_kcd2_dice_solver.sh"
cat >"$TEST_TMPDIR/bin/systemctl" <<'EOF'
#!/usr/bin/env bash
printf 'systemctl %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
"$TEST_TMPDIR/barrier.sh" redeploy systemctl
EOF
chmod +x "$TEST_TMPDIR/bin/systemctl"

# Checker stub: PASS for kuhy (finishing last), FAIL lines for dice,
# unreachable for popes. Every call joins the check barrier first.
cat >"$TEST_TMPDIR/src/utils/agent_ready/check.sh" <<'EOF'
#!/usr/bin/env bash
printf 'check %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
host="${2#*//}"
"$TEST_TMPDIR/barrier.sh" check "${host%%.*}"
case "$2" in
*//kuhy.*)
	sleep 0.5
	exit "${FAKE_KUHY_RC:-0}"
	;;
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
	rm -rf "$TEST_TMPDIR/barrier"
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
_t_eq 0 "$(grep -c '^SERIAL check' "$TEST_TMPDIR/calls.log" || true)" "the three checks run concurrently"
_t_eq "kuhy dice popes" "$(grep -oE '//[a-z]+' "$TEST_TMPDIR/out" | tr -d / | paste -sd' ')" \
	"verdicts print in site order even when kuhy finishes last"
_t_eq 3 "$(grep -cE '^check url https://[^ ]+ --budget 45$' "$TEST_TMPDIR/calls.log")" \
	"each check gets the checker's full 45 s network budget"

printf '== full run\n'
_t_eq 1 "$(FAKE_RC_setup_kcd2_dice_solver=1 run_wrapper)" "full run exits 1"
_t_called "setup_personal_website serve" "website serve ran"
_t_called "setup_kcd2_dice_solver serve" "dice serve ran"
_t_called "systemctl --user restart signal-bot-popes-site.service" "popes unit restarted"
_t_has "$(cat "$TEST_TMPDIR/out")" "kcd2-dice                    FAILED (exit 1)" "a failed serve is reported"
_t_eq 3 "$(grep -c '^check url' "$TEST_TMPDIR/calls.log")" "a failed serve does not skip the checks"
_t_eq 0 "$(grep -c '^SERIAL redeploy' "$TEST_TMPDIR/calls.log" || true)" "the three redeploy steps run concurrently"

printf '== the check budget shrinks to fit the run deadline\n'
_t_eq 1 "$(FAKE_SLEEP=2 AGENT_READY_RUN_DEADLINE=12 run_wrapper)" "slow redeploy still checks (dice fails)"
_t_eq 3 "$(grep -cE '^check url https://[^ ]+ --budget [1-5]$' "$TEST_TMPDIR/calls.log")" \
	"checks get only what is left of the deadline"
_t_eq 1 "$(FAKE_SLEEP=2 AGENT_READY_RUN_DEADLINE=8 run_wrapper)" "no time left fails the run"
_t_eq 0 "$(grep -c '^check url' "$TEST_TMPDIR/calls.log" || true)" "no checker starts once the deadline is spent"
_t_eq 3 "$(grep -c '^UNDETERMINED .*no time left' "$TEST_TMPDIR/out")" "each site reports no time left"

printf '== exit codes\n'
_t_eq 2 "$(run_wrapper --bogus)" "unknown argument exits 2"
help_text="$(bash "$WRAPPER" --help)"
_t_has "$help_text" "--verify-only" "help documents --verify-only"
_t_eq 0 "$(grep -c 'in_parallel' <<<"$help_text" || true)" "help stops at the header block"

_t_report "redeploy agent-ready sites"
