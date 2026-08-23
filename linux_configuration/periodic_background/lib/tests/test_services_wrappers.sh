#!/usr/bin/env bash
# Tests for lib/services_wrappers.sh — the pacman and makepkg wrapper checks.
#
# Both checks assert four independent things: the /usr/bin symlink points at
# the wrapper, the .orig backup exists, the installed files exist, and the
# install-time drift manifest still verifies. The last one is the reason these
# checks exist at all — on 2026-08-03 a week-stale wrapper passed every
# existence check while the manifest would have caught it — so drift gets a
# case for each of its three outcomes (verified, drifted, no manifest).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_wrappers.sh
. "${SCRIPT_DIR}/../services_wrappers.sh"

# Stage a fully healthy pacman wrapper install inside the fixture root, with a
# drift manifest that verifies.
stage_pacman_ok() {
	sysfile usr/local/bin/pacman_wrapper
	sysfile usr/bin/pacman.orig
	ln -sf "${SERVICES_ROOT}/usr/local/bin/pacman_wrapper" "${SERVICES_ROOT}/usr/bin/pacman"
	sysfile usr/local/bin/words.txt
	sysfile usr/local/bin/pacman_blocked_keywords.txt
	sysfile usr/local/bin/pacman_whitelist.txt
	(cd "${SERVICES_ROOT}" && sha256sum usr/local/bin/pacman_wrapper >"$PACMAN_WRAPPER_MANIFEST")
}

# Same for makepkg. The makepkg check additionally wants a shared lock library,
# a rewrap helper and the upgrade-survival pacman hook.
stage_makepkg_ok() {
	sysfile usr/local/bin/makepkg_wrapper
	sysfile usr/bin/makepkg.orig
	ln -sf "${SERVICES_ROOT}/usr/local/bin/makepkg_wrapper" "${SERVICES_ROOT}/usr/bin/makepkg"
	sysfile usr/local/bin/pacman_lock_lib.sh
	sysfile usr/local/bin/rewrap_pkg_managers.sh
	sysfile etc/pacman.d/hooks/96-restore-pkg-wrappers.hook
	(cd "${SERVICES_ROOT}" && sha256sum usr/local/bin/makepkg_wrapper >"$MAKEPKG_WRAPPER_MANIFEST")
}

# check_pacman_wrapper runs its manifest through `sha256sum -c`, whose paths are
# relative to the cwd, so every call is made from the fixture root.
#
# Deliberately NOT `(cd ... && check)`: the checks mutate SERVICE_STATUS,
# ISSUES_FOUND and MISSING_SCRIPTS, and a subshell would strand every one of
# those, leaving the assertions below silently testing nothing.
run_pacman_check() {
	local prev="$PWD"
	cd "${SERVICES_ROOT}" || return 1
	check_pacman_wrapper
	local rc=$?
	cd "$prev" || return 1
	return $rc
}

run_makepkg_check() {
	local prev="$PWD"
	cd "${SERVICES_ROOT}" || return 1
	check_makepkg_wrapper
	local rc=$?
	cd "$prev" || return 1
	return $rc
}

echo "== check_pacman_wrapper: a healthy install records ok =="
reset_state
stage_pacman_ok
run_pacman_check >"${TEST_TMPDIR}/out.txt"
_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}
out="$(cat "${TEST_TMPDIR}/out.txt")"
_t_called_in "$out" "Pacman symlink points to wrapper" "the symlink is accepted"
_t_called_in "$out" "no drift" "a verifying manifest reports no drift"
_t_not_called 'ran install_pacman_wrapper' "a healthy install runs no installer"

echo "== check_pacman_wrapper: pacman not a symlink =="
reset_state
make_installer "$PACMAN_WRAPPER_INSTALL"
stage_pacman_ok
rm -f "${SERVICES_ROOT}/usr/bin/pacman"
sysfile usr/bin/pacman # a real file, not a link
run_pacman_check >/dev/null
_t_called 'ran install_pacman_wrapper' "a missing wrapper symlink runs the installer"

echo "== check_pacman_wrapper: symlink points somewhere else =="
reset_state
make_installer "$PACMAN_WRAPPER_INSTALL"
stage_pacman_ok
sysfile usr/local/bin/impostor
ln -sf "${SERVICES_ROOT}/usr/local/bin/impostor" "${SERVICES_ROOT}/usr/bin/pacman"
run_pacman_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "expected" "a wrong symlink target names the expected path"
_t_called 'ran install_pacman_wrapper' "a wrong symlink target runs the installer"

echo "== check_pacman_wrapper: missing .orig backup =="
reset_state
make_installer "$PACMAN_WRAPPER_INSTALL"
stage_pacman_ok
sysrm usr/bin/pacman.orig
run_pacman_check >/dev/null
_t_called 'ran install_pacman_wrapper' "a missing .orig backup runs the installer"

echo "== check_pacman_wrapper: missing supporting files only warn =="
reset_state
stage_pacman_ok
sysrm usr/local/bin/words.txt usr/local/bin/pacman_whitelist.txt
run_pacman_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "Supporting file missing" "a missing supporting file is reported"
_t_not_called 'ran install_pacman_wrapper' "but it does not trigger a reinstall"

echo "== check_pacman_wrapper: content drift is an error even when files exist =="
reset_state
make_installer "$PACMAN_WRAPPER_INSTALL"
stage_pacman_ok
# Every existence check still passes; only the content changed. This is the
# exact shape of the 2026-08-03 stale-wrapper incident.
printf 'tampered\n' >"${SERVICES_ROOT}/usr/local/bin/pacman_wrapper"
run_pacman_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "stale or tampered" "drift is reported despite every file being present"
_t_called 'ran install_pacman_wrapper' "drift triggers a reinstall"

echo "== check_pacman_wrapper: an absent manifest is unverifiable, not a pass =="
reset_state
make_installer "$PACMAN_WRAPPER_INSTALL"
stage_pacman_ok
rm -f "$PACMAN_WRAPPER_MANIFEST"
run_pacman_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "unverifiable" "a missing manifest is called out"
_t_called 'ran install_pacman_wrapper' "a missing manifest triggers a reinstall"

echo "== check_pacman_wrapper: --status reports without repairing =="
reset_state
make_installer "$PACMAN_WRAPPER_INSTALL"
STATUS_ONLY=1
run_pacman_check >/dev/null
_t_not_called 'ran install_pacman_wrapper' "--status never installs"
_t_eq "error" "$(get_service_status "pacman_wrapper")" "the error is still recorded"

echo "== check_pacman_wrapper: a missing installer is a broken-self-repair error =="
reset_state
rm -f "$PACMAN_WRAPPER_INSTALL"
run_pacman_check >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "the missing installer is recorded"

echo "== check_makepkg_wrapper: a healthy install records ok =="
reset_state
stage_makepkg_ok
run_makepkg_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "Makepkg symlink points to wrapper" "the symlink is accepted"
_t_eq "ok" "$(get_service_status "makepkg_wrapper")" "a healthy install records ok"

echo "== check_makepkg_wrapper: each missing piece triggers a reinstall =="
for missing in usr/bin/makepkg.orig usr/local/bin/pacman_lock_lib.sh \
	usr/local/bin/rewrap_pkg_managers.sh etc/pacman.d/hooks/96-restore-pkg-wrappers.hook; do
	reset_state
	make_installer "$MAKEPKG_WRAPPER_INSTALL"
	stage_makepkg_ok
	sysrm "$missing"
	run_makepkg_check >/dev/null
	_t_called 'ran install_makepkg_wrapper' "a missing ${missing##*/} runs the installer"
done

echo "== check_makepkg_wrapper: not a symlink =="
reset_state
make_installer "$MAKEPKG_WRAPPER_INSTALL"
stage_makepkg_ok
rm -f "${SERVICES_ROOT}/usr/bin/makepkg"
sysfile usr/bin/makepkg
run_makepkg_check >/dev/null
_t_called 'ran install_makepkg_wrapper' "a missing wrapper symlink runs the installer"

echo "== check_makepkg_wrapper: symlink points somewhere else =="
reset_state
make_installer "$MAKEPKG_WRAPPER_INSTALL"
stage_makepkg_ok
sysfile usr/local/bin/impostor
ln -sf "${SERVICES_ROOT}/usr/local/bin/impostor" "${SERVICES_ROOT}/usr/bin/makepkg"
run_makepkg_check >/dev/null
_t_called 'ran install_makepkg_wrapper' "a wrong symlink target runs the installer"

echo "== check_makepkg_wrapper: wrapper file missing =="
reset_state
make_installer "$MAKEPKG_WRAPPER_INSTALL"
stage_makepkg_ok
sysrm usr/local/bin/makepkg_wrapper
run_makepkg_check >/dev/null
_t_called 'ran install_makepkg_wrapper' "a missing wrapper script runs the installer"

echo "== check_makepkg_wrapper: drift and absent manifest =="
reset_state
make_installer "$MAKEPKG_WRAPPER_INSTALL"
stage_makepkg_ok
printf 'tampered\n' >"${SERVICES_ROOT}/usr/local/bin/makepkg_wrapper"
run_makepkg_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "stale or tampered" "makepkg drift is reported"

reset_state
make_installer "$MAKEPKG_WRAPPER_INSTALL"
stage_makepkg_ok
rm -f "$MAKEPKG_WRAPPER_MANIFEST"
run_makepkg_check >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "unverifiable" "an absent makepkg manifest is called out"

echo "== check_makepkg_wrapper: --status and a missing installer =="
reset_state
make_installer "$MAKEPKG_WRAPPER_INSTALL"
STATUS_ONLY=1
run_makepkg_check >/dev/null
_t_not_called 'ran install_makepkg_wrapper' "--status never installs"

reset_state
rm -f "$MAKEPKG_WRAPPER_INSTALL"
run_makepkg_check >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "the missing makepkg installer is recorded"

_t_summary
