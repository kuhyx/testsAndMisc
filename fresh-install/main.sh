#!/bin/sh 
set -e

# Function to play a sound on error
play_error_sound() {
    #pactl set-sink-volume @DEFAULT_SINK@ +50%
    for i in 1 2 3; do
        paplay /usr/share/sounds/freedesktop/stereo/dialog-error.oga
    done
    #pactl set-sink-volume @DEFAULT_SINK@ -50%
}

# Trap errors and call the play_error_sound function
trap 'play_error_sound' ERR


sudo -v
git config --global init.defaultBranch main

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
        yes | makepkg -s --nocheck --skipchecksums --skipinteg --skippgpcheck --noconfirm --needed
        yes | sudo pacman -U  *.pkg.tar.zst
    else
        echo "$pkg_name is already installed"
    fi
}

process_packages() {
    local file_path=$1
    > failed.txt
    > done.txt

    while IFS= read -r pkg_name; do
        if [ -z "$pkg_name" ]; then
            continue
        fi

        local repo_url="https://aur.archlinux.org/${pkg_name}-git.git"
        local repo_dir="${pkg_name}-git"

        git clone $repo_url
        if [ -d "$repo_dir" ] && [ -z "$(ls -A $repo_dir)" ]; then
            echo "Repository $repo_dir is empty, trying without -git suffix"
            repo_url="https://aur.archlinux.org/${pkg_name}.git"
            repo_dir="${pkg_name}"

            git clone $repo_url
            if [ -d "$repo_dir" ] && [ -z "$(ls -A $repo_dir)" ]; then
                echo "Repository $repo_dir is empty, trying to install with pacman"
                if sudo pacman -Sy --noconfirm $pkg_name; then
                    echo "$pkg_name" >> done.txt
                else
                    echo "$pkg_name" >> failed.txt
                fi
            else
                if install_from_aur $repo_url $pkg_name; then
                    echo "$pkg_name" >> done.txt
                else
                    echo "$pkg_name" >> failed.txt
                fi
            fi
        else
            if install_from_aur $repo_url $pkg_name; then
                echo "$pkg_name" >> done.txt
            else
                echo "$pkg_name" >> failed.txt
            fi
        fi
    done < "$file_path"
}

sudo cp /etc/makepkg.conf /etc/makepkg.conf.bak
sudo cp ./makepkg.conf /etc/makepkg.conf
sudo cp /etc/pacman.conf /etc/pacman.conf.bak
sudo cp ./pacman.conf /etc/pacman.conf
# sudo cp /etc/mkinitcpio.conf /etc/mkinitcpio.conf.bak
# sudo cp ./mkinitcpio.conf /etc/mkinitcpio.conf
# mkinitcpio -P

# pacman
pacman_packages=(
    linux
    distcc
    git
    bluez
    bluez-utils
    icmake
    yodl
    texlive-plaingeneric
    code
    docbook-xsl
    glu
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
    freeglut
    texlive-latexextra
    biber
    texlive-bibtexextra
    texlive-pictures
    texlive-fontsextra
    texlive-formatsextra
    texlive-pstricks
    texlive-games
    texlive-humanities
    texlive-science
    node-gyp
    plantuml
    npm
    ruby-ronn
    go-tools
    asciidoctor
    man-db
    git-lfs
    nodejs
    electron
    yarn
    openssl-1.1
    tk
    jasper
    libdc1394
    cblas
    pegtl
    hdf5
    proj
    gcc-fortran
    python-nose
    python-pyproject-metadata
    meson-python
    lapack
    python-numpy
    openmpi
    boost
    suitesparse
    vtk
    junit
    java-hamcrest
    ant
    chrpath
    source-highlight
    gdb
    python-markdown
    gtk-doc
    gobject-introspection
    cdparanoia
    adobe-source-sans-pro-fonts
    perl-font-ttf
    perl-sort-versions
    ttf-liberation
    aalib
    libcaca
    libdv
    qt5-wayland
    qt6-tools
    qt6-shadertools
    gst-plugins-base
    libgphoto2
    lapacke
    opencv
    cuda
    vulkan-validation-layers
    libltc
    libavtp
    libmpcdec
    neon
    soundtouch
    wildmidi
    gtk2
    ghostpcl
    ghostxps
    liblqr
    djvulibre
    imagemagick
    zbar
    wpewebkit
    openh264
    libmpeg2
    ladspa
    check
    lirc
    rtkit
    xmltoman
    python-pyqt5
    smbclient
    libomxil-bellagio
    rhash
    avisynthplus
    librist
    expac
    gn
    gperf
    lld
    lldb
    ocaml
    ocaml-ctypes
    python-pyparsing
    ffmpeg
    lua52
    cabextract
    mingw-w64-gcc
    lib32-gst-plugins-base-libs
    lib32-gnutls
    lib32-gmp
    lib32-libcups
    lib32-libpulse
    lib32-libxcomposite
    lib32-libxinerama
    lib32-opencl-icd-loader
    lib32-pcsclite
    lib32-sdl2
    lib32-v4l-utils
    samba
    lib32-attr
    lib32-libvpx
    libsoup
    lib32-libsoup
    lib32-speex
    steam-native-runtime
    fontforge
    python-pefile
    glib2-devel
    lib32-gtk3
    rust
    lib32-rust-libs
    python-booleanoperations
    python-brotli
    python-defcon
    python-fontmath
    python-fontpens
    python-fonttools
    python-fs
    python-tqdm
    python-ufoprocessor
    python-unicodedata2
    python-zopfli
    afdko
    pyside6
    python-pyaml
    python-zstandard
    zip
    virtualbox
    virtualbox-guest-iso
    virtualbox-ext-vnc
    imath
    embree
    # https://wiki.archlinux.org/title/Java#OpenJDK
    jdk-openjdk
    openjdk-doc
    openjdk-src
    libharu
    openxr
    opencolorio
    openimageio
    openvdb
    # for unreal engine
    lttng-ust2.12
    opensubdiv
    openshadinglanguage
    blender
    p7zip
    udftools
    dotnet-runtime
    dotnet-sdk
    godot
    joyutils
    gparted
    nvidia-open 
    nvidia-utils
    lib32-nvidia-utils
    xorg-xinput
    glew
    mangohud
    lib32-mangohud
    pcmanfm-gtk3
    # https://wiki.archlinux.org/title/File_manager_functionality#File_managers_other_than_Dolphin_and_Konqueror
    tumbler
    ffmpegthumbnailer
    webp-pixbuf-loader
    poppler-glib
    freetype2
    libgsf
    totem
    evince
    gnome-epub-thumbnailer
    f3d
    python-dbus-next
    python-parse
    python-systemd
    python-colorlog
    zsh
    keepassxc
    # https://wiki.archlinux.org/title/TeX_Live
    ghostscript
    perl
    ruby
    texlive
    texlive-basic
    texlive-latex
    texlive-latexrecommended
    texlive-latexextra
    texlive-fontsrecommended
    texlive-fontsextra
    texlive-xetex
    texlive-luatex
    texlive-bibtexextra 
    texlive-mathscience
    texlive-lang
    perl-yaml-tiny
    perl-file-homedir
    texlive-binextra
    texlive-plaingeneric
    )

for pkg in "${pacman_packages[@]}"; do
    if ! pacman -Qi $pkg > /dev/null 2>&1; then
        # Check if the package exists in the AUR packages list
        if ! echo "${aur_packages[@]}" | grep -q "$pkg"; then
            yes | sudo pacman -Sy --noconfirm $pkg
        else        
            echo "$pkg exists in AUR packages, skipping pacman installation"
        fi
    else
        echo "$pkg is already installed"
    fi
done
if ! command -v nvm &> /dev/null; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
else
    echo "nvm is already installed"
fi
export NVM_DIR=$HOME/.nvm;
source $NVM_DIR/nvm.sh;
nvm i v18.20.5
sudo systemctl enable bluetooth.service
sudo systemctl start bluetooth.service
aur_packages=(
    "https://aur.archlinux.org/visual-studio-code-bin.git visual-studio-code-bin"
    "https://aur.archlinux.org/thorium-browser-bin.git thorium-browser-bin"
    "https://aur.archlinux.org/mkinitcpio-git.git mkinitcpio-git"
    "https://aur.archlinux.org/yay-git.git yay-git"
    # "https://aur.archlinux.org/qdirstat-git.git qdirstat-git"
    # "https://aur.archlinux.org/qdirstat.git qdirstat"
    # "https://aur.archlinux.org/expac-git.git expac-git"
    # "https://aur.archlinux.org/gn-git.git gn-git"
    # "https://aur.archlinux.org/gperf-git.git gperf-git"
    "https://aur.archlinux.org/http-parser-git.git http-parser-git"
    # "https://aur.archlinux.org/python-recommonmark.git python-recommonmark"
    # "https://aur.archlinux.org/lldb-git.git lldb-git"
    # "https://aur.archlinux.org/ocaml-ctypes-git.git ocaml-ctypes-git"
    # "https://aur.archlinux.org/swig-git.git swig-git"
    #"https://aur.archlinux.org/z3-git.git z3-git"

    # "https://aur.archlinux.org/llvm-git.git     llvm-git"
    "https://aur.archlinux.org/python310.git python310"
    # "https://aur.archlinux.org/nodejs-lts-hydrogen.git nodejs-lts-hydrogen"
    # "https://aur.archlinux.org/electron25.git electron25"
    # "https://aur.archlinux.org/openvino.git openvino"
    "https://aur.archlinux.org/slack-electron.git slack-electron"
    "https://aur.archlinux.org/bash-completion-git.git bash-completion-git"
    # "https://aur.archlinux.org/glew-git.git glew-git"
    "https://aur.archlinux.org/libaec-git.git libaec-git"
    # "https://aur.archlinux.org/hdf5-git.git hdf5-git"
    # "https://aur.archlinux.org/packages/proj-git.git proj-git"
    "https://aur.archlinux.org/pugixml-git.git  pugixml-git"
    "https://aur.archlinux.org/gl2ps-git.git gl2ps-git"
    # "https://aur.archlinux.org/lapack-git.git lapack-git"
    "https://aur.archlinux.org/cython-git.git cython-git"
    "https://aur.archlinux.org/patchelf-git.git patchelf-git"
    # "https://aur.archlinux.org/python-numpy-git.git python-numpy-git"
    # "https://aur.archlinux.org/numactl-git.git numactl-git"
    # "https://aur.archlinux.org/openmpi-git.git openmpi-git"
    # "https://aur.archlinux.org/boost-git.git boost-git"
    "https://aur.archlinux.org/utf8cpp-git.git utf8cpp-git"
    "https://aur.archlinux.org/eigen-git.git eigen-git"
    # "https://aur.archlinux.org/vtk-git.git vtk-git"
    # "https://aur.archlinux.org/ant-git.git ant-git"
    # "https://aur.archlinux.org/chrpath-git.git chrpath-git"
    "https://aur.archlinux.org/openexr-git.git openexr-git"

    # "https://aur.archlinux.org/gdb-git.git gdb-git"
     "https://aur.archlinux.org/valgrind-git.git valgrind-git"
    # "https://aur.archlinux.org/gobject-introspection-git.git gobject-introspection-git"
    # "https://aur.archlinux.org/cdparanoia-git.git cdparanoia-git"
    "https://aur.archlinux.org/sdl12-compat-git.git sdl12-compat-git"
    "https://aur.archlinux.org/libvisual.git libvisual"
    "https://aur.archlinux.org/wayland-protocols-git.git wayland-protocols-git"
    "https://aur.archlinux.org/libtremor-git.git libtremor-git"    

    # "https://aur.archlinux.org/qt5-wayland-git.git qt5-wayland-git"
    "https://aur.archlinux.org/libshout-git.git libshout-git"
    "https://aur.archlinux.org/taglib-git.git taglib-git"
    "https://aur.archlinux.org/twolame-git.git twolame-git"
    "https://aur.archlinux.org/wavpack-git.git wavpack-git"
    # "https://aur.archlinux.org/qt6-tools-git.git qt6-tools-git"
    "https://aur.archlinux.org/autoconf-archive-git.git autoconf-archive-git"

    # "https://aur.archlinux.org/libgphoto2-git.git libgphoto2-git"
    # "https://aur.archlinux.org/protobuf-git.git protobuf-git"
    # "https://aur.archlinux.org/lapacke-git.git lapacke-git"
    "https://aur.archlinux.org/vulkan-utility-libraries-git.git vulkan-utility-libraries-git"
    # "https://aur.archlinux.org/vulkan-validation-layers-git.git vulkan-validation-layers-git"
    # "https://aur.archlinux.org/cuda-git.git cuda-git"
    # "https://aur.archlinux.org/libltc-git.git libltc-git"
    # "https://aur.archlinux.org/libavtp-git.git libavtp-git"
    "https://aur.archlinux.org/chromaprint-git.git chromaprint-git"
    "https://aur.archlinux.org/libdca-git.git libdca-git"
    # "https://aur.archlinux.org/libmpcdec-git.git libmpcdec-git"
    # "https://aur.archlinux.org/neon-git.git neon-git"
    "https://aur.archlinux.org/rtmpdump-git.git rtmpdump-git"
    # "https://aur.archlinux.org/soundtouch-git.git soundtouch-git"
    
    "https://aur.archlinux.org/spandsp-git.git spandsp-git"
    "https://aur.archlinux.org/libsrtp-git.git libsrtp-git"
    "https://aur.archlinux.org/yasm-git.git yasm-git"
    "https://aur.archlinux.org/svt-hevc-git.git svt-hevc-git"
    "https://aur.archlinux.org/zvbi-git.git zvbi-git"
    # "https://aur.archlinux.org/wildmidi-git.git wildmidi-git"
    "https://aur.archlinux.org/zxing-cpp-git.git zxing-cpp-git"
    "https://aur.archlinux.org/libwmf-git.git libwmf-git"
    "https://aur.archlinux.org/opencl-headers-git.git opencl-headers-git"
    "https://aur.archlinux.org/libzip-git.git libzip-git"
    # "https://aur.archlinux.org/ghostpcl-git.git ghostpcl-git"
    # "https://aur.archlinux.org/ghostxps-git.git ghostxps-git"
    # "https://aur.archlinux.org/liblqr-git.git liblqr-git"
    # "https://aur.archlinux.org/djvulibre-git.git djvulibre-git"

    # "https://aur.archlinux.org/imagemagick-git.git imagemagick-git"

    # "https://aur.archlinux.org/zbar-git.git zbar-git"
    # "https://aur.archlinux.org/wpewebkit-git.git wpewebkit-git"
    "https://aur.archlinux.org/vo-aacenc.git vo-aacenc"
    "https://aur.archlinux.org/a52dec-git.git a52dec-git"
    # "https://aur.archlinux.org/libmpeg2-git.git libmpeg2-git"
    "https://aur.archlinux.org/frei0r-plugins-git.git frei0r-plugins-git"
    # "https://aur.archlinux.org/ladspa-git.git ladspa-git"
    "https://aur.archlinux.org/celt-git.git celt-git"
    "https://aur.archlinux.org/libgme-git.git libgme-git"
    "https://aur.archlinux.org/libwrap.git libwrap"
    "https://aur.archlinux.org/rtmpdump-git.git rtmpdump-git"
    # "https://aur.archlinux.org/smbclient-git.git smbclient-git"
    "https://aur.archlinux.org/twolame-git.git twolame-git"
    "https://aur.archlinux.org/wavpack-git.git wavpack-git"
    "https://aur.archlinux.org/zvbi-git.git zvbi-git"
    "https://aur.archlinux.org/sndio-git.git sndio-git"
    "https://aur.archlinux.org/codec2-git.git codec2-git"
    # "https://aur.archlinux.org/flite1.git flite1"
    # "https://aur.archlinux.org/libilbc-git.git libilbc-git"
    "https://aur.archlinux.org/kvazaar-git.git kvazaar-git"
    "https://aur.archlinux.org/shine-git.git shine-git"
    "https://aur.archlinux.org/vo-amrwbenc.git vo-amrwbenc"
    "https://aur.archlinux.org/xavs.git xavs"
    "https://aur.archlinux.org/ndi-sdk.git ndi-sdk"
    "https://aur.archlinux.org/rockchip-mpp.git rockchip-mpp"
    "https://aur.archlinux.org/bash-completion-git.git bash-completion-git"
    "https://aur.archlinux.org/libaec-git.git libaec-git"
    # "https://aur.archlinux.org/hdf5-git.git hdf5-git"
    # "https://aur.archlinux.org/packages/proj-git.git proj-git"
    "https://aur.archlinux.org/pugixml-git.git  pugixml-git"
    "https://aur.archlinux.org/gl2ps-git.git gl2ps-git"
    # "https://aur.archlinux.org/lapack-git.git lapack-git"
    "https://aur.archlinux.org/cython-git.git cython-git"
    "https://aur.archlinux.org/patchelf-git.git patchelf-git"
    # "https://aur.archlinux.org/python-numpy-git.git python-numpy-git"
    # "https://aur.archlinux.org/openmpi-git.git openmpi-git"
    # "https://aur.archlinux.org/boost-git.git boost-git"
    "https://aur.archlinux.org/utf8cpp-git.git utf8cpp-git"
    "https://aur.archlinux.org/eigen-git.git eigen-git"
    # "https://aur.archlinux.org/vtk-git.git vtk-git"
    # "https://aur.archlinux.org/ant-git.git ant-git"
    # "https://aur.archlinux.org/chrpath-git.git chrpath-git"
    "https://aur.archlinux.org/openexr-git.git openexr-git"

    # "https://aur.archlinux.org/gdb-git.git gdb-git"
     "https://aur.archlinux.org/valgrind-git.git valgrind-git"
    # "https://aur.archlinux.org/gobject-introspection-git.git gobject-introspection-git"
    # "https://aur.archlinux.org/cdparanoia-git.git cdparanoia-git"
    "https://aur.archlinux.org/sdl12-compat-git.git sdl12-compat-git"
    "https://aur.archlinux.org/libvisual.git libvisual"
    "https://aur.archlinux.org/qt5-tools-git.git qt5-tools-git"
    "https://aur.archlinux.org/wayland-protocols-git.git wayland-protocols-git"
    "https://aur.archlinux.org/libtremor-git.git libtremor-git"
    "https://aur.archlinux.org/nasm-git.git nasm-git"
    # "https://aur.archlinux.org/aalib-git.git aalib-git"
    # "https://aur.archlinux.org/libcaca-git.git libcaca-git"
    #"https://aur.archlinux.org/libdv-git.git libdv-git"
    # "https://aur.archlinux.org/qt5-declarative-git.git qt5-declarative-git"
    # "https://aur.archlinux.org/qt5-wayland-git.git qt5-wayland-git"
    "https://aur.archlinux.org/libshout-git.git libshout-git"
    "https://aur.archlinux.org/taglib-git.git taglib-git"
    "https://aur.archlinux.org/twolame-git.git twolame-git"
    "https://aur.archlinux.org/wavpack-git.git wavpack-git"
    # "https://aur.archlinux.org/qt6-tools-git.git qt6-tools-git"
    # "https://aur.archlinux.org/qt6-shadertools-git.git qt6-shadertools-git"
    "https://aur.archlinux.org/autoconf-archive-git.git autoconf-archive-git"

    # "https://aur.archlinux.org/libgphoto2-git.git libgphoto2-git"
    # "https://aur.archlinux.org/lapacke-git.git lapacke-git"
    "https://aur.archlinux.org/vulkan-utility-libraries-git.git vulkan-utility-libraries-git"
    # "https://aur.archlinux.org/vulkan-validation-layers-git.git vulkan-validation-layers-git"
    # "https://aur.archlinux.org/cuda-git.git cuda-git"
    # "https://aur.archlinux.org/libltc-git.git libltc-git"
    # "https://aur.archlinux.org/libavtp-git.git libavtp-git"
    "https://aur.archlinux.org/chromaprint-git.git chromaprint-git"
    "https://aur.archlinux.org/libdca-git.git libdca-git"
    # "https://aur.archlinux.org/libmpcdec-git.git libmpcdec-git"
    # "https://aur.archlinux.org/neon-git.git neon-git"
    "https://aur.archlinux.org/rtmpdump-git.git rtmpdump-git"
    # "https://aur.archlinux.org/soundtouch-git.git soundtouch-git"
    
    "https://aur.archlinux.org/spandsp-git.git spandsp-git"
    "https://aur.archlinux.org/libsrtp-git.git libsrtp-git"
    "https://aur.archlinux.org/yasm-git.git yasm-git"
    "https://aur.archlinux.org/svt-hevc-git.git svt-hevc-git"
    "https://aur.archlinux.org/zvbi-git.git zvbi-git"
    # "https://aur.archlinux.org/wildmidi-git.git wildmidi-git"
    "https://aur.archlinux.org/zxing-cpp-git.git zxing-cpp-git"
    "https://aur.archlinux.org/libwmf-git.git libwmf-git"
    "https://aur.archlinux.org/opencl-headers-git.git opencl-headers-git"
    "https://aur.archlinux.org/libzip-git.git libzip-git"
    # "https://aur.archlinux.org/ghostpcl-git.git ghostpcl-git"
    # "https://aur.archlinux.org/ghostxps-git.git ghostxps-git"
    # "https://aur.archlinux.org/liblqr-git.git liblqr-git"
    # "https://aur.archlinux.org/djvulibre-git.git djvulibre-git"

    # "https://aur.archlinux.org/imagemagick-git.git imagemagick-git"

    # "https://aur.archlinux.org/zbar-git.git zbar-git"
    # "https://aur.archlinux.org/wpewebkit-git.git wpewebkit-git"
    "https://aur.archlinux.org/vo-aacenc.git vo-aacenc"
    "https://aur.archlinux.org/a52dec-git.git a52dec-git"
    # "https://aur.archlinux.org/libmpeg2-git.git libmpeg2-git"
    "https://aur.archlinux.org/frei0r-plugins-git.git frei0r-plugins-git"
    # "https://aur.archlinux.org/ladspa-git.git ladspa-git"
    "https://aur.archlinux.org/celt-git.git celt-git"
    "https://aur.archlinux.org/libgme-git.git libgme-git"
    "https://aur.archlinux.org/libwrap.git libwrap"
    "https://aur.archlinux.org/rtmpdump-git.git rtmpdump-git"
    # "https://aur.archlinux.org/smbclient-git.git smbclient-git"
    "https://aur.archlinux.org/twolame-git.git twolame-git"
    "https://aur.archlinux.org/wavpack-git.git wavpack-git"
    "https://aur.archlinux.org/zvbi-git.git zvbi-git"
    "https://aur.archlinux.org/sndio-git.git sndio-git"
    "https://aur.archlinux.org/codec2-git.git codec2-git"
    "https://aur.archlinux.org/flite1.git flite1"
    # "https://aur.archlinux.org/glibc-git.git glibc-git"
    # "https://aur.archlinux.org/gcc-git.git gcc-git"
    "https://aur.archlinux.org/plzip.git plzip"
    "https://aur.archlinux.org/zsh-git.git zsh"
    "https://aur.archlinux.org/asciidoc-git.git asciidoc"
    "https://aur.archlinux.org/xmlto-git.git xmlto"
    "https://aur.archlinux.org/jsoncpp-git.git jsoncpp"
    "https://aur.archlinux.org/libuv-git.git libuv"
    "https://aur.archlinux.org/cppdap-git.git cppdap"
    # "https://aur.archlinux.org/bluez-git.git bluez-git"
    "https://aur.archlinux.org/lynx-git.git lynx-git"
    "https://aur.archlinux.org/pacman-git.git pacman-git"
    # "https://aur.archlinux.org/mold-git.git mold-git"
    "https://aur.archlinux.org/glu-git.git glu-git"
    "https://aur.archlinux.org/mupdf-git.git mupdf-git"
    # "https://aur.archlinux.org/exiv2-git.git exiv2-git"
    "https://aur.archlinux.org/libraw-git.git libraw-git"
    "https://aur.archlinux.org/nomacs-git.git nomacs-git"
    "https://aur.archlinux.org/aribb24-git.git aribb24-git"
    # "https://aur.archlinux.org/avisynthplus-git.git avisynthplus-git"
   #  "https://aur.archlinux.org/lcevcdec.git lcevcdec"
    "https://aur.archlinux.org/lensfun-git.git lensfun-git"
    # "https://aur.archlinux.org/python-librabbitmq.git python-librabbitmq"
   # "https://aur.archlinux.org/librist-git.git librist-git"
    "https://aur.archlinux.org/quirc-git.git quirc-git"
    "https://aur.archlinux.org/svt-vp9-git.git svt-vp9-git"
    "https://aur.archlinux.org/davs2-git.git davs2-git"
    "https://aur.archlinux.org/libaribcaption-git.git libaribcaption-git"
    "https://aur.archlinux.org/libklvanc-git.git libklvanc-git"
    "https://aur.archlinux.org/uavs3d-git.git uavs3d-git"
    # "https://aur.archlinux.org/vvenc-git.git vvenc-git"
    "https://aur.archlinux.org/xavs2-git.git xavs2-git"
    "https://aur.archlinux.org/xevd.git xevd"
    "https://aur.archlinux.org/xeve.git xeve"
    "https://aur.archlinux.org/amf-headers-git.git amf-headers-git"
    #"https://aur.archlinux.org/ffmpeg-git.git ffmpeg-git"
    #"https://aur.archlinux.org/mpv-full-git.git mpv-full-git"
    # "https://aur.archlinux.org/mpv-git.git mpv-git"
    "https://aur.archlinux.org/unzrip-git.git unzrip-git"
    "https://aur.archlinux.org/python-vdf.git python-vdf"   
    "https://aur.archlinux.org/lib32-gmp-hg.git lib32-gmp"
    "https://aur.archlinux.org/sane-git.git sane-git"
    #"https://aur.archlinux.org/lib32-sdl2-git.git lib32-sdl2-git"
    "https://aur.archlinux.org/unixodbc-git.git unixodbc-git"
    # "https://aur.archlinux.org/wine-git.git wine-git"
    "https://aur.archlinux.org/winetricks-git.git winetricks-git"
    "https://aur.archlinux.org/protontricks-git.git protontricks-git"
    "https://aur.archlinux.org/lib32-lzo.git lib32-lzo"
    "https://aur.archlinux.org/mingw-w64-tools.git mingw-w64-tools"
    "https://aur.archlinux.org/python-ufonormalizer.git python-ufonormalizer"
    "https://aur.archlinux.org/python-cu2qu.git python-cu2qu"
    "https://aur.archlinux.org/psautohint.git psautohint"
    # "https://aur.archlinux.org/proton-ge-custom-bin.git proton-ge-custom-bin"
    "https://aur.archlinux.org/python-inputs.git python-inputs"
    "https://aur.archlinux.org/python-steam.git python-steam"
    "https://aur.archlinux.org/protonup-qt.git protonup-qt"
    "https://aur.archlinux.org/protonhax-git.git protonhax-git"
    # "https://aur.archlinux.org/msvc-wine-git.git msvc-wine-git"
    "https://aur.archlinux.org/deluge-git.git deluge-git"
    "https://aur.archlinux.org/nvm-git.git nvm-git"
    "https://aur.archlinux.org/unityhub.git unityhub"
    # "https://aur.archlinux.org/unityhub-beta.git unityhub-beta"
    # "https://aur.archlinux.org/keepassxc-git.git keepassxc-git"
    #"https://aur.archlinux.org/nvidia-open-git.git nvidia-open-git"
    "https://aur.archlinux.org/autorandr-git.git autorandr-git"
    "https://aur.archlinux.org/xorg-xrandr-git.git xorg-xrandr-git"
    "https://aur.archlinux.org/mpv-plugin-xrandr.git mpv-plugin-xrandr"

    # "https://aur.archlinux.org/alembic-git.git alembic-git"
    # "https://aur.archlinux.org/embree-git.git embree-git"
    # "https://aur.archlinux.org/opencolorio-git.git opencolorio-git"
    #"https://aur.archlinux.org/openimageio-git.git openimageio-git"
    #"https://aur.archlinux.org/opencollada.git opencollada"
    "https://aur.archlinux.org/libdecor-git.git libdecor-git"
    # https://wiki.archlinux.org/title/Microsoft_fonts
    "https://aur.archlinux.org/httpfs2-2gbplus.git  httpfs2-2gbplus"
    "https://aur.archlinux.org/ttf-ms-win10-auto.git ttf-ms-win10-auto"
    # "https://aur.archlinux.org/httpdirfs-git. git httpdirfs-git"
    # "https://aur.archlinux.org/godot-git.git godot-git"
    "https://aur.archlinux.org/icu63.git icu63"
    "https://aur.archlinux.org/github-cli-git.git github-cli-git"
    "https://aur.archlinux.org/github-copilot-cli.git github-copilot-cli"
    # "https://aur.archlinux.org/tinycmmc-git.git tinycmmc"
    # "https://aur.archlinux.org/evtest-qt-git.git evtest-qt-git"
    # https://wiki.archlinux.org/title/Gamepad#
    # "https://aur.archlinux.org/jstest-gtk-git.git jstest-gtk-git"
    "https://aur.archlinux.org/xboxdrv-git.git xboxdrv-git"
    "https://aur.archlinux.org/xpadneo-dkms-git.git xpadneo-dkms-git"
    "https://aur.archlinux.org/xpadneo-dkms-git.git xpadneo-dkms-git"
    "https://aur.archlinux.org/xone-dongle-firmware.git xone-dongle-firmware"
    # "https://aur.archlinux.org/gparted-git.git gparted-git"    
    # "https://aur.archlinux.org/ferdium-git.git ferdium-git"
    "https://aur.archlinux.org/ferdium.git ferdium"
    "https://aur.archlinux.org/gamemode-git.git gamemode-git"
    #"https://aur.archlinux.org/mangohud-git.git mangohud-git"
    #"https://aur.archlinux.org/lib32-mangohud-git.git lib32-mangohud-git"
    # https://wiki.archlinux.org/title/File_manager_functionality#File_managers_other_than_Dolphin_and_Konqueror
    "https://aur.archlinux.org/python-pyvips.git python-pyvips"
    "https://aur.archlinux.org/ffmpeg-audio-thumbnailer.git ffmpeg-audio-thumbnailer"
    "https://aur.archlinux.org/raw-thumbnailer.git raw-thumbnailer"
    "https://aur.archlinux.org/mcomix.git mcomix"
    "https://aur.archlinux.org/folderpreview.git folderpreview"
    # "https://aur.archlinux.org/python-pip-git.git pip-git"
    "https://aur.archlinux.org/pyenv-git.git pyenv-git"
    # "https://aur.archlinux.org/python-pipx-git.git pipx-git"

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

cd ~/linux-configuration
hosts/install.sh
i3-configuration/install.sh
yes | sudo pacman -Syuu 

# Installing unreal engine
cd ~/aur
if [ ! -d "$(basename https://aur.archlinux.org/unreal-engine.git .git)" ]; then
    git clone https://aur.archlinux.org/unreal-engine.git
fi

#cd unreal-engine
## gh auth login
#gh repo clone EpicGames/UnrealEngine -- -b release --single-branch
#makepkg -s --nocheck --skipchecksums --skipinteg --skippgpcheck --noconfirm --needed
