#!/usr/bin/env bash
# Tests for transcribe_pkgmgr.sh — package-manager detection and the CUDA check.
#
# No jail: every branch turns on `command -v <manager>` and every install goes
# through sudo, both of which the harness's PATH stub dir intercepts. The
# suite asserts on RECORDED ARGV, because which packages a branch would
# install is the part a presence test cannot see.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./transcribe_harness.sh
. "$SCRIPT_DIR/transcribe_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script defines above its source line.
OFFLINE=0
VENV_DIR="$TEST_TMPDIR/venv"
PY_HELPERS="$TEST_TMPDIR/helpers.py"

# shellcheck source=../transcribe_pkgmgr.sh
. "$TRANSCRIBE_LIB_DIR/transcribe_pkgmgr.sh"

# --- detect_pkg_mgr: none of them present -----------------------------------
_t_eq "none" "$(detect_pkg_mgr)" "detect_pkg_mgr reports 'none' with no manager on PATH"

# --- detect_pkg_mgr: each manager, in the documented priority order ---------
# Later entries are added on top of earlier ones to prove the ORDER, not just
# that each name is recognised: apt must win over dnf, dnf over yum, and so on.
_t_stub zypper
_t_eq "zypper" "$(detect_pkg_mgr)" "detect_pkg_mgr finds zypper"
_t_stub pacman
_t_eq "pacman" "$(detect_pkg_mgr)" "pacman takes priority over zypper"
_t_stub yum
_t_eq "yum" "$(detect_pkg_mgr)" "yum takes priority over pacman"
_t_stub dnf
_t_eq "dnf" "$(detect_pkg_mgr)" "dnf takes priority over yum"
_t_stub apt-get
_t_eq "apt" "$(detect_pkg_mgr)" "apt-get takes highest priority and reports 'apt'"

# --- has_libcublas12: absent everywhere -------------------------------------
cublas_rc=0
has_libcublas12 || cublas_rc=$?
_t_eq "1" "$cublas_rc" "has_libcublas12 fails when no CUDA library exists"

# --- has_libcublas12: found in a venv's nvidia site-packages ----------------
mkdir -p "$VENV_DIR/bin"
printf '#!/usr/bin/env bash\nprintf "3.11\\n"\n' >"$VENV_DIR/bin/python"
chmod +x "$VENV_DIR/bin/python"
mkdir -p "$VENV_DIR/lib/python3.11/site-packages/nvidia/cublas/lib"
: >"$VENV_DIR/lib/python3.11/site-packages/nvidia/cublas/lib/libcublas.so.12"
cublas_rc=0
has_libcublas12 || cublas_rc=$?
_t_eq "0" "$cublas_rc" "has_libcublas12 finds the library inside the venv's nvidia packages"

# --- ensure_cuda_runtime: already present is a no-op ------------------------
_t_reset_calls
ensure_cuda_runtime
_t_lacks "$(_t_calls)" 'sudo' "ensure_cuda_runtime installs nothing when cuBLAS is already present"

# --- ensure_cuda_runtime: offline and missing exits 6 -----------------------
rm -f "$VENV_DIR/lib/python3.11/site-packages/nvidia/cublas/lib/libcublas.so.12"
offline_rc=0
(
	OFFLINE=1
	ensure_cuda_runtime
) >/dev/null 2>&1 || offline_rc=$?
_t_eq "6" "$offline_rc" "ensure_cuda_runtime exits 6 when offline and CUDA is missing"

# --- ensure_cuda_runtime: no sudo means the install is skipped -------------
no_sudo_out="$( (ensure_cuda_runtime) 2>&1)" || true
_t_has "$no_sudo_out" 'sudo not found' "ensure_cuda_runtime reports a missing sudo instead of failing on it"

# --- ensure_cuda_runtime: the pacman branch ---------------------------------
# sudo is a pass-through so the manager stub below records the real argv.
printf '#!/usr/bin/env bash\nexec "$@"\n' >"$TEST_TMPDIR/bin/sudo"
chmod +x "$TEST_TMPDIR/bin/sudo"
rm -f "$TEST_TMPDIR/bin/apt-get" "$TEST_TMPDIR/bin/dnf" "$TEST_TMPDIR/bin/yum"
_t_reset_calls
pac_rc=0
(ensure_cuda_runtime) >/dev/null 2>&1 || pac_rc=$?
_t_has "$(_t_calls)" 'pacman -Sy --noconfirm cuda cudnn' "the pacman branch installs cuda and cudnn"
_t_eq "6" "$pac_rc" "a still-missing cuBLAS after the install attempt exits 6"

# --- ensure_cuda_runtime: the apt branch ------------------------------------
_t_stub apt-get
_t_reset_calls
(ensure_cuda_runtime) >/dev/null 2>&1 || true
_t_has "$(_t_calls)" 'apt-get install -y nvidia-cuda-toolkit' "the apt branch installs the CUDA toolkit"

# --- ensure_cuda_runtime: dnf and yum share one branch ----------------------
rm -f "$TEST_TMPDIR/bin/apt-get"
_t_stub dnf
_t_reset_calls
(ensure_cuda_runtime) >/dev/null 2>&1 || true
_t_has "$(_t_calls)" 'dnf install -y cuda cudnn' "the dnf branch installs cuda and cudnn"

rm -f "$TEST_TMPDIR/bin/dnf"
_t_stub yum
_t_reset_calls
(ensure_cuda_runtime) >/dev/null 2>&1 || true
_t_has "$(_t_calls)" 'yum install -y cuda cudnn' "the shared dnf|yum branch also drives yum"

# --- ensure_cuda_runtime: the zypper branch ---------------------------------
rm -f "$TEST_TMPDIR/bin/yum" "$TEST_TMPDIR/bin/pacman"
_t_stub zypper
_t_reset_calls
(ensure_cuda_runtime) >/dev/null 2>&1 || true
_t_has "$(_t_calls)" 'zypper install -y cuda cudnn' "the zypper branch installs cuda and cudnn"

# --- ensure_cuda_runtime: an unknown manager warns --------------------------
rm -f "$TEST_TMPDIR/bin/zypper"
unknown_out="$( (ensure_cuda_runtime) 2>&1)" || true
_t_has "$unknown_out" 'cannot install CUDA automatically' "an unknown package manager warns rather than guessing"

_t_report "test_transcribe_pkgmgr.sh"
