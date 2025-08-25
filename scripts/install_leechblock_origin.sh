#!/usr/bin/env bash
# Installs LeechBlock NG extension for Chrome/Chromium and/or Firefox
# and fetches/imports LeechBlockOptions.txt from a provided gist.
#
# Chrome/Chromium: enforced install via policy (ExtensionInstallForcelist)
# Firefox: system-wide side-load by placing XPI in distribution/extensions/
# Options: the script downloads LeechBlockOptions.txt to ~/.config/leechblock/
#          and opens the extension options page to let you import the file.

set -Eeuo pipefail

# Globals & flags
VERBOSE=false

GIST_ID="fb2417de59e5b6f295079364a9fb0ae0"
GIST_USER="kuhyx"
OPTIONS_FILENAME="LeechBlockOptions.json"
RAW_GIST_URL="https://gist.githubusercontent.com/${GIST_USER}/${GIST_ID}/raw/${OPTIONS_FILENAME}"

# Chrome Web Store (LeechBlock NG) extension ID
CHROME_EXT_ID="blaaajhemilngeeffpbfkdjjoefldkok"
CHROME_UPDATE_URL="https://clients2.google.com/service/update2/crx"

# Firefox AMO latest XPI (stable pattern)
FF_ADDON_SLUG="leechblock-ng"
FF_LATEST_XPI_URL="https://addons.mozilla.org/firefox/downloads/latest/${FF_ADDON_SLUG}/latest.xpi"
FF_EXTENSION_ID="leechblockng@proginosko.com"

OPTIONS_DIR="$HOME/.config/leechblock"
OPTIONS_PATH="${OPTIONS_DIR}/${OPTIONS_FILENAME}"

bold() { echo -e "\033[1m$*\033[0m"; }
note() { echo -e "[+] $*"; }
warn() { echo -e "[!] $*"; }
err()  { echo -e "[x] $*" 1>&2; }
dbg()  { if [[ "$VERBOSE" == true ]]; then echo -e "[.] $*"; fi }

require_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		err "Required command not found: $1"
		exit 1
	fi
}

need_root() {
	if [[ $EUID -ne 0 ]]; then
		warn "Some steps require root (policies and system install). Requesting sudo..."
		exec sudo --preserve-env=HOME "$0" "$@"
	fi
}

detect_browsers() {
	BROWSERS=()
	# Chromium family
	for bin in google-chrome chromium chromium-browser brave-browser brave vivaldi thorium-browser thorium microsoft-edge microsoft-edge-stable; do
		if command -v "$bin" >/dev/null 2>&1; then BROWSERS+=("$bin"); fi
	done
	# Firefox
	if command -v firefox >/dev/null 2>&1; then BROWSERS+=(firefox); fi
}

parse_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
			-v|--verbose)
				VERBOSE=true
				shift
				;;
			-h|--help)
				cat <<EOF
Usage: $(basename "$0") [--verbose]
Installs LeechBlock NG and downloads/imports options.
	-v, --verbose   More logging
	-h, --help      Show help
EOF
				exit 0
				;;
			--as-root)
				# internal flag for re-exec
				shift
				;;        
			*)
				warn "Unknown argument: $1"
				shift
				;;
		esac
	done
}

resolve_gist_raw_url() {
	# Try multiple candidates; if page parsing works, prefer the exact match
	local page="https://gist.github.com/${GIST_USER}/${GIST_ID}"
	local candidates=()
	candidates+=("${RAW_GIST_URL}")
	candidates+=("https://gist.githubusercontent.com/${GIST_USER}/${GIST_ID}/raw")
	candidates+=("https://gist.github.com/${GIST_USER}/${GIST_ID}/raw/${OPTIONS_FILENAME}")

	# Try to scrape the gist page for an exact raw link
	if command -v curl >/dev/null 2>&1; then
		dbg "Fetching gist page to discover raw link: ${page}"
		local html
		if html=$(curl -fsSL "$page" 2>/dev/null); then
			local link
			# Prefer a link that contains the filename
			link=$(printf '%s' "$html" | grep -oE 'https://gist\.githubusercontent\.com/[^" ]+/raw/[^" ]+' | grep -i "/${OPTIONS_FILENAME}" | head -n1 || true)
			if [[ -z "$link" ]]; then
				# Fallback to any raw link on the page
				link=$(printf '%s' "$html" | grep -oE 'https://gist\.githubusercontent\.com/[^" ]+/raw/[^" ]+' | head -n1 || true)
			fi
			if [[ -n "$link" ]]; then
				candidates=("$link" "${candidates[@]}")
			fi
		else
			dbg "Failed to fetch gist page for discovery; will use default candidates"
		fi
	fi

	printf '%s\n' "${candidates[@]}"
}

download_options() {
	require_cmd curl
	mkdir -p "${OPTIONS_DIR}"
	note "Downloading LeechBlock options to ${OPTIONS_PATH}"

	local urls
	IFS=$'\n' read -r -d '' -a urls < <(resolve_gist_raw_url && printf '\0')

	local ok=false
	for u in "${urls[@]}"; do
		[[ -z "$u" ]] && continue
		note "Attempting: $u"
		local tmp="${OPTIONS_PATH}.tmp"
		# Capture HTTP code while following redirects
		local code
		code=$(curl -sS -L -w '%{http_code}' -o "$tmp" "$u" || true)
		dbg "HTTP code for $u => $code"
		if [[ "$code" == "200" || "$code" == "302" || "$code" == "301" ]]; then
			# If file seems HTML (gist page), skip; otherwise accept
			if file --mime-type "$tmp" 2>/dev/null | grep -q 'text/html'; then
				dbg "Downloaded HTML, not the raw options; trying next candidate"
				continue
			fi
			mv "$tmp" "$OPTIONS_PATH"
			ok=true
			break
		else
			warn "Failed ($code): $u"
		fi
	done

	if [[ "$ok" != true ]]; then
		err "Could not download options from gist. Last tried: ${urls[-1]}"
		exit 1
	fi

	note "Options saved. Size: $(wc -c < "${OPTIONS_PATH}") bytes"
}

install_chrome_policy() {
	local entry
	entry="${CHROME_EXT_ID};${CHROME_UPDATE_URL}"
	local policy_json
	policy_json='{ "ExtensionInstallForcelist": [ '"\"${entry}\""' ] }'

	if command -v google-chrome >/dev/null 2>&1; then
		local dir="/etc/opt/chrome/policies/managed"
		mkdir -p "$dir"
		echo "$policy_json" > "${dir}/leechblock.json"
		note "Chrome policy installed at ${dir}/leechblock.json"
	fi

	# Chromium (Arch uses /etc/chromium)
	if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then
		local dir="/etc/chromium/policies/managed"
		mkdir -p "$dir"
		echo "$policy_json" > "${dir}/leechblock.json"
		note "Chromium policy installed at ${dir}/leechblock.json"
	fi

	note "Chrome/Chromium will fetch LeechBlock NG on next start (or after a minute if running)."
}

	# Generic installer for Chromium-based browsers (per-user, no root):
	# Creates External Extensions JSON in the browser's user config dir.
	install_chromium_external_user() {
		local config_dir="$1"; shift || true
		mkdir -p "${config_dir}/External Extensions"
		local json_path="${config_dir}/External Extensions/${CHROME_EXT_ID}.json"
		echo "{ \"external_update_url\": \"${CHROME_UPDATE_URL}\" }" > "$json_path"
		note "Per-user external extension registered: $json_path"
	}

	# Policy writer for Chromium-based browsers; takes one or more policy directories
	install_chromium_policy_dirs() {
		local entry
		entry="${CHROME_EXT_ID};${CHROME_UPDATE_URL}"
		local policy_json
		policy_json='{ "ExtensionInstallForcelist": [ '"\"${entry}\""' ] }'
		for dir in "$@"; do
			mkdir -p "$dir"
			echo "$policy_json" > "${dir}/leechblock.json"
			note "Policy installed at ${dir}/leechblock.json"
		done
	}

install_firefox_distribution() {
	# Target typical Firefox system distribution directory
	local distro_dir="/usr/lib/firefox/distribution"
	local ext_dir="${distro_dir}/extensions"
	if ! command -v firefox >/dev/null 2>&1; then
		warn "Firefox not detected; skipping Firefox install."
		return 0
	fi

	require_cmd curl
	mkdir -p "$ext_dir"
	local xpi_path="${ext_dir}/${FF_EXTENSION_ID}.xpi"
	note "Downloading Firefox XPI to ${xpi_path}"
	curl -fL --retry 3 --retry-delay 2 "${FF_LATEST_XPI_URL}" -o "${xpi_path}"
	chmod 644 "${xpi_path}"
	note "Firefox will side-load LeechBlock NG from ${xpi_path} on next start."
}

open_import_pages() {
	# Best-effort: open the extension options/import pages to quickly import the downloaded file.
	# Chrome-based: try chrome-extension://<id>/options.html (may vary per version)
	# Fallback: open the store page with guidance.
	if command -v google-chrome >/dev/null 2>&1; then
		(google-chrome "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
	fi
	if command -v chromium >/dev/null 2>&1; then
		(chromium "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
	fi
	if command -v chromium-browser >/dev/null 2>&1; then
		(chromium-browser "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
	fi
		if command -v brave-browser >/dev/null 2>&1; then
			(brave-browser "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi
		if command -v brave >/dev/null 2>&1; then
			(brave "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi
		if command -v vivaldi >/dev/null 2>&1; then
			(vivaldi "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi
		if command -v thorium-browser >/dev/null 2>&1; then
			(thorium-browser "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi
		if command -v thorium >/dev/null 2>&1; then
			(thorium "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi
		if command -v microsoft-edge >/dev/null 2>&1; then
			(microsoft-edge "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi
		if command -v microsoft-edge-stable >/dev/null 2>&1; then
			(microsoft-edge-stable "chrome-extension://${CHROME_EXT_ID}/options.html" >/dev/null 2>&1 || true) &
		fi

	# Firefox: cannot know the moz-extension UUID beforehand; open about:addons
	if command -v firefox >/dev/null 2>&1; then
		(firefox about:addons >/dev/null 2>&1 || true) &
	fi

	cat <<EOF

Next steps to import options (one-time):
1) Locate the saved options at: ${OPTIONS_PATH}
2) In the LeechBlock NG options, go to Import/Export and choose Import from file.
3) Select the ${OPTIONS_FILENAME} and confirm.

If the options page didn't open automatically, you can open:
- Chrome/Chromium: chrome-extension://${CHROME_EXT_ID}/options.html (paste in address bar)
- Firefox: open Add-ons Manager (about:addons) -> LeechBlock NG -> Preferences
EOF
}

main() {
	bold "LeechBlock NG installer"
	parse_args "$@"
	detect_browsers
	if [[ ${#BROWSERS[@]} -eq 0 ]]; then
		warn "No supported browsers detected (Chrome/Chromium/Firefox). Proceeding to download options only."
	else
		note "Detected browsers: ${BROWSERS[*]}"
	fi

	download_options

	# Per-user installs for Chromium-based browsers (works without root)
	if command -v google-chrome >/dev/null 2>&1; then
		install_chromium_external_user "$HOME/.config/google-chrome"
	fi
	if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then
		install_chromium_external_user "$HOME/.config/chromium"
	fi
	if command -v brave-browser >/dev/null 2>&1 || command -v brave >/dev/null 2>&1; then
		install_chromium_external_user "$HOME/.config/BraveSoftware/Brave-Browser"
	fi
	if command -v vivaldi >/dev/null 2>&1; then
		install_chromium_external_user "$HOME/.config/vivaldi"
	fi
	if command -v thorium-browser >/dev/null 2>&1 || command -v thorium >/dev/null 2>&1; then
		install_chromium_external_user "$HOME/.config/thorium-browser"
	fi
	if command -v microsoft-edge >/dev/null 2>&1 || command -v microsoft-edge-stable >/dev/null 2>&1; then
		install_chromium_external_user "$HOME/.config/microsoft-edge"
	fi

	# Elevate for system policy installs if possible
	if [[ $EUID -ne 0 ]]; then
		sudo --preserve-env=HOME "$0" --as-root || warn "Skipping system policy installs (no sudo)."
		# After root part returns, open import pages as user
		open_import_pages
		exit 0
	fi

	# Root section: install policies / side-loads
	# Chrome
	if command -v google-chrome >/dev/null 2>&1; then
		install_chromium_policy_dirs /etc/opt/chrome/policies/managed
	fi
	# Chromium
	if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then
		install_chromium_policy_dirs /etc/chromium/policies/managed
	fi
	# Brave (try common paths)
	if command -v brave-browser >/dev/null 2>&1 || command -v brave >/dev/null 2>&1; then
		install_chromium_policy_dirs /etc/opt/brave/policies/managed /etc/brave/policies/managed
	fi
	# Vivaldi
	if command -v vivaldi >/dev/null 2>&1; then
		install_chromium_policy_dirs /etc/opt/vivaldi/policies/managed /etc/vivaldi/policies/managed
	fi
	# Thorium
	if command -v thorium-browser >/dev/null 2>&1 || command -v thorium >/dev/null 2>&1; then
		install_chromium_policy_dirs /etc/opt/thorium/policies/managed /etc/thorium/policies/managed
	fi
	# Edge (optional; best effort)
	if command -v microsoft-edge >/dev/null 2>&1 || command -v microsoft-edge-stable >/dev/null 2>&1; then
		install_chromium_policy_dirs /etc/opt/edge/policies/managed /etc/edge/policies/managed
	fi
	if command -v firefox >/dev/null 2>&1; then
		install_firefox_distribution
	fi

	note "Root tasks done. Returning to user session to open import pages..."
}

if [[ "${1:-}" == "--as-root" ]]; then
	shift || true
	# Now running as root (from re-exec)
	if command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then
		# Handled per browser in --as-root main block; keep for backward compat
		install_chromium_policy_dirs /etc/opt/chrome/policies/managed /etc/chromium/policies/managed
	fi
	if command -v firefox >/dev/null 2>&1; then
		install_firefox_distribution
	fi
	exit 0
fi

main "$@"

