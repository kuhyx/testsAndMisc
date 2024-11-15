#!/bin/sh
yes | sudo pacman -S --needed ttf-dejavu noto-fonts ttf-font-awesome bc intel-gpu-tools jq iw
sudo setcap cap_perfmon+ep /usr/bin/intel_gpu_top
cp -r i3blocks ~/.config/
cp -r i3 ~/.config/
i3-msg reload
