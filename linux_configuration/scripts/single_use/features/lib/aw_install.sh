#!/bin/bash
# ActivityWatch install, both packaged and manual.
#
# Sourced by setup_activitywatch.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# Function to install ActivityWatch
install_activitywatch() {
	echo ""
	echo "2. Installing ActivityWatch..."
	echo "============================="

	# Check if we need sudo for installation
	check_sudo "install"

	echo "Installing activitywatch-bin from AUR..."

	# Check if an AUR helper is available
	local aur_helpers=("yay" "paru" "makepkg")
	local helper_found=""

	for helper in "${aur_helpers[@]}"; do
		if command -v "$helper" &>/dev/null; then
			helper_found="$helper"
			break
		fi
	done

	if [[ -n $helper_found && $helper_found != "makepkg" ]]; then
		echo "Using AUR helper: $helper_found"
		if [[ $EUID -eq 0 ]]; then
			# Running as root, need to install as user
			sudo -u "$ACTUAL_USER" "$helper_found" -S --noconfirm activitywatch-bin
		else
			"$helper_found" -S --noconfirm activitywatch-bin
		fi
	else
		echo "No AUR helper found. Installing manually with makepkg..."
		install_activitywatch_manual
	fi

	echo "✓ ActivityWatch installation completed"
}

# Function to manually install ActivityWatch via makepkg
install_activitywatch_manual() {
	local temp_dir="/tmp/activitywatch-install"
	local original_user="$ACTUAL_USER"

	# Create temp directory
	mkdir -p "$temp_dir"
	# Guarded: the next command is `git clone ... .`, which would otherwise
	# clone into whatever directory the caller happened to be in.
	cd "$temp_dir" || {
		print_error "Cannot enter $temp_dir"
		return 1
	}

	# Download PKGBUILD
	if command -v git &>/dev/null; then
		sudo -u "$original_user" git clone https://aur.archlinux.org/activitywatch-bin.git .
	else
		echo "Installing git..."
		pacman -S --noconfirm git
		sudo -u "$original_user" git clone https://aur.archlinux.org/activitywatch-bin.git .
	fi

	# Build and install package
	sudo -u "$original_user" makepkg -si --noconfirm

	# Cleanup
	cd /
	rm -rf "$temp_dir"
}
