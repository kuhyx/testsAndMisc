#!/bin/bash
# setup_media_cloud_sync.sh — install the "downloads media → dufs cloud" sync.
#
# Installs systemd units that mirror ~/Downloads images/videos into the dufs
# cloud (unzipped + browsable) so they're viewable from anywhere:
#   • media-cloud-sync.service  (oneshot → sync_media_to_cloud.sh)
#   • media-cloud-sync.timer    (catch-up every 30 min)
#   • media-cloud-sync.path     (immediate, when ~/Downloads changes)
# Plus a drop-in so the existing media-organizer (which zips + deletes Downloads
# for local cold archive) runs AFTER the cloud sync — nothing is deleted before
# the cloud has a copy.
#
# Runs on the dufs host (the PC). Run as your normal user; sudo is used only for
# the system units.

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
readonly HERE
readonly SYNC_SCRIPT="$HERE/sync_media_to_cloud.sh"
RUN_USER="$(id -un)"
readonly RUN_USER
readonly DOWNLOADS="$HOME/Downloads"

C() { printf '\033[1;34m[media-cloud-setup]\033[0m %s\n' "$*"; }
OK() { printf '\033[1;32m  ✓\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[media-cloud-setup] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }
usage() { grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'; exit 0; }

write_unit() {  # write_unit <name> <content-on-stdin>
	sudo tee "/etc/systemd/system/$1" >/dev/null
	OK "wrote /etc/systemd/system/$1"
}

main() {
	[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage
	[[ -x "$SYNC_SCRIPT" ]] || die "missing $SYNC_SCRIPT"

	# fd is the only extra dependency of the sync script.
	if command -v pacman >/dev/null; then
		sudo pacman -S --needed --noconfirm fd >/dev/null
	elif command -v apt-get >/dev/null; then
		sudo apt-get install -y fd-find >/dev/null
	fi
	command -v fd >/dev/null || command -v fdfind >/dev/null || die "fd (fd-find) not installed"
	OK "dependencies present"

	C "Installing systemd units"
	write_unit media-cloud-sync.service <<EOF
[Unit]
Description=Mirror organized downloads media into the dufs cloud (unzipped, browsable)
After=network.target

[Service]
Type=oneshot
User=$RUN_USER
ExecStart=$SYNC_SCRIPT
EOF

	write_unit media-cloud-sync.timer <<EOF
[Unit]
Description=Periodically mirror ~/Downloads media into the dufs cloud

[Timer]
OnBootSec=2min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
EOF

	write_unit media-cloud-sync.path <<EOF
[Unit]
Description=Watch ~/Downloads and mirror new media into the dufs cloud

[Path]
PathModified=$DOWNLOADS
Unit=media-cloud-sync.service

[Install]
WantedBy=multi-user.target
EOF

	# Ordering drop-in: the organizer (zips + deletes Downloads) must run AFTER
	# the cloud sync, so media reaches the cloud before it is pruned locally.
	C "Ordering the existing media-organizer after the cloud sync"
	sudo mkdir -p /etc/systemd/system/media-organizer.service.d
	sudo tee /etc/systemd/system/media-organizer.service.d/10-after-cloud-sync.conf >/dev/null <<EOF
[Unit]
After=media-cloud-sync.service
Wants=media-cloud-sync.service
EOF
	OK "drop-in installed (harmless if media-organizer isn't set up)"

	sudo systemctl daemon-reload
	sudo systemctl enable --now media-cloud-sync.timer media-cloud-sync.path
	OK "timer + path watcher enabled"

	C "Initial sweep (this may take a moment)…"
	"$SYNC_SCRIPT"

	local cloud_root
	cloud_root="$(sed -nE 's/^serve-path:[[:space:]]*//p' "$HOME/.config/dufs/dufs.yaml" 2>/dev/null | head -1)"
	cloud_root="${cloud_root:-$HOME/cloud}"
	cat <<EOF

────────────────────────────────────────────────────────────────────────────
  Done. Your Downloads images/videos are now MOVED into ${cloud_root}/Media/YYYY/MM
  automatically (within ~30 min, or right after Downloads changes) — no
  duplication: the files leave Downloads and live only in the cloud folder.
  Files still downloading (modified in the last 2 min) are left until they settle.
  Browse them at your cloud URL, e.g. https://kuhy-cloud.duckdns.org/Media/
  (Because media is moved out first, organize_downloads.sh no longer zips it —
  the cloud folder is the storage now.)
────────────────────────────────────────────────────────────────────────────
EOF
}

main "$@"
