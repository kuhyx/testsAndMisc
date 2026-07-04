---
name: self-hosted-service-exposure
description: Use BEFORE deploying any Docker-based self-hosted service on this machine that needs to be reachable from the public internet (a git server, a note server, any "expose X to the internet" or "access X from my phone off WiFi" request). Captures the working DuckDNS + Caddy + firewall pattern and a critical nftables/Docker networking gotcha discovered while standing up self-hosted Gitea.
---

# Self-hosted service exposure (public internet)

## What's already true on this host — don't rebuild these

- **DuckDNS** (`kuhy.duckdns.org`) is kept updated by an existing cron job installed
  by `install_joplin.sh`'s `setup_duckdns()` (`~/.joplin-server/duckdns-update.sh`,
  `*/5 * * * *`). Check `crontab -l | grep duckdns` before adding a new updater —
  `setup_wireguard_ssh.sh`'s own `setup_duckdns()` also has a
  `duckdns_already_updated()` guard for this reason. **Do not add a second one.**
- **The firewall is owned entirely by**
  `linux_configuration/scripts/single_use/features/setup_wireguard_ssh.sh`. It
  regenerates `/etc/nftables.conf` from scratch on every `setup` run (`flush
  ruleset` + fixed heredoc). **Never hand-edit `/etc/nftables.conf` directly or
  from a second script** — the next `setup` re-run (e.g. adding a WireGuard peer)
  will silently wipe an independent edit. To open a new port, extend this script
  (see its `allow-web` subcommand, which persists an `ALLOW_WEB` flag and adds
  `tcp dport { 80, 443 } accept`) rather than writing a new firewall rule
  elsewhere. If a service needs a port other than 80/443, add another named flag
  following the same pattern, don't fork the ruleset logic.
- Run `sudo setup_wireguard_ssh.sh allow-web` once per host to open 80/443; it's
  idempotent and safe to call from a new service's own setup script.

## The pattern: Caddy + app container, not a hand-rolled reverse proxy

For any new publicly-exposed service:

1. **Caddy** (`caddy:2.8` image) is the only container bound to host `80`/`443`.
   A ~5-line Caddyfile (`domain { reverse_proxy target:port }`) gets you automatic
   Let's Encrypt HTTPS with no manual cert handling.
2. The app container itself is **never** bound to a public port — only reachable
   internally by Caddy.
3. Headless bootstrap: prefer the app's own env-var/CLI config over a web
   installer wizard, so the whole thing is scriptable with zero manual steps
   (see `setup_gitea.sh`'s `GITEA__security__INSTALL_LOCK=true` +
   `gitea admin user create` for a working example).

## The critical gotcha: Docker bridge networking silently loses outbound access

**Symptom**: Caddy's ACME certificate request times out
(`context deadline exceeded`), or an app container can't reach any external API,
even though `curl` from the host itself works fine and DNS resolves correctly
inside the container.

**Root cause**: this host's custom nftables ruleset defines its own
`chain forward { policy drop; }` with **zero accept rules**. Docker manages a
*separate* set of forwarding rules via legacy `iptables` (`ip_tables` kernel
module, not `nf_tables`) that correctly `ACCEPT` bridge-network traffic — but
`ip_tables` and `nf_tables` both register at the same `NF_INET_FORWARD` netfilter
hook, and **a DROP verdict from either one is terminal**, regardless of what the
other subsystem decided. So nftables' default-drop forward chain silently kills
all Docker bridge-network container egress, even though `docker ps`/`iptables -L
DOCKER-FORWARD` show everything looks correctly configured on Docker's side.

Confirm this is what's happening:
```bash
docker exec <container> wget -qO- --timeout=5 https://api.ipify.org   # hangs/times out
sudo nft list ruleset | grep -A3 "chain forward"                       # policy drop, no rules
sudo iptables -L DOCKER-FORWARD -n -v                                   # shows ACCEPT rules matching, but doesn't matter
```

**Fix used for Gitea (recommended, minimal blast radius)**: run the
public-facing containers with `network_mode: host` instead of a Docker bridge
network. This sidesteps the FORWARD chain entirely (host-networked containers
only hit INPUT/OUTPUT, both already permissive on this host) without touching
the shared firewall script. Bind the app itself to `127.0.0.1:<port>` explicitly
(e.g. `GITEA__server__HTTP_ADDR=127.0.0.1`) so it isn't accidentally exposed —
with host networking there's no bridge isolation to rely on.

**Alternative (broader fix, requires explicit user sign-off)**: add
`ct state established,related accept` + `ip saddr 172.16.0.0/12 accept` to
`setup_wireguard_ssh.sh`'s forward chain. Fixes egress for *all* Docker
containers on the host (useful if `joplin-server`/`open-webui` ever need
outbound access too), but it's a change to shared, security-relevant
infrastructure beyond any single service's scope — ask before applying it,
don't default to it silently.

## Bash gotcha hit while scripting the readiness check

`docker logs <container> | grep -q "ready-string"` can spuriously fail forever
under `set -o pipefail`: `grep -q` quits at the first match, SIGPIPE-ing
`docker logs` before it finishes writing, and `pipefail` propagates that
upstream non-zero exit even though `grep` itself succeeded. Fix: capture into a
variable first, then grep the variable —
```bash
logs=$(docker logs "$container" 2>&1)
if grep -q "ready-string" <<<"$logs"; then ...
```

## Credentials for anything the server needs to reach out to (e.g. pulling private repos)

Default to the **least-privilege credential**, not whatever's already
authenticated in the shell (e.g. `gh auth token`). A publicly-exposed host
storing a broad-scope token is a bigger blast radius if compromised. If the
service needs to read from a third-party private resource, prefer a
purpose-scoped token (e.g. a GitHub fine-grained PAT, `Contents: Read-only`,
scoped to only the specific repos needed) even though it requires a one-time
manual step (can't be scripted — token creation UIs generally can't be
automated). **Ask the user which tradeoff they want** rather than silently
picking the convenient broad-scope option — this is a real security decision,
not an implementation detail.

## Verification checklist before declaring a public deployment done

1. `docker compose ps` — containers healthy.
2. `docker logs <caddy-container> | grep -i "certificate obtained"` — a real
   cert was issued. If it never appears, check egress (gotcha above) before
   suspecting the router.
3. Let's Encrypt's own external validation succeeding (visible in the same log,
   e.g. `served key authentication certificate ... remote: <external IP>`) is
   strong indirect proof that inbound 80/443 is already reachable from the
   internet — a genuinely external validator reached this host. Don't stop
   there, but it means the router forward is very likely already fine.
4. `curl` from the host itself only proves the app works — it hairpins through
   loopback and does **not** prove external reachability.
5. **The real acceptance test is on the user**: open the URL from a phone with
   WiFi off, on cellular data.

## Boot persistence — confirm these are all `enabled`, not just running

A service surviving a reboot needs all of:
```bash
systemctl is-enabled docker      # containers won't come back without this
systemctl is-enabled nftables    # firewall rules reload from /etc/nftables.conf
systemctl is-enabled cronie      # or crond -- DuckDNS updater needs this
docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}'  # unless-stopped or always
```
If all of the above hold, no boot-time script or systemd unit is needed for the
service itself — the Docker daemon restarts `unless-stopped` containers on its
own startup, independent of `docker compose` ever being re-invoked.

## Reference implementation

`linux_configuration/scripts/single_use/features/setup_gitea.sh` and
`migrate_github_to_gitea.sh` are working, idempotent examples of this whole
pattern end to end (firewall, Caddy, headless bootstrap, host networking
workaround, least-privilege external credential). Copy the shape, not
necessarily the Gitea specifics, for the next self-hosted service.
