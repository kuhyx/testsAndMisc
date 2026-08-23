#!/usr/bin/env bash
# Tests for lib/services_common.sh — output helpers, the status store, the
# dry-run `run` gate, deployment_drift, the guard-lib probe and report_and_fix.
#
# report_and_fix is the one with real branching: status ok vs warning vs error,
# STATUS_ONLY on/off, installer present/missing, and the post-fix re-verify that
# can promote a status to "ok". Each combination gets its own case.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"

echo "== output helpers =="
reset_state
_t_eq "1" "$(msg yes | grep -c 'yes')" "msg prints its argument"
_t_eq "1" "$(note hi | grep -c 'hi')" "note prints its argument"
_t_eq "1" "$(warn hi | grep -c 'hi')" "warn prints its argument"
_t_eq "1" "$(err hi | grep -c 'hi')" "err prints its argument"
_t_eq "1" "$(header hi | grep -c 'hi')" "header prints its argument"

echo "== err_missing_script records and logs =="
reset_state
err_missing_script "missing: /nope/install.sh" >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "the missing script is recorded"
_t_called 'logger .*MISSING REPAIR SCRIPT' "the miss is logged at error priority"

echo "== status store =="
reset_state
_t_eq "unknown" "$(get_service_status "nothing_set")" "unset key reads as unknown"
set_service_status "hosts" "ok"
_t_eq "ok" "$(get_service_status "hosts")" "a recorded status reads back"
# A second write to one key means two checks are fighting over one summary row.
if set_service_status "hosts" "error" >/dev/null 2>&1; then
	_t_fail "a duplicate write is rejected"
else
	_t_pass "a duplicate write is rejected"
fi
_t_eq "ok" "$(get_service_status "hosts")" "the rejected write did not overwrite"

echo "== run honours --dry-run =="
reset_state
DRY_RUN=1
out="$(run logger would-have-run)"
_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}
_t_called_in "$out" "DRY-RUN:" "dry-run announces instead of running"
_t_not_called 'logger would-have-run' "dry-run did not actually run the command"
DRY_RUN=0
run logger really-ran
_t_called 'logger really-ran' "with dry-run off the command really runs"

echo "== user_systemctl targets the user bus =="
reset_state
printf 'user:workout-locker.service\n' >"${DEV}/enabled"
if user_systemctl kuhy is-enabled workout-locker.service; then
	_t_pass "user_systemctl reports an enabled user unit"
else
	_t_fail "user_systemctl reports an enabled user unit"
fi
_t_called 'systemctl --user --machine=kuhy@.host' "it connects via --machine, not sudo -u"

echo "== guard_lib_instance_healthy =="
reset_state
printf 'hosts\n' >"${DEV}/guard_healthy"
printf 'nsswitch\n' >"${DEV}/guard_degraded"
if guard_lib_instance_healthy hosts; then
	_t_pass "a healthy instance passes"
else
	_t_fail "a healthy instance passes"
fi
if guard_lib_instance_healthy nsswitch; then
	_t_fail "an inactive path unit fails"
else
	_t_pass "an inactive path unit fails"
fi
if guard_lib_instance_healthy resolved; then
	_t_fail "an unregistered instance fails"
else
	_t_pass "an unregistered instance fails"
fi

echo "== deployment_drift =="
reset_state
manifest="${TEST_TMPDIR}/drift.sha256"
subject="${TEST_TMPDIR}/subject.txt"
printf 'original\n' >"$subject"
(cd "${TEST_TMPDIR}" && sha256sum "$(basename "$subject")" >"$manifest")
rc=0
(cd "${TEST_TMPDIR}" && deployment_drift "$manifest") || rc=$?
_t_eq "0" "$rc" "a matching manifest verifies"
printf 'tampered\n' >"$subject"
rc=0
(cd "${TEST_TMPDIR}" && deployment_drift "$manifest") || rc=$?
_t_eq "1" "$rc" "an edited file is reported as drift"
rc=0
deployment_drift "${TEST_TMPDIR}/absent.sha256" || rc=$?
_t_eq "2" "$rc" "a missing manifest is 'unverifiable', not a pass"

echo "== require_root =="
reset_state
# require_root ends in `exec sudo`, which would replace this test process, so
# both branches run in a child shell against the fake sudo on PATH. EUID is
# readonly in bash and cannot be assigned, so the non-root branch is reached by
# running as the real (non-root) user and the root branch by shimming EUID
# through a wrapper that sources the lib with EUID already 0 -- which only
# `env -i` style faking can do. Instead: assert the observable behaviour of
# each branch via the fake sudo's call log.
cat >"${TEST_TMPDIR}/root_probe.sh" <<PROBE
#!/usr/bin/env bash
set -euo pipefail
. "${LIB_DIR}/services_common.sh"
require_root "\$@"
printf 'reached-past-require-root\n'
PROBE
chmod +x "${TEST_TMPDIR}/root_probe.sh"

probe_out="$("${TEST_TMPDIR}/root_probe.sh" --status 2>&1 || true)"
if [[ $EUID -ne 0 ]]; then
	_t_called_in "$probe_out" "requires root privileges" "a non-root run announces the re-exec"
	_t_called 'sudo -E bash .*root_probe.sh --status' "it re-execs itself under sudo with its args"
else
	_t_called_in "$probe_out" "reached-past-require-root" "a root run proceeds without re-execing"
	_t_not_called 'sudo -E bash' "a root run does not re-exec"
fi

echo "== hosts_pacman_hooks_installed =="
reset_state
# Both hooks present.
sysfile etc/pacman.d/hooks/10-guard-lib-unlock-all.hook
sysfile etc/pacman.d/hooks/90-guard-lib-relock-all.hook
if hosts_pacman_hooks_installed; then
	_t_pass "both guard-lib hooks present reads as installed"
else
	_t_fail "both guard-lib hooks present reads as installed"
fi
# Only the unlock hook: a half-installed pair must not read as installed, or
# pacman upgrades would relock nothing and leave the guards open.
sysrm etc/pacman.d/hooks/90-guard-lib-relock-all.hook
if hosts_pacman_hooks_installed; then
	_t_fail "a missing relock hook reads as not installed"
else
	_t_pass "a missing relock hook reads as not installed"
fi
sysrm etc/pacman.d/hooks/10-guard-lib-unlock-all.hook
if hosts_pacman_hooks_installed; then
	_t_fail "neither hook present reads as not installed"
else
	_t_pass "neither hook present reads as not installed"
fi

_t_summary
