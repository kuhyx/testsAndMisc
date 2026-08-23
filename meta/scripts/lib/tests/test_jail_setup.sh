#!/usr/bin/env bash
# build_jail, write_cases, build_mount_script and reconcile_pass_failures.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./coverage_tool_harness.sh
. "$HERE/coverage_tool_harness.sh"

EXTRA_SHIMS=()
BIND_PATHS=()
CASES=()
# shellcheck source=../shell_coverage_jail_setup.sh
. "$HERE/../shell_coverage_jail_setup.sh"

# --- build_jail -------------------------------------------------------------
# It mints its own $JAIL via mktemp, so it is the one function not given one.
EXTRA_SHIMS=(mytool)
build_jail
_t_eq "yes" "$([[ -d "$JAIL/cov" && -d "$JAIL/trace" && -d "$JAIL/bin" ]] && echo yes)" \
	"build_jail creates cov/, trace/ and bin/"

xtrace="$(cat "$JAIL/xtrace_env.sh")"
_t_has "$xtrace" 'PS4=' "the BASH_ENV file assigns PS4"
_t_has "$xtrace" 'set -x' "the BASH_ENV file re-applies set -x"
# The heredoc is quoted so these reach the traced shell unexpanded; if they had
# been expanded at write time the trace loses its per-line file:line prefix.
_t_has "$xtrace" "${DOLLAR}{BASH_SOURCE}" "BASH_SOURCE is left unexpanded for the traced shell"
_t_has "$xtrace" "${DOLLAR}{LINENO}" "LINENO is left unexpanded for the traced shell"

_t_eq "yes" "$([[ -x "$JAIL/bin/systemctl" ]] && echo yes)" \
	"a default shim is written and executable"
_t_eq "yes" "$([[ -x "$JAIL/bin/mytool" ]] && echo yes)" \
	"an EXTRA_SHIMS entry is shimmed too"

# A shim records the call and exits 0, so a subject calling systemctl does not
# die inside the jail.
"$JAIL/bin/systemctl" start nothing.service
_t_has "$(cat "$JAIL/calls.log")" "systemctl start nothing.service" \
	"a shim logs its arguments to calls.log"
_t_eq "0" "$(
	"$JAIL/bin/pkill" -9 anything >/dev/null 2>&1
	echo $?
)" \
	"a shim exits 0 rather than failing the subject"

built_jail="$JAIL"

# --- write_cases ------------------------------------------------------------
_t_new_jail
CASES=("" "--flag one" "two")
write_cases
_t_eq "3" "$(wc -l <"$JAIL/cases")" "write_cases writes one line per case"
_t_eq "--flag one" "$(sed -n '2p' "$JAIL/cases")" "a case keeps its arguments verbatim"
_t_eq "" "$(sed -n '1p' "$JAIL/cases")" "the empty case is preserved as a blank line"
_t_drop_jail

# --- build_mount_script -----------------------------------------------------
_t_new_jail
BIND_PATHS=(/etc /var/lib)
build_mount_script
mounts="$(cat "$JAIL/mounts.sh")"
_t_has "$mounts" "mkdir -p /etc" "each bind target is mkdir'd first"
_t_has "$mounts" "mount --bind" "each bind emits a mount --bind"
_t_eq "2" "$(grep -c 'mount --bind' "$JAIL/mounts.sh")" "one mount per bind path"
# A failed bind must be fatal: a silent failure sends the subject's writes at
# the REAL path, which is the misdiagnosis the jail exists to prevent.
_t_has "$mounts" "exit 1" "a failed bind exits rather than warning"
# Distinct source dirs, so two binds cannot collide on one mnt dir.
_t_has "$mounts" "mnt0" "the first bind uses mnt0"
_t_has "$mounts" "mnt1" "the second bind uses mnt1"
_t_drop_jail

# An empty BIND_PATHS is legal and yields an empty script, not an error.
_t_new_jail
BIND_PATHS=()
build_mount_script
_t_eq "0" "$(grep -c 'mount --bind' "$JAIL/mounts.sh" || true)" \
	"no bind paths yields no mounts"
_t_drop_jail

# --- reconcile_pass_failures ------------------------------------------------
# Equal failure counts: the trace is complete, so it passes and the kcov file
# becomes the one --fail-on-case-error reads.
_t_new_jail
printf '1\n' >"$JAIL/case_failures.kcov"
printf '1\n' >"$JAIL/case_failures.trace"
(reconcile_pass_failures) >/dev/null 2>&1
_t_eq "0" "$?" "equal failures in both passes is not an error"
reconcile_pass_failures >/dev/null 2>&1
_t_eq "yes" "$([[ -f "$JAIL/case_failures" ]] && echo yes)" \
	"the kcov failures are collapsed into case_failures"
_t_drop_jail

# More trace failures than kcov failures means a PARTIAL trace: it must fail
# loudly, because a short trace under-reports and looks like real uncovered code.
_t_new_jail
: >"$JAIL/case_failures.kcov"
printf '1\n2\n' >"$JAIL/case_failures.trace"
out="$( (reconcile_pass_failures) 2>&1)"
rc=$?
_t_eq "1" "$rc" "a trace pass with MORE failures exits 1"
_t_has "$out" "trace is partial" "and says the trace is partial"
_t_has "$out" "raise --timeout" "and names the usual fix"
_t_drop_jail

# Neither pass failed: nothing to reconcile and no case_failures file.
_t_new_jail
(reconcile_pass_failures) >/dev/null 2>&1
_t_eq "0" "$?" "no failure files at all is not an error"
reconcile_pass_failures >/dev/null 2>&1
_t_eq "no" "$([[ -f "$JAIL/case_failures" ]] && echo yes || echo no)" \
	"a clean run writes no case_failures file"
_t_drop_jail

rm -rf "$built_jail"
_t_summary
