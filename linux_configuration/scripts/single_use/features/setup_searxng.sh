#!/bin/bash
#
# setup_searxng.sh — SearXNG metasearch at searx.kuhy.duckdns.org
#
# Runs a private SearXNG instance behind the existing shared Caddy edge
# (gitea-caddy), configured to earn an A+ Mozilla Observatory grade while
# staying "Vanilla" (settings-only changes — no template or static-file edits).
#
# No DuckDNS work is needed: DuckDNS wildcards *.kuhy.duckdns.org, so adding the
# Caddy snippet is enough to get a certificate.
#
# What it does (idempotent — safe to re-run):
#   - Installs runtime deps.
#   - Writes ~/searxng/{docker-compose.yml,core-config/settings.yml}.
#   - Runs valkey (limiter backend) on 127.0.0.1:6379.
#   - Runs searxng on 127.0.0.1:8090, both with network_mode: host.
#   - Adds a reverse-proxy + security-header snippet to the shared edge.
#   - Opens the firewall via setup_wireguard_ssh.sh (already open in practice).
#
# Why network_mode: host — this host's nftables ruleset has
# `chain forward { policy drop; }` with no accept rules, and a DROP at
# NF_INET_FORWARD is terminal regardless of Docker's own legacy-iptables
# ACCEPTs. Docker BRIDGE networking therefore has zero outbound access here, so
# a stock bridge-network SearXNG cannot reach a single search engine. Host
# networking sidesteps the FORWARD chain entirely. The cost is that there is no
# bridge isolation left, so both containers are pinned to loopback explicitly
# and that binding is asserted before the site is published.
#
# Reboot survival: containers use restart: unless-stopped and docker.service is
# enabled — no systemd unit is needed.
#
# Usage:
#   setup_searxng.sh [setup]   Deploy (default).
#   setup_searxng.sh status    Self-diagnose the deployment.
#   setup_searxng.sh help      Show this help.
#
# Prerequisite: setup_gitea.sh must have been run at least once (the gitea-caddy
# edge must exist). Run as your normal user, not root.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
# shellcheck source=../../lib/common.sh
source "${SCRIPT_DIR}/../../lib/common.sh"

# --- Configuration ----------------------------------------------------------
readonly SEARX_DOMAIN="searx.kuhy.duckdns.org"
# 8080 is granian's default AND is already taken on this host, so it is set
# explicitly rather than left alone.
readonly SEARX_PORT="8090"
readonly VALKEY_PORT="6379"
# searxng/searxng:latest as of 2026-08-09 == release 2026.8.4. See the comment
# on the image: line in the compose heredoc for why this is pinned.
readonly SEARX_IMAGE="searxng/searxng@sha256:f4c8e59de166ed71f6380c0847c312ca51f0d41996e31d0559163b6b09ecde52"
readonly SEARX_DATA_DIR="${HOME}/searxng"
readonly SEARX_COMPOSE="${SEARX_DATA_DIR}/docker-compose.yml"
readonly SEARX_CONFIG_DIR="${SEARX_DATA_DIR}/core-config"
readonly SEARX_SETTINGS="${SEARX_CONFIG_DIR}/settings.yml"
readonly SEARX_LIMITER="${SEARX_CONFIG_DIR}/limiter.toml"
# Shared edge owned by setup_gitea.sh.
readonly GITEA_DATA_DIR="${HOME}/gitea"
readonly SITES_DIR="${GITEA_DATA_DIR}/sites"
readonly SEARX_SNIPPET="${SITES_DIR}/searx.caddy"
readonly CADDY_CONTAINER="gitea-caddy"
readonly SEARX_CONTAINER="searxng"
readonly VALKEY_CONTAINER="searxng-valkey"
# Sibling script (single source of truth for the firewall).
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"

die() {
	log_error "$1"
	exit 1
}

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit "${1:-0}"
}

# --- Phase 1: preflight -----------------------------------------------------
port_in_use() {
	local port="$1"
	ss -ltn 2>/dev/null | grep -qE "[:.]${port}[[:space:]]"
}

# A port held by one of OUR OWN containers is a re-run, not a conflict. Only a
# foreign holder is fatal, otherwise the second `setup` run can never succeed.
port_held_by_us() {
	local port="$1" name pid listeners
	for name in "$SEARX_CONTAINER" "$VALKEY_CONTAINER"; do
		pid="$(docker inspect -f '{{.State.Pid}}' "$name" 2>/dev/null || echo "")"
		[[ -n $pid && $pid != "0" ]] || continue
		listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"
		if grep -qE "[:.]${port}[[:space:]]" <<<"$listeners"; then
			return 0
		fi
	done
	return 1
}

preflight() {
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root."
	install_missing_pacman_packages docker docker-compose openssl curl
	is_service_active docker || die "docker.service is not running."
	docker ps --format '{{.Names}}' | grep -qx "$CADDY_CONTAINER" ||
		die "The ${CADDY_CONTAINER} edge is not running — run setup_gitea.sh first."

	local port
	for port in "$SEARX_PORT" "$VALKEY_PORT"; do
		if port_in_use "$port" && ! port_held_by_us "$port"; then
			die "Port ${port} is already in use by something else. Free it or change the port."
		fi
	done
	log_ok "Preflight passed (edge up, ports ${SEARX_PORT}/${VALKEY_PORT} available)."
}

# --- Phase 2: write the stack -----------------------------------------------
# Regenerating secret_key on every run would invalidate every image-proxy HMAC
# and every stored preference cookie, so an existing one is reused. openssl,
# not an inline python heredoc (house shell rule).
read_or_make_secret() {
	local existing=""
	if [[ -f $SEARX_SETTINGS ]]; then
		existing="$(grep -oP '^\s*secret_key:\s*"\K[^"]+' "$SEARX_SETTINGS" 2>/dev/null || true)"
	fi
	if [[ -n $existing ]]; then
		printf '%s' "$existing"
	else
		openssl rand -hex 32
	fi
}

# The container entrypoint chowns core-config/ and settings.yml to its own
# searxng user (uid 977), after which this script's own user can no longer
# overwrite them — so a second `setup` run dies with "Permission denied" unless
# ownership is reclaimed first. Idempotence is the whole point of this script,
# so reclaim rather than skip.
reclaim_config_ownership() {
	local target
	for target in "$SEARX_CONFIG_DIR" "$SEARX_SETTINGS" "$SEARX_LIMITER"; do
		[[ -e $target ]] || continue
		[[ -O $target ]] && continue
		if ! sudo -n chown "$(id -u):$(id -g)" "$target" 2>/dev/null; then
			die "${target} is owned by the container (uid 977) and passwordless sudo is unavailable. Run: sudo chown -R $(id -u):$(id -g) ${SEARX_CONFIG_DIR}"
		fi
		log_info "Reclaimed ownership of ${target} from the container."
	done
}

write_stack() {
	ensure_dir "$SEARX_CONFIG_DIR"
	reclaim_config_ownership

	cat >"$SEARX_COMPOSE" <<EOF
# Managed by setup_searxng.sh — do not edit by hand.
services:
  valkey:
    container_name: ${VALKEY_CONTAINER}
    image: valkey/valkey:8-alpine
    # --bind is load-bearing: with host networking there is no bridge to hide
    # behind, and upstream's own compose omits it.
    command: valkey-server --bind 127.0.0.1 --port ${VALKEY_PORT} --save 30 1 --appendonly no
    network_mode: host
    restart: unless-stopped
    volumes:
      - valkey-data:/data
    cap_drop: [ALL]
    cap_add: [SETGID, SETUID, DAC_OVERRIDE]

  searxng:
    container_name: ${SEARX_CONTAINER}
    # PINNED BY DIGEST, deliberately not :latest. Every non-obvious thing this
    # file works around was established empirically against THIS image
    # (2026.8.4): granian binds :: rather than the documented 127.0.0.1, the key
    # is valkey.url not redis.url, server.bind_address is inert, the entrypoint
    # chowns the config to uid 977, cap_drop breaks the config read, and
    # public_instance force-enables link_token. A silent :latest bump can
    # invalidate any of those and the guards would fail closed with a mystery.
    # To upgrade: change the digest, re-run setup, re-check status.
    image: ${SEARX_IMAGE}
    network_mode: host
    restart: unless-stopped
    depends_on: [valkey]
    volumes:
      - ${SEARX_CONFIG_DIR}:/etc/searxng:rw
    environment:
      # server.bind_address in settings.yml is INERT in this image (it is only
      # read under __main__, i.e. the Flask dev server). granian is the actual
      # server and it binds :: by default -- verified empirically, despite its
      # own docs claiming 127.0.0.1. These two vars are the only thing keeping
      # this off the LAN.
      - GRANIAN_HOST=127.0.0.1
      - GRANIAN_PORT=${SEARX_PORT}
      - SEARXNG_BASE_URL=https://${SEARX_DOMAIN}/
    # No cap_drop here. The entrypoint starts as root to chown -R /etc/searxng
    # and read the settings before dropping to uid 977, so dropping ALL caps
    # (even re-adding CHOWN/SETGID/SETUID) loses DAC_OVERRIDE/FOWNER and the
    # worker dies with "[Errno 13] Permission denied: /etc/searxng/settings.yml".
    # Verified empirically: identical run without cap_drop has zero perm errors.
    logging:
      driver: json-file
      options: { max-size: "1m", max-file: "1" }

volumes:
  valkey-data:
EOF
	log_ok "Wrote ${SEARX_COMPOSE}."

	local secret
	secret="$(read_or_make_secret)"

	cat >"$SEARX_SETTINGS" <<EOF
# Managed by setup_searxng.sh — do not edit by hand.
#
# "Vanilla" constraint: everything here is a SETTINGS change. No ui.static_path,
# no templates_path, no injected CSS/JS -- the shipped static files must keep
# matching upstream.
use_default_settings: true

general:
  instance_name: "${SEARX_DOMAIN}"
  # Keeps a public instance from advertising an admin contact to scrapers.
  contact_url: false
  enable_metrics: true

server:
  port: ${SEARX_PORT}
  bind_address: "127.0.0.1"  # inert under granian; kept for correctness/clarity
  secret_key: "${secret}"
  limiter: true
  # public_instance is deliberately NOT set. It force-enables link_token, a
  # browser-proof challenge that requires the client to fetch a probe resource —
  # which makes /search?format=json unusable for any scripted client (it 429s or
  # 302s forever, and no limiter.toml setting can override it because the flag
  # forces it on). It exists to satisfy searx.space directory norms, and this
  # instance is deliberately unlisted, so it costs the JSON API for nothing.
  # Rate limiting and the image proxy are kept via their own keys below.
  # Required by the strict CSP: proxying images keeps them same-origin so
  # img-src can stay 'self' without breaking result thumbnails.
  image_proxy: true
  method: "POST"

search:
  safe_search: 0
  autocomplete: "duckduckgo"
  default_lang: "en"
  # json is enabled for programmatic/MCP use. Note this interacts with the
  # limiter's bot detection -- see the off-host verification step.
  formats:
    - html
    - json

outgoing:
  # Caps the tail so one dead engine cannot hold up a whole search.
  request_timeout: 3.0
  max_request_timeout: 6.0
  pool_connections: 100
  pool_maxsize: 20
  enable_http2: true

valkey:
  # Key is valkey.url; redis.url still parses but emits a DeprecationWarning.
  url: valkey://127.0.0.1:${VALKEY_PORT}/0

ui:
  static_use_hash: true
  infinite_scroll: false
  query_in_title: true

# Engine pruning — MEASURED on this host (5+ varied queries, /stats + the
# unresponsive_engines field), not guessed. Each entry says why.
#
# Cross-checked against this host's own /etc/hosts blocklist first: pinterest
# resolves to 0.0.0.0 here (blackholed by generate_hosts_file.sh), so it fails
# for a LOCAL reason and would have been misdiagnosed as a slow/dead upstream.
# It is disabled to stop the pointless request, not because the engine is bad.
#
# Re-check periodically with:
#   curl -s 'http://127.0.0.1:${SEARX_PORT}/search?q=test&format=json' \\
#     | grep -o '"unresponsive_engines":.*'
# Engine pruning, kuhy-selected 2026-08-09 from the /preferences engine table:
# every engine that was erroring (CAPTCHA / access denied / timeout / parsing
# error / crash) plus the slow tail, across all categories.
#
# Retained on purpose: google cse, wikipedia/wikidata and the specialist
# lookups (arch linux wiki, github, stackexchange, pypi, ...).
#
# IMPORTANT about general search: the merged general view is served by
# google cse ALONE, and was before this pruning too. The plain google and bing
# engines are marked "inactive: true" upstream, meaning they only run when
# explicitly invoked with a bang (!go -> 20 results, !bi -> 10, both
# verified working). So the pruning removed only engines that were already
# contributing zero results -- but it also means general search has a single
# point of failure. If google cse ever starts erroring, general search returns
# nothing until another engine is enabled or !go/!bi is used.
#
# pinterest is blackholed to 0.0.0.0 by this host's own /etc/hosts
# (generate_hosts_file.sh) -- a LOCAL failure that looks identical to a dead
# upstream. Disabled to stop the pointless request, not because the engine is bad.
#
# USE "inactive: true", NOT "disabled: true". Straight from enginelib:
#   disabled -> "disable BY DEFAULT ... will allow the user to manually
#               activate it in the settings"  (i.e. only the default for a
#               fresh visitor; anyone with an existing preferences cookie keeps
#               running the engine)
#   inactive -> "Remove the engine from the settings (disabled & removed)"
# The first pass used "disabled" and the pruned engines kept executing for any
# browser session that already had a preferences cookie -- yandex images was
# still throwing JSONDecodeErrors in the log minutes after being "disabled".
#
# EXCEPTION -- brave and qwant use "disabled", not "inactive", ON PURPOSE.
# They own an outgoing connection pool that sibling engines reference by name
# ("network: brave" <- brave.images/.videos/.news; "network: qwant" <- qwant
# news/images/videos). "inactive" REMOVES the definition, so the siblings'
# lookup dies at startup with KeyError: 'qwant' and the container never comes
# up. "disabled" keeps the pool defined while hiding the engine from results.
# Pool owners in this image: brave, qwant, yandex, piped, yacy -- of which only
# brave and qwant are pruned here. Check before making any of the rest inactive:
#   grep -B4 'network: <name>' /usr/local/searxng/searx/settings.yml
#
# Re-check periodically:
#   curl -s 'http://127.0.0.1:8090/search?q=test&format=json' | grep -o '"unresponsive_engines":.*'
engines:
  # === general ===
  - { name: brave, disabled: true }             # too many requests
  - { name: duckduckgo, inactive: true }        # CAPTCHA
  - { name: startpage, inactive: true }         # Suspended: CAPTCHA
  - { name: dogpile, inactive: true }           # access denied
  - { name: encyclosearch, inactive: true }     # timeout
  - { name: fastbot, inactive: true }           # access denied
  - { name: fireball, inactive: true }          # access denied
  - { name: quark, inactive: true }             # unexpected crash
  - { name: qwant, disabled: true }             # CAPTCHA
  - { name: sogou, inactive: true }             # CAPTCHA
  - { name: tusksearch, inactive: true }        # HTTP error
  - { name: yahoo, inactive: true }             # HTTP protocol error
  - { name: yep, inactive: true }               # access denied
  - { name: naver, inactive: true }             # 1.9s
  - { name: baidu, inactive: true }             # 1.7s
  - { name: abcnyheter, inactive: true }        # 1.5s
  - { name: boardreader, inactive: true }       # 1.5s
  - { name: crowdview, inactive: true }         # 1.0s

  # === images === (keeping ONLY google cse images)
  - { name: dogpile images, inactive: true }    # access denied
  - { name: findfiles images, inactive: true }  # unexpected crash
  - { name: library of congress, inactive: true } # parsing error
  - { name: pinterest, inactive: true }         # 0.0.0.0 in /etc/hosts (local)
  - { name: qwant images, inactive: true }      # CAPTCHA
  - { name: tusksearch images, inactive: true } # HTTP error
  - { name: wikicommons.images, inactive: true } # too many requests
  - { name: yandex images, inactive: true }     # parsing error
  - { name: quark images, inactive: true }      # 2.9s
  - { name: 1x, inactive: true }                # 2.5s
  - { name: baidu images, inactive: true }      # 2.5s
  - { name: picjumbo, inactive: true }          # 2.4s
  - { name: naver images, inactive: true }      # 2.3s
  - { name: sogou images, inactive: true }      # 2.0s
  - { name: unsplash, inactive: true }          # 1.2s
  - { name: duckduckgo images, inactive: true }
  - { name: flickr, inactive: true }            # 1.0s
  - { name: bing images, inactive: true }       # cut for the sub-1s images goal
  - { name: deviantart, inactive: true }        # cut for the sub-1s images goal
  - { name: openverse, inactive: true }         # cut for the sub-1s images goal
  - { name: pexels, inactive: true }            # cut for the sub-1s images goal
  - { name: artic, inactive: true }             # cut for the sub-1s images goal
  - { name: devicons, inactive: true }          # cut for the sub-1s images goal
  - { name: lucide, inactive: true }            # cut for the sub-1s images goal
  - { name: wallhaven, inactive: true }         # cut for the sub-1s images goal
  # Not in the /preferences list kuhy sent -- these only surfaced as
  # unresponsive under load, same failure pattern, so pruned with the rest.
  - { name: brave.images, inactive: true }      # too many requests
  - { name: startpage images, inactive: true }  # Suspended: CAPTCHA

  # === videos ===
  - { name: 360search videos, inactive: true }  # unexpected crash
  - { name: acfun, inactive: true }             # timeout
  - { name: brave.videos, inactive: true }      # too many requests
  - { name: dogpile videos, inactive: true }    # access denied
  - { name: fireball videos, inactive: true }   # access denied
  - { name: niconico, inactive: true }          # HTTP connection error
  - { name: pixabay videos, inactive: true }    # timeout
  - { name: tusksearch videos, inactive: true } # HTTP error
  - { name: vimeo, inactive: true }             # access denied
  - { name: youtube, inactive: true }           # HTTP connection error
  - { name: naver videos, inactive: true }      # 2.4s
  - { name: sogou videos, inactive: true }      # 2.0s
  - { name: iqiyi, inactive: true }             # 1.3s
  - { name: rumble, inactive: true }            # 1.3s

  # === news ===
  - { name: bing news, inactive: true }         # parsing error
  - { name: brave.news, inactive: true }        # too many requests
  - { name: dogpile news, inactive: true }      # access denied
  - { name: fireball news, inactive: true }     # access denied
  - { name: google news, inactive: true }       # Suspended: CAPTCHA
  - { name: startpage news, inactive: true }    # Suspended: CAPTCHA
  - { name: tusksearch news, inactive: true }   # HTTP error
  - { name: sogou wechat, inactive: true }      # 1.7s
  - { name: naver news, inactive: true }        # 1.7s

  # === music ===
  - { name: radio browser, inactive: true }     # HTTP error
  - { name: yandex music, inactive: true }      # HTTP error

  # === it ===
  - { name: codeberg, inactive: true }          # timeout
  - { name: metacpan, inactive: true }          # HTTP error
  - { name: nixos wiki, inactive: true }        # timeout
  - { name: baidu kaifa, inactive: true }       # 2.0s
  - { name: gitea.com, inactive: true }         # 1.8s
  - { name: rubygems, inactive: true }          # 1.1s

  # === science ===
  - { name: openairepublications, inactive: true } # 2.7s
  - { name: openairedatasets, inactive: true }  # 2.7s

  # === files ===
  - { name: 1337x, inactive: true }             # HTTP connection error
  - { name: btdigg, inactive: true }            # 1.5s
  - { name: findfiles, inactive: true }         # 1.2s
  - { name: kickass, inactive: true }           # HTTP connection error (surfaced under load)

  # === social media ===
  - { name: 9gag, inactive: true }              # access denied
  - { name: tootfinder, inactive: true }        # access denied
EOF
	# 640, NOT 600. The entrypoint chowns this file to the container's searxng
	# user (uid 977), but granian's worker runs as a different uid and only has
	# GROUP access — mode 600 makes it unreadable and the worker dies with
	# "[Errno 13] Permission denied: /etc/searxng/settings.yml". It still is not
	# world-readable, so secret_key stays protected.
	chmod 640 "$SEARX_SETTINGS"
	log_ok "Wrote ${SEARX_SETTINGS}."

	# Without this file SearXNG logs "missing config file:
	# /etc/searxng/limiter.toml" and runs with no trusted_proxies, so the
	# forwarded client IP is never trusted and botdetection 429s *everything*.
	cat >"$SEARX_LIMITER" <<'EOF'
# Managed by setup_searxng.sh — do not edit by hand.
[botdetection]

ipv4_prefix = 32
ipv6_prefix = 48

# The edge (gitea-caddy) shares the host network namespace, so its requests
# arrive from loopback. Without 127.0.0.0/8 here the X-Forwarded-For that Caddy
# sends is ignored, every request looks like it came from the proxy itself, and
# rate limiting collapses onto a single bucket.
trusted_proxies = [
  '127.0.0.0/8',
  '::1',
]

[botdetection.ip_limit]
filter_link_local = false
# Off (the shipped default). link_token sends a probe the client must fetch to
# prove it renders HTML, which no scripted JSON client can satisfy. IP-based
# rate limiting below is unaffected and still applies.
link_token = false

[botdetection.ip_lists]
block_ip = []

# pass_ip bypasses ALL botdetection (including the Sec-Fetch/User-Agent probe
# headers) for these addresses.
#
# This is what makes search.formats = [html, json] usable. A scripted JSON
# client — an MCP server, a script — cannot send Sec-Fetch-Mode/Site/Dest, and
# botdetection 429s anything that lacks them, so WITHOUT this entry the JSON API
# is unreachable for every non-browser client. Verified: with browser headers a
# search returns 200 + results; the identical request without Sec-Fetch-* gets
# 429.
#
# Deliberately LOOPBACK ONLY. Requests arriving through the public edge carry
# the real client IP in X-Forwarded-For (trusted_proxies above), so they are
# still fully rate-limited — this exempts only tools running on this host.
pass_ip = [
  '127.0.0.0/8',
  '::1',
]
EOF
	chmod 640 "$SEARX_LIMITER"
	log_ok "Wrote ${SEARX_LIMITER}."
}

# --- Phase 3/4: start -------------------------------------------------------
# Sends the Host header the edge will actually forward, and requires a
# non-empty body. A bare "curl http://127.0.0.1:PORT/" against a host-matcher
# misconfiguration returns an empty 200 — it passes while every real request
# serves a blank page.
wait_for_site() {
	local _ size
	for _ in $(seq 1 60); do
		# Browser-shaped headers: without them botdetection answers 429 and this
		# readiness probe would spin for its full 60s against a healthy backend.
		size="$(curl -s --compressed -o /dev/null -w '%{size_download}' \
			-A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
			-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
			-H 'Accept-Language: en-US,en;q=0.9' \
			-H 'Accept-Encoding: gzip, deflate, br' \
			-H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-Dest: document' \
			-H "Host: ${SEARX_DOMAIN}" "http://127.0.0.1:${SEARX_PORT}/" 2>/dev/null || echo 0)"
		if [[ ${size:-0} -gt 0 ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

wait_for_valkey() {
	local _ out
	for _ in $(seq 1 30); do
		out="$(docker exec "$VALKEY_CONTAINER" valkey-cli -h 127.0.0.1 -p "$VALKEY_PORT" ping 2>/dev/null || true)"
		if [[ $out == "PONG" ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

# These containers share the host network namespace with the public edge, so a
# misconfiguration does not fail locally — it quietly exposes an unfronted
# service to the whole LAN, or steals a share of :80/:443 from every other site
# on the box. Gate on it rather than trust the config to stay correct.
assert_loopback_only() {
	local container="$1" port="$2" pid listeners
	pid="$(docker inspect -f '{{.State.Pid}}' "$container" 2>/dev/null || echo "")"
	[[ -n $pid && $pid != "0" ]] || die "Could not read the ${container} PID."

	listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"

	# Demand positive evidence FIRST. Asserting only the absence of a bad bind
	# fails open: if `ss` returns nothing — a stale PID, or sudo -n unavailable —
	# every "is it bad?" test misses and the guard reports success having looked
	# at nothing.
	if ! grep -qE '(^|[[:space:]])127\.0\.0\.1:'"${port}"'([[:space:]]|$)' <<<"$listeners"; then
		docker stop "$container" >/dev/null 2>&1 || true
		die "Could not confirm ${container} listens on 127.0.0.1:${port}. Container stopped."
	fi
	if grep -qE ':(80|443)\b' <<<"$listeners"; then
		docker stop "$container" >/dev/null 2>&1 || true
		die "${container} bound :80/:443 — it would contend with ${CADDY_CONTAINER}. Container stopped."
	fi
	# Reject *, 0.0.0.0 AND [::] — granian's real default is ::, which a
	# 0.0.0.0-only check would sail straight past.
	if grep -qE '(\*|0\.0\.0\.0|\[::\]):'"${port}"'\b' <<<"$listeners"; then
		docker stop "$container" >/dev/null 2>&1 || true
		die "${container} bound ${port} on all interfaces, not loopback. Container stopped."
	fi
	log_ok "${container} listens on loopback:${port} only — no contention, not LAN-exposed."
}

start_stack() {
	log_info "Starting valkey + searxng…"
	docker compose -f "$SEARX_COMPOSE" up -d
	# `up -d` is a no-op when only a BIND-MOUNTED config file changed — compose
	# compares the compose spec, not the files it mounts. settings.yml and
	# limiter.toml are read once at startup, so without an explicit restart the
	# container keeps serving the previous config and every verification below
	# silently tests the OLD deployment. (Hit for real: limiter.toml was written
	# at 15:06 while the container had been running since 15:02, so botdetection
	# kept 429ing with "missing config file".)
	log_info "Restarting searxng to pick up settings.yml / limiter.toml…"
	docker restart "$SEARX_CONTAINER" >/dev/null

	if wait_for_valkey; then
		log_ok "valkey answering PING on 127.0.0.1:${VALKEY_PORT}."
	else
		die "valkey did not become ready — the limiter would silently no-op."
	fi

	if wait_for_site; then
		log_ok "SearXNG answering on http://127.0.0.1:${SEARX_PORT}/."
	else
		docker stop "$SEARX_CONTAINER" >/dev/null 2>&1 || true
		die "SearXNG did not become reachable on 127.0.0.1:${SEARX_PORT} (container stopped)."
	fi

	assert_loopback_only "$VALKEY_CONTAINER" "$VALKEY_PORT"
	assert_loopback_only "$SEARX_CONTAINER" "$SEARX_PORT"
}

# --- Phase 5: front it on the public domain ---------------------------------
# Header syntax matters and is easy to get wrong:
#   Header "value"   -> "set"     (REPLACES any existing value)  <-- what we want
#   +Header "value"  -> "add"     (appends, yielding duplicates)
#   >Header "value"  -> "replace" (substring search/replace WITHIN a value —
#                                  NOT a header setter. Using it here silently
#                                  produced no header at all: it adapts to
#                                  {"replace": {"": [{"search_regexp": "..."}]}}
#                                  and matches nothing. Verified via caddy adapt.)
# This matters because SearXNG sends X-Content-Type-Options and Referrer-Policy
# itself via default_http_headers (its Referrer-Policy is `no-referrer`, which
# differs from ours), so the bare/"set" form is required to override rather than
# duplicate them.
write_snippet() {
	cat >"$SEARX_SNIPPET" <<EOF
# Managed by setup_searxng.sh — do not edit by hand.
${SEARX_DOMAIN} {
	header {
		# Bare name = "set" = replace. Do NOT prefix with '+' (appends, causing
		# duplicate headers) or '>' (substring-replace, which sets nothing).
		Content-Security-Policy "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; manifest-src 'self'"
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		X-Content-Type-Options "nosniff"
		Referrer-Policy "strict-origin-when-cross-origin"
		Permissions-Policy "geolocation=(), microphone=(), camera=(), interest-cohort=()"
		# No HSTS preload: duckdns.org is a public suffix, so kuhy.duckdns.org is
		# the registrable domain — preloading would force HTTPS on every sibling
		# subdomain and is effectively irreversible. Not needed to clear A+.
		-Server
	}
	reverse_proxy 127.0.0.1:${SEARX_PORT} {
		# SearXNG's botdetection needs the real client IP. Without this it logs
		# "X-Forwarded-For nor X-Real-IP header is set!" and 429s every request,
		# including the front page. Paired with trusted_proxies in limiter.toml —
		# both halves are required, neither works alone.
		header_up X-Forwarded-For {http.request.remote.host}
		header_up X-Real-IP {http.request.remote.host}
	}
}
EOF
	log_ok "Wrote ${SEARX_SNIPPET}."
}

# --- Phase 6: reload the edge -----------------------------------------------
reload_caddy() {
	if docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
		docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
		log_ok "Reloaded ${CADDY_CONTAINER}."
	else
		rm -f "$SEARX_SNIPPET"
		die "Caddy config invalid — snippet removed, edge left untouched."
	fi
}

# --- Phase 7: firewall ------------------------------------------------------
# setup_wireguard_ssh.sh owns /etc/nftables.conf and regenerates it from scratch
# — `flush ruleset` and all — on every run, momentarily dropping the whole
# ruleset. Since all this needs is 80/443 already being accepted, check first
# and only pay for the regeneration when the rule is genuinely missing.
web_ports_open() {
	local line ports
	while read -r line; do
		# Exact token membership: a loose regex would also match "8080, 4433".
		ports=",${line//[^0-9,]/},"
		if [[ $ports == *,80,* && $ports == *,443,* ]]; then
			return 0
		fi
	done < <(sudo -n nft list ruleset 2>/dev/null | grep -oE 'tcp dport \{[^}]*\}')
	return 1
}

ensure_firewall() {
	if web_ports_open; then
		log_ok "Ports 80/443 already accepted — leaving the ruleset untouched."
		return 0
	fi
	log_info "Opening ports 80/443 via setup_wireguard_ssh.sh…"
	sudo bash "$WG_SCRIPT" allow-web
}

# --- Phase 8: report --------------------------------------------------------
print_report() {
	cat <<EOF

============================================================================
SearXNG deployed.
============================================================================
  Search : https://${SEARX_DOMAIN}/
  JSON   : https://${SEARX_DOMAIN}/search?q=test&format=json

Next, in order:
  1. Header check (each must print exactly 1):
       for h in content-security-policy strict-transport-security \\
                x-content-type-options referrer-policy permissions-policy; do
         printf '%s: ' "\$h"
         curl -sI https://${SEARX_DOMAIN}/ | grep -ci "^\$h:"
       done
  2. Mozilla Observatory scan of ${SEARX_DOMAIN} — that scan IS the A+ grade.
  3. JSON API FROM ANOTHER MACHINE (phone on cellular, not this host):
       curl 'https://${SEARX_DOMAIN}/search?q=test&format=json'
     A from-host curl cannot surface bot-detection rejection. If this returns
     403/429, fix the limiter allowlist — do NOT disable the limiter.

Acceptance test (do this on your phone):
  Turn Wi-Fi OFF (use cellular) and run a real search at https://${SEARX_DOMAIN}/
============================================================================
EOF
}

setup_cmd() {
	print_setup_header "SearXNG setup"
	preflight
	write_stack
	# The snippet goes into the SHARED sites/ directory, so it is written only
	# after the backend is up and verified. Writing it first means a failure in
	# start_stack leaves an orphan behind that the next `caddy reload` from any
	# other service picks up — the edge then serves this domain as a 502 and
	# starts ACME retries for a host with no backend.
	start_stack
	write_snippet
	reload_caddy
	ensure_firewall
	print_report
	log_ok "SearXNG setup complete."
}

# --- status: self-diagnose --------------------------------------------------
status_line() {
	if [[ $1 -eq 0 ]]; then
		log_ok "$2"
	else
		log_warn "$2"
	fi
}

check_http() {
	# Prints 0 to stdout if the URL returns 200 with a non-empty body, else 1.
	# The body-size check matters: a host-matcher misconfiguration answers 200
	# with nothing in it, which a status-only check would call healthy.
	# Certificates are NOT skipped — `curl -k` would report a failed-ACME cert as
	# healthy, which is exactly the green-while-broken this exists to catch.
	# Browser-shaped headers are REQUIRED, not cosmetic. botdetection runs a
	# separate check per header and 429s on the FIRST one that fails, so the full
	# set below must be sent every time. All four matter:
	#   Accept-Language   -> http_accept_language   (omitting this alone 429s)
	#   Accept-Encoding   -> http_accept_encoding   (needs gzip or deflate)
	#   Accept            -> http_accept
	#   Sec-Fetch-*       -> http_sec_fetch         (302-redirects when invalid)
	# Diagnosing which one bit is easy but non-obvious: set `debug: true` under
	# general: in settings.yml, restart, and the log prints
	# "NOT OK (searx.botdetection.<method>)" naming the exact check.
	# (Observed: dropping only Accept-Language turned a healthy 200 into a 429.)
	local url="$1" out code size
	out="$(curl -s --compressed -o /dev/null -w '%{http_code} %{size_download}' --max-time 10 \
		-A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
		-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
		-H 'Accept-Language: en-US,en;q=0.9' \
		-H 'Accept-Encoding: gzip, deflate, br' \
		-H 'Sec-Fetch-Mode: navigate' \
		-H 'Sec-Fetch-Site: none' \
		-H 'Sec-Fetch-Dest: document' \
		${2:+-H "Host: $2"} "$url" 2>/dev/null || echo "000 0")"
	read -r code size <<<"$out"
	[[ $code == "200" && ${size:-0} -gt 0 ]] && echo 0 || echo 1
}

check_container() {
	local name="$1" port="$2" pid listeners
	if ! docker ps --format '{{.Names}}' | grep -qx "$name"; then
		status_line 1 "${name} container not running"
		return
	fi
	status_line 0 "${name} container running"
	pid="$(docker inspect -f '{{.State.Pid}}' "$name" 2>/dev/null || echo "")"
	listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"
	if [[ -z $listeners ]]; then
		status_line 1 "${name}: could not read listeners (needs sudo -n) — binding UNVERIFIED"
	elif grep -qE '(\*|0\.0\.0\.0|\[::\]):'"${port}"'\b' <<<"$listeners"; then
		status_line 1 "${name} is bound to ALL INTERFACES on ${port} — LAN-exposed"
	elif grep -qE '(^|[[:space:]])127\.0\.0\.1:'"${port}"'([[:space:]]|$)' <<<"$listeners"; then
		status_line 0 "${name} listens on loopback:${port} only"
	else
		status_line 1 "${name} not listening on ${port} as expected"
	fi
}

# Duplicated headers are the classic silent A+ killer, so count them rather than
# merely checking presence.
check_headers() {
	local headers out h count
	# Same browser-header requirement as check_http — a 429 carries none of these
	# headers, so a bare curl would report all five as MISSING on a healthy site.
	out="$(curl -sI --compressed --max-time 10 \
		-A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
		-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
		-H 'Accept-Language: en-US,en;q=0.9' \
		-H 'Accept-Encoding: gzip, deflate, br' \
		-H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-Dest: document' \
		"https://${SEARX_DOMAIN}/" 2>/dev/null || true)"
	if [[ -z $out ]]; then
		status_line 1 "could not fetch headers from https://${SEARX_DOMAIN}/"
		return
	fi
	headers=(content-security-policy strict-transport-security
		x-content-type-options referrer-policy permissions-policy)
	for h in "${headers[@]}"; do
		count="$(grep -ci "^${h}:" <<<"$out" || true)"
		if [[ $count -eq 1 ]]; then
			status_line 0 "header ${h}: exactly 1"
		elif [[ $count -eq 0 ]]; then
			status_line 1 "header ${h}: MISSING"
		else
			status_line 1 "header ${h}: DUPLICATED (${count}) — costs the A+ grade"
		fi
	done
}

status_cmd() {
	print_setup_header "SearXNG status"

	if has_cmd docker; then
		status_line 0 "docker present"
	else
		status_line 1 "docker missing"
	fi

	# NOTE: deliberately no ownership/mode assertion on settings.yml — the
	# entrypoint chowns the bind mount to uid 977, so a "must be kuhy-owned,
	# mode 600" check would false-fail on every run after first start.
	if [[ -f $SEARX_SETTINGS ]]; then
		status_line 0 "settings.yml present"
	else
		status_line 1 "settings.yml missing — run setup"
	fi
	# Its absence is not cosmetic: with no limiter.toml there are no
	# trusted_proxies, so botdetection 429s every request including the homepage.
	if [[ -f $SEARX_LIMITER ]]; then
		status_line 0 "limiter.toml present"
	else
		status_line 1 "limiter.toml missing — botdetection will 429 everything"
	fi

	check_container "$VALKEY_CONTAINER" "$VALKEY_PORT"
	check_container "$SEARX_CONTAINER" "$SEARX_PORT"

	# The limiter silently no-ops when valkey is unreachable, so a working search
	# does NOT prove the limiter works. Check the backend directly.
	local ping
	ping="$(docker exec "$VALKEY_CONTAINER" valkey-cli -h 127.0.0.1 -p "$VALKEY_PORT" ping 2>/dev/null || true)"
	if [[ $ping == "PONG" ]]; then
		status_line 0 "valkey reachable — limiter backend live"
	else
		status_line 1 "valkey NOT reachable — the limiter is silently disabled"
	fi

	status_line "$(check_http "http://127.0.0.1:${SEARX_PORT}/" "$SEARX_DOMAIN")" \
		"local SearXNG (127.0.0.1:${SEARX_PORT}, Host: ${SEARX_DOMAIN})"

	if [[ -f $SEARX_SNIPPET ]]; then
		status_line 0 "Caddy snippet present"
	else
		status_line 1 "Caddy snippet missing"
	fi
	if getent hosts "$SEARX_DOMAIN" >/dev/null; then
		status_line 0 "${SEARX_DOMAIN} resolves"
	else
		status_line 1 "${SEARX_DOMAIN} does not resolve"
	fi
	status_line "$(check_http "https://${SEARX_DOMAIN}/")" \
		"external https://${SEARX_DOMAIN}/"

	check_headers

	# A loading front page proves nothing about the actual product. Egress is the
	# fragile part on this host (bridge networking has no outbound access at all),
	# so run a real query and require real results. Uses the loopback JSON API,
	# which pass_ip exempts from botdetection.
	local json hits
	json="$(curl -s --compressed --max-time 30 \
		"http://127.0.0.1:${SEARX_PORT}/search?q=arch+linux&format=json" 2>/dev/null || true)"
	hits="$(grep -o '"url"' <<<"$json" | wc -l)"
	if [[ ${hits:-0} -gt 0 ]]; then
		status_line 0 "live search returned ${hits} results (engines reachable)"
	else
		status_line 1 "live search returned NO results — check egress/engines"
	fi
	# Surfaces engines that are failing rather than merely slow; these are the
	# candidates for pruning.
	local dead
	dead="$(grep -oE '"unresponsive_engines": \[\[[^]]*' <<<"$json" | head -c 300 || true)"
	[[ -n $dead ]] && log_info "unresponsive engines: ${dead#*: }"

	# After pruning, general search is served by google cse alone (google/bing
	# are inactive: true upstream and only answer to !go / !bi). That is a single
	# point of failure worth naming explicitly rather than discovering as "no
	# results", so check the engine that is actually carrying the category.
	if [[ ${hits:-0} -eq 0 ]]; then
		log_warn "general search has no working engine — try: !go <query> / !bi <query>,"
		log_warn "or re-enable an engine in the 'engines:' block of ${SEARX_SETTINGS}"
	fi

	log_info "Not checked here (needs another machine): the JSON API under bot"
	log_info "detection. Run from your phone on cellular, not from this host:"
	log_info "  curl 'https://${SEARX_DOMAIN}/search?q=test&format=json'"
}

main() {
	local cmd="${1:-setup}"
	case "$cmd" in
	setup)
		setup_cmd
		;;
	status)
		status_cmd
		;;
	help | -h | --help)
		usage
		;;
	*)
		log_error "Unknown command: $cmd"
		usage 1
		;;
	esac
}

main "$@"
