#!/usr/bin/env bats
# Tests for scripts/deploy.sh against a scratch origin + "live" clone, so the
# real ~/src/testsAndMisc is never touched.
#
#   bats linux_configuration/tests/test_deploy.bats

bats_require_minimum_version 1.5.0

setup() {
	ROOT="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/../.." && pwd)"
	SCRIPT="$ROOT/scripts/deploy.sh"
	T="$BATS_TEST_TMPDIR"
	export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.com
	export GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.com
	git init -q --bare -b main "$T/origin.git"
	git clone -q "$T/origin.git" "$T/dev" 2>/dev/null
	mkdir -p "$T/dev/linux_configuration/.githooks"
	echo a >"$T/dev/file.txt"
	touch "$T/dev/linux_configuration/.githooks/pre-commit"
	git -C "$T/dev" add -A
	git -C "$T/dev" commit -q -m base
	git -C "$T/dev" push -q origin HEAD:main
	git clone -q "$T/origin.git" "$T/live"
	git -C "$T/live" config core.hooksPath linux_configuration/.githooks
	export TESTSANDMISC_DIR="$T/live"
}

push_change() {
	echo "$1" >"$T/dev/${2:-file.txt}"
	git -C "$T/dev" commit -qam "$1"
	git -C "$T/dev" push -q origin HEAD:main
}

@test "CLAUDE.md declares scripts/deploy.sh as the deploy command" {
	local tick="\`" n=0 line
	while IFS= read -r line; do
		[[ "$line" == "- deploy: ${tick}scripts/deploy.sh${tick}"* ]] && n=$((n + 1))
	done <"$ROOT/CLAUDE.md"
	[ "$n" -eq 1 ]
	[ -x "$SCRIPT" ]
}

@test "fast-forwards the live checkout to origin/main" {
	push_change b
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[ "$(git -C "$T/live" rev-parse HEAD)" = "$(git -C "$T/origin.git" rev-parse main)" ]
}

@test "is idempotent: a second run is a no-op that still passes" {
	push_change b
	"$SCRIPT"
	run "$SCRIPT"
	[ "$status" -eq 0 ]
}

@test "keeps unrelated uncommitted work and still deploys" {
	echo wip >"$T/live/other.txt"
	git -C "$T/live" add other.txt
	push_change b
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[ "$(cat "$T/live/other.txt")" = wip ]
}

@test "refuses when uncommitted work collides with the update" {
	echo mine >"$T/live/file.txt"
	push_change theirs
	run "$SCRIPT"
	[ "$status" -ne 0 ]
	[ "$(cat "$T/live/file.txt")" = mine ]
}

@test "fails the health check when hooks are not wired" {
	git -C "$T/live" config --unset core.hooksPath
	run "$SCRIPT"
	[ "$status" -ne 0 ]
	[[ "$output" == *hooksPath* ]]
}

@test "fails when the live checkout is not on main" {
	git -C "$T/live" switch -q -c feature
	run "$SCRIPT"
	[ "$status" -ne 0 ]
}
