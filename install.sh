#!/bin/sh

# Check if Intel GPU is detected
if lspci | grep -i 'vga' | grep -i 'intel'; then
    yes | sudo pacman -S --needed intel-gpu-tools
    sudo setcap cap_perfmon+ep /usr/bin/intel_gpu_top
fi

yes | sudo pacman -S --needed ttf-dejavu noto-fonts ttf-font-awesome bc jq iw
cp -r i3blocks ~/.config/
cp -r i3 ~/.config/
i3-msg reload