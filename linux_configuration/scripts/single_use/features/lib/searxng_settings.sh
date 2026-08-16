#!/bin/bash
# The SearXNG settings.yml, including why it is mode 640 and not 600.
#
# Sourced by setup_searxng.sh; split out to keep searxng_stack.sh under
# the 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

write_searx_settings() {
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
}
