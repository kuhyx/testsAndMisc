#!/usr/bin/env bash
# lib/tests/test_thorium_repairs_deep.sh — tests for thorium_repairs.sh's
# fix_aggressive and test_thorium.
#
# Split from test_thorium_repairs.sh to hold every file under the 250-line
# cap. test_thorium is the awkward one: it backgrounds the browser, sleeps,
# and then BLOCKS on `read -r -p`. Every case here therefore feeds it stdin,
# because a stub that leaves the read waiting hangs the whole suite -- and
# under the coverage jail that presents as a case timeout, not as a hang.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=thorium_harness.sh
. "${SCRIPT_DIR}/thorium_harness.sh"

# shellcheck source=../thorium_repairs.sh
. "${FIXES_DIR}/lib/thorium_repairs.sh"

printf '\n-- fix_aggressive --\n'

# Case 1: not aggressive -> returns without touching anything.
thorium_reset
_t_profile "Default/Cache/f"
_t_run fix_aggressive
_t_eq "yes" "$(_t_exists Default/Cache)" "fix_aggressive: leaves the cache alone by default"
_t_lacks "$out" "aggressive fixes" "fix_aggressive: says nothing when not enabled"

# Case 2: aggressive with every path present -> all six removed.
thorium_reset
AGGRESSIVE=true
_t_profile "Default/Service Worker/f" "Default/Cache/f" "Default/Code Cache/f" \
	"Default/IndexedDB/f" "BrowserMetrics/f" "component_crx_cache/f"
_t_run fix_aggressive
_t_contains "$out" "may lose some site data" "fix_aggressive: warns about data loss"
_t_eq "no" "$(_t_exists "Default/Service Worker")" "fix_aggressive: removes Service Worker"
_t_eq "no" "$(_t_exists Default/Cache)" "fix_aggressive: removes Cache"
_t_eq "no" "$(_t_exists "Default/Code Cache")" "fix_aggressive: removes Code Cache"
_t_eq "no" "$(_t_exists Default/IndexedDB)" "fix_aggressive: removes IndexedDB"
_t_eq "no" "$(_t_exists BrowserMetrics)" "fix_aggressive: removes BrowserMetrics"
_t_eq "no" "$(_t_exists component_crx_cache)" "fix_aggressive: removes the crx cache"

# Case 3: aggressive with a HEALTHY database -> checked, left in place.
thorium_reset
AGGRESSIVE=true
_t_profile "Default/Web Data" "Default/History"
_t_stub sqlite3 'exit 0'
_t_run fix_aggressive
_t_contains "$out" "Checking database: Web Data" "fix_aggressive: checks Web Data"
_t_contains "$out" "Checking database: History" "fix_aggressive: checks History"
_t_eq "yes" "$(_t_exists "Default/Web Data")" "fix_aggressive: keeps a healthy database"
_t_lacks "$out" "may be corrupted" "fix_aggressive: does not cry corruption on a good db"

# Case 4: aggressive with a CORRUPT database -> backed up.
thorium_reset
AGGRESSIVE=true
_t_profile "Default/Web Data"
_t_stub sqlite3 'exit 1'
_t_run fix_aggressive
_t_contains "$out" "may be corrupted: Web Data" "fix_aggressive: reports the corruption"
_t_eq "no" "$(_t_exists "Default/Web Data")" "fix_aggressive: moves the corrupt db aside"
_t_eq "yes" "$(_t_exists "Default/Web Data${BACKUP_SUFFIX}")" \
	"fix_aggressive: the corrupt db is backed up, not deleted"

# Case 5: sqlite3 not installed -> the integrity check is skipped entirely,
# and the database is left untouched rather than assumed bad.
thorium_reset
AGGRESSIVE=true
_t_profile "Default/History"
_t_unstub sqlite3
_t_hide sqlite3
_t_run fix_aggressive
_t_eq "yes" "$(_t_exists Default/History)" "fix_aggressive: keeps the db without sqlite3"
_t_lacks "$out" "may be corrupted" "fix_aggressive: makes no corruption claim without sqlite3"
_t_full_path

printf '\n-- test_thorium --\n'

# Case 6: TEST_AFTER unset -> returns immediately, browser never launched.
thorium_reset
_t_run test_thorium
_t_lacks "$(_t_calls)" "thorium-browser" "test_thorium: does not launch when not asked"

# Case 7: dry-run says what it would do and launches nothing.
thorium_reset
TEST_AFTER=true
DRY_RUN=true
_t_run test_thorium
_t_contains "$out" "Would test thorium-browser startup" "test_thorium: dry-run states intent"
_t_lacks "$(_t_calls)" "thorium-browser" "test_thorium: dry-run launches nothing"

# Case 8: the browser stays up, and the prompt is answered "n" -> killed.
# The stub sleeps longer than the lib's own 4s wait so the process is still
# alive when `kill -0` runs.
thorium_reset
TEST_AFTER=true
_t_stub thorium-browser 'sleep 30'
test_thorium <<<"n" >"${TEST_TMPDIR}/tt_out" 2>&1
out="$(cat "${TEST_TMPDIR}/tt_out")"
_t_contains "$out" "Thorium started successfully" "test_thorium: reports a successful start"
_t_contains "$out" "Browser closed" "test_thorium: closes the browser when answered n"

# Case 9: answered with a bare newline -> the default keeps it running.
thorium_reset
TEST_AFTER=true
_t_stub thorium-browser 'sleep 30'
test_thorium <<<"" >"${TEST_TMPDIR}/tt_out" 2>&1
out="$(cat "${TEST_TMPDIR}/tt_out")"
_t_contains "$out" "Browser left running" "test_thorium: default answer leaves it running"

# Case 10: the browser dies immediately -> the failure advice, and exit 1.
# Run in a subshell: the lib calls `exit 1` on this path, which would
# otherwise end this test file early.
thorium_reset
TEST_AFTER=true
_t_stub thorium-browser 'exit 1'
rc=0
(test_thorium </dev/null >"${TEST_TMPDIR}/tt_out" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/tt_out")"
_t_eq "1" "$rc" "test_thorium: exits 1 when the browser will not stay up"
_t_contains "$out" "still crashing after fixes" "test_thorium: reports the crash"
_t_contains "$out" "yay -S thorium-browser-bin" "test_thorium: suggests a reinstall"

printf '\nthorium_repairs (deep): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
