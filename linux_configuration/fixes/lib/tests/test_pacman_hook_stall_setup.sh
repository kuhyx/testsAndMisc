#!/usr/bin/env bash
# Tests for lib/pacman_hook_stall_setup.sh: require_root, validate_requirements,
# resolve_package_file.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_harness.sh"

# --- require_root ------------------------------------------------------------

# Under unshare -r, EUID is 0 inside this shell, so require_root's `exec sudo`
# branch must never fire (a real invocation would replace this test process).
# "$@" matches the real call site (diagnose_pacman_hook_stall.sh: require_root "$@").
if (require_root "$@"); then
	_t_pass "require_root: no-ops when EUID is already 0"
else
	_t_fail "require_root: no-op path failed as root"
fi

# --- validate_requirements ----------------------------------------------------

reset_state
if (validate_requirements); then
	_t_pass "validate_requirements: passes with fakes on PATH, readable log, no lock"
else
	_t_fail "validate_requirements: unexpectedly failed the happy path"
fi

reset_state
: >"${PACMAN_LOCK}"
if (validate_requirements) 2>/dev/null; then
	_t_fail "validate_requirements: should reject when PACMAN_LOCK exists"
else
	_t_pass "validate_requirements: rejects when PACMAN_LOCK exists"
fi
rm -f "${PACMAN_LOCK}"

reset_state
rm -f "${PACMAN_LOG}"
if (validate_requirements) 2>/dev/null; then
	_t_fail "validate_requirements: should reject an unreadable PACMAN_LOG"
else
	_t_pass "validate_requirements: rejects an unreadable PACMAN_LOG"
fi
: >"${PACMAN_LOG}"

reset_state
if (PATH="${TEST_TMPDIR}/empty_path" validate_requirements) 2>/dev/null; then
	_t_fail "validate_requirements: should reject a missing required tool"
else
	_t_pass "validate_requirements: rejects a missing required tool"
fi

# --- resolve_package_file -----------------------------------------------------

reset_state
mkdir -p "${CACHE_DIR}"
touch "${CACHE_DIR}/base-devel-1.2.3-1-x86_64.pkg.tar.zst"
got="$(resolve_package_file)"
_t_eq "${CACHE_DIR}/base-devel-1.2.3-1-x86_64.pkg.tar.zst" "$got" \
	"resolve_package_file: finds the cached package for the installed version"

reset_state
: >"${DEV}/fail_query"
if (resolve_package_file) 2>/dev/null; then
	_t_fail "resolve_package_file: should reject a package that is not installed"
else
	_t_pass "resolve_package_file: rejects a package that is not installed"
fi

reset_state
rm -f "${CACHE_DIR}"/*.pkg.tar.zst 2>/dev/null || true
if (resolve_package_file) 2>/dev/null; then
	_t_fail "resolve_package_file: should reject when the cache has no matching file"
else
	_t_pass "resolve_package_file: rejects when the cache has no matching file"
fi

echo
echo "pacman_hook_stall_setup: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
