#!/bin/sh

# Resolve the directory this script lives in and work from there, so every
# relative path below (i3blocks/, i3/) resolves no matter where it is invoked.
SCRIPT_DIR=$(unset CDPATH; cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

# Function to detect if the system is Ubuntu
is_ubuntu() {
	[ -f /etc/os-release ] && grep -qi 'ubuntu' /etc/os-release
}

# Function to detect screen resolution and set font size
set_font_size() {
	width=""
	if command -v xdpyinfo >/dev/null 2>&1; then
		resolution=$(xdpyinfo | grep dimensions | awk '{print $2}')
		width=$(echo "$resolution" | cut -d 'x' -f 1)
	elif command -v xrandr >/dev/null 2>&1; then
		width=$(xrandr --current 2>/dev/null | awk '/\*/ {print $1}' | head -1 | cut -d 'x' -f 1)
	fi
	# Do not change this font size, it actually makes i3blocks unbearable to look at:
	# Icons (like for slack) are too small and i3blocks are too big
	# Network monitor jumping becomes annoying
	if [ -n "$width" ] && [ "$width" -gt 1920 ] 2>/dev/null; then
		echo "8"
	else
		echo "8"
	fi
}

# Check if Intel GPU is detected
if lspci | grep -i 'vga' | grep -i 'intel'; then
	if is_ubuntu; then
		sudo apt-get update
		sudo apt-get install -y intel-gpu-tools
		sudo setcap cap_perfmon+ep /usr/bin/intel_gpu_top
	else
		yes | sudo pacman -S --needed intel-gpu-tools
		sudo setcap cap_perfmon+ep /usr/bin/intel_gpu_top
	fi
fi

if is_ubuntu; then
	sudo apt-get update
	sudo apt-get install -y fonts-dejavu-core fonts-noto fonts-font-awesome bc jq iw pulseaudio-utils
else
	yes | sudo pacman -S --needed ttf-dejavu noto-fonts ttf-font-awesome bc jq iw acpi
fi

# Set font size based on screen resolution
font_size=$(set_font_size)

# Make the i3blocks shell scripts executable (only *.sh — the `config` file
# and any runtime artifacts must stay non-executable).
find i3blocks -type f -name '*.sh' -exec chmod +x {} \;

# Deploy i3blocks by SYMLINKING each repo file into ~/.config/i3blocks rather
# than copying it. A plain `cp -r` here was the source of silent drift: edits
# to a repo script never reached the running copy (and live tweaks never made
# it back to the repo). Symlinks make the repo the single source of truth, so
# editing a repo script IS editing the deployed one — drift becomes impossible.
mkdir -p "$HOME/.config/i3blocks"
for src in "$SCRIPT_DIR"/i3blocks/*; do
	[ -f "$src" ] || continue
	ln -sfn "$src" "$HOME/.config/i3blocks/$(basename "$src")"
done

# i3 config is copied (not symlinked) because it needs a per-machine font-size
# mutation applied below; symlinking would write that change back into the repo.
cp -r i3 ~/.config/
sed -i "s/font pango:System San Francisco Display, FontAwesome [0-9]*/font pango:System San Francisco Display, FontAwesome $font_size/" ~/.config/i3/config
i3-msg reload
