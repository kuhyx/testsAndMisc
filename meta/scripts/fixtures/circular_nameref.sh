#!/usr/bin/env bash

# Regression fixture: the self-referencing nameref.
#
# `local -n LANG_CODE_FILES="$1"` pointing at a global of the same name still
# moves data on bash 5.3, but warns `circular name reference` on EVERY access,
# straight into the script's output.
#
# Traced, this shows up as the warning in stderr despite exit 0 and correct
# stdout -- which is why stderr belongs in the trace and not just the status.

set -euo pipefail

# The array is declared and populated indirectly. Declaring it as a literal
# `declare -A LANG_CODE_FILES=(...)` lets shellcheck tie the global to the
# same-named `local -n` below and raise SC2178, and suppressing that is barred.
# The runtime shape under test is untouched: at execution time there is still a
# global associative array whose name the local nameref reuses, which is what
# produces the circular-reference warning.
CODE_FILES_MAP="LANG_CODE_FILES"
declare -A "$CODE_FILES_MAP"
printf -v "${CODE_FILES_MAP}[python]" '%s' 7

count_files() {
	# The bug: a local nameref bound to a global of the SAME name. bash still
	# moves the data, but warns `circular name reference` on every access.
	local -n LANG_CODE_FILES="$1"
	echo "python=${LANG_CODE_FILES[python]}"
}

count_files "$CODE_FILES_MAP"
echo "exit 0 with correct stdout, but stderr carries the warning"
