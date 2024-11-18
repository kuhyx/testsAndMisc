#!/bin/sh

sudo mkdir -p /home/packages
sudo mkdir -p /home/sources

sudo chown $USER:$USER /home/packages
chmod 755 /home/packages
sudo chown $USER:$USER /home/sources
chmod 755 /home/sources
yes | sudo pacman -S --needed mold ccache zstd lz4 xz pigz pbzip2 lbzip2  
sudo cp makepkg.conf /etc/
