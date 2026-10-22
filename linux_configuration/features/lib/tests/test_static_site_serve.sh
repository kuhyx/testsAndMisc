#!/usr/bin/env bash
# Tests for the `serve` subcommand of setup_personal_website.sh and
# setup_kcd2_dice_solver.sh: re-render the inner compose + Caddyfile and
# recreate only that site's container, with no sudo, pacman, rebuild or edge
# reload.
#
# Hermetic by necessity, not by taste. Every path in the entry scripts is a
# readonly constant under $HOME and the website's container_name is fixed, so a
# real `docker compose up --force-recreate` from a throwaway dir would recreate
# the LIVE personal-website container. Instead the real entry scripts run with
# HOME pointed at a temp dir and docker/curl stubbed on PATH. The rendered
# Caddyfile itself is served by real caddy in e2e_agent_ready_caddy.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"
FEATURES_DIR="$(cd "$FEATURES_LIB_DIR/.." && pwd)"
readonly FEATURES_DIR

_t_setup_env
trap _t_teardown EXIT

# docker records every call; `docker exec <c> netstat` answers $FAKE_LISTENERS,
# the sudo-free listener table the dice edge-conflict guard reads.
cat >"$TEST_TMPDIR/bin/docker" <<'EOF'
#!/usr/bin/env bash
printf 'docker %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
if [[ $1 == exec && $* == *netstat* ]]; then
	printf '%s\n' "${FAKE_LISTENERS:-}"
fi
EOF
# curl expands only the -w variables the readiness loops ask for, plus the \n
# escape as real curl does.
cat >"$TEST_TMPDIR/bin/curl" <<'EOF'
#!/usr/bin/env bash
printf 'curl %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
while [[ $# -gt 0 ]]; do
	if [[ $1 == -w ]]; then
		fmt="${2//'%{http_code}'/${FAKE_CODE:-200}}"
		printf '%b' "${fmt//'%{size_download}'/1234}"
	fi
	shift
done
EOF
chmod +x "$TEST_TMPDIR/bin/docker" "$TEST_TMPDIR/bin/curl"
# Anything serve must never reach. `sleep` only to keep the 404 case fast.
for cmd in sudo pacman pnpm systemctl sleep; do
	_t_stub "$cmd"
done

readonly OK_LISTENERS="tcp 0 0 127.0.0.1:8089 0.0.0.0:* LISTEN 1/caddy"
readonly WEB_SERVE="$TEST_TMPDIR/services/personal-website-serve"
readonly DICE_SERVE="$TEST_TMPDIR/services/kcd2-dice-serve"

make_dist() {
	mkdir -p "$TEST_TMPDIR/src/$1/dist"
	printf '<!doctype html>\n' >"$TEST_TMPDIR/src/$1/dist/index.html"
}

# run_serve <script> -> exit status; output in $TEST_TMPDIR/out.
run_serve() {
	: >"$TEST_TMPDIR/calls.log"
	local rc=0
	HOME="$TEST_TMPDIR" bash "$FEATURES_DIR/$1" serve >"$TEST_TMPDIR/out" 2>&1 || rc=$?
	echo "$rc"
}

assert_nothing_heavy() {
	local hits
	hits="$(grep -E '^(sudo|pacman|pnpm|systemctl) |caddy reload' "$TEST_TMPDIR/calls.log" || true)"
	_t_eq "" "$hits" "$1: no sudo, pacman, pnpm, systemctl or edge reload"
}

printf '== usage advertises serve\n'
for script in setup_personal_website.sh setup_kcd2_dice_solver.sh; do
	_t_has "$(bash "$FEATURES_DIR/$script" help)" "$script serve" "$script help lists serve"
done

printf '== serve refuses without a build, before touching docker\n'
for script in setup_personal_website.sh setup_kcd2_dice_solver.sh; do
	_t_eq 1 "$(run_serve "$script")" "$script serve with no dist/ exits 1"
	_t_eq 0 "$(grep -c '^docker' "$TEST_TMPDIR/calls.log" || true)" "$script: no docker call without a build"
done

make_dist personal-website
make_dist kcd2-dice-solver

printf '== website serve\n'
_t_eq 0 "$(run_serve setup_personal_website.sh)" "website serve exits 0"
_t_file_has "$WEB_SERVE/docker-compose.yml" "container_name: personal-website" "website compose rendered"
_t_file_has "$WEB_SERVE/Caddyfile" 'rel=\\"ai-catalog\\"' "website Caddyfile carries the Link header"
_t_called "docker compose -f $WEB_SERVE/docker-compose.yml up -d --force-recreate" \
	"website container force-recreated"
assert_nothing_heavy "website serve"

printf '== dice serve\n'
export FAKE_LISTENERS="$OK_LISTENERS"
_t_eq 0 "$(run_serve setup_kcd2_dice_solver.sh)" "dice serve exits 0"
_t_file_has "$DICE_SERVE/docker-compose.yml" "container_name: kcd2-dice" "dice compose rendered"
_t_file_has "$DICE_SERVE/Caddyfile" "handle_errors 404" "dice Caddyfile carries the 404 handler"
_t_called "docker compose -f $DICE_SERVE/docker-compose.yml up -d --force-recreate" \
	"dice container force-recreated"
_t_called "docker exec kcd2-dice netstat -ltnp" "dice edge guard ran without sudo"
assert_nothing_heavy "dice serve"

printf '== dice serve fails closed\n'
FAKE_LISTENERS="$OK_LISTENERS"$'\n'"tcp 0 0 :::80 :::* LISTEN 1/caddy"
_t_eq 1 "$(run_serve setup_kcd2_dice_solver.sh)" "a :80 listener fails serve"
_t_called "docker stop kcd2-dice" "the contending container is stopped"
_t_has "$(cat "$TEST_TMPDIR/out")" "bound :80/:443" "  ...for the :80 reason"
FAKE_LISTENERS="$OK_LISTENERS"$'\n'"tcp 0 0 :::8089 :::* LISTEN 1/caddy"
_t_eq 1 "$(run_serve setup_kcd2_dice_solver.sh)" "an all-interfaces :8089 listener fails serve"
_t_has "$(cat "$TEST_TMPDIR/out")" "on all interfaces" "  ...for the all-interfaces reason"
FAKE_LISTENERS=""
_t_eq 1 "$(run_serve setup_kcd2_dice_solver.sh)" "no attributable listener fails serve"
_t_has "$(cat "$TEST_TMPDIR/out")" "Could not confirm" "  ...for the missing-evidence reason"
FAKE_LISTENERS="$OK_LISTENERS"
_t_eq 1 "$(FAKE_CODE=404 run_serve setup_kcd2_dice_solver.sh)" "a 404 with a body is not ready"
_t_has "$(cat "$TEST_TMPDIR/out")" "did not become reachable" "  ...for the readiness reason"

_t_report "static-site serve"
