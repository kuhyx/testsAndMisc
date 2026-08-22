#!/usr/bin/env bash
# lib/tests/transcribe_harness.sh — shared fixture for the transcribe libs.
#
# Sourced, not executed. One harness per DIRECTORY, not per file: jscpd fails
# the commit above 2% duplication, and near-identical per-file harnesses are
# exactly how that trips.
#
# Unlike the features/lib harness, these subjects need NO jail. They branch on
# `command -v <pkg manager>` and shell out through sudo; both are intercepted
# by a PATH stub dir, so nothing here can reach a real package manager. The
# suites assert on the RECORDED ARGV -- which packages a branch would install
# is the thing worth checking, and it is invisible to a presence test.
set -euo pipefail

PASS=0
FAIL=0

_t_pass() {
	PASS=$((PASS + 1))
	printf '  OK: %s\n' "$1"
}

_t_fail() {
	FAIL=$((FAIL + 1))
	printf '  FAIL: %s\n' "$1"
}

_t_eq() {
	if [[ $2 == "$1" ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (want '${1}', got '${2}')"
	fi
}

_t_has() {
	if [[ $1 == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (want a substring '${2}')"
	fi
}

_t_lacks() {
	if [[ $1 != *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (did not want a substring '${2}')"
	fi
}

TRANSCRIBE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TRANSCRIBE_LIB_DIR

log() { printf '[log] %s\n' "$*"; }

_t_setup_env() {
	TEST_TMPDIR="$(mktemp -d)"
	export TEST_TMPDIR
	mkdir -p "$TEST_TMPDIR/bin"
	# PATH is REPLACED rather than prepended, but coreutils is kept: these
	# subjects branch on which package managers exist and this host really
	# has pacman, so a prepended dir could not HIDE it and every "not
	# installed" case would silently assert nothing. The stub dir plus a
	# private coreutils dir is the whole PATH; package managers and sudo
	# appear only when a test puts them there.
	mkdir -p "$TEST_TMPDIR/coreutils"
	local tool
	# `bash` is in this list because every stub carries a `#!/usr/bin/env bash`
	# shebang, and env resolves it through the RESTRICTED PATH. Without it each
	# stub dies with "env: 'bash': No such file or directory" and the branch it
	# was standing in for is silently never taken.
	for tool in basename bash cat chmod cp env grep ln mkdir mktemp printf rm sed; do
		if command -v "$tool" >/dev/null 2>&1; then
			ln -sf "$(command -v "$tool")" "$TEST_TMPDIR/coreutils/$tool"
		fi
	done
	PATH="$TEST_TMPDIR/bin:$TEST_TMPDIR/coreutils"
	export PATH
}

# Record-and-succeed stub. The argv is the assertion target, so it is written
# verbatim to one line of the call log.
_t_stub() {
	printf '#!/usr/bin/env bash\nprintf "%%s %%s\\n" "%s" "$*" >>"%s/calls.log"\nexit 0\n' \
		"$1" "$TEST_TMPDIR" >"$TEST_TMPDIR/bin/$1"
	chmod +x "$TEST_TMPDIR/bin/$1"
}

# A stub that FAILS, for the "install failed; continuing" best-effort paths.
_t_stub_failing() {
	printf '#!/usr/bin/env bash\nprintf "%%s %%s\\n" "%s" "$*" >>"%s/calls.log"\nexit 1\n' \
		"$1" "$TEST_TMPDIR" >"$TEST_TMPDIR/bin/$1"
	chmod +x "$TEST_TMPDIR/bin/$1"
}

# Remove a stub AND forget it. bash caches executable locations in a hash
# table, so `command -v foo` keeps succeeding after foo is deleted until the
# table is cleared -- which silently turns every "tool is missing" test into a
# "tool is present" test that asserts the opposite of its own name. Verified:
# without the `hash -r` the removed stub is STILL FOUND.
_t_unstub() {
	rm -f "$TEST_TMPDIR/bin/$1"
	hash -r
}

_t_calls() {
	if [[ -f "$TEST_TMPDIR/calls.log" ]]; then
		cat "$TEST_TMPDIR/calls.log"
	fi
}

_t_reset_calls() {
	: >"$TEST_TMPDIR/calls.log"
}

_t_teardown() {
	if [[ -n ${TEST_TMPDIR:-} && -d ${TEST_TMPDIR} ]]; then
		rm -rf "$TEST_TMPDIR"
	fi
}

_t_report() {
	printf '\n%s: %d passed, %d failed\n' "${1:-tests}" "$PASS" "$FAIL"
	[[ $FAIL -eq 0 ]]
}
