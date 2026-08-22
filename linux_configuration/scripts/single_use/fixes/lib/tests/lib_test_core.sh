#!/usr/bin/env bash
# lib/tests/lib_test_core.sh — assertion + sandbox primitives shared by the
# per-family harnesses in this directory.
#
# Sourced, not executed. Provides exactly the pieces every family needs and
# nothing family-specific: a PASS/FAIL tally, the _t_* assertions, a
# throwaway $TEST_TMPDIR wiped on EXIT, and a $FAKE_BIN stub directory
# prepended to PATH.
#
# Deliberately does NOT touch pacman_hook_stall_harness.sh, which predates it
# and whose six libs are already off the coverage allowlist -- i.e. gated at
# 100% with no exemption. Refactoring that harness to sit on top of this one
# would put banked work at risk for no coverage gain.
set -uo pipefail

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
	local want="$1" got="$2" what="$3"
	if [[ "$got" == "$want" ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want '${want}', got '${got}')"
	fi
}

# _t_contains HAYSTACK NEEDLE WHAT — substring assertion.
_t_contains() {
	local haystack="$1" needle="$2" what="$3"
	if [[ "$haystack" == *"$needle"* ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (expected to contain '${needle}', got: ${haystack})"
	fi
}

# _t_lacks HAYSTACK NEEDLE WHAT — negative substring assertion.
_t_lacks() {
	local haystack="$1" needle="$2" what="$3"
	if [[ "$haystack" != *"$needle"* ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (expected NOT to contain '${needle}', got: ${haystack})"
	fi
}

TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TEST_TMPDIR}"' EXIT

readonly DEV="${TEST_TMPDIR}/device"
readonly FAKE_BIN="${TEST_TMPDIR}/fake_bin"
mkdir -p "${DEV}" "${FAKE_BIN}"
: >"${DEV}/calls"

export PATH="${FAKE_BIN}:${PATH}"

# _t_stub NAME BODY — write an executable stub NAME into $FAKE_BIN whose body
# is BODY, then drop bash's cached path for NAME.
#
# Every stub records its own invocation into $DEV/calls before running BODY,
# so _t_calls works uniformly without each stub repeating the boilerplate.
_t_stub() {
	local name="$1" body="$2"
	# The recording preamble is written with a quoted heredoc so $0 and $@
	# reach the stub file unexpanded and expand when the STUB runs. Using
	# $0/$@ rather than the stub's literal name is what keeps this a plain
	# heredoc with nothing for the writer to interpolate.
	cat >"${FAKE_BIN}/${name}" <<'STUB_PREAMBLE'
#!/usr/bin/env bash
printf '%s %s\n' "${0##*/}" "$*" >>"${LIB_TEST_DEV}/calls"
STUB_PREAMBLE
	printf '%s\n' "$body" >>"${FAKE_BIN}/${name}"
	chmod +x "${FAKE_BIN}/${name}"
	hash -r
}

# _t_stub_writes NAME ARGNUM CONTENT — stub NAME so it writes CONTENT to the
# path in its ARGNUM-th argument, then succeeds.
#
# Exists because downloaders take their destination positionally
# (`wget -q "$url" -O "$dest"` puts it in $4), and writing that stub body as a
# quoted string means embedding a literal $4 the writer must not expand. The
# argument number is passed as data instead, so no caller needs to quote a $.
_t_stub_writes() {
	local name="$1" argnum="$2" content="$3"
	# The dollar that selects the positional argument is assembled from a
	# character rather than written literally, so nothing in this file is a
	# quoted expression that only looks like it should expand.
	local dollar
	dollar="$(printf '\044')"
	local body
	body="printf %s '${content}' >\"${dollar}{${argnum}}\""
	body+="
exit 0"
	_t_stub "$name" "$body"
}

# _t_unstub NAME... — remove stubs and drop bash's cached executable paths.
#
# `rm` alone does NOT hide a stub: bash caches the resolved location of every
# command it has run, so a later call re-executes the deleted file's path and
# fails with "No such file or directory" instead of falling through to the
# real binary. `hash -r` is the part that matters.
_t_unstub() {
	local name
	for name in "$@"; do
		rm -f "${FAKE_BIN}/${name}"
	done
	hash -r
}

# _t_calls — print everything the stubs recorded this round.
_t_calls() {
	cat "${DEV}/calls" 2>/dev/null || true
}

# _t_reset_calls — start a fresh recording window.
_t_reset_calls() {
	: >"${DEV}/calls"
}

export LIB_TEST_DEV="${DEV}"
