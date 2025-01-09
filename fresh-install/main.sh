#!/bin/sh 
set -e
sudo -v

install_from_aur() {
    if [ ! -d "$HOME/aur" ]; then
        mkdir ~/aur
    fi
    cd ~/aur
    local repo_url=$1
    local pkg_name=$2

    if [ ! -d "$(basename $repo_url .git)" ]; then
        git clone $repo_url
    else
        echo "Repository $(basename $repo_url .git) already cloned"
    fi
    cd $(basename $repo_url .git)
    if ! pacman -Qi $pkg_name > /dev/null 2>&1; then
        makepkg -A -i --nocheck --skipchecksums --skipinteg --skippgpcheck
    else
        echo "$pkg_name is already installed"
    fi
}

# pacman
pacman_packages=(
    distcc
    git
    bluez-utils
    icmake
    yodl
    texlive-plaingeneric
    code
    docbook-xsl
    python-build
    python-installer
    emacs-nox
    pavucontrol
    pbzip2
    lzlib
    re2c
    ninja
    libical
    bluez
    pavucontrol-qt
    mold
    zstd
    lz4
    xz
    pigz
    lbzip2
    doxygen
    graphviz
    tcl
    pngcrush
    gcc-ada
    gcc-d
    ttf-dejavu
    noto-fonts
    ttf-font-awesome
    bc
    acpi
    cargo
)

for pkg in "${pacman_packages[@]}"; do
    if ! pacman -Qi $pkg > /dev/null 2>&1; then
        # Check if the package exists in the AUR packages list
        if ! echo "${aur_packages[@]}" | grep -q "$pkg"; then
            sudo pacman -S --noconfirm $pkg
        else
            echo "$pkg exists in AUR packages, skipping pacman installation"
        fi
    else
        echo "$pkg is already installed"
    fi
done
sudo systemctl enable bluetooth.service
sudo systemctl start bluetooth.service

# omz 




aur_packages=(
    # "https://aur.archlinux.org/glibc-git.git glibc-git"
    "https://aur.archlinux.org/gcc-git.git gcc-git"
    "https://aur.archlinux.org/plzip.git plzip"
    "https://aur.archlinux.org/zsh-git.git zsh"
    "https://aur.archlinux.org/visual-studio-code-bin.git visual-studio-code-bin"
    "https://aur.archlinux.org/asciidoc-git.git asciidoc"
    "https://aur.archlinux.org/xmlto-git.git xmlto"
    "https://aur.archlinux.org/jsoncpp-git.git jsoncpp"
    "https://aur.archlinux.org/libuv-git.git libuv"
    "https://aur.archlinux.org/rhash-git.git rhash"
    "https://aur.archlinux.org/cppdap-git.git cppdap"
    "https://aur.archlinux.org/bluez-git.git bluez-git"
    "https://aur.archlinux.org/lynx-git.git lynx-git"iw
    "https://aur.archlinux.org/pacman-git.git pacman-git"
    # "https://aur.archlinux.org/mold-git.git mold-git"
    "https://aur.archlinux.org/thorium-browser-bin.git thorium-browser"
    "https://aur.archlinux.org/mupdf-git.git mupdf-git"
    "https://aur.archlinux.org/nomacs-git.git nomacs-git"
    "https://aur.archlinux.org/ffmpeg-full-git.git ffmpeg-full-git"
    "https://aur.archlinux.org/mpv-full-git.git mpv-full-git"
    "https://aur.archlinux.org/protontricks-git.git protontricks-git"
    "https://aur.archlinux.org/bottles-git.git bottles-git"
    "https://aur.archlinux.org/proton-ge-custom.git proton-ge-custom"
    "https://aur.archlinux.org/protonup-qt.git protonup-qt"
    "https://aur.archlinux.org/protonhax-git.git protonhax-git"
    "https://aur.archlinux.org/wine-git.git wine-git"
    "https://aur.archlinux.org/msvc-wine-git.git msvc-wine-git"
    "https://aur.archlinux.org/jq-git.git jq-git"
    "https://aur.archlinux.org/iw-git.git iw-git"
)

for pkg in "${aur_packages[@]}"; do
    repo_url=$(echo $pkg | awk '{print $1}')
    pkg_name=$(echo $pkg | awk '{print $2}')
    install_from_aur $repo_url $pkg_name
done

if [ ! -d "$HOME/.oh-my-zsh" ]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
    echo "Oh My Zsh is already installed"
fi

