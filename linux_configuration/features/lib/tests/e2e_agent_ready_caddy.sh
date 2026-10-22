#!/usr/bin/env bash
# End-to-end AgentReady check of the inner Caddyfile a static-site lib renders.
#
#   linux_configuration/features/lib/tests/e2e_agent_ready_caddy.sh website|dice
#
# Deliberately NOT named test_*.sh: run_all.sh runs those inside the namespace
# jail, which has no docker. This one runs on the host and needs docker plus
# ~/src/utils/agent_ready.
#
# It renders the inner Caddyfile with the real lib function into a temp dir,
# serves a COPY of the site's built dist/ (dotfiles included, as the live bind
# mount does) from a throwaway caddy:2.8 container -- the image production pins
# -- on a spare loopback port, then runs the checker in url mode plus exact
# asserts the checker is too lenient to make (it also accepts text/xml,
# application/json and text/plain where the spec here demands more).
#
# Host mapping: robots.txt and the sitemap carry absolute PUBLIC URLs, and the
# checker treats any other host as off-site. So the checker is pointed at
# http://<public host> with http_proxy aimed at the container: urllib then sends
# every request to 127.0.0.1:<port> carrying the public Host header. A canary
# run BEFORE the container starts must exit 3 (connection refused); output from
# it would mean the checker reached the live site and proves nothing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

readonly IMAGE="caddy:2.8"
readonly CHECKER="${HOME}/src/utils/agent_ready/check.sh"
CONTAINER=""

cleanup() {
	if [[ -n $CONTAINER ]]; then
		docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
	fi
	_t_teardown
}

# Stand-ins for the common.sh helpers the libs inherit from their entry script.
log_ok() { :; }
log_info() { :; }
ensure_dir() { mkdir -p "$1"; }

# Globals each lib takes from above its entry script's source line.
render_website() {
	WEBSITE_SRC="$TEST_TMPDIR/src"
	WEBSITE_PORT="$PORT"
	WEBSITE_DATA_DIR="$TEST_TMPDIR/serve"
	WEBSITE_COMPOSE="$WEBSITE_DATA_DIR/docker-compose.yml"
	WEBSITE_INNER_CADDY="$CADDYFILE_OUT"
	# shellcheck source=../website_build.sh
	. "$FEATURES_LIB_DIR/website_build.sh"
	write_website_stack
}

render_dice() {
	DICE_DOMAIN="$HOST"
	DICE_PORT="$PORT"
	DICE_SRC="$TEST_TMPDIR/src"
	DICE_DATA_DIR="$TEST_TMPDIR/serve"
	DICE_COMPOSE="$DICE_DATA_DIR/docker-compose.yml"
	DICE_INNER_CADDY="$CADDYFILE_OUT"
	DICE_CONTAINER="kcd2-dice"
	CADDY_CONTAINER="gitea-caddy"
	# shellcheck source=../kcd2_serve.sh
	. "$FEATURES_LIB_DIR/kcd2_serve.sh"
	write_serve_stack
}

run_checker() {
	HTTP_PROXY="http://127.0.0.1:${PORT}" http_proxy="http://127.0.0.1:${PORT}" \
		NO_PROXY="" no_proxy="" "$CHECKER" url "http://${HOST}" --budget 40
}

# "<status> <content-type>" for one path, body kept in $TEST_TMPDIR/body.
probe() {
	curl -s -o "$TEST_TMPDIR/body" -D "$TEST_TMPDIR/headers" -w '%{http_code} %{content_type}' \
		--max-time 5 -H "Host: ${HOST}" "http://127.0.0.1:${PORT}$1"
}

case "${1:-}" in
website)
	HOST="kuhy.duckdns.org" PORT=18088 SRC_DIST="${HOME}/src/personal-website/dist"
	PAGE="/blog/hello-world" PAGE_FILE="blog/hello-world/index.html" MIRROR="/blog/hello-world.md"
	;;
dice)
	HOST="dice.kuhy.duckdns.org" PORT=18089 SRC_DIST="${HOME}/src/kcd2-dice-solver/dist"
	PAGE="/how-it-works/" PAGE_FILE="how-it-works/index.html" MIRROR="/how-it-works/index.md"
	;;
*)
	printf 'usage: %s website|dice\n' "$0" >&2
	exit 2
	;;
esac

_t_setup_env
trap cleanup EXIT
CADDYFILE_OUT="$TEST_TMPDIR/Caddyfile"
mkdir -p "$TEST_TMPDIR/dist"
cp -a "$SRC_DIST/." "$TEST_TMPDIR/dist"
"render_$1"

printf '== rendered site block\n'
sed -n "/^:${PORT} {/,/^}/p" "$CADDYFILE_OUT"

printf '== canary (no container yet): checker must exit 3\n'
canary=0
run_checker >/dev/null 2>&1 || canary=$?
_t_eq 3 "$canary" "checker cannot reach the live site through the proxy mapping"

if docker run --rm -v "$CADDYFILE_OUT:/etc/caddy/Caddyfile:ro" "$IMAGE" \
	caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
	_t_pass "caddy validate"
else
	_t_fail "caddy validate"
fi

CONTAINER="agent-ready-e2e-$1-$$"
docker run -d --name "$CONTAINER" --network host \
	-v "$TEST_TMPDIR/dist:/srv:ro" -v "$CADDYFILE_OUT:/etc/caddy/Caddyfile:ro" \
	"$IMAGE" >/dev/null
for _ in $(seq 1 30); do
	[[ "$(probe / || true)" == 200* ]] && break
	sleep 0.2
done

printf '== exact HTTP asserts\n'
_t_has "$(probe /)" "200 text/html" "/ is 200 html"
_t_has "$(cat "$TEST_TMPDIR/headers")" '</.well-known/ai-catalog.json>; rel="ai-catalog"' "/ sends the ai-catalog Link header"
_t_has "$(probe "$PAGE")" "200 text/html" "$PAGE is 200 html"
if cmp -s "$TEST_TMPDIR/body" "$TEST_TMPDIR/dist/$PAGE_FILE"; then
	_t_pass "$PAGE serves its own prerendered $PAGE_FILE, not the shell"
else
	_t_fail "$PAGE serves its own prerendered $PAGE_FILE, not the shell"
fi
_t_eq "200 text/plain; charset=utf-8" "$(probe /robots.txt)" "/robots.txt type"
_t_eq "200 text/plain; charset=utf-8" "$(probe /llms.txt)" "/llms.txt type"
_t_eq "200 application/xml" "$(probe /sitemap.xml)" "/sitemap.xml type"
_t_eq "200 application/ai-catalog+json" "$(probe /.well-known/ai-catalog.json)" "ai-catalog type"
_t_eq "200 text/markdown; charset=utf-8" "$(probe /index.md)" "/index.md type"
_t_eq "200 text/markdown; charset=utf-8" "$(probe "$MIRROR")" "$MIRROR type"
_t_has "$(probe /agentready-e2e-nope)" "404 text/html" "unknown path is a 404 html page"
if cmp -s "$TEST_TMPDIR/body" "$TEST_TMPDIR/dist/404.html"; then
	_t_pass "404 body is dist/404.html"
else
	_t_fail "404 body is dist/404.html"
fi
_t_has "$(probe /nope.md)" "404 text/html" "missing .md is a 404 html page, not markdown"

printf '== AgentReady url mode (http://%s via 127.0.0.1:%s)\n' "$HOST" "$PORT"
status=0
run_checker || status=$?
_t_eq 0 "$status" "agent_ready url mode exit"

_t_report "e2e agent-ready $1"
