#!/bin/sh
yes | sudo pacman -S --needed mold ccache zstd lz4 xz pigz pbzip2 lbzip2  
sudo cp makepkg.conf /etc/
