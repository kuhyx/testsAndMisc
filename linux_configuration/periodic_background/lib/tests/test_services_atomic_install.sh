#!/usr/bin/env bash
# Tests for lib/atomic_install.sh — installing a live /usr/local/bin script.
#
# A running bash reads its script lazily, so truncating the file in place
# (`sed ... > target`) lets a running instance execute a half-new file. The
# installer must render beside the target and rename over it: the target gets
# a NEW inode and a process holding the old one keeps reading the old bytes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../atomic_install.sh
. "${SCRIPT_DIR}/../atomic_install.sh"

BIN="${SYSROOT_DIR}/usr/local/bin"
TEMPLATE="${TEST_TMPDIR}/template.sh"
printf '#!/bin/bash\necho __NAME__ new\n' >"$TEMPLATE"

echo "== install_rendered_script: replaces the live file by rename =="
printf '#!/bin/bash\necho old\n' >"${BIN}/live.sh"
old_inode="$(stat -c %i "${BIN}/live.sh")"
exec 9<"${BIN}/live.sh" # a "running instance" holding the old inode open
install_rendered_script "$TEMPLATE" "${BIN}/live.sh" -e 's|__NAME__|hosts|g'
new_inode="$(stat -c %i "${BIN}/live.sh")"
if [[ $new_inode != "$old_inode" ]]; then
	_t_pass "the target has a new inode"
else
	_t_fail "the target kept inode $old_inode (written in place)"
fi
_t_eq $'#!/bin/bash\necho old' "$(cat <&9)" "the old inode's content is untouched for the running instance"
exec 9<&-
_t_eq $'#!/bin/bash\necho hosts new' "$(cat "${BIN}/live.sh")" "the target holds the rendered template"
if [[ -x "${BIN}/live.sh" ]]; then
	_t_pass "the target is executable"
else
	_t_fail "the target is not executable"
fi
_t_eq "live.sh" "$(ls "$BIN")" "no temp file is left beside the target"

echo "== install_rendered_script: a script that fails bash -n never replaces the target =="
printf '#!/bin/bash\nif then fi (\n' >"${TEST_TMPDIR}/broken.sh"
before="$(stat -c %i "${BIN}/live.sh")"
if install_rendered_script "${TEST_TMPDIR}/broken.sh" "${BIN}/live.sh" 2>/dev/null; then
	_t_fail "a syntax error was installed"
else
	_t_pass "a syntax error returns non-zero"
fi
_t_eq "$before" "$(stat -c %i "${BIN}/live.sh")" "the live file is untouched after a syntax error"
_t_eq "live.sh" "$(ls "$BIN")" "no temp file is left after a syntax error"

echo "== install_rendered_script: a missing template fails closed =="
if install_rendered_script "${TEST_TMPDIR}/nope.sh" "${BIN}/live.sh" 2>/dev/null; then
	_t_fail "a missing template reported success"
else
	_t_pass "a missing template returns non-zero"
fi
_t_eq "live.sh" "$(ls "$BIN")" "no temp file is left after a missing template"

echo "== restart_if_active: restarts only a running unit =="
reset_state
: >"${DEV}/active"
restart_if_active hosts-file-monitor.service >/dev/null
_t_not_called 'systemctl restart hosts-file-monitor.service' "a stopped unit is not started by the installer"
printf 'hosts-file-monitor.service\n' >"${DEV}/active"
restart_if_active hosts-file-monitor.service >/dev/null
_t_called 'systemctl restart hosts-file-monitor.service' "a running unit is restarted onto the new file"

_t_summary
