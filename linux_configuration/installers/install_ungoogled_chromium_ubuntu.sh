#!/usr/bin/env bash
# Install ungoogled-chromium on Ubuntu/Debian with full uBlock Origin (MV2,
# all filter lists pre-enabled) loaded on every launch.
#
# Why ungoogled-chromium instead of plain chromium/google-chrome: Chromium
# removed Manifest V2 extension support starting with Chromium 138 (the last
# MV2 code paths are gone as of Chromium 151), which breaks full uBlock
# Origin (uBO's full/classic build is MV2-only; the MV3 "uBO Lite" that
# survives the cutoff drops dynamic filter lists and most cosmetic
# filtering). ungoogled-chromium is a Chromium fork whose maintainers
# currently patch the MV2 extension runtime back in — a maintainer-patched
# stopgap, not a permanent guarantee. Re-run this script's uBO seeding step
# (or check the ungoogled-chromium changelog) if a future release drops that
# patch and uBO stops loading.
#
# What this script does:
#   1. Installs ungoogled-chromium from a .deb release (no official Debian/
#      Ubuntu package exists upstream; berkley4/ungoogled-chromium-debian is
#      the community-maintained binary build referenced from
#      ungoogled-software's own binaries index).
#   2. Installs uBlock Origin unpacked via apt (webext-ublock-origin-chromium,
#      Debian/Ubuntu universe) and wires --load-extension so it's always
#      loaded, matching the Arch pacman_wrapper.sh + install_leechblock.sh
#      pattern in this repo (but standalone: no digital-wellbeing blocking
#      layer, no LeechBlock — just the browser + full ad blocker).
#   3. Pre-enables every uBO filter list (not just the out-of-the-box
#      defaults) via seed_ublock_storage.js, the same LevelDB-seeding
#      mechanism seed_leechblock_storage.js already uses in this repo.
#
# Usage:
#   ./install_ungoogled_chromium_ubuntu.sh [--force]
#
# --force re-seeds uBO's filter-list selection even if it looks configured.
#
# Requires: Ubuntu/Debian with apt, sudo, curl, node+npm (for the seeder).
# Must be run while ungoogled-chromium is NOT open (the seeder writes to its
# LevelDB storage directly and a running browser holds it locked).

set -Eeuo pipefail

SCRIPT_NAME=${0##*/}
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
DIGITAL_WELLBEING_DIR="$SCRIPT_DIR/../periodic_background/digital_wellbeing"
SEEDER_SCRIPT="$DIGITAL_WELLBEING_DIR/seed_ublock_storage.js"

UBLOCK_EXT_PATH="/usr/share/chromium/extensions/ublock-origin"
DEB_RELEASE_REPO="berkley4/ungoogled-chromium-debian"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

FORCE=0
for arg in "$@"; do
	case "$arg" in
	--force) FORCE=1 ;;
	--help | -h)
		echo "Usage: $SCRIPT_NAME [--force]"
		echo ""
		echo "  --force  Re-seed uBO's filter-list selection even if already configured."
		exit 0
		;;
	*)
		error "Unknown option: $arg"
		exit 1
		;;
	esac
done

if [[ "$(id -u)" -eq 0 ]]; then
	error "Don't run this as root. It calls sudo itself where needed."
	exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
	error "apt-get not found — this script targets Ubuntu/Debian."
	exit 1
fi

if pgrep -x chrome >/dev/null 2>&1 || pgrep -f "ungoogled-chromium" >/dev/null 2>&1; then
	error "ungoogled-chromium appears to be running. Close it first — the uBO seeding step writes to its LevelDB storage directly and a running browser holds it locked."
	exit 1
fi

# ── 1. Install ungoogled-chromium from the community .deb release ──────
if command -v ungoogled-chromium >/dev/null 2>&1; then
	info "ungoogled-chromium already installed ($(ungoogled-chromium --version 2>/dev/null || echo 'version unknown')) — skipping install."
else
	info "Fetching latest ungoogled-chromium .deb release info from ${DEB_RELEASE_REPO}..."
	RELEASE_JSON=$(curl -fsSL "https://api.github.com/repos/${DEB_RELEASE_REPO}/releases/latest")
	DEB_URL=$(echo "$RELEASE_JSON" | grep -oP '"browser_download_url":\s*"\K[^"]+ungoogled-chromium_[^"]+_amd64\.deb(?=")' | grep -v dbgsym | head -1)
	SANDBOX_URL=$(echo "$RELEASE_JSON" | grep -oP '"browser_download_url":\s*"\K[^"]+ungoogled-chromium-sandbox_[^"]+_amd64\.deb(?=")' | grep -v dbgsym | head -1)

	if [[ -z "$DEB_URL" || -z "$SANDBOX_URL" ]]; then
		error "Could not find expected .deb assets in the latest ${DEB_RELEASE_REPO} release."
		error "Check https://github.com/${DEB_RELEASE_REPO}/releases manually."
		exit 1
	fi

	TMP_DIR="$(mktemp -d)"
	trap 'rm -rf "$TMP_DIR"' EXIT

	info "Downloading $(basename "$DEB_URL")..."
	curl -fsSL -o "$TMP_DIR/chromium.deb" "$DEB_URL"
	info "Downloading $(basename "$SANDBOX_URL")..."
	curl -fsSL -o "$TMP_DIR/sandbox.deb" "$SANDBOX_URL"

	info "Installing via apt (resolves runtime deps automatically)..."
	sudo apt-get update -qq
	sudo apt-get install -y "$TMP_DIR/sandbox.deb" "$TMP_DIR/chromium.deb"

	if ! command -v ungoogled-chromium >/dev/null 2>&1; then
		error "Install finished but 'ungoogled-chromium' is not on PATH — check apt output above."
		exit 1
	fi
	info "✓ ungoogled-chromium installed: $(ungoogled-chromium --version 2>/dev/null || echo 'installed')"
fi

# ── 2. Install uBlock Origin (unpacked, MV2) and wire --load-extension ──
if [[ ! -d "$UBLOCK_EXT_PATH" ]]; then
	info "Installing webext-ublock-origin-chromium (unpacked uBO)..."
	sudo apt-get update -qq
	sudo apt-get install -y webext-ublock-origin-chromium
fi

if [[ ! -d "$UBLOCK_EXT_PATH" ]]; then
	error "webext-ublock-origin-chromium installed but $UBLOCK_EXT_PATH is missing."
	error "Check 'dpkg -L webext-ublock-origin-chromium' for the actual install path and update UBLOCK_EXT_PATH in this script."
	exit 1
fi
info "✓ uBlock Origin unpacked at $UBLOCK_EXT_PATH"

REAL_BIN="$(command -v ungoogled-chromium)"
LOAD_EXT_FLAG="--load-extension=\"$UBLOCK_EXT_PATH\""

if grep -q -- "$LOAD_EXT_FLAG" "$REAL_BIN" 2>/dev/null; then
	info "ungoogled-chromium already wired to load uBlock Origin — skipping."
else
	ORIG_BACKUP="${REAL_BIN}.orig"
	if file "$REAL_BIN" 2>/dev/null | grep -qi 'text\|script'; then
		# Real launcher is a shell script (typical for the chromium-launcher
		# package this .deb depends on) — patch its exec line in place so any
		# custom flags it already applies (GPU workarounds, profile dir, etc.)
		# are preserved rather than bypassed by a wrapper.
		if grep -qE '^exec ' "$REAL_BIN"; then
			info "Patching exec line in $REAL_BIN to add uBlock Origin..."
			if [[ ! -f "$ORIG_BACKUP" ]]; then
				info "Backing up $REAL_BIN → $ORIG_BACKUP"
				sudo cp -a "$REAL_BIN" "$ORIG_BACKUP"
			fi
			sudo sed -i "s|^exec \(.*\) \"\\\$@\"|exec \1 $LOAD_EXT_FLAG \"\\\$@\"|" "$REAL_BIN"
			info "✓ ungoogled-chromium exec line patched with uBlock Origin"
		else
			error "Launcher at $REAL_BIN is a script but has no recognisable 'exec' line — patch it manually."
			exit 1
		fi
	else
		# Real launcher is a compiled binary — wrap it instead of patching.
		info "Wrapping $REAL_BIN with a uBlock Origin loader..."
		if [[ ! -f "$ORIG_BACKUP" ]]; then
			sudo cp -a "$REAL_BIN" "$ORIG_BACKUP"
		fi
		sudo tee "$REAL_BIN" >/dev/null <<WRAP
#!/usr/bin/env bash
# __UBLOCK_WRAPPER__ — auto-generated by install_ungoogled_chromium_ubuntu.sh
# Original backed up at: $ORIG_BACKUP
exec "$ORIG_BACKUP" --load-extension="$UBLOCK_EXT_PATH" "\$@"
WRAP
		sudo chmod +x "$REAL_BIN"
		info "✓ ungoogled-chromium now always launches with uBlock Origin"
	fi
fi

# ── 3. Pre-enable every uBO filter list ─────────────────────────────────
if ! command -v node >/dev/null 2>&1; then
	warn "node not found — installing via apt (needed for the filter-list seeder)."
	sudo apt-get update -qq
	sudo apt-get install -y nodejs npm
fi

if [[ ! -f "$SEEDER_SCRIPT" ]]; then
	error "Seeder script not found at $SEEDER_SCRIPT — is this repo checkout complete?"
	exit 1
fi

if [[ ! -d "$DIGITAL_WELLBEING_DIR/node_modules/classic-level" ]]; then
	info "Installing Node deps for the seeder (classic-level)..."
	npm install --prefix "$DIGITAL_WELLBEING_DIR" 2>&1 | grep -v '^npm warn' || true
fi

info "Launching ungoogled-chromium once to create its profile/extension storage dirs..."
"$REAL_BIN" --headless=new --disable-gpu about:blank >/dev/null 2>&1 &
BROWSER_PID=$!
sleep 4
kill "$BROWSER_PID" 2>/dev/null || true
wait "$BROWSER_PID" 2>/dev/null || true

SEED_ARGS=("--ext-path=$UBLOCK_EXT_PATH")
[[ "$FORCE" -eq 1 ]] && SEED_ARGS+=(--force)
info "Seeding uBlock Origin filter-list selection (all lists)..."
node "$SEEDER_SCRIPT" "${SEED_ARGS[@]}"

cat <<EOF

${GREEN}Done.${NC} ungoogled-chromium is installed with uBlock Origin always loaded
and every filter list selected.

Note: newly-selected 3rd-party filter lists are only marked *selected* by
this seeding step — uBO downloads and compiles their actual content on its
own update cycle (~105s) after the next real launch with network access.
Launch ungoogled-chromium normally once and give it a couple of minutes
before expecting every list to be actively blocking.
EOF
