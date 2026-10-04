#!/bin/bash

# ============================================================================
# Run only the pytest files related to files changed vs HEAD (staged, unstaged
# and untracked). Quiet: failures plus a one-line summary. Falls back to the
# full suite when a change cannot be mapped to tests. Coverage is NOT measured
# here (the full gate is meta/scripts/pytest_changed_packages.py); addopts is
# overridden to drop the -v/--cov flags from meta/pyproject.toml.
# ============================================================================

set -euo pipefail

readonly OPTS='--strict-markers --strict-config'

main() {
	cd "$(git rev-parse --show-toplevel)"
	local changed=() tests=() full=0 f base t
	while IFS= read -r f; do
		[[ -n "$f" && -e "$f" ]] && changed+=("$f")
	done < <({
		git diff --name-only HEAD 2>/dev/null || true
		git ls-files --others --exclude-standard
	} | sort -u)

	for f in "${changed[@]}"; do
		case "$f" in
		*/conftest.py | conftest.py | meta/pyproject.toml | pyproject.toml | meta/requirements*.txt) full=1 ;;
		python_pkg/*.py | linux_configuration/tests/*.py | tests/*.py)
			base="$(basename "$f" .py)"
			if [[ "$base" == test_* || "$base" == *_test ]]; then
				tests+=("$f")
			else
				while IFS= read -r t; do tests+=("$t"); done \
					< <(git ls-files "*test_${base}.py" "*${base}_test.py")
			fi
			;;
		esac
	done

	if [[ $full -eq 0 && ${#changed[@]} -eq 0 ]]; then
		echo "no changes vs HEAD: nothing to test"
		exit 0
	fi
	if [[ $full -eq 0 && ${#tests[@]} -gt 0 ]]; then
		python3 -m pytest -q --tb=short -o addopts="$OPTS" "${tests[@]}"
		exit $?
	fi
	if [[ $full -eq 0 ]] && ! printf '%s\n' "${changed[@]}" | grep -q '\.py$'; then
		echo "no python changes: nothing to test"
		exit 0
	fi
	echo "no mapped tests: running full suite"
	python3 -m pytest -q --tb=short -o addopts="$OPTS"
}

main "$@"
exit $?
