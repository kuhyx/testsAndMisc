#!/usr/bin/env bats
# Tests for meta/scripts/check_ci_green.sh with a stubbed `gh` and a scratch git
# repo, so no network and no real CI state is involved.
#
#   bats linux_configuration/tests/test_check_ci_green.bats

bats_require_minimum_version 1.5.0

setup() {
	SCRIPT="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/../.." && pwd)/meta/scripts/check_ci_green.sh"
	unset CI_GREEN_SKIP GITHUB_ACTIONS PRE_COMMIT_FROM_REF PRE_COMMIT_TO_REF
	mkdir -p "$BATS_TEST_TMPDIR/bin" "$BATS_TEST_TMPDIR/repo"
	cat >"$BATS_TEST_TMPDIR/bin/gh" <<'STUB'
#!/bin/bash
[[ $1 == auth ]] && exit 0
echo "${FAKE_CONCLUSION:-failure}"
STUB
	chmod +x "$BATS_TEST_TMPDIR/bin/gh"
	export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
	cd "$BATS_TEST_TMPDIR/repo" || return 1
	git init -q .
	git config user.email t@example.com
	git config user.name t
	git commit -q --allow-empty -m base
}

stage() {
	local f
	for f in "$@"; do
		mkdir -p "$(dirname "$f")"
		echo x >"$f"
		git add "$f"
	done
}

@test "green baseline passes regardless of files" {
	stage src/app.py
	FAKE_CONCLUSION=success run "$SCRIPT"
	[ "$status" -eq 0 ]
}

@test "red baseline blocks a code change" {
	stage src/app.py
	run "$SCRIPT"
	[ "$status" -eq 1 ]
	[[ $output == *"main is RED"* ]]
}

@test "red baseline blocks nothing staged (fail closed)" {
	run "$SCRIPT"
	[ "$status" -eq 1 ]
}

@test "red baseline allows a pin-only change and says so" {
	stage meta/.fvmrc app/pubspec.yaml app/pubspec.lock web/package.json web/pnpm-lock.yaml requirements-test.txt pyproject.toml
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[[ $output == *"EXEMPTION FIRED"* ]]
	[[ $output == *"meta/.fvmrc"* ]]
}

@test "red baseline blocks a pin mixed with code" {
	stage meta/.fvmrc src/app.py
	run "$SCRIPT"
	[ "$status" -eq 1 ]
	[[ $output != *"EXEMPTION FIRED"* ]]
}

@test "lookalike names are not pins" {
	stage notes/requirements.md my.fvmrc.bak
	run "$SCRIPT"
	[ "$status" -eq 1 ]
}

@test "push range of pins is exempt, range with code is not" {
	local base
	base="$(git rev-parse HEAD)"
	stage meta/.fvmrc
	git commit -q -m pin
	PRE_COMMIT_FROM_REF="$base" PRE_COMMIT_TO_REF="$(git rev-parse HEAD)" run "$SCRIPT"
	[ "$status" -eq 0 ]
	stage src/app.py
	git commit -q -m code
	PRE_COMMIT_FROM_REF="$base" PRE_COMMIT_TO_REF="$(git rev-parse HEAD)" run "$SCRIPT"
	[ "$status" -eq 1 ]
}

@test "unusable push range fails closed" {
	PRE_COMMIT_FROM_REF=0000000 PRE_COMMIT_TO_REF=deadbeef run "$SCRIPT"
	[ "$status" -eq 1 ]
}
