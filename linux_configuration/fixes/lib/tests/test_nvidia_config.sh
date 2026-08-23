#!/usr/bin/env bash
# lib/tests/test_nvidia_config.sh — tests for nvidia_config.sh's backup_file,
# configure_xorg and configure_gcc_workaround.
#
# install_pyroveil lives in test_nvidia_config_pyroveil.sh, split out to hold
# every file under the 250-line cap.
#
# Calls go through _t_run rather than `out="$(...)"`: command substitution
# forks a subshell, and kcov does not register a lib whose first execution
# happens inside one.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=nvidia_config_harness.sh
. "${SCRIPT_DIR}/nvidia_config_harness.sh"

# shellcheck source=../nvidia_config.sh
. "${FIXES_DIR}/lib/nvidia_config.sh"

printf '\n-- backup_file --\n'

# Case 1: a file that does not exist is not backed up, and that is not an error.
nvidia_reset
_t_run backup_file "${TEST_TMPDIR}/absent"
_t_eq "0" "$?" "backup_file: returns 0 for a missing file"
_t_lacks "$out" "Backed up" "backup_file: says nothing about a missing file"

# Case 2: an existing file is copied aside and the original left in place.
nvidia_reset
printf 'ORIGINAL\n' >"${XORG_CONF}"
_t_run backup_file "${XORG_CONF}"
_t_contains "$out" "Backed up" "backup_file: reports the backup"
_t_eq "1" "$(_t_backups "${XORG_CONF}")" "backup_file: writes exactly one backup"
_t_eq "ORIGINAL" "$(cat "${XORG_CONF}")" "backup_file: leaves the original in place"

printf '\n-- configure_xorg --\n'

# Case 3: a fresh machine -> the drop-in dir is created and the config written
# with RenderAccel TRUE. Setting it false forces software rendering and pins
# Xorg at 30%+ CPU, which is why the value is asserted rather than assumed.
nvidia_reset
rm -rf "${XORG_CONF_D}"
_t_run configure_xorg
conf="$(_t_nvidia_conf)"
_t_contains "$conf" 'Option "RenderAccel" "true"' \
	"configure_xorg: enables RenderAccel"
_t_lacks "$conf" '"RenderAccel" "false"' \
	"configure_xorg: never writes the software-rendering value"
_t_contains "$conf" 'Driver "nvidia"' "configure_xorg: selects the nvidia driver"
_t_contains "$conf" 'Identifier "NVIDIA Card"' "configure_xorg: names the device section"
_t_contains "$out" "Created" "configure_xorg: reports what it created"

# Case 4: an existing xorg.conf is backed up before anything is written.
nvidia_reset
printf 'OLD XORG\n' >"${XORG_CONF}"
_t_run configure_xorg
_t_eq "1" "$(_t_backups "${XORG_CONF}")" "configure_xorg: backs up an existing xorg.conf"
_t_eq "OLD XORG" "$(cat "${XORG_CONF}")" "configure_xorg: does not overwrite xorg.conf itself"

# Case 5: an existing 20-nvidia.conf is backed up too, then replaced.
nvidia_reset
printf 'OLD NVIDIA CONF\n' >"${XORG_CONF_D}/20-nvidia.conf"
_t_run configure_xorg
_t_eq "1" "$(_t_backups "${XORG_CONF_D}/20-nvidia.conf")" \
	"configure_xorg: backs up an existing nvidia drop-in"
_t_contains "$(_t_nvidia_conf)" "RenderAccel" \
	"configure_xorg: replaces the drop-in with the managed one"

printf '\n-- configure_gcc_workaround --\n'

# Case 6: a profile without the variable -> appended.
nvidia_reset
printf '# existing profile\n' >"${PROFILE_FILE}"
_t_run configure_gcc_workaround
profile="$(_t_profile_text)"
_t_contains "$profile" "export IGNORE_CC_MISMATCH=1" \
	"configure_gcc_workaround: exports the variable"
_t_contains "$profile" "# existing profile" \
	"configure_gcc_workaround: appends rather than replacing the profile"
_t_contains "$profile" "Added by nvidia_troubleshoot.sh" \
	"configure_gcc_workaround: stamps the addition"
_t_contains "$out" "Added IGNORE_CC_MISMATCH=1" "configure_gcc_workaround: reports the change"

# Case 7: already present -> not appended a second time. Running the fix twice
# must not grow /etc/profile without bound.
nvidia_reset
printf 'export IGNORE_CC_MISMATCH=1\n' >"${PROFILE_FILE}"
_t_run configure_gcc_workaround
_t_contains "$out" "already configured" "configure_gcc_workaround: reports the skip"
_t_eq "1" "$(grep -c 'IGNORE_CC_MISMATCH' "${PROFILE_FILE}")" \
	"configure_gcc_workaround: does not duplicate the export"

# Case 8: the profile is backed up before being modified.
nvidia_reset
printf '# profile\n' >"${PROFILE_FILE}"
_t_run configure_gcc_workaround
_t_eq "1" "$(_t_backups "${PROFILE_FILE}")" \
	"configure_gcc_workaround: backs up the profile first"

printf '\nnvidia_config (xorg/gcc): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
