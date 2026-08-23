#!/usr/bin/env bash

set -euo pipefail

# install_ffmpeg_with_arnndn.sh — helper to install/upgrade FFmpeg with arnndn and full audio filters
#
# Tries distro packages first; if not suitable, offers to build from source.
# This script prints commands and asks for confirmation before building.

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

print_info() {
	echo "[info] $*"
}

detect_distro() {
	if [[ -f /etc/os-release ]]; then
		. /etc/os-release
		echo "${ID:-unknown}"
	else
		echo "unknown"
	fi
}

main() {
	local distro
	distro=$(detect_distro)
	print_info "Detected distro: $distro"

	if has_cmd ffmpeg && ffmpeg -hide_banner -filters | grep -q " arnndn "; then
		print_info "Your ffmpeg already supports arnndn."
	else
		case "$distro" in
		ubuntu | debian)
			print_info "On Ubuntu/Debian, the official repo may lack newer filters. Consider a PPA or build from source."
			echo "Options:"
			echo "  - ppa: sudo add-apt-repository ppa:savoury1/ffmpeg6 && sudo apt update && sudo apt install ffmpeg"
			echo "  - source build (recommended for latest): run this script to build from source"
			;;
		arch | manjaro | endeavouros)
			print_info "On Arch-based distros, ffmpeg is recent. Try: sudo pacman -Syu ffmpeg"
			;;
		fedora)
			print_info "On Fedora, try: sudo dnf install ffmpeg"
			;;
		*)
			print_info "Distro not recognized; will offer source build."
			;;
		esac
	fi

	if ask_yes_no "Build FFmpeg from source with rnnoise/arnndn support now?"; then
		echo "This will clone FFmpeg and build locally under ./ffmpeg-build. Continue?"
		if ! ask_yes_no "Proceed"; then
			exit 0
		fi
		set -x
		mkdir -p ffmpeg-build && cd ffmpeg-build
		# Prepare repository
		if [[ -d FFmpeg ]]; then
			if [[ -d FFmpeg/.git ]]; then
				if ask_yes_no "An existing FFmpeg source directory was found. Reuse and update it?"; then
					set +e
					git -C FFmpeg fetch --all --tags --prune
					git -C FFmpeg pull --rebase --ff-only || true
					set -e
				else
					if ask_yes_no "Delete existing FFmpeg directory and re-clone?"; then
						rm -rf FFmpeg
					else
						echo "Keeping existing FFmpeg directory as-is."
					fi
				fi
			else
				if ask_yes_no "Non-git 'FFmpeg' directory exists. Delete and re-clone?"; then
					rm -rf FFmpeg
				else
					echo "Cannot proceed with a non-git FFmpeg directory present. Aborting."
					exit 4
				fi
			fi
		fi
		# Dependencies
		if [[ $distro == "ubuntu" || $distro == "debian" ]]; then
			sudo apt update
			sudo apt install -y git build-essential yasm nasm pkg-config libx264-dev libx265-dev libvpx-dev libopus-dev libfdk-aac-dev libmp3lame-dev libvorbis-dev libass-dev libfreetype6-dev libgnutls28-dev libaom-dev libdav1d-dev libxvidcore-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev libxcb-shape0-dev libdrm-dev libvulkan-dev libva-dev libvdpau-dev librtmp-dev libunistring-dev libgnutls28-dev libchromaprint-dev libbluray-dev librubberband-dev libspeex-dev libsoxr-dev libvmaf-dev libzimg-dev libsvtav1-dev libtheora-dev libwebp-dev libopenal-dev libjack-jackd2-dev libpulse-dev librnnoise-dev
		elif [[ $distro == "arch" || $distro == "manjaro" || $distro == "endeavouros" ]]; then
			sudo pacman -Syu --needed base-devel yasm nasm pkgconf rnnoise
		elif [[ $distro == "fedora" ]]; then
			sudo dnf install -y git make gcc yasm nasm pkgconf-pkg-config rnnoise-devel libX11-devel libXext-devel libXfixes-devel libXv-devel libXrandr-devel libXi-devel libXtst-devel libXinerama-devel freetype-devel fontconfig-devel libass-devel libvpx-devel libaom-devel libdav1d-devel zimg-devel rubberband-devel soxr-devel libvorbis-devel opus-devel lame-devel
		else
			echo "Note: please ensure rnnoise development headers are installed (pkg-config rnnoise)." >&2
		fi
		if [[ ! -d FFmpeg/.git ]]; then
			git clone https://github.com/FFmpeg/FFmpeg.git --depth=1
		fi
		cd FFmpeg
		RN_FLAG=""
		# Some FFmpeg versions auto-detect rnnoise without a flag; include the flag only if supported
		if ./configure --help | grep -q "librnnoise"; then
			RN_FLAG="--enable-librnnoise"
		else
			echo "[info] configure has no --enable-librnnoise; relying on auto-detection via pkg-config (rnnoise)." >&2
		fi

		./configure \
			--enable-gpl --enable-nonfree \
			--enable-libx264 --enable-libx265 --enable-libvpx --enable-libopus --enable-libmp3lame \
			--enable-libvorbis --enable-libass --enable-fontconfig --enable-libfreetype \
			--enable-librubberband --enable-libsoxr --enable-libzimg --enable-libvmaf \
			--enable-libdav1d --enable-libaom --enable-libsvtav1 \
			${RN_FLAG} \
			--enable-ffplay --enable-ffprobe
		make -j"$(nproc)"
		echo "Build complete. You can run ./ffmpeg-build/FFmpeg/ffmpeg from this folder or 'sudo make install' to install system-wide."
		set +x
	else
		echo "Skipped building from source."
	fi
}

main "$@"
