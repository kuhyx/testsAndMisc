# shellcheck shell=bash
# ============================================================================
# ci_mirror_range.sh — resolve WHAT a push must re-check.
#
# Sourced by ci_mirror.sh. Splits out of it to stay under the 250-line cap.
#
# The push range arrives as PRE_COMMIT_FROM_REF/PRE_COMMIT_TO_REF, which
# pre-commit exports because the pre-push hook passes --from-ref/--to-ref
# resolved from the refs git feeds it on stdin. Those are the REMOTE's actual
# shas, so unlike `origin/main` they cannot go stale and silently widen or
# empty the range.
# ============================================================================

# Files whose change invalidates any narrower scope: the gate's own machinery
# and the hook definitions. Editing a hook must re-check the whole repo, or the
# new rule only ever sees the handful of files in the same push.
readonly GATE_WIDENING_RE='^(\.pre-commit-config\.yaml|meta/scripts/|meta/pyproject\.toml|requirements\.txt|linux_configuration/\.githooks/)'

# Shared shell foundations. A change here can affect every suite, so it fans
# out to all of them rather than to the suite that happens to contain it.
readonly SHELL_WIDENING_RE='^linux_configuration/scripts/lib/|/tests/lib_test_(core|path)\.sh$'

# Emit the paths in the push range, one per line. Empty output means "no range
# known", which callers must treat as "check everything", never as "nothing".
changed_paths() {
	if [[ -z "${PRE_COMMIT_FROM_REF:-}" || -z "${PRE_COMMIT_TO_REF:-}" ]]; then
		return 0
	fi
	git -C "$ROOT" diff --name-only \
		"$PRE_COMMIT_FROM_REF" "$PRE_COMMIT_TO_REF" 2>/dev/null || true
}

# True when the whole repo must be swept: no known range, or a gate file moved.
needs_full_sweep() {
	local paths="$1"
	[[ -z "$paths" ]] && return 0
	grep -qE "$GATE_WIDENING_RE" <<<"$paths" && return 0
	return 1
}

# True when the push touches Python at all. The pytest stage is all-or-nothing
# by design (whole-repo 100% branch coverage), so this is a run/skip decision,
# not a subset one.
touches_python() {
	grep -qE '\.py$|^requirements\.txt$' <<<"$1"
}

# Map changed paths to the lib/tests suites that must run.
#
# Printing nothing means no shell suite needs to run. A shared-foundation
# change prints every suite instead of just the enclosing one.
select_shell_suites() {
	local paths="$1" all_suites="$2"
	if ! grep -qE '\.(sh|bash)$|/tests/' <<<"$paths"; then
		return 0
	fi
	if grep -qE "$SHELL_WIDENING_RE" <<<"$paths"; then
		printf '%s\n' "$all_suites"
		return 0
	fi

	# A suite covers the entry scripts in its PARENT directory as well as its
	# own lib/, so the parent is the right scope -- but match it
	# non-recursively. `scripts/lib/tests` has parent
	# `linux_configuration/scripts`, which is a prefix of every other suite's
	# path; a recursive match there would fire it on every shell push.
	# `[^/]+$` keeps a path in the parent itself, while the second alternative
	# picks up the suite's own lib/ and tests/ at any depth.
	local suite parent
	while IFS= read -r suite; do
		[[ -z "$suite" ]] && continue
		parent="${suite%/lib/tests/run_all.sh}"
		parent="${parent#./}"
		if grep -qE "^${parent}/([^/]+$|lib/)" <<<"$paths"; then
			printf '%s\n' "$suite"
		fi
	done <<<"$all_suites"
}
