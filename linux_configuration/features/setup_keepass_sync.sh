#!/bin/bash
# setup_keepass_sync.sh — set up "one KeePass vault, synced everywhere".
#
# IDENTICAL on every Linux device (PC and laptop alike): each keeps one local
# working vault at ~/Keepass/Passwords.kdbx and syncs it to the canonical copy
# on the dufs server over WebDAV, at the moment you open KeePass. You open the
# vault with a single command — `keepass-open` — on every machine. The phone
# uses KeePassDX (same idea: enter password → Synchronize over WebDAV → use).
#
# The vault MASTER password is never stored — you type it into keepass-open,
# which holds it only in memory for that session. Only the dufs *server*
# password (transport, not the vault key) is cached in the keyring.
#
# Cross-distro (pacman / apt). Run as your normal user; sudo is used only for
# package install and to retire the old one-way mirror unit if present.

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
readonly HERE
readonly CONFIG_DIR="$HOME/.config/keepass-sync"
readonly CONFIG="$CONFIG_DIR/config.env"
readonly BIN_DIR="$HOME/.local/bin"
readonly KEYRING_SERVICE="${KP_KEYRING_SERVICE:-keepass-sync}"
readonly LOCAL_DB="$HOME/Keepass/Passwords.kdbx"

C() { printf '\033[1;34m[keepass-setup]\033[0m %s\n' "$*"; }
OK() { printf '\033[1;32m  ✓\033[0m %s\n' "$*"; }
WARN() { printf '\033[1;33m  !\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[keepass-setup] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }
usage() { grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'; exit 0; }

install_deps() {
	C "Installing dependencies"
	if command -v pacman >/dev/null; then
		sudo pacman -S --needed --noconfirm keepassxc fd curl inotify-tools libsecret
	elif command -v apt-get >/dev/null; then
		sudo apt-get update -qq
		sudo apt-get install -y keepassxc fd-find curl inotify-tools libsecret-tools
	else
		die "no supported package manager (pacman/apt) found"
	fi
	command -v keepassxc-cli >/dev/null || die "keepassxc-cli missing after install"
	command -v secret-tool >/dev/null || die "secret-tool (libsecret) missing after install"
	OK "dependencies present"
}

main() {
	[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage
	C "Setting up unified KeePass sync (same on every device)"
	install_deps

	# --- config: dufs WebDAV endpoint + server credential -------------------
	local url user dpass
	read -r -p "dufs vault URL [https://kuhy-cloud.duckdns.org/Keepass/Passwords.kdbx]: " url
	url="${url:-https://kuhy-cloud.duckdns.org/Keepass/Passwords.kdbx}"
	read -r -p "dufs web username: " user
	read -r -s -p "dufs web password (server credential — cached in keyring): " dpass; echo
	[[ -n "$user" && -n "$dpass" ]] || die "dufs username/password required"
	printf '%s' "$dpass" | secret-tool store --label='dufs server password (keepass-sync)' \
		service "$KEYRING_SERVICE" key dufs
	OK "cached dufs server password in the keyring"

	mkdir -p "$CONFIG_DIR"
	{
		echo "LOCAL_DB=$LOCAL_DB"
		echo "REMOTE_MODE=webdav"
		echo "REMOTE_URL=$url"
		echo "DUFS_USER=$user"
	} >"$CONFIG"
	chmod 600 "$CONFIG"
	OK "wrote $CONFIG"

	# --- bootstrap the local working vault if this device doesn't have one ---
	if [[ ! -f "$LOCAL_DB" ]]; then
		mkdir -p "$(dirname "$LOCAL_DB")"
		if curl -fsS -u "$user:$dpass" -o "$LOCAL_DB" "$url" 2>/dev/null; then
			OK "bootstrapped $LOCAL_DB from the cloud"
		else
			WARN "no vault on the server yet — a local one will be published on first open"
		fi
	else
		OK "local vault already present: $LOCAL_DB"
	fi

	# --- retire the old one-way mirror unit (dufs host only) ----------------
	# is-enabled/is-active are pipe-free and work as non-root (unlike
	# `list-unit-files | grep -q`, which misfires under set -o pipefail).
	if systemctl is-enabled keepass-cloud-sync.path >/dev/null 2>&1 \
		|| systemctl is-active keepass-cloud-sync.path >/dev/null 2>&1; then
		C "Retiring the old one-way keepass-cloud-sync units"
		sudo systemctl disable --now keepass-cloud-sync.path keepass-cloud-sync.service 2>/dev/null || true
		OK "old one-way sync retired"
	fi

	# --- install the two commands -------------------------------------------
	mkdir -p "$BIN_DIR"
	ln -sf "$HERE/keepass-open.sh" "$BIN_DIR/keepass-open"
	OK "installed keepass-open → $BIN_DIR/keepass-open"
	local cons="$BIN_DIR/keepass-consolidate"
	cat >"$cons" <<EOF
#!/bin/bash
# Prompt for the master password and fold stray vaults into the canonical one.
set -euo pipefail
read -r -s -p "KeePass master password: " KP_MASTER_PW; echo
export KP_MASTER_PW
exec "$HERE/keepass_consolidate.sh" --canonical "$LOCAL_DB" "\$@"
EOF
	chmod +x "$cons"
	OK "installed keepass-consolidate → $cons"

	cat <<EOF

────────────────────────────────────────────────────────────────────────────
  Done. Same on every device. Open your vault with:   keepass-open
  It: asks your master password (never stored) → folds in strays → pulls+merges
  the latest → opens KeePassXC on $LOCAL_DB → publishes your edits on close.

  • Make sure $BIN_DIR is on your PATH.
  • Always open via 'keepass-open' (not the raw KeePassXC icon) so it syncs.
  • Phone: KeePassDX → open the database from URL (WebDAV):
      $url
    then use its Synchronize action after editing.
────────────────────────────────────────────────────────────────────────────
EOF
}

main "$@"
