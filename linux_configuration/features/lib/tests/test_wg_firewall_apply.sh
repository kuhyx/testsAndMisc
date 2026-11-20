#!/usr/bin/env bash
# Tests for verify_nftables_then_apply -- a firewall reload and the WARP window.
#
# A reload replaces 'inet filter' and with it the warp_open set that
# warp_window.sh filled. Each todoImplementer deploy ran 'allow-web', the set
# came back empty, and the work laptop's warp-home tick read "closed" and
# dropped WARP mid-workday. The window must survive a reload with the time it
# had left, and a reload that changes nothing must not happen at all.
#
# nft and systemctl are fakes that model just enough state: one file stands
# for the open window element, and anything that loads the ruleset empties it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

NFT_CONF="$TEST_TMPDIR/nftables.conf"
WINDOW="$TEST_TMPDIR/warp_open.elem"
log_ok() { log "$1"; }
log_warn() { log "$1"; }
die() {
	log "$1"
	exit 1
}
is_service_active() { return 0; }
sleep() { :; }
# The real one (lib/common_services.sh) is 'enable --now', i.e. a second load.
enable_service() { systemctl enable --now "$1"; }

# shellcheck source=../wg_firewall.sh
. "$FEATURES_LIB_DIR/wg_firewall.sh"
# After the source line, or the real one replaces the stub.
restore_docker_rules() { :; }

cat >"$TEST_TMPDIR/bin/nft" <<EOF
#!/usr/bin/env bash
printf 'nft %s\n' "\$*" >>"$TEST_TMPDIR/calls.log"
case "\$*" in
"-c -f "*) exit 0 ;;
"-f "*) rm -f "$WINDOW" ;;
"list table inet filter") exit 0 ;;
"list set inet filter warp_open")
	printf 'set warp_open {\n'
	[[ -f "$WINDOW" ]] && printf '\telements = { %s }\n' "\$(<"$WINDOW")"
	printf '}\n' ;;
"add element inet filter warp_open "*)
	el="\${*#add element inet filter warp_open }"
	el="\${el#\{ }"
	printf '%s expires 5h31m31s119ms\n' "\${el% \}}" >"$WINDOW" ;;
esac
EOF
cat >"$TEST_TMPDIR/bin/systemctl" <<EOF
#!/usr/bin/env bash
printf 'systemctl %s\n' "\$*" >>"$TEST_TMPDIR/calls.log"
[[ "\$*" == *--now* || "\$*" == start* || "\$*" == restart* ]] && rm -f "$WINDOW"
exit 0
EOF
chmod +x "$TEST_TMPDIR/bin/nft" "$TEST_TMPDIR/bin/systemctl"

window() { cat "$WINDOW" 2>/dev/null || printf 'closed'; }

printf '\n-- a reload keeps an open WARP window --\n'
printf 'old ruleset\n' >"$NFT_CONF"
printf 'new ruleset\n' >"${NFT_CONF}.new"
printf '0.0.0.0/0 timeout 5h32m21s expires 5h31m31s119ms\n' >"$WINDOW"
: >"$TEST_TMPDIR/calls.log"
(verify_nftables_then_apply) >/dev/null 2>&1
_t_called 'nft -f' "a changed ruleset is loaded"
_t_has "$(window)" '0.0.0.0/0 timeout 5h31m31s119ms' \
	"the window is back with the time it had left, not more"

printf '\n-- a reload never opens a closed window --\n'
rm -f "$WINDOW"
printf 'newer ruleset\n' >"${NFT_CONF}.new"
(verify_nftables_then_apply) >/dev/null 2>&1
_t_eq 'closed' "$(window)" "a closed window stays closed"

printf '\n-- an unchanged ruleset is not reloaded --\n'
cp "$NFT_CONF" "${NFT_CONF}.new"
printf '0.0.0.0/0 timeout 1h expires 59m\n' >"$WINDOW"
: >"$TEST_TMPDIR/calls.log"
out="$(verify_nftables_then_apply 2>&1)"
if grep -qE '^nft -f|--now|^systemctl (re)?start' "$TEST_TMPDIR/calls.log"; then
	_t_fail "no load and no service start when nothing changed"
else
	_t_pass "no load and no service start when nothing changed"
fi
_t_has "$(window)" 'expires 59m' "the window is untouched"
_t_has "$out" 'unchanged' "the skip is reported"
_t_not "the scratch ruleset is cleaned up" test -e "${NFT_CONF}.new"

_t_report "test_wg_firewall_apply.sh"
