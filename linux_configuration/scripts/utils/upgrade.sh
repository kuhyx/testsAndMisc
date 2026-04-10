#!/bin/bash
# System upgrade script with automatic apt source hygiene
# Fixes common warnings/errors before running upgrades.
# All fixes are idempotent and safe to re-run.

set -euo pipefail

log() { printf '[upgrade] %s\n' "$*"; }

# =====================================================================
# Fix 1: Duplicate repository — microsoft-edge.list is a copy of
#        google-chrome.list (both point to dl.google.com/linux/chrome)
# =====================================================================
fix_duplicate_chrome_edge_repo() {
	local edge="/etc/apt/sources.list.d/microsoft-edge.list"

	if [[ ! -f $edge ]]; then
		return
	fi

	# Only act if edge list points to the chrome repo (the known bug)
	if grep -q 'dl.google.com/linux/chrome' "$edge" 2>/dev/null; then
		log "Disabling duplicate microsoft-edge.list (identical to google-chrome.list)"
		mv "$edge" "${edge}.disabled"
	fi
}

# =====================================================================
# Fix 2: Expired Cloudflare WARP GPG key (expired 2025-12-03)
# =====================================================================
fix_cloudflare_key() {
	local keyring="/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg"
	local source_list="/etc/apt/sources.list.d/cloudflare-client.list"

	if [[ ! -f $source_list ]]; then
		return
	fi

	# Check if key is expired
	local expired
	expired=$(gpg --no-default-keyring --keyring "$keyring" --list-keys 2>&1 | grep -c 'expired' || true)

	if [[ ${expired:-0} -gt 0 ]]; then
		log "Refreshing expired Cloudflare WARP GPG key..."
		curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg \
			| gpg --yes --dearmor -o "$keyring" 2>/dev/null \
			&& log "Cloudflare key refreshed." \
			|| log "WARNING: Could not refresh Cloudflare key (network issue?). Skipping."
	fi
}

# =====================================================================
# Fix 3: WineHQ key in legacy trusted.gpg + repo targets focal not noble
# =====================================================================
fix_wine_legacy_key() {
	local legacy_keyring="/etc/apt/trusted.gpg"
	local wine_key_id="D43F640145369C51D786DDEA76F1A20FF987672F"
	local modern_keyring="/usr/share/keyrings/winehq-archive.gpg"

	# Check if wine key is in the legacy keyring
	if ! gpg --no-default-keyring --keyring "$legacy_keyring" --list-keys "$wine_key_id" >/dev/null 2>&1; then
		return
	fi

	log "Migrating WineHQ key from legacy trusted.gpg to modern keyring..."

	# Export key to modern location
	gpg --no-default-keyring --keyring "$legacy_keyring" \
		--export "$wine_key_id" \
		| gpg --yes --dearmor -o "$modern_keyring" 2>/dev/null

	# Remove from legacy keyring (suppress the deprecation warning)
	apt-key del "$wine_key_id" >/dev/null 2>&1 || true

	# Fix the source file to use signed-by and correct distro codename
	local codename
	codename=$(lsb_release -cs 2>/dev/null || echo "noble")

	# Find all wine source files
	for src in /etc/apt/sources.list.d/*wine*.list; do
		[[ -f $src ]] || continue

		# Check if already using signed-by
		if grep -q 'signed-by=' "$src" 2>/dev/null; then
			continue
		fi

		local old_codename
		old_codename=$(grep -oP 'ubuntu/?\s+\K\w+' "$src" | head -1)

		log "Updating $src: ${old_codename:-unknown} → $codename, adding signed-by"
		sed -i \
			-e "s|deb https://|deb [arch=amd64 signed-by=$modern_keyring] https://|" \
			-e "s|deb-src https://|# deb-src [arch=amd64 signed-by=$modern_keyring] https://|" \
			-e "s|ubuntu/ ${old_codename}|ubuntu/ ${codename}|g" \
			-e "s|ubuntu ${old_codename}|ubuntu ${codename}|g" \
			"$src"
	done

	log "WineHQ key migrated and source updated."
}

# =====================================================================
# Run all fixes, then upgrade
# =====================================================================
log "Running apt source hygiene checks..."
fix_duplicate_chrome_edge_repo
fix_cloudflare_key
fix_wine_legacy_key
log "Apt source checks complete."

echo ""
log "Installing aptitude if needed..."
apt-get install -y aptitude

log "Starting system upgrade..."
apt-get -y update && apt-get -y upgrade && apt-get -y dist-upgrade
apt-get -y autoremove
aptitude -y update && aptitude -y safe-upgrade && aptitude -y dist-upgrade

log "Upgrade complete."
