#!/usr/bin/env bash
# shellcheck source=./detect_gpu.sh
# shellcheck source=./detect_gpu_and_install.sh
set -e

# shellcheck source=lib/packages.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/packages.sh"

# Trap errors and call the play_error_sound function
trap 'play_error_sound' ERR

sudo -v
git config --global init.defaultBranch main

# GPU detection (now split vendor-specific logic)
if [ -f "./detect_gpu.sh" ]; then
	# shellcheck source=./detect_gpu.sh disable=SC1091
	. ./detect_gpu.sh
elif [ -f "./detect_gpu_and_install.sh" ]; then
	# shellcheck source=./detect_gpu_and_install.sh disable=SC1091
	. ./detect_gpu_and_install.sh
else
	echo "GPU detection scripts not found; continuing without GPU specific installation."
fi

sudo cp /etc/makepkg.conf /etc/makepkg.conf.bak
sudo cp ./makepkg.conf /etc/makepkg.conf
sudo cp /etc/pacman.conf /etc/pacman.conf.bak
sudo cp ./pacman.conf /etc/pacman.conf
# sudo cp /etc/mkinitcpio.conf /etc/mkinitcpio.conf.bak
# sudo cp ./mkinitcpio.conf /etc/mkinitcpio.conf
# mkinitcpio -P
# Reflector install / service management (idempotent & resilient)
if pacman -Qi reflector >/dev/null 2>&1; then
	echo "reflector already installed"
else
	yes | sudo pacman -Sy --noconfirm reflector || echo "Warning: reflector install failed (continuing)"
fi
# Prefer timer over service (Arch default)
if systemctl list-unit-files | grep -q '^reflector.timer'; then
	if systemctl is-enabled reflector.timer >/dev/null 2>&1; then
		echo "reflector.timer already enabled"
	else
		sudo systemctl enable reflector.timer || echo "Warning: could not enable reflector.timer"
	fi
	if systemctl is-active reflector.timer >/dev/null 2>&1; then
		echo "reflector.timer already active"
	else
		if ! sudo systemctl start reflector.timer; then
			echo "Warning: failed to start reflector.timer (check: systemctl status reflector.timer; journalctl -xeu reflector.timer)"
		fi
	fi
elif systemctl list-unit-files | grep -q '^reflector.service'; then
	if systemctl is-enabled reflector.service >/dev/null 2>&1; then
		echo "reflector.service already enabled"
	else
		sudo systemctl enable reflector.service || echo "Warning: could not enable reflector.service"
	fi
	if systemctl is-active reflector.service >/dev/null 2>&1; then
		echo "reflector.service already running"
	else
		if ! sudo systemctl start reflector.service; then
			echo "Warning: failed to start reflector.service (check: systemctl status reflector.service; journalctl -xeu reflector.service)"
		fi
	fi
else
	echo "reflector systemd unit not found (neither timer nor service)"
fi
# Read AUR packages from file (needed before pacman processing)
declare -a aur_packages=()
declare -a aur_package_names=()
while IFS= read -r line; do
	if [[ -n $line && $line =~ ^[a-z0-9] ]]; then
		aur_packages+=("$line")
		aur_package_names+=("${line%% *}")
	fi
done <"aur_packages.txt"

# Read pacman packages from file
declare -a pacman_packages
while IFS= read -r line; do
	# Skip empty lines and comments (lines not starting with alphanumeric characters)
	if [[ -n $line && $line =~ ^[a-z0-9] ]]; then
		pacman_packages+=("$line")
	fi
done <"pacman_packages.txt"

for pkg in "${pacman_packages[@]}"; do
	# Skip NVIDIA packages if GPU is not NVIDIA
	if [ "$GPU_VENDOR" != "nvidia" ] && { [ "$pkg" = "nvidia" ] || [ "$pkg" = "nvidia-utils" ] || [ "$pkg" = "lib32-nvidia-utils" ]; }; then
		echo "Skipping $pkg (GPU vendor: $GPU_VENDOR)"
		continue
	fi
	# Check for texlive subpackages
	if [ "$pkg" == "texlive" ]; then
		# shellcheck disable=SC2034  # Used via nameref in all_subpackages_installed
		texlive_sub_pkgs=(
			texlive-basic texlive-bibtexextra texlive-binextra texlive-context texlive-fontsextra
			texlive-fontsrecommended texlive-fontutils texlive-formatsextra texlive-games texlive-humanities
			texlive-latex texlive-latexextra texlive-latexrecommended texlive-luatex texlive-mathscience
			texlive-metapost texlive-music texlive-pictures texlive-plaingeneric texlive-pstricks
			texlive-publishers texlive-xetex
		)
		if all_subpackages_installed texlive_sub_pkgs; then
			echo "All texlive subpackages are installed, skipping texlive"
			continue
		fi
	fi

	# Check for texlive-lang subpackages
	if [ "$pkg" == "texlive-lang" ]; then
		# shellcheck disable=SC2034  # Used via nameref in all_subpackages_installed
		texlive_lang_sub_pkgs=(
			texlive-langarabic texlive-langchinese texlive-langcjk texlive-langcyrillic
			texlive-langczechslovak texlive-langenglish texlive-langeuropean texlive-langfrench
			texlive-langgerman texlive-langgreek texlive-langitalian texlive-langjapanese
			texlive-langkorean texlive-langother texlive-langpolish texlive-langportuguese
			texlive-langspanish
		)
		if all_subpackages_installed texlive_lang_sub_pkgs; then
			echo "All texlive-lang subpackages are installed, skipping texlive-lang"
			continue
		fi
	fi

	if ! pacman -Qi "$pkg" &>/dev/null; then
		if ! printf '%s
' "${aur_package_names[@]}" | grep -Fxq "$pkg"; then
			yes | sudo pacman -Sy --noconfirm "$pkg"
		else
			echo "$pkg exists in AUR packages, skipping pacman installation"
		fi
	else
		echo "$pkg is already installed"
	fi
done
if ! command -v nvm &>/dev/null; then
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
else
	echo "nvm is already installed"
fi
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
	# shellcheck source=/dev/null
	. "$NVM_DIR/nvm.sh"
else
	echo "nvm.sh not found at $NVM_DIR/nvm.sh" >&2
fi
if command -v nvm &>/dev/null; then
	nvm i v18.20.5
	nvm install --lts
else
	echo "nvm command unavailable; skipping Node installation" >&2
fi
sudo systemctl enable bluetooth.service
sudo systemctl start bluetooth.service

for entry in "${aur_packages[@]}"; do
	pkg_name=${entry%% *}
	repo_url=${entry#* }
	if [ "$repo_url" = "$pkg_name" ] || [ -z "$repo_url" ]; then
		repo_url="https://aur.archlinux.org/${pkg_name}.git"
	fi
	install_from_aur "$repo_url" "$pkg_name"
done

cd ~/linux-configuration/fresh-install
if [ ! -d "$HOME/.config/mpv" ]; then
	mkdir -p "$HOME/.config/mpv"
fi
cp mpv.conf "$HOME/.config/mpv/mpv.conf"

if [ ! -d "$HOME/.oh-my-zsh" ]; then
	yes | sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
	echo "Oh My Zsh is already installed"
fi

cd ~/linux-configuration
sudo "$HOME/hosts-blocker/install.sh"
i3/install.sh
periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh
fixes/nvidia_troubleshoot.sh
sudo features/setup_activitywatch.sh
sudo utils/setup_media_organizer.sh
yes | sudo periodic_background/setup_periodic_system.sh
yes | protonup
yes | sudo pacman -Syuu

#cd unreal-engine
## gh auth login
#gh repo clone EpicGames/UnrealEngine -- -b release --single-branch
#makepkg -s --nocheck --skipchecksums --skipinteg --skippgpcheck --noconfirm --needed

utils/setup_passwordless_system.sh
