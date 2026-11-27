#!/usr/bin/env bats
# Tests for features/keepass_sync.sh in webdav mode against a stubbed curl and
# keepassxc-cli, so no real vault or dufs server is touched.
#
# Requires: bats (extra/bats). Run with:
#   bats linux_configuration/tests/test_keepass_sync.bats

bats_require_minimum_version 1.5.0

setup() {
	REPO_DIR="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/.." && pwd)"
	SCRIPT="$REPO_DIR/features/keepass_sync.sh"
	mkdir -p "$BATS_TEST_TMPDIR/bin" "$BATS_TEST_TMPDIR/vault"
	export CALLS="$BATS_TEST_TMPDIR/calls"
	: >"$CALLS"
	# Fake curl: records its argv, answers the ?hash probe with $FAKE_HTTP_CODE
	# via -w (000 = connection failed, exit 7 like the real one), accepts uploads.
	cat >"$BATS_TEST_TMPDIR/bin/curl" <<'STUB'
#!/bin/bash
echo "curl $*" >>"$CALLS"
out="" prev="" probe=0
for a in "$@"; do
	[[ "$a" == "-T" ]] && exit 0
	[[ "$a" == "-w" ]] && probe=1
	[[ "$prev" == "-o" ]] && out="$a"
	prev="$a"
done
[[ -n "$out" && "$out" != /dev/null ]] && : >"$out"
((probe)) && printf '%s' "$FAKE_HTTP_CODE"
[[ "$FAKE_HTTP_CODE" == 000 ]] && exit 7
# Without -w the caller used -f: an HTTP error is exit 22 and no body.
((probe == 0 && FAKE_HTTP_CODE >= 400)) && exit 22
exit 0
STUB
	printf '#!/bin/bash\nexit 0\n' >"$BATS_TEST_TMPDIR/bin/keepassxc-cli"
	chmod +x "$BATS_TEST_TMPDIR/bin/curl" "$BATS_TEST_TMPDIR/bin/keepassxc-cli"
	export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
	LOCAL_DB="$BATS_TEST_TMPDIR/vault/Passwords.kdbx"
	printf 'local-vault' >"$LOCAL_DB"
	export KP_SYNC_CONFIG="$BATS_TEST_TMPDIR/config.env"
	cat >"$KP_SYNC_CONFIG" <<EOF
LOCAL_DB=$LOCAL_DB
REMOTE_MODE=webdav
REMOTE_URL=https://dufs.invalid/Keepass/Passwords.kdbx
DUFS_USER=u
EOF
	export KP_STATE_DIR="$BATS_TEST_TMPDIR/state" KP_MASTER_PW=x KP_DUFS_PW=y
}

# $1 = HTTP code the ?hash probe returns; asserts nothing was uploaded.
assert_skip_without_upload() {
	export FAKE_HTTP_CODE="$1"
	run bash "$SCRIPT"
	[ "$status" -eq 0 ]
	[[ "$output" == *"remote unreachable"* ]]
	[ "$(cat "$LOCAL_DB")" = local-vault ]
	run ! grep -q -- ' -T ' "$CALLS"
}

@test "an unreachable remote is a skip that leaves the vault alone" {
	assert_skip_without_upload 000
}

@test "a 5xx on the hash probe never publishes over the remote" {
	assert_skip_without_upload 503
}

@test "a missing remote (404) gets the local vault as its first copy" {
	export FAKE_HTTP_CODE=404
	run bash "$SCRIPT"
	[ "$status" -eq 0 ]
	[[ "$output" == *"first copy"* ]]
	grep -q -- ' -T ' "$CALLS"
}
