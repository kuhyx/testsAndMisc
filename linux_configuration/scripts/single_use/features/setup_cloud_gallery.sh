#!/bin/bash
# setup_cloud_gallery.sh — build and deploy the React media-gallery SPA so it
# becomes the UI of the dufs cloud (served same-origin behind the existing auth).
#
# It builds cloud_gallery/ (Vite), copies the static build into the dufs serve
# path, turns on dufs `render-spa`, generates thumbnails, and wires thumbnail
# regeneration into the Phase-2 media sync. Run on the dufs host (the PC).
#
# The SPA lists directories with WebDAV PROPFIND and streams files with GET, so
# it works under render-spa without disturbing the KeePass sync (file GET/PUT/
# ?hash are unaffected — verified).

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
readonly HERE
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
readonly REPO_ROOT
readonly GALLERY_DIR="$REPO_ROOT/cloud_gallery"
readonly THUMBS_SCRIPT="$REPO_ROOT/linux_configuration/scripts/single_use/utils/generate_thumbnails.sh"
readonly DUFS_YAML="$HOME/.config/dufs/dufs.yaml"

C() { printf '\033[1;34m[cloud-gallery]\033[0m %s\n' "$*"; }
OK() { printf '\033[1;32m  ✓\033[0m %s\n' "$*"; }
WARN() { printf '\033[1;33m  !\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[cloud-gallery] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

cloud_root() {
	local sp=""
	[[ -f "$DUFS_YAML" ]] && sp="$(sed -nE 's/^serve-path:[[:space:]]*//p' "$DUFS_YAML" | head -1)"
	printf '%s' "${sp:-$HOME/cloud}"
}

install_deps() {
	C "Installing build + thumbnail dependencies"
	local pkgs=(imagemagick ffmpeg)
	command -v node >/dev/null || pkgs+=(nodejs)
	command -v pnpm >/dev/null || pkgs+=(pnpm)
	command -v fd >/dev/null || pkgs+=(fd)
	if command -v pacman >/dev/null; then
		sudo pacman -S --needed --noconfirm "${pkgs[@]}"
	else
		die "this installer targets the Arch dufs host (pacman)"
	fi
	command -v node >/dev/null || die "node missing after install"
	command -v pnpm >/dev/null || die "pnpm missing after install"
	OK "dependencies present ($(node -v), pnpm $(pnpm -v))"
	command -v ffmpeg >/dev/null && ffmpeg -version >/dev/null 2>&1 \
		|| WARN "ffmpeg is present but not runnable — video posters will be skipped (fix ffmpeg, e.g. full system upgrade)"
}

build_spa() {
	C "Building the gallery (pnpm build)"
	[[ -d "$GALLERY_DIR" ]] || die "missing $GALLERY_DIR"
	(cd "$GALLERY_DIR" && pnpm install --silent && pnpm build)
	[[ -f "$GALLERY_DIR/dist/index.html" ]] || die "build produced no dist/index.html"
	OK "built $GALLERY_DIR/dist"
}

deploy_spa() {
	local root; root="$(cloud_root)"
	C "Deploying the SPA into the cloud root: $root"
	mkdir -p "$root"
	rm -rf "$root/assets"
	cp -r "$GALLERY_DIR/dist/assets" "$root/assets"
	cp -f "$GALLERY_DIR/dist/index.html" "$root/index.html"
	OK "deployed index.html + assets/"
}

enable_render_spa() {
	[[ -f "$DUFS_YAML" ]] || die "dufs config $DUFS_YAML not found — run setup_dufs_cloud.sh first"
	if grep -q '^render-spa:' "$DUFS_YAML"; then
		OK "dufs render-spa already enabled"
	else
		# Insert after the allow-all line so the app shell is served for the UI.
		sed -i '/^allow-all:/a render-spa: true' "$DUFS_YAML"
		OK "enabled render-spa in dufs.yaml"
	fi
	sudo systemctl restart dufs.service
	OK "dufs restarted"
}

wire_thumbnails() {
	C "Generating thumbnails + wiring into media sync"
	bash "$THUMBS_SCRIPT" || WARN "initial thumbnail pass reported problems (continuing)"
	# Regenerate thumbnails after each Phase-2 media sync (best-effort).
	if systemctl is-enabled media-cloud-sync.timer >/dev/null 2>&1 \
		|| systemctl is-active media-cloud-sync.path >/dev/null 2>&1; then
		sudo mkdir -p /etc/systemd/system/media-cloud-sync.service.d
		sudo tee /etc/systemd/system/media-cloud-sync.service.d/10-thumbnails.conf >/dev/null <<EOF
[Service]
ExecStartPost=-$THUMBS_SCRIPT
EOF
		sudo systemctl daemon-reload
		OK "thumbnails will refresh after each media sync"
	else
		WARN "media-cloud-sync not set up — run setup_media_cloud_sync.sh for auto thumbnails"
	fi
}

main() {
	[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] \
		&& { grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'; exit 0; }
	install_deps
	build_spa
	deploy_spa
	enable_render_spa
	wire_thumbnails
	local url="https://kuhy-cloud.duckdns.org"
	cat <<EOF

────────────────────────────────────────────────────────────────────────────
  Cloud gallery deployed. Open ${url}/ (log in with your dufs credentials).
  Browse folders, view images in the lightbox, play videos, upload/download,
  delete, and edit .txt/.md files — all from the browser.
  Rebuild + redeploy anytime by re-running this script.
────────────────────────────────────────────────────────────────────────────
EOF
}

main "$@"
