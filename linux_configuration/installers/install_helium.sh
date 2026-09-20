#!/usr/bin/env bash
# Install Helium (https://github.com/imputnet/helium-linux) — the Chromium
# fork that still runs FULL uBlock Origin (Manifest V2) on Arch.
#
# Why Helium: Chromium 151 removed the last MV2 code paths and Google purged
# uBO from the Web Store on 2026-08-31, so plain chromium / ungoogled-chromium
# can no longer load it. Helium is GPL-3, built on ungoogled-chromium, and
# bundles uBO as a component extension (ID blockjmkbacgjkknlgpkjjiijinjdanf)
# — it is not in the profile, so a cloned profile cannot lose it.
#
# What this does:
#   1. yay -S helium-browser-bin
#   2. routes /usr/local/bin/helium-browser through browser-preexec-wrapper,
#      the same pre-exec hook every other browser here gets (hosts-blocker
#      refresh + LeechBlock NG via --load-extension). Skipping this would
#      silently drop the site blocker when switching from chromium.
#   3. --clone-profile: copies ~/.config/chromium -> ~/.config/net.imput.helium
#      (Helium's profile dir), minus lock files. Refuses if the target exists
#      or a browser is running (LevelDB copies inconsistently from a live
#      process). Helium's Chromium base must be >= the source profile's
#      "Last Version" or Chromium treats it as a downgrade; checked here.
#   4. runs verify_helium.py: MV2 uBO present, /etc/chromium/policies applied
#      (Helium reads that dir natively — no symlink needed), ad-block score.
#
# Usage: ./install_helium.sh [--clone-profile] [--no-verify]

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly PKG="helium-browser-bin"
readonly HELIUM_BIN="/usr/bin/helium-browser"
readonly WRAPPER="/usr/local/bin/browser-preexec-wrapper"
readonly WRAPPER_LINK="/usr/local/bin/helium-browser"
readonly SRC_PROFILE="${XDG_CONFIG_HOME:-$HOME/.config}/chromium"
readonly DST_PROFILE="${XDG_CONFIG_HOME:-$HOME/.config}/net.imput.helium"

CLONE_PROFILE=false
VERIFY=true

usage() {
	sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
	exit 0
}

# Everything the clone + verify steps fork: rsync, Xvfb, the CDP websocket
# client; base-devel + git only matter on a box without yay (makepkg path).
readonly -a PACMAN_DEPS=(rsync xorg-server-xvfb python-websockets python-cryptography base-devel git)

validate_requirements() {
	command -v pacman >/dev/null 2>&1 || {
		error "pacman not found. This script is for Arch Linux."
		exit 1
	}
	info "Ensuring pacman deps: ${PACMAN_DEPS[*]}"
	sudo pacman -S --needed --noconfirm "${PACMAN_DEPS[@]}"
}

# yay when present (the normal case here); otherwise the same clone+makepkg
# path fresh-install/lib/packages.sh uses, so a bare box works too.
install_from_aur() {
	if command -v yay >/dev/null 2>&1; then
		yay -S --needed --noconfirm "$PKG"
		return
	fi
	local build_dir="$HOME/sdk/aur/$PKG"
	mkdir -p "$HOME/sdk/aur"
	[[ -d $build_dir ]] || git clone "https://aur.archlinux.org/$PKG.git" "$build_dir"
	# The PKGBUILD verifies the release tarball's signature; yay imports the
	# key on its own, bare makepkg does not.
	local key
	while read -r key; do
		gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys "$key"
	done < <(cd "$build_dir" && makepkg --printsrcinfo | awk '/validpgpkeys/ {print $3}')
	(cd "$build_dir" && makepkg -si --needed --noconfirm)
}

install_package() {
	if pacman -Q "$PKG" >/dev/null 2>&1; then
		info "$PKG already installed ($(pacman -Q "$PKG" | cut -d' ' -f2))"
	else
		info "Installing $PKG from AUR..."
		install_from_aur
	fi
	[[ -x $HELIUM_BIN ]] || {
		error "$HELIUM_BIN missing after install"
		exit 1
	}
}

# /usr/local/bin precedes /usr/bin, so `helium-browser` from dmenu/a shell
# resolves to the wrapper, exactly like chromium/firefox do on this machine.
wire_wrapper() {
	if [[ ! -x $WRAPPER ]]; then
		warn "$WRAPPER not installed (periodic_background/setup_periodic_system.sh) — skipping wrapper link"
		return 0
	fi
	if [[ -L $WRAPPER_LINK && $(readlink -f "$WRAPPER_LINK") == "$WRAPPER" ]]; then
		info "Wrapper link already in place: $WRAPPER_LINK"
		return 0
	fi
	info "Linking $WRAPPER_LINK -> $WRAPPER"
	sudo ln -sf "$WRAPPER" "$WRAPPER_LINK"
}

# Chromium refuses (or silently resets) a profile written by a newer build.
# `--version` prints "Helium 0.17.2.1 (Chromium 153.0.8010.52)" — the
# parenthesised Chromium number is the one a profile's "Last Version" holds.
profile_downgrade_check() {
	local src_ver helium_ver
	src_ver="$(cat "$SRC_PROFILE/Last Version" 2>/dev/null || echo 0)"
	helium_ver="$("$HELIUM_BIN" --version 2>/dev/null | grep -oE 'Chromium [0-9]+(\.[0-9]+){3}' | cut -d' ' -f2)"
	[[ -n $helium_ver ]] || {
		error "Could not determine Helium's Chromium base version"
		exit 1
	}
	if [[ "$(printf '%s\n%s\n' "$src_ver" "$helium_ver" | sort -V | tail -1)" != "$helium_ver" ]]; then
		error "Helium $helium_ver is older than the source profile ($src_ver) — cloning would be a downgrade."
		exit 1
	fi
	info "Profile version $src_ver <= Helium $helium_ver — clone is safe"
}

clone_profile() {
	[[ -d $SRC_PROFILE ]] || {
		error "No source profile at $SRC_PROFILE"
		exit 1
	}
	[[ -e $DST_PROFILE ]] && {
		error "$DST_PROFILE already exists — refusing to overwrite. Remove it yourself if you want a re-clone."
		exit 1
	}
	if pgrep -f '/usr/lib/chromium|ungoogled-chromium|/opt/helium-browser' >/dev/null 2>&1; then
		error "A Chromium/Helium process is running — close it first (a live profile copies inconsistently)."
		exit 1
	fi
	profile_downgrade_check
	info "Cloning $SRC_PROFILE -> $DST_PROFILE"
	rsync -a \
		--exclude='SingletonLock' --exclude='SingletonSocket' --exclude='SingletonCookie' \
		--exclude='DevToolsActivePort' --exclude='Crash Reports' --exclude='BrowserMetrics*' \
		"$SRC_PROFILE/" "$DST_PROFILE/"
	info "Cloned $(du -sh "$DST_PROFILE" | cut -f1)"
	warn "Saved passwords are keyring-encrypted under Chromium's own label; check one in Helium before trusting the clone."
}

run_verify() {
	info "Verifying under Xvfb (never the live display)..."
	python3 "$SCRIPT_DIR/verify_helium.py"
}

main() {
	validate_requirements
	install_package
	wire_wrapper
	if $CLONE_PROFILE; then clone_profile; fi
	if $VERIFY; then run_verify; fi
	info "Done. Launch with: helium-browser"
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--clone-profile) CLONE_PROFILE=true ;;
	--no-verify) VERIFY=false ;;
	-h | --help) usage ;;
	*)
		error "Unknown option: $1"
		exit 1
		;;
	esac
	shift
done

main
