#!/usr/bin/env bash
# Tests for rpi_nc_ca.sh — installing the Pi's CA into the client's trust stores.
#
# The subject sudo-copies into /etc/ca-certificates, /usr/local/share and
# /etc/pki, and appends to /etc/hosts. Those writes are the point, so they run
# for real inside the jail, which bind-mounts every one of those paths to a
# throwaway dir. See jail_args beside this file.
#
# The five OS branches are selected by SEEDING the marker file each one tests
# for (/etc/arch-release, /etc/debian_version, ...) inside the jailed /etc.
# That is only safe because /etc is bind-mounted: on a real host this would
# make the machine claim to be a different distribution.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

# --- Refuse to run outside the jail -----------------------------------------
# The suite seeds /etc/arch-release and friends and appends to /etc/hosts.
# An unwritable /etc means we are NOT contained.
if [[ ! -w /etc ]]; then
	printf 'REFUSING: this suite must run under shell_coverage_jail.sh\n' >&2
	exit 1
fi

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script defines above its source line.
PI_PASSWORD="hunter2"
PI_USER="pi"
PI_HOSTNAME="raspberrypi"

log_info() { printf '[INFO] %s\n' "$*"; }
log_success() { printf '[OK] %s\n' "$*"; }
log_warning() { printf '[WARN] %s\n' "$*"; }
die() {
	printf '[DIE] %s\n' "$*" >&2
	exit 1
}

discover_raspberry_pi() { printf '10.0.0.7\n'; }

# sshpass writes the CA to stdout, which the subject redirects into the file.
# A record-only stub would leave an EMPTY file and the subject would die --
# a stub must materialise what the real tool produces.
_t_ssh_emits_ca() {
	cat >"$TEST_TMPDIR/bin/sshpass" <<'SSHPASS'
#!/usr/bin/env bash
printf -- '-----BEGIN CERTIFICATE-----\nFAKECA\n-----END CERTIFICATE-----\n'
SSHPASS
	chmod +x "$TEST_TMPDIR/bin/sshpass"
}

# shellcheck source=../rpi_nc_ca.sh
. "$FEATURES_LIB_DIR/rpi_nc_ca.sh"

[[ -n $PI_HOSTNAME && -n $PI_USER ]] ||
	die "fixture globals are empty; the suite would assert nothing"

# --- show_help --------------------------------------------------------------
help_out="$(show_help)"
_t_has "$help_out" 'Usage:' "show_help prints a usage line"
_t_has "$help_out" 'raspberry_pi_nextcloud.sh' "show_help names the entry script"

# --- phase_install_ca: refuses without a password ---------------------------
no_pw_out="$(
	PI_PASSWORD=""
	phase_install_ca 2>&1
)" || true
_t_has "$no_pw_out" 'PI_PASSWORD not set' "phase_install_ca dies when PI_PASSWORD is unset"

# --- phase_install_ca: refuses when the Pi cannot be found ------------------
no_pi_out="$(
	discover_raspberry_pi() { printf '\n'; }
	phase_install_ca 2>&1
)" || true
_t_has "$no_pi_out" 'Failed to discover' "phase_install_ca dies when the Pi is undiscoverable"

# --- phase_install_ca: refuses on an empty CA download ----------------------
_t_stub sshpass
empty_out="$(phase_install_ca 2>&1)" || true
_t_has "$empty_out" 'Failed to download CA' "phase_install_ca dies when the downloaded CA is empty"

# --- phase_install_ca: the Arch branch --------------------------------------
_t_ssh_emits_ca
_t_stub trust
_t_stub certutil
_t_stub curl
rm -f /etc/debian_version /etc/redhat-release
: >/etc/arch-release
mkdir -p /etc/ca-certificates/trust-source/anchors
arch_out="$(phase_install_ca 2>&1)"
_t_has "$arch_out" 'Detected Arch Linux' "the Arch branch is selected by /etc/arch-release"
_t_file_has /etc/ca-certificates/trust-source/anchors/nextcloud-ca.crt 'FAKECA' \
	"the Arch branch copies the CA into the system anchor dir"
_t_called 'trust' "the Arch branch runs trust extract-compat"
_t_file_has /etc/hosts 'raspberrypi' "the hostname is appended to /etc/hosts"

# --- phase_install_ca: /etc/hosts is not duplicated on a second run ---------
second_out="$(phase_install_ca 2>&1)"
_t_eq "1" "$(grep -c 'raspberrypi' /etc/hosts)" "a second run does not duplicate the /etc/hosts entry"
_t_has "$second_out" 'already in /etc/hosts' "the second run reports the entry already exists"

# --- phase_install_ca: the Debian branch ------------------------------------
rm -f /etc/arch-release
: >/etc/debian_version
mkdir -p /usr/local/share/ca-certificates
_t_stub update-ca-certificates
deb_out="$(phase_install_ca 2>&1)"
_t_has "$deb_out" 'Detected Debian/Ubuntu' "the Debian branch is selected by /etc/debian_version"
_t_file_has /usr/local/share/ca-certificates/nextcloud-ca.crt 'FAKECA' \
	"the Debian branch copies the CA into /usr/local/share"
_t_called 'update-ca-certificates' "the Debian branch runs update-ca-certificates"

# --- phase_install_ca: the RHEL branch --------------------------------------
rm -f /etc/debian_version
: >/etc/redhat-release
mkdir -p /etc/pki/ca-trust/source/anchors
_t_stub update-ca-trust
rhel_out="$(phase_install_ca 2>&1)"
_t_has "$rhel_out" 'Detected RHEL/Fedora' "the RHEL branch is selected by /etc/redhat-release"
_t_file_has /etc/pki/ca-trust/source/anchors/nextcloud-ca.crt 'FAKECA' \
	"the RHEL branch copies the CA into the pki anchor dir"
_t_called 'update-ca-trust' "the RHEL branch runs update-ca-trust"

# --- phase_install_ca: the unknown-OS branch --------------------------------
rm -f /etc/redhat-release
unknown_out="$(phase_install_ca 2>&1)"
_t_has "$unknown_out" 'Unknown OS' "an unrecognised OS warns instead of failing"

# --- phase_install_ca: the macOS branch -------------------------------------
# Selected by `uname` rather than a marker file, so the stub is what picks it.
_t_stub security
cat >"$TEST_TMPDIR/bin/uname" <<'UNAME'
#!/usr/bin/env bash
printf 'Darwin\n'
UNAME
chmod +x "$TEST_TMPDIR/bin/uname"
mac_out="$(phase_install_ca 2>&1)"
_t_has "$mac_out" 'Detected macOS' "the macOS branch is selected when uname reports Darwin"
_t_has "$mac_out" 'system keychain' "the macOS branch reports the keychain install"
rm -f "$TEST_TMPDIR/bin/uname"

# --- phase_install_ca: certutil reports the CA is ALREADY installed ---------
# `certutil -L` emitting a line containing "Nextcloud" takes the else branch.
cat >"$TEST_TMPDIR/bin/certutil" <<'CERTUTIL'
#!/usr/bin/env bash
printf 'Nextcloud Home CA   CT,C,C\n'
exit 0
CERTUTIL
chmod +x "$TEST_TMPDIR/bin/certutil"
already_out="$(phase_install_ca 2>&1)"
_t_has "$already_out" 'already installed in Chrome/Chromium' \
	"an existing NSS entry is reported rather than re-added"

# --- phase_install_ca: certutil FAILS to add the CA -------------------------
# -L must succeed-but-not-match (so the add is attempted) while -A fails.
cat >"$TEST_TMPDIR/bin/certutil" <<'CERTUTIL'
#!/usr/bin/env bash
for arg in "$@"; do
	if [[ $arg == -A ]]; then
		exit 1
	fi
done
exit 0
CERTUTIL
chmod +x "$TEST_TMPDIR/bin/certutil"
cannot_out="$(phase_install_ca 2>&1)"
_t_has "$cannot_out" 'Could not install in Chrome/Chromium' \
	"a failing certutil -A warns instead of aborting"

# --- phase_install_ca: the Firefox loop, all three outcomes -----------------
# A profile dir must exist for the loop body to run at all; the glob otherwise
# yields a literal unmatched pattern that fails the -d test.
mkdir -p ~/.mozilla/firefox/abcd.default

# certutil -A still fails here (stubbed above), so nothing installs.
ff_fail_out="$(phase_install_ca 2>&1)"
_t_has "$ff_fail_out" 'Could not install in Firefox' \
	"a profile whose certutil -A fails reports the manual-import warning"

# -L succeeds but does not match, and -A now succeeds: the CA is added.
_t_stub certutil
ff_add_out="$(phase_install_ca 2>&1)"
_t_has "$ff_add_out" 'CA installed in Firefox' "a successful certutil -A reports the Firefox install"

# -L matches "Nextcloud": already present, so the add is skipped.
cat >"$TEST_TMPDIR/bin/certutil" <<'CERTUTIL'
#!/usr/bin/env bash
printf 'Nextcloud Home CA   CT,C,C\n'
exit 0
CERTUTIL
chmod +x "$TEST_TMPDIR/bin/certutil"
ff_have_out="$(phase_install_ca 2>&1)"
_t_has "$ff_have_out" 'CA installed in Firefox' "an already-present Firefox CA still reports success"

# --- phase_install_ca: HTTPS verification succeeds --------------------------
cat >"$TEST_TMPDIR/bin/curl" <<'CURL'
#!/usr/bin/env bash
printf 'installed\n'
CURL
chmod +x "$TEST_TMPDIR/bin/curl"
verified_out="$(phase_install_ca 2>&1)"
_t_has "$verified_out" 'HTTPS connection verified' "a status.php reporting 'installed' verifies the connection"

_t_report "test_rpi_nc_ca.sh"
