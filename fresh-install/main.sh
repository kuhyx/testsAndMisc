#!/usr/bin/env bash
# shellcheck source=./detect_gpu.sh
# shellcheck source=./detect_gpu_and_install.sh
set -e

# Function to play a sound on error
play_error_sound() {
	#pactl set-sink-volume @DEFAULT_SINK@ +50%
	for _ in 1 2 3; do
		paplay /usr/share/sounds/freedesktop/stereo/dialog-error.oga
	done
	#pactl set-sink-volume @DEFAULT_SINK@ -50%
}

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

install_from_aur() {
	local repo_url pkg_name repo_dir
	repo_url="$1"
	pkg_name="$2"

	mkdir -p "$HOME/aur"
	cd "$HOME/aur" || return 1
	repo_dir="$(basename "$repo_url" .git)"

	if [ ! -d "$repo_dir" ]; then
		git clone "$repo_url"
	else
		echo "Repository $repo_dir already cloned; updating"
		(cd "$repo_dir" && git fetch --all -q && git reset --hard origin/HEAD -q || git pull --ff-only || true)
	fi
	cd "$repo_dir" || return 1

	if pacman -Qi "$pkg_name" >/dev/null 2>&1; then
		echo "$pkg_name is already installed"
		return 0
	fi

	echo "Cleaning old package artifacts to avoid duplicate -U targets"
	find . -maxdepth 1 -type f -name '*.pkg.tar.*' -delete 2>/dev/null || true

	echo "Building $pkg_name (clean build)"
	# -c (clean up work dirs after) -C (clean build - remove src/ and pkg/ first)
	if ! yes | makepkg -s -c -C --noconfirm --nocheck --skipchecksums --skipinteg --skippgpcheck --needed; then
		echo "Build failed for $pkg_name" >&2
		return 1
	fi

	# Collect only the freshly built packages (should now be only current version)
	mapfile -t built_pkgs < <(find . -maxdepth 1 -type f -name '*.pkg.tar.zst' -printf './%f\n')
	if [ ${#built_pkgs[@]} -eq 0 ]; then
		echo "No package files produced for $pkg_name" >&2
		return 1
	fi

	echo "Installing built package(s): ${built_pkgs[*]}"
	if ! yes | sudo pacman -U --noconfirm "${built_pkgs[@]}"; then
		echo "Installation failed for $pkg_name" >&2
		return 1
	fi
}

# Helper: try to install from AUR and log result to done.txt/failed.txt
try_aur_install() {
	local repo_url="$1"
	local pkg_name="$2"
	if install_from_aur "$repo_url" "$pkg_name"; then
		echo "$pkg_name" >>done.txt
	else
		echo "$pkg_name" >>failed.txt
	fi
}

process_packages() {
	local file_path
	file_path="$1"
	: >failed.txt
	: >done.txt

	while IFS= read -r pkg_name; do
		if [ -z "$pkg_name" ]; then
			continue
		fi

		local repo_url repo_dir
		repo_url="https://aur.archlinux.org/${pkg_name}-git.git"
		repo_dir="${pkg_name}-git"

		git clone "$repo_url"
		if [ -d "$repo_dir" ] && [ -z "$(ls -A "$repo_dir")" ]; then
			echo "Repository $repo_dir is empty, trying without -git suffix"
			repo_url="https://aur.archlinux.org/${pkg_name}.git"
			repo_dir="${pkg_name}"

			git clone "$repo_url"
			if [ -d "$repo_dir" ] && [ -z "$(ls -A "$repo_dir")" ]; then
				echo "Repository $repo_dir is empty, trying to install with pacman"
				if sudo pacman -Sy --noconfirm "$pkg_name"; then
					echo "$pkg_name" >>done.txt
				else
					echo "$pkg_name" >>failed.txt
				fi
			else
				try_aur_install "$repo_url" "$pkg_name"
			fi
		else
			try_aur_install "$repo_url" "$pkg_name"
		fi
	done <"$file_path"
}

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

# Helper: Check if all subpackages are installed
# Returns 0 if ALL subpackages are installed, 1 otherwise
all_subpackages_installed() {
	local -n sub_pkgs_ref=$1
	for subpkg in "${sub_pkgs_ref[@]}"; do
		if ! pacman -Qi "$subpkg" &>/dev/null; then
			return 1
		fi
	done
	return 0
}

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
sudo hosts/install.sh
i3-configuration/install.sh
scripts/digital_wellbeing/pacman/install_pacman_wrapper.sh
scripts/fixes/nvidia_troubleshoot.sh
sudo scripts/features/setup_activitywatch.sh
sudo scripts/utils/setup_media_organizer.sh
sudo scripts/digital_wellbeing/setup_pc_startup_monitor.sh
yes | sudo scripts/setup_periodic_system.sh
sudo scripts/setup_thorium_startup.sh
yes | protonup
yes | sudo pacman -Syuu

#cd unreal-engine
## gh auth login
#gh repo clone EpicGames/UnrealEngine -- -b release --single-branch
#makepkg -s --nocheck --skipchecksums --skipinteg --skippgpcheck --noconfirm --needed

scripts/utils/setup_passwordless_system.sh
