#!/bin/bash

# ============================================================================
# Fixture tests for boot-repair.
#
# Each test builds a throwaway root tree in a temp dir and runs boot-repair
# against it with --root, so nothing on the real machine is touched. This
# exercises detection, repair and the safety guards; it cannot exercise
# mount/modprobe, which need the live system.
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly BOOT_REPAIR="$SCRIPT_DIR/../boot-repair"

PASS=0
FAIL=0
WORKROOT=""

cleanup() {
	[[ -n $WORKROOT && -d $WORKROOT ]] && rm -rf "$WORKROOT"
}
trap cleanup EXIT

pass() {
	PASS=$((PASS + 1))
	printf '  [PASS] %s\n' "$1"
}

fail() {
	FAIL=$((FAIL + 1))
	printf '  [FAIL] %s\n' "$1"
	[[ -n ${2:-} ]] && printf '         %s\n' "$2"
}

# assert_contains <description> <haystack> <needle>
assert_contains() {
	if [[ $2 == *"$3"* ]]; then
		pass "$1"
	else
		fail "$1" "expected to find: $3"
	fi
}

# assert_not_contains <description> <haystack> <needle>
assert_not_contains() {
	if [[ $2 != *"$3"* ]]; then
		pass "$1"
	else
		fail "$1" "did not expect: $3"
	fi
}

# assert_eq <description> <actual> <expected>
assert_eq() {
	if [[ $2 == "$3" ]]; then
		pass "$1"
	else
		fail "$1" "expected '$3', got '$2'"
	fi
}

# shellcheck source=lib/boot_repair_cases.sh
source "$SCRIPT_DIR/lib/boot_repair_cases.sh"


# ----------------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------------

main() {
	WORKROOT="$(mktemp -d)" || {
		echo "mktemp failed" >&2
		exit 2
	}

	[[ -x $BOOT_REPAIR ]] || {
		echo "boot-repair not executable at $BOOT_REPAIR" >&2
		exit 2
	}

	echo "=== boot-repair fixture tests ==="
	echo

	test_healthy_system
	test_stale_esp_kernel_detected
	test_incomplete_tree_ignored
	test_picks_newest_complete
	test_fstab_nofail_fixed
	test_shadow_files_removed
	test_shadow_guard_refuses_real_esp
	test_parallel_downloads_fixed
	test_missing_modules_dep
	test_no_kernel_at_all
	test_help_and_bad_args

	echo
	echo "=== $PASS passed, $FAIL failed ==="
	[[ $FAIL -eq 0 ]]
}

main "$@"
