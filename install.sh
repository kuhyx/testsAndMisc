#!/bin/sh
sudo pacman -S --needed ttf-dejavu noto-fonts ttf-font-awesome
cp -r i3blocks ~/.config/
cp -r i3 ~/.config/
i3-msg reload
