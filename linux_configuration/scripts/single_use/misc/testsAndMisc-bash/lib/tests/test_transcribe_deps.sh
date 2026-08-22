#!/usr/bin/env bash
# Tests for transcribe_deps.sh — the system-dependency install phase.
#
# No jail: every branch turns on `command -v` and every install goes through
# sudo, both intercepted by the harness's PATH stub dir. The assertions are on
# RECORDED ARGV, because WHICH packages each distro branch would install is
# the part that actually differs between them and the part a presence test
# cannot see -- pacman gets python-virtualenv where apt gets python3-venv.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./transcribe_harness.sh
. "$SCRIPT_DIR/transcribe_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script defines above its source line.
OFFLINE=0
FW_DIARIZE=0

# detect_pkg_mgr lives next door and is what selects the branch below.
# shellcheck source=../transcribe_pkgmgr.sh
. "$TRANSCRIBE_LIB_DIR/transcribe_pkgmgr.sh"
# shellcheck source=../transcribe_deps.sh
. "$TRANSCRIBE_LIB_DIR/transcribe_deps.sh"

# A pass-through sudo, so the package-manager stub records the real argv.
printf '#!/usr/bin/env bash\nexec "$@"\n' >"$TEST_TMPDIR/bin/sudo"
chmod +x "$TEST_TMPDIR/bin/sudo"

# --- everything already present is a no-op ----------------------------------
_t_stub ffmpeg
_t_stub espeak-ng
_t_reset_calls
present_out="$(install_system_deps 2>&1)"
_t_has "$present_out" 'System deps present' "install_system_deps reports a satisfied system"
_t_lacks "$(_t_calls)" 'pacman' "nothing is installed when ffmpeg and espeak-ng are both present"

# --- offline with a missing dep exits 5 -------------------------------------
_t_unstub ffmpeg
offline_rc=0
(
	OFFLINE=1
	install_system_deps
) >/dev/null 2>&1 || offline_rc=$?
_t_eq "5" "$offline_rc" "a missing dep in offline mode exits 5"

# --- no sudo means the install is skipped, not failed -----------------------
_t_unstub sudo
_t_stub pacman
no_sudo_out="$(install_system_deps 2>&1)"
_t_has "$no_sudo_out" 'sudo not found' "a missing sudo skips the install instead of failing"
printf '#!/usr/bin/env bash\nexec "$@"\n' >"$TEST_TMPDIR/bin/sudo"
chmod +x "$TEST_TMPDIR/bin/sudo"

# --- the pacman branch uses Arch package names ------------------------------
_t_reset_calls
install_system_deps >/dev/null 2>&1
pac_calls="$(_t_calls)"
_t_has "$pac_calls" 'python-virtualenv' "the pacman branch asks for python-virtualenv, not python3-venv"
_t_has "$pac_calls" 'ffmpeg' "the pacman branch installs the missing ffmpeg"
_t_lacks "$pac_calls" 'espeak-ng' "the pacman branch omits espeak-ng, which is already present"

# --- the apt branch uses Debian package names and refreshes first -----------
_t_unstub pacman
_t_stub apt-get
_t_reset_calls
install_system_deps >/dev/null 2>&1
apt_calls="$(_t_calls)"
_t_has "$apt_calls" 'apt-get update -y' "the apt branch refreshes the package list first"
_t_has "$apt_calls" 'python3-venv' "the apt branch asks for python3-venv, not python-virtualenv"

# --- the dnf branch ---------------------------------------------------------
_t_unstub apt-get
_t_stub dnf
_t_reset_calls
install_system_deps >/dev/null 2>&1
_t_has "$(_t_calls)" 'dnf install -y python3-venv' "the dnf branch installs python3-venv"

# --- the yum branch ---------------------------------------------------------
_t_unstub dnf
_t_stub yum
_t_reset_calls
install_system_deps >/dev/null 2>&1
_t_has "$(_t_calls)" 'yum install -y python3-venv' "the yum branch installs python3-venv"

# --- the zypper branch uses its own versioned python names ------------------
_t_unstub yum
_t_stub zypper
_t_reset_calls
install_system_deps >/dev/null 2>&1
_t_has "$(_t_calls)" 'python311-virtualenv' "the zypper branch asks for python311-virtualenv"

# --- an unknown package manager warns rather than guessing ------------------
_t_unstub zypper
unknown_out="$(install_system_deps 2>&1)"
_t_has "$unknown_out" 'Unknown package manager' "an unrecognised manager warns instead of installing"

# --- a failing install is best-effort, never fatal --------------------------
_t_stub_failing pacman
failing_out="$(install_system_deps 2>&1)"
_t_has "$failing_out" 'pacman install failed; continuing' "a failing install is reported and survived"

# --- diarization: the libsndfile probe is host-dependent --------------------
# FW_DIARIZE=1 adds a check for libsndfile at three absolute paths. This host
# HAS /usr/lib/libsndfile.so, so need_libsndfile is legitimately 0 here and
# the "add libsndfile to the package list" branch cannot be reached without a
# jail that hides the library. Asserting it would mean asserting nothing.
#
# What IS testable without a jail: with diarization on and the library
# present, the satisfied-system message names libsndfile.
_t_stub ffmpeg
diarize_out="$(
	FW_DIARIZE=1
	install_system_deps 2>&1
)"
_t_has "$diarize_out" 'libsndfile' \
	"FW_DIARIZE=1 names libsndfile in the satisfied-deps message when the library is present"

_t_report "test_transcribe_deps.sh"
