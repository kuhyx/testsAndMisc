#!/bin/sh

# Function to detect if the system is Ubuntu
is_ubuntu() {
    [ -f /etc/os-release ] && grep -qi 'ubuntu' /etc/os-release
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
    sudo apt-get install -y fonts-dejavu-core fonts-noto fonts-font-awesome bc jq iw
else
    yes | sudo pacman -S --needed ttf-dejavu noto-fonts ttf-font-awesome bc jq iw
fi

cp -r i3blocks ~/.config/
cp -r i3 ~/.config/
i3-msg reload