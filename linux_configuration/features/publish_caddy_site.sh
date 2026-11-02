#!/bin/bash
# Publish a loopback service at https://<name>.kuhy.duckdns.org through the
# existing Caddy edge (container gitea-caddy, host network, ports 80/443,
# HTTP-01 certs; see setup_gitea.sh). No sudo: the user is in the docker group.
#
#   publish_caddy_site.sh <name> <port>            # write snippet, validate, reload
#   publish_caddy_site.sh <name> <port> --dry-run  # validate only, change nothing
#
# Optional bearer gate: if ~/.config/<name>-mcp/token exists (or TOKEN_FILE),
# requests without "Authorization: Bearer <token>" get 401 at the edge.
# DNS: *.kuhy.duckdns.org already resolves to the home IP; nothing to add.
set -euo pipefail

readonly SITES_DIR="${SITES_DIR:-${HOME}/services/gitea/sites}"
readonly CONTAINER="${CONTAINER:-gitea-caddy}"
readonly IMAGE="${CADDY_IMAGE:-caddy:2.8}"

die() {
	echo "Error: $*" >&2
	exit 1
}

[[ $# -ge 2 ]] || die "usage: $0 <name> <port> [--dry-run]"
readonly NAME="$1" PORT="$2" MODE="${3:-}"
[[ "$NAME" =~ ^[a-z0-9-]+$ ]] || die "bad name: $NAME"
[[ "$PORT" =~ ^[0-9]{4,5}$ ]] || die "bad port: $PORT"
command -v docker >/dev/null || die "docker is required"
[[ -d "$SITES_DIR" ]] || die "no Caddy site directory at $SITES_DIR"

readonly HOST="${NAME}.kuhy.duckdns.org"
readonly TOKEN_FILE="${TOKEN_FILE:-${HOME}/.config/${NAME}-mcp/token}"

render() {
	echo "# Managed by publish_caddy_site.sh -- do not edit by hand."
	echo "${HOST} {"
	if [[ -f "$TOKEN_FILE" ]]; then
		printf '\t@unauth not header Authorization "Bearer %s"\n' "$(<"$TOKEN_FILE")"
		printf '\trespond @unauth "unauthorized" 401\n'
	fi
	printf '\treverse_proxy 127.0.0.1:%s {\n\t\tflush_interval -1\n\t}\n}\n' "$PORT"
}

# Validate with a throwaway container on a tmp copy: never touches the live edge.
validate_copy() {
	local tmp
	tmp="$(mktemp -d)"
	trap 'rm -rf "$tmp"' RETURN
	mkdir -p "$tmp/sites"
	cp -a "$SITES_DIR"/. "$tmp/sites/" 2>/dev/null || true
	render >"$tmp/sites/${HOST}.caddy"
	printf 'import /etc/caddy/sites/*.caddy\n' >"$tmp/Caddyfile"
	docker run --rm -v "$tmp/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$tmp/sites:/etc/caddy/sites:ro" \
		"$IMAGE" caddy validate --config /etc/caddy/Caddyfile
}

validate_copy
[[ "$MODE" == "--dry-run" ]] && {
	echo "dry run ok: ${HOST} -> 127.0.0.1:${PORT}"
	exit 0
}

render >"${SITES_DIR}/${HOST}.caddy"
chmod 600 "${SITES_DIR}/${HOST}.caddy"
docker exec "$CONTAINER" caddy reload --config /etc/caddy/Caddyfile
echo "published https://${HOST} -> 127.0.0.1:${PORT}"
