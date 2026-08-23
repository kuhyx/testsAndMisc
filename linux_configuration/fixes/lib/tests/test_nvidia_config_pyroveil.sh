#!/usr/bin/env bash
# lib/tests/test_nvidia_config_pyroveil.sh — tests for nvidia_config.sh's
# install_pyroveil.
#
# Split from test_nvidia_config.sh to hold every file under the 250-line cap.
#
# The interactive arm BLOCKS on `read -p`, so the two cases that exercise it
# feed stdin explicitly. A case that leaves the read waiting hangs the whole
# suite, and under the coverage jail that presents as a case timeout rather
# than as a hang.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=nvidia_config_harness.sh
. "${SCRIPT_DIR}/nvidia_config_harness.sh"

# shellcheck source=../nvidia_config.sh
. "${FIXES_DIR}/lib/nvidia_config.sh"

printf '\n-- install_pyroveil --\n'

# Case 1: non-interactive -> auto-installs without prompting.
nvidia_reset
_t_run install_pyroveil
_t_eq "0" "$?" "install_pyroveil: returns 0 on a clean auto-install"
_t_contains "$out" "Auto-installing Pyroveil" "install_pyroveil: says it is auto-installing"
calls="$(_t_calls)"
_t_contains "$calls" "git clone" "install_pyroveil: clones the repository"
_t_contains "$calls" "sudo -u testuser" \
	"install_pyroveil: drops to the invoking user rather than building as root"
_t_contains "$out" "installed successfully" "install_pyroveil: reports success"

# Case 2: the helper script is written, executable, and owned by the user.
nvidia_reset
_t_run install_pyroveil
helper="${USER_HOME}/run-with-pyroveil.sh"
_t_eq "yes" "$([[ -f "$helper" ]] && echo yes || echo no)" \
	"install_pyroveil: creates the helper script"
_t_eq "yes" "$([[ -x "$helper" ]] && echo yes || echo no)" \
	"install_pyroveil: makes the helper executable"
_t_contains "$(cat "$helper")" 'export PYROVEIL=1' \
	"install_pyroveil: the helper sets PYROVEIL"
_t_contains "$(cat "$helper")" 'PYROVEIL_DIR="'"${USER_HOME}"'/pyroveil"' \
	"install_pyroveil: the helper points at the install dir"
_t_contains "$(_t_calls)" "chown testuser:testuser" \
	"install_pyroveil: hands the helper to the user, not root"

# Case 3: an existing checkout is updated rather than re-cloned.
nvidia_reset
mkdir -p "${USER_HOME}/pyroveil"
_t_run install_pyroveil
_t_contains "$out" "already exists. Updating" "install_pyroveil: reports the update path"
_t_lacks "$(_t_calls)" "git clone" "install_pyroveil: does not re-clone over a checkout"

# Case 4: a missing build dependency -> refuse, with the package hint, and
# return non-zero so the caller knows nothing was installed.
nvidia_reset
_t_unstub ninja
_t_hide ninja
rc=0
_t_run install_pyroveil || rc=$?
_t_eq "1" "$rc" "install_pyroveil: returns 1 when a dependency is missing"
_t_contains "$out" "Missing dependencies: ninja" "install_pyroveil: names the missing tool"
_t_contains "$out" "pacman -S base-devel git cmake ninja" \
	"install_pyroveil: gives the install command"
_t_lacks "$(_t_calls)" "git clone" "install_pyroveil: clones nothing when deps are missing"
_t_full_path

# Case 5: several missing dependencies are all listed, not just the first.
nvidia_reset
_t_unstub ninja cmake
_t_hide ninja cmake
rc=0
_t_run install_pyroveil || rc=$?
_t_eq "1" "$rc" "install_pyroveil: still returns 1 with several missing"
_t_contains "$out" "cmake" "install_pyroveil: lists cmake"
_t_contains "$out" "ninja" "install_pyroveil: lists ninja too"
_t_full_path

# Case 6: interactive, answered "y" -> installs.
nvidia_reset
INTERACTIVE_MODE="true"
install_pyroveil <<<"y" >"${TEST_TMPDIR}/o" 2>&1
out="$(cat "${TEST_TMPDIR}/o")"
# `read -p` writes its prompt straight to the terminal, not to stdout or
# stderr, so it is not observable in captured output. What IS observable is
# that the interactive arm did not auto-install: the "Auto-installing" line
# belongs to the non-interactive branch only.
_t_lacks "$out" "Auto-installing Pyroveil" \
	"install_pyroveil: takes the prompt branch, not the auto branch"
_t_contains "$(_t_calls)" "git clone" "install_pyroveil: installs when the answer is y"

# Case 7: interactive, answered "n" -> skipped, nothing installed.
nvidia_reset
INTERACTIVE_MODE="true"
install_pyroveil <<<"n" >"${TEST_TMPDIR}/o" 2>&1
out="$(cat "${TEST_TMPDIR}/o")"
_t_contains "$out" "Skipping Pyroveil installation" "install_pyroveil: honours a no"
_t_lacks "$(_t_calls)" "git clone" "install_pyroveil: clones nothing when declined"
_t_eq "no" "$([[ -f "${USER_HOME}/run-with-pyroveil.sh" ]] && echo yes || echo no)" \
	"install_pyroveil: writes no helper when declined"

printf '\nnvidia_config (pyroveil): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
