#!/bin/bash
# Regression test: Raspberry Pi / laptop SSH discovery uses rustscan, never
# nmap (nonfree NPSL licence; the pacman wrapper refuses to install it).
#
# Runs the real discover/ensure_dependencies functions with stubbed
# ip/getent/sshpass/rustscan/nmap/pacman on PATH and asserts:
#   - rustscan is called as `-a <net> -p 22 -g` and nmap is never executed
#   - our own IP is excluded and the Pi (answering the hostname probe) is found
#   - ensure_dependencies asks for rustscan, not nmap
#   - no script in the set still invokes nmap

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
FEATURES="$(cd -- "$SCRIPT_DIR/.." && pwd)/features"

fail() {
	printf 'FAIL: %s\n' "$1" >&2
	exit 1
}

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
STUBS="$TMP_DIR/stubs"
mkdir -p "$STUBS"
export STUB_LOG="$TMP_DIR/calls.log"
: >"$STUB_LOG"

stub() { # name; body on stdin
	{
		printf '#!/bin/bash\n'
		cat
	} >"$STUBS/$1"
	chmod +x "$STUBS/$1"
}
stub ip <<'STUB'
if [[ $1 == -4 ]]; then
	echo "    inet 192.168.1.5/24 brd 192.168.1.255 scope global eth0"
else
	echo "default via 192.168.1.1 dev eth0"
fi
STUB
stub getent <<'STUB'
exit 2
STUB
stub nmap <<'STUB'
echo "nmap $*" >>"$STUB_LOG"
exit 1
STUB
stub rustscan <<'STUB'
echo "rustscan $*" >>"$STUB_LOG"
printf '192.168.1.5 -> [22]\n192.168.1.43 -> [22]\n192.168.1.26 -> [22]\n'
STUB
stub pacman <<'STUB'
echo "pacman $*" >>"$STUB_LOG"
STUB
stub sudo <<'STUB'
"$@"
STUB
# sshpass -p PW ssh ... user@IP CMD : only .43 is the Pi.
stub sshpass <<'STUB'
for a in "$@"; do [[ $a == *@* ]] && ip=${a#*@}; done
echo "ssh $ip" >>"$STUB_LOG"
if [[ $ip == 192.168.1.43 ]]; then
	case "${*: -1}" in hostname) echo nextcloud-pi ;; *) echo ok ;; esac
fi
STUB

log_info() { :; }
log_success() { :; }
die() {
	printf 'die: %s\n' "$*" >&2
	exit 1
}
export PI_HOSTNAME=nextcloud-pi PI_USER=pi PI_PASSWORD=pw REMOTE_LAPTOP_IP=192.168.1.17

# Runs discover_raspberry_pi from the given lib with every external stubbed.
check_discover() { # lib file
	: >"$STUB_LOG"
	(
		PATH="$STUBS:$PATH"
		# Real ensure_dependencies (no-op: rustscan/sshpass stubs are on PATH).
		# shellcheck source=../features/lib/rpi_nc_deps.sh
		source "$FEATURES/lib/rpi_nc_deps.sh"
		# shellcheck source=/dev/null
		source "$FEATURES/lib/$1"
		found=$(discover_raspberry_pi)
		[[ $found == 192.168.1.43 ]] || fail "$1 found '$found', want 192.168.1.43"
	)
	grep -qx 'rustscan -a 192.168.1.0/24 -p 22 -g' "$STUB_LOG" ||
		fail "$1: rustscan not called with '-a 192.168.1.0/24 -p 22 -g': $(tr '\n' '|' <"$STUB_LOG")"
	if grep -q '^nmap' "$STUB_LOG"; then fail "$1 ran nmap"; fi
	if grep -qx 'ssh 192.168.1.5' "$STUB_LOG"; then fail "$1 tried our own IP"; fi
	printf 'ok discover %s\n' "$1"
}
check_discover nc_discover.sh
check_discover rpi_nc_deps.sh

# --- ensure_dependencies asks for rustscan, not nmap ------------------------
: >"$STUB_LOG"
rm -f "$STUBS/rustscan" "$STUBS/sshpass" # hide them so the install branch runs
(
	PATH="$STUBS"
	hash -r
	# shellcheck source=../features/lib/rpi_nc_deps.sh
	source "$FEATURES/lib/rpi_nc_deps.sh"
	ensure_dependencies >/dev/null 2>&1 || true
)
grep -q '^pacman -S --noconfirm rustscan' "$STUB_LOG" ||
	fail "ensure_dependencies did not request rustscan: $(tr '\n' '|' <"$STUB_LOG")"
grep -E '^pacman .*nmap' "$STUB_LOG" && fail "ensure_dependencies still requests nmap"
printf 'ok rpi_nc_deps dependencies\n'

# --- no remaining nmap invocation in the set --------------------------------
for f in lib/nc_discover.sh lib/nc_remote.sh lib/rpi_nc_deps.sh lib/nc_flash.sh \
	lib/nc_image.sh lib/pi_flash_remote.sh raspberry_pi_flash_sd.sh; do
	if grep -nE '(^|[^[:alnum:]_-])nmap([^[:alnum:]_-]|$)' "$FEATURES/$f"; then
		fail "$f still mentions nmap"
	fi
done
printf 'ok no nmap references\n'
