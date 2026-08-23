#!/usr/bin/env bash
# lib/tests/test_thorium_repairs.sh — tests for thorium_repairs.sh's profile
# repairs: Local State, singleton locks, GPU cache and crash reports.
#
# fix_aggressive and test_thorium live in test_thorium_repairs_deep.sh, split
# out to hold every file under the 250-line cap.
#
# Calls go through _t_run rather than `out="$(...)"`: command substitution
# forks a subshell, and kcov does not register a lib whose first execution
# happens inside one.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=thorium_harness.sh
. "${SCRIPT_DIR}/thorium_harness.sh"

# shellcheck source=../thorium_repairs.sh
. "${FIXES_DIR}/lib/thorium_repairs.sh"

printf '\n-- fix_local_state --\n'

# Case 1: no Local State at all -- a fresh install.
thorium_reset
_t_run fix_local_state
_t_eq "0" "$?" "fix_local_state: returns 0 with no Local State"
_t_contains "$out" "No Local State file found" "fix_local_state: reports a fresh install"

# Case 2: valid JSON is STILL backed up -- the lib treats a readable Local
# State as a crash source in its own right, not just a corrupt one.
thorium_reset
_t_profile "Local State"
_t_stub python3 'exit 0'
_t_run fix_local_state
_t_contains "$out" "backing up (common crash source)" \
	"fix_local_state: backs up even valid JSON"
_t_eq "no" "$(_t_exists "Local State")" "fix_local_state: moves the valid file aside"
_t_eq "yes" "$(_t_exists "Local State${BACKUP_SUFFIX}")" \
	"fix_local_state: the backup carries the suffix"

# Case 3: corrupted JSON -- python3 exits non-zero.
thorium_reset
_t_profile "Local State"
_t_stub python3 'exit 1'
_t_run fix_local_state
_t_contains "$out" "appears corrupted" "fix_local_state: reports corruption"
_t_eq "yes" "$(_t_exists "Local State${BACKUP_SUFFIX}")" \
	"fix_local_state: backs up the corrupt file"

# Case 4: dry-run leaves the file in place.
thorium_reset
_t_profile "Local State"
_t_stub python3 'exit 0'
DRY_RUN=true
_t_run fix_local_state
_t_eq "yes" "$(_t_exists "Local State")" "fix_local_state: dry-run keeps the file"
_t_contains "$out" "Would backup" "fix_local_state: dry-run says what it would do"

printf '\n-- fix_singleton_locks --\n'

# Case 5: no locks present.
thorium_reset
_t_run fix_singleton_locks
_t_contains "$out" "No stale lock files found" "fix_singleton_locks: reports none found"

# Case 6: all three locks present -> all cleared.
thorium_reset
_t_profile SingletonLock SingletonSocket SingletonCookie
_t_run fix_singleton_locks
_t_eq "no" "$(_t_exists SingletonLock)" "fix_singleton_locks: clears SingletonLock"
_t_eq "no" "$(_t_exists SingletonSocket)" "fix_singleton_locks: clears SingletonSocket"
_t_eq "no" "$(_t_exists SingletonCookie)" "fix_singleton_locks: clears SingletonCookie"
_t_lacks "$out" "No stale lock files found" \
	"fix_singleton_locks: does not claim none were found"

# Case 7: only one lock present -- the partial case, which the counter must
# still treat as "something was cleared".
thorium_reset
_t_profile SingletonLock
_t_run fix_singleton_locks
_t_eq "no" "$(_t_exists SingletonLock)" "fix_singleton_locks: clears the one lock"
_t_lacks "$out" "No stale lock files found" \
	"fix_singleton_locks: counts a single lock as cleared"

printf '\n-- fix_gpu_cache --\n'

# Case 8: nothing cached.
thorium_reset
_t_run fix_gpu_cache
_t_contains "$out" "No GPU cache to clear" "fix_gpu_cache: reports an empty cache"

# Case 9: all four cache locations, including the Default/ ones.
thorium_reset
_t_profile GPUCache/f "Default/GPUCache/f" ShaderCache/f "Default/ShaderCache/f"
_t_run fix_gpu_cache
_t_eq "no" "$(_t_exists GPUCache)" "fix_gpu_cache: clears the top-level GPUCache"
_t_eq "no" "$(_t_exists Default/GPUCache)" "fix_gpu_cache: clears the profile GPUCache"
_t_eq "no" "$(_t_exists ShaderCache)" "fix_gpu_cache: clears the top-level ShaderCache"
_t_eq "no" "$(_t_exists Default/ShaderCache)" "fix_gpu_cache: clears the profile ShaderCache"
_t_lacks "$out" "No GPU cache to clear" "fix_gpu_cache: does not claim the cache was empty"

printf '\n-- fix_crash_reports --\n'

# Case 10: no crash directory.
thorium_reset
_t_run fix_crash_reports
_t_eq "0" "$?" "fix_crash_reports: returns 0 with no crash directory"

# Case 11: crash directory present but EMPTY -> left alone, since the count
# gate is what decides, not the directory's existence.
thorium_reset
mkdir -p "${THORIUM_CONFIG_DIR}/Crash Reports"
_t_run fix_crash_reports
_t_eq "yes" "$(_t_exists "Crash Reports")" "fix_crash_reports: keeps an empty crash dir"

# Case 12: crash reports present -> removed and counted.
thorium_reset
_t_profile "Crash Reports/a" "Crash Reports/b"
_t_run fix_crash_reports
_t_eq "no" "$(_t_exists "Crash Reports")" "fix_crash_reports: removes the crash dir"
_t_contains "$out" "Cleared 2 crash report(s)" "fix_crash_reports: counts the reports"

# Case 13: dry-run reports the count without deleting.
thorium_reset
_t_profile "Crash Reports/a"
DRY_RUN=true
_t_run fix_crash_reports
_t_eq "yes" "$(_t_exists "Crash Reports")" "fix_crash_reports: dry-run keeps the dir"
_t_contains "$out" "Would clear 1 crash report(s)" "fix_crash_reports: dry-run states the count"

printf '\nthorium_repairs (profile): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
