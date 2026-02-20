#!/bin/sh

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

# Make all scripts in i3blocks executable
find i3blocks -type f -exec chmod +x {} \;
cp -r i3blocks ~/.config/
cp -r i3 ~/.config/
sed -i "s/font pango:System San Francisco Display, FontAwesome [0-9]*/font pango:System San Francisco Display, FontAwesome $font_size/" ~/.config/i3/config
i3-msg reload
