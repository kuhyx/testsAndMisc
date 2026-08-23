#!/bin/bash
# The SearXNG compose stack and settings files.
#
# Sourced by setup_searxng.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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
	write_searx_settings
	write_searx_limiter
}
