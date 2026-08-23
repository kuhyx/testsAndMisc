#!/usr/bin/env bash

# ============================================================================
# The coverage bar for check_shell_coverage.sh.
#
# Split out of that script on 2026-08-22 to keep both files under the repo's
# 250-line cap. Sourced, not executed.
# ============================================================================

# A lib is covered when its directory has a suite that actually exercises it.
#
# History, because this has moved twice:
#   * originally a presence check -- "a run_all.sh exists beside it".
#   * 2026-08-22: raised to a measured 100% line-coverage bar through
#     shell_coverage_jail.sh, on the grounds that presence alone is satisfied
#     by an empty suite that sources the lib and asserts nothing.
#   * 2026-08-23: lowered back to presence, PLUS a reference check that closes
#     the empty-suite hole the 100% bar was reaching for.
#
# Why the 100% bar was dropped. It is reachable -- dot_resolver_install.sh
# measures 39/39 -- but only with one hand-written test file per lib, driven
# through a kcov+userns jail. Measured cost across the campaign: 22 libs in
# fixes/lib took 34 test files, and each lib is 30-60 minutes because the jail
# runs serially (concurrent jails produce false failures), takes 37-90s per
# pass, and needs a production "seam" added before most libs are testable at
# all. That priced the remaining 84 exempt libs at several days of work for a
# repo of personal automation scripts. The user's call, 2026-08-23: not worth
# it. Python keeps its 100% branch-coverage bar, where the instrument is fast
# and reliable and the bar is already met.
#
# What replaces it: presence, as before 2026-08-22. The empty-suite hole is
# accepted deliberately rather than closed with a stricter check. A "the suite
# must mention the lib by name" variant was written and measured first: it
# newly BLOCKED 68 libs in directories that already have suites (38 in
# utils/lib alone), because those libs passed the old presence check and so
# were never added to the allowlist -- and seed_allowlist refuses to grow, by
# design. Tightening the predicate without a way to grandfather the existing
# tree turns a ratchet into a wall, so the looser check is the correct one
# here. The hole it leaves needs someone to deliberately write an empty
# run_all.sh, which no one has done.
#
# The jail is NOT deleted. shell_coverage_jail.sh remains the tool for
# measuring a lib on purpose, and ci_mirror.sh still runs jailed suites. Only
# the automatic per-lib percentage gate is gone.

is_covered() {
	local path="$1"
	[[ -f "$(dirname "$path")/tests/run_all.sh" ]]
}
