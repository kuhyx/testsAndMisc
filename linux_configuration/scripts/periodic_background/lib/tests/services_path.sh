#!/usr/bin/env bash
# lib/tests/services_path.sh — build the PATH the tests run under.
#
# Sourced by services_harness.sh once $FAKE_BIN and $TEST_TMPDIR exist. Split
# out of the harness to keep both under the repo-wide 250-line cap.

# `command -v <app>` decides whether the app/browser/VBox checks apply, and it
# is a bash builtin that cannot be shimmed. The tests control it by owning PATH:
# $FAKE_BIN holds the shims and the staged fake apps, and $REAL_BIN is a
# curated directory of symlinks to the genuine coreutils the shims and the
# checks themselves need (grep, sed, tail, ...).
#
# Crucially the machine's own /usr/bin is NOT on PATH, so a really-installed
# discord or chromium cannot make "no target apps present" untestable -- which
# it did, until these tests caught it. Every symlink is created from an
# explicit list and the loop fails loudly on a tool it cannot find, because a
# silently-missing tool shows up much later as a `set -e` abort mid-suite with
# no message, which cost a debugging round the first time.
readonly REAL_BIN="${TEST_TMPDIR}/real_bin"
mkdir -p "${REAL_BIN}"

for real in bash sh env grep egrep awk sed find wc cut tr basename dirname \
	seq sha256sum cat ls mkdir rmdir rm chmod chown ln readlink realpath \
	stat sort head tail uniq id getent date mktemp touch cp mv diff xargs \
	tee expr; do
	real_path="$(PATH="/usr/local/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
		command -v "$real" 2>/dev/null)" || {
		printf 'harness: required tool not found on the system: %s\n' "$real" >&2
		exit 1
	}
	ln -sf "$real_path" "${REAL_BIN}/${real}"
done
unset real real_path
