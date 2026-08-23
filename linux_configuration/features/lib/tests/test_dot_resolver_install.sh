#!/usr/bin/env bash
# Tests for dot_resolver_install.sh — the DoT resolver's install half.
#
# Every function here sudo-writes a systemd unit, an stunnel config or an
# nftables rule against LIVE infrastructure (dns.kuhy.duckdns.org:853). They
# are executed for real, not mocked, because the generated CONTENT is the
# thing worth asserting -- a unit file with the wrong ExecStart is exactly the
# bug a presence check would miss.
#
# This is only safe under meta/scripts/shell_coverage_jail.sh, which runs the
# suite inside a user+mount namespace with /etc, /usr/local/bin and /var/lib
# bind-mounted to a throwaway dir. Run directly on a real host it would
# rewrite the resolver, so it refuses to start unless the jail is in place.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

# --- Refuse to run outside the jail -----------------------------------------
# The jail bind-mounts /etc, so the real resolver's config is absent inside it.
# Seeing the host's own stunnel config means we are NOT contained.
if [[ -f /etc/stunnel/dot-resolver.conf ]] && [[ ! -w /etc ]]; then
	printf 'REFUSING: this suite must run under shell_coverage_jail.sh\n' >&2
	exit 1
fi

_t_setup_env
trap _t_teardown EXIT

# The values the entry script defines above its source line.
SCRIPT_NAME="setup_dot_resolver.sh"
CERT_DIR="/etc/stunnel/dot"
STUNNEL_CONF="/etc/stunnel/dot-resolver.conf"
SYNC_SCRIPT="/usr/local/bin/sync-dot-cert.sh"
DOT_PORT=853
DOMAIN="dns.kuhy.duckdns.org"
BIND_ADDR="10.8.0.1"
CADDY_CONTAINER="caddy"

# install_cert_sync interpolates this at GENERATION time (the heredoc is
# unquoted), baking the resolved path into the script it writes. That is
# deliberate, not a bug -- the live /usr/local/bin/sync-dot-cert.sh carries a
# fully populated src=. The fixture must therefore define it exactly as the
# entry script does, or the generated script gets src="" and the assertion
# below silently passes over an empty path.
cert_source_dir() {
	printf '/data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/%s' \
		"$DOMAIN"
}

# shellcheck source=../dot_resolver_install.sh
. "$FEATURES_LIB_DIR/dot_resolver_install.sh"

# Fixture self-check: a typo in one of these names would turn every assertion
# below into a silent no-op rather than a failure.
[[ -n $CERT_DIR && -n $STUNNEL_CONF && -n $SYNC_SCRIPT ]] ||
	{
		printf 'fixture globals are not populated\n' >&2
		exit 1
	}

mkdir -p /etc/stunnel /etc/systemd/system /usr/local/bin

# --- install_cert_sync ------------------------------------------------------
install_cert_sync
_t_file_has "$SYNC_SCRIPT" 'combined.pem' "cert sync script assembles combined.pem"
_t_file_has "$SYNC_SCRIPT" "src=\"/data/caddy/certificates" "cert source path is baked in, not left empty"
_t_file_has "$SYNC_SCRIPT" 'reload-or-restart' "cert sync restarts stunnel after renewal"
if [[ -d $CERT_DIR ]]; then
	_t_pass "cert dir created"
else
	_t_fail "cert dir created"
fi
_t_eq "700" "$(stat -c '%a' "$CERT_DIR")" "cert dir is mode 700 (it holds a private key)"
_t_eq "755" "$(stat -c '%a' "$SYNC_SCRIPT")" "sync script is executable"

# --- install_stunnel_conf ---------------------------------------------------
install_stunnel_conf
_t_file_has "$STUNNEL_CONF" "accept = $BIND_ADDR:$DOT_PORT" "stunnel accepts on the bind address"
_t_file_has "$STUNNEL_CONF" 'connect = 127.0.0.1:53' "stunnel forwards to local dnsmasq"
_t_file_has "$STUNNEL_CONF" 'sslVersionMin = TLSv1.2' "stunnel refuses pre-TLS1.2 (Android requires it)"
_t_file_has "$STUNNEL_CONF" "cert = $CERT_DIR/combined.pem" "stunnel reads the synced cert"

# --- install_units ----------------------------------------------------------
_t_stub systemctl
install_units
_t_file_has /etc/systemd/system/stunnel-dot.service 'stunnel' "stunnel unit installed"
_t_file_has /etc/systemd/system/dot-cert-sync.service "$SYNC_SCRIPT" "cert-sync service runs the sync script"
_t_file_has /etc/systemd/system/dot-cert-sync.timer 'OnCalendar' "cert-sync timer is scheduled"
_t_called 'daemon-reload' "units are followed by a daemon-reload"

# --- open_firewall: the WireGuard-only branch -------------------------------
# nft absent entirely: the function must still return cleanly rather than
# aborting the install on a host without nftables.
out="$(open_firewall 2>&1)"
_t_has "$out" 'WireGuard-only' "wg-bound install needs no router forward"

# nft present and the rule already there: must not add a duplicate.
_t_stub nft
printf '#!/usr/bin/env bash\nprintf "nft %%s\\n" "$*" >>"%s/calls.log"\nif [[ $* == *list* ]]; then printf "iifname \\"wg0\\" tcp dport %s accept\\n" ; fi\nexit 0\n' \
	"$TEST_TMPDIR" "$DOT_PORT" >"$TEST_TMPDIR/bin/nft"
chmod +x "$TEST_TMPDIR/bin/nft"
out="$(open_firewall 2>&1)"
_t_has "$out" 'already permits' "an existing wg0 rule is not duplicated"

# nft present and the rule missing: must add it, scoped to wg0.
printf '#!/usr/bin/env bash\nprintf "nft %%s\\n" "$*" >>"%s/calls.log"\nexit 0\n' \
	"$TEST_TMPDIR" >"$TEST_TMPDIR/bin/nft"
chmod +x "$TEST_TMPDIR/bin/nft"
out="$(open_firewall 2>&1)"
_t_has "$out" 'wg0 only' "a missing wg0 rule is added"
_t_called 'add rule inet filter input iifname wg0' "the added rule is scoped to the tunnel"

# nft present but the ADD fails (a locked-down or read-only ruleset): the
# install must warn and carry on, never abort. `nft list` still has to succeed
# or the outer guard short-circuits before the add is attempted.
cat >"$TEST_TMPDIR/bin/nft" <<'NFT'
#!/usr/bin/env bash
printf 'nft %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
[[ $* == *add* ]] && exit 1
exit 0
NFT
chmod +x "$TEST_TMPDIR/bin/nft"
out="$(open_firewall 2>&1)"
_t_has "$out" 'WARNING: could not add nftables rule' "a failed wg0 rule add warns instead of aborting"

# --- open_firewall: the publicly-bound branch -------------------------------
# A public bind is an open resolver, so the rule MUST carry a rate limit.
BIND_ADDR="0.0.0.0"
out="$(open_firewall 2>&1)"
_t_has "$out" 'rate limited' "a public bind is rate limited"
_t_called 'limit rate 25/second burst 50' "the public rule carries the documented limit"
_t_has "$out" 'router forwards' "a public bind asks for a router forward"

# The same add-failure path on the public branch.
out="$(open_firewall 2>&1)"
_t_has "$out" 'WARNING: could not add rate-limited nftables rule' \
	"a failed public rule add warns instead of aborting"
BIND_ADDR="10.8.0.1"

# --- run_check --------------------------------------------------------------
# Everything healthy: stunnel active, port listening, cert present.
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_TMPDIR/bin/systemctl"
chmod +x "$TEST_TMPDIR/bin/systemctl"
printf '#!/usr/bin/env bash\nprintf "LISTEN 0 0 10.8.0.1:%s\\n"\n' "$DOT_PORT" >"$TEST_TMPDIR/bin/ss"
chmod +x "$TEST_TMPDIR/bin/ss"
install -m 600 /dev/null "$CERT_DIR/combined.pem"
printf 'cert\n' >"$CERT_DIR/combined.pem"
if run_check >/dev/null 2>&1; then
	_t_pass "run_check passes on a healthy install"
else
	_t_fail "run_check passes on a healthy install"
fi

# stunnel down: must fail and say which check failed.
printf '#!/usr/bin/env bash\n[[ $* == *is-active* ]] && exit 1\nexit 0\n' >"$TEST_TMPDIR/bin/systemctl"
chmod +x "$TEST_TMPDIR/bin/systemctl"
out="$(run_check 2>&1 || true)"
_t_has "$out" 'FAIL stunnel-dot.service not active' "a stopped stunnel is reported"

# Certificate missing: the check that must be run as root to be correct.
rm -f "$CERT_DIR/combined.pem"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_TMPDIR/bin/systemctl"
chmod +x "$TEST_TMPDIR/bin/systemctl"
out="$(run_check 2>&1 || true)"
_t_has "$out" 'FAIL certificate missing' "a missing certificate is reported"

# Nothing listening on the port.
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_TMPDIR/bin/ss"
chmod +x "$TEST_TMPDIR/bin/ss"
out="$(run_check 2>&1 || true)"
_t_has "$out" 'FAIL nothing listening' "a silent port is reported"

# kdig present and the DoT query failing. The check is skipped entirely when
# kdig is absent, so this arm only exists on a host that has knot-utils --
# which makes it exactly the arm most likely to rot unnoticed.
printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/kdig"
chmod +x "$TEST_TMPDIR/bin/kdig"
printf 'cert\n' >"$CERT_DIR/combined.pem"
printf '#!/usr/bin/env bash\nprintf "LISTEN 0 0 10.8.0.1:%s\\n"\n' "$DOT_PORT" >"$TEST_TMPDIR/bin/ss"
chmod +x "$TEST_TMPDIR/bin/ss"
out="$(run_check 2>&1 || true)"
_t_has "$out" 'FAIL DoT query did not answer' "an unanswered DoT query is reported"

_t_report "test_dot_resolver_install.sh"
