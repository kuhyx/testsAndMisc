# Phone DNS filtering: parked 2026-08-05

Unrooted DNS-level blocking is **on hold**, not abandoned. The code is in place
and inert; what is missing is a resolver that is always reachable.

## Why it stopped

Android's Private DNS in `hostname` mode **fails closed**. Measured on the
Pixel 6a (23181JEGR08034, Android 16), twice, by pinning
`private_dns_specifier` to a host with no reachable DoT listener:

```
settings put global private_dns_mode hostname
ping example.com   ->  ping: unknown host example.com
```

There is no fallback to the carrier's resolver. The phone simply has no DNS.
This matches the spec rather than being a quirk: hostname mode is RFC 8310's
strict profile, and Google's own Public DNS documentation states that failure to
establish TLS on 853 is "a hard error and will result in no DNS service".

That disqualifies any design where the resolver lives on a machine that can be
switched off. The home stack (dnsmasq + stunnel on this PC) works correctly and
was verified end to end, but "PC off" means "phone has no internet", which is
not acceptable for a daily driver.

## What was left running, and why

`stunnel-dot.service` is still active on `10.8.0.1:853` (WireGuard only, with
`iifname "wg0" tcp dport 853 accept` in nftables). It is unreachable from the
LAN and the WAN — verified — so it costs nothing to leave in place, and it
makes the next attempt testable immediately.

To remove it entirely:

```bash
sudo systemctl disable --now stunnel-dot.service dot-cert-sync.timer
sudo rm -f /etc/stunnel/dot-resolver.conf /etc/systemd/system/stunnel-dot.service
rm -f ~/gitea/sites/dns.caddy && docker exec gitea-caddy caddy reload \
  --config /etc/caddy/Caddyfile --adapter caddyfile
```

## What still needs deciding

An always-on resolver. Research (2026-08-05) narrowed this considerably, and
**ruled out the hybrid hosted approach that looked most attractive**:

- **No hosted provider can ingest a 185k-domain list.** NextDNS supports no
  custom lists at all; AdGuard caps custom rules at 1K personal / 5K team;
  ControlD caps at 10K. All are two orders of magnitude short. "Provider lists
  for the bulk plus my custom entries" is therefore not available as designed —
  the bulk is the part that does not fit.
- **Free tiers fail OPEN.** NextDNS and AdGuard both stop _filtering_ past
  300k queries/month while continuing to resolve. For a self-control tool that
  is the worst possible failure: it looks like it is working and silently is
  not. A single phone exceeds 300k without difficulty.
- **Oracle Always Free reclaims idle instances** (<20% CPU over 7 days). A DNS
  resolver is idle by nature, so the free tier actively conflicts with the
  always-on requirement.
- **NextDNS has no profile lock** — the account password is the only barrier,
  so it adds nothing on the tamper-resistance axis.

Remaining options, ranked:

1. **Cheap VPS running AdGuard Home** (Hetzner CAX11 ~€6/mo). Keeps full control
   of the 185,681-domain list, always on, and everything built this session
   ports unchanged. The only option that satisfies both always-on and list
   control.
2. **Existing always-on hardware** (Pi, old phone, router), if any exists — same
   properties as the VPS, no monthly cost, but needs a device that genuinely
   stays powered.
3. **NextDNS Pro ($19.90/yr)** — accept their category blocking (porn / gambling
   / social / video, plus per-service YouTube) _instead of_ the StevenBlack list
   rather than alongside it. Covers the intent, not the exact list. Cheapest
   always-on path if list control is negotiable.

## What is already built and stays useful

- `python_pkg/focus_policy` — policy + hosts→domain conversion. Delivery
  agnostic; feeds any of the three options above. `to_dnsmasq_conf()` targets a
  self-hosted resolver, `to_domain_list()` a VpnService or an upload.
- `phone_focus_mode/dns_enforcer.sh` — `DNS_TRUSTED_DOT_HOST` is **empty**, so
  behaviour is byte-identical to before. Set it to any trusted DoT hostname
  (hosted or self-hosted) and the enforcer allows that one endpoint through the
  853 block and pins Private DNS to it.
- `setup_dot_resolver.sh` / `setup_phone_wireguard.sh` — both verified working.
  The WireGuard tunnel is up and handshaking; `--check` passes on both.
- `focus_owner` — unaffected. Device Owner app-blocking is a separate layer and
  is the stronger one for tamper resistance anyway. Note that
  `DISALLOW_CONFIG_PRIVATE_DNS` (API 29+, device-owner only, applies globally)
  is confirmed to exist and is what would stop the phone's user editing Private
  DNS in Settings — so whichever resolver is eventually chosen, the lock comes
  from Device Owner, not from the provider. Pair it with `DISALLOW_CONFIG_VPN`.

## Gotcha for whoever picks this up

A DoT endpoint bound to a private address needs its **hostname to resolve to
that private address**. `dns.kuhy.duckdns.org` resolves to the public IP, and
with `AllowedIPs = 10.8.0.0/24` (split tunnel) that routes outside the tunnel to
a closed port — Android never even opened a connection. Split-horizon DNS does
not fix it either, because on mobile data the phone uses the carrier's resolver.
A hosted provider avoids this entirely; a VPS avoids it by having a real public
address that is meant to be reached.
