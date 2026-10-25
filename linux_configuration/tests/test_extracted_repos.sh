#!/bin/bash
# Regression tests for lib/extracted_repos.sh.
#
# The 2026-09-11 home tidy moved every extracted repo from ~/<name> to
# ~/src/<name>, but extracted_repo_dir kept building ~/<name>. Every caller
# broke silently; dns-blocklist-refresh.service failed nightly for six weeks
# with "Feed generator not found: /home/kuhy/hosts-blocker/...".

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)

fail() {
	printf 'FAIL: %s\n' "$1" >&2
	exit 1
}

TMP_DIR=$(mktemp -d)
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# Resolve <name> against a fake home, in a clean shell, with no override set.
resolve() {
	EXTRACTED_REPOS_HOME="$TMP_DIR" bash -c '
		unset HOSTS_BLOCKER_DIR SCREEN_LOCKER_DIR
		source "$1/lib/extracted_repos.sh"
		extracted_repo_dir "$2"
	' _ "$REPO_DIR" "$1"
}

# 1. Repo checked out under ~/src (the current layout) -> ~/src/<name>.
mkdir -p "$TMP_DIR/src/hosts-blocker"
got=$(resolve hosts-blocker)
[[ $got == "$TMP_DIR/src/hosts-blocker" ]] || fail "src layout: got '$got'"

# 2. Only the legacy ~/<name> checkout exists -> keep finding it.
mkdir -p "$TMP_DIR/screen-locker"
got=$(resolve screen-locker)
[[ $got == "$TMP_DIR/screen-locker" ]] || fail "legacy layout: got '$got'"

# 3. Neither exists -> ~/src/<name>, which is also where a clone lands.
got=$(resolve wake-alarm)
[[ $got == "$TMP_DIR/src/wake-alarm" ]] || fail "missing repo: got '$got'"

# 4. The per-repo override still wins over both layouts.
got=$(EXTRACTED_REPOS_HOME="$TMP_DIR" HOSTS_BLOCKER_DIR=/opt/hb bash -c '
	source "$1/lib/extracted_repos.sh"; extracted_repo_dir hosts-blocker
' _ "$REPO_DIR")
[[ $got == "/opt/hb" ]] || fail "override: got '$got'"

printf 'PASS: test_extracted_repos.sh\n'
