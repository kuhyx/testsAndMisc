#!/usr/bin/env bash

# Regression fixture: the `set -e` function-tail abort.
#
# Reproduces the analyze_repo.sh bug. Eight `((MAP[x] > 0)) && HAS_Y=true` lines
# were top-level statements, where a false `&&` merely leaves $? non-zero.
# Wrapped into a function they become its RETURN VALUE, and the last one --
# false for most inputs -- kills the script under set -e.
#
# Traced, this shows up as exit 1 with every later call missing from the trace.

set -euo pipefail

declare -A LANG_FILES=([python]=3 [java]=0)

detect_languages() {
	local HAS_PYTHON=false HAS_JAVA=false
	((LANG_FILES[python] > 0)) && HAS_PYTHON=true
	# Read both flags BEFORE the failing tail, not after. An earlier revision
	# put `echo "java=$HAS_JAVA"` at the end to satisfy SC2034 -- which made
	# that echo the function's last statement, gave it exit 0, and silently
	# deleted the very bug this fixture exists to reproduce. The trace went
	# from exit 1 to exit 0 and the check passed while testing nothing. Keep
	# the bare conditional last.
	echo "python=$HAS_PYTHON java=$HAS_JAVA"
	# The tail. False, so the function returns 1 and set -e aborts the script.
	((LANG_FILES[java] > 0)) && HAS_JAVA=true
}

detect_languages
echo "reached the line after detect_languages"
systemctl status something
