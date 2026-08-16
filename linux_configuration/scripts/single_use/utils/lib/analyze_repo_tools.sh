#!/bin/bash
# Package-manager detection and installation of the analysis toolchain
# (ctags, cscope, clang, ugrep, tokei, scc, counts).
#
# Sourced by analyze_repo.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and the
# colour constants defined above the source line.

install_missing_tools() {
	local MISSING_TOOLS=()
	local MISSING_AUR=()

	# Check for required tools
	command -v git &>/dev/null || MISSING_TOOLS+=("git")
	command -v ctags &>/dev/null || MISSING_TOOLS+=("ctags")
	command -v cscope &>/dev/null || MISSING_TOOLS+=("cscope")
	command -v clang &>/dev/null || MISSING_TOOLS+=("clang")
	command -v ugrep &>/dev/null || MISSING_TOOLS+=("ugrep")

	# Check for AUR tools
	command -v tokei &>/dev/null || MISSING_AUR+=("tokei")
	command -v scc &>/dev/null || MISSING_AUR+=("scc")

	# Check for Rust 'counts' tool (install via cargo if missing)
	if ! command -v counts &>/dev/null; then
		if command -v cargo &>/dev/null; then
			echo "Installing 'counts' via cargo (fast word counter)..."
			cargo install counts 2>/dev/null || echo "Warning: counts install failed, will use Python fallback"
		fi
	fi

	# If nothing is missing, return
	if [ ${#MISSING_TOOLS[@]} -eq 0 ] && [ ${#MISSING_AUR[@]} -eq 0 ]; then
		echo -e "${GREEN}All required tools are installed.${NC}"
		return 0
	fi

	echo -e "${YELLOW}Missing tools detected. Installing...${NC}"

	# Detect package manager
	if command -v pacman &>/dev/null; then
		# Arch Linux
		if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
			echo "Installing from official repos: ${MISSING_TOOLS[*]}"
			sudo pacman -S --needed --noconfirm "${MISSING_TOOLS[@]}"
		fi

		if [ ${#MISSING_AUR[@]} -gt 0 ]; then
			# Find or install AUR helper
			if command -v yay &>/dev/null; then
				AUR_HELPER="yay"
			elif command -v paru &>/dev/null; then
				AUR_HELPER="paru"
			else
				echo "No AUR helper found. Installing yay..."
				sudo pacman -S --needed --noconfirm base-devel git
				TEMP_DIR=$(mktemp -d)
				git clone https://aur.archlinux.org/yay.git "$TEMP_DIR/yay"
				(cd "$TEMP_DIR/yay" && makepkg -si --noconfirm)
				rm -rf "$TEMP_DIR"
				AUR_HELPER="yay"
			fi

			echo "Installing from AUR: ${MISSING_AUR[*]}"
			$AUR_HELPER -S --needed --noconfirm "${MISSING_AUR[@]}"
		fi

	elif command -v apt-get &>/dev/null; then
		# Debian/Ubuntu
		echo "Installing tools via apt..."
		sudo apt-get update

		# Map tool names to package names
		APT_PACKAGES=()
		for tool in "${MISSING_TOOLS[@]}"; do
			case $tool in
			ctags) APT_PACKAGES+=("universal-ctags") ;;
			ugrep) APT_PACKAGES+=("ugrep") ;;
			*) APT_PACKAGES+=("$tool") ;;
			esac
		done

		[ ${#APT_PACKAGES[@]} -gt 0 ] && sudo apt-get install -y "${APT_PACKAGES[@]}"

		# Install tokei/scc via cargo or snap
		for aur_tool in "${MISSING_AUR[@]}"; do
			if command -v cargo &>/dev/null; then
				echo "Installing $aur_tool via cargo..."
				cargo install "$aur_tool"
			elif command -v snap &>/dev/null; then
				echo "Installing $aur_tool via snap..."
				sudo snap install "$aur_tool"
			else
				echo -e "${YELLOW}Warning: Cannot install $aur_tool. Install cargo or snap first.${NC}"
			fi
		done

	elif command -v dnf &>/dev/null; then
		# Fedora
		echo "Installing tools via dnf..."
		sudo dnf install -y "${MISSING_TOOLS[@]}" "${MISSING_AUR[@]}" 2>/dev/null || {
			# tokei/scc might need cargo
			for aur_tool in "${MISSING_AUR[@]}"; do
				if command -v cargo &>/dev/null; then
					cargo install "$aur_tool"
				fi
			done
		}

	elif command -v brew &>/dev/null; then
		# macOS with Homebrew
		echo "Installing tools via brew..."
		ALL_TOOLS=("${MISSING_TOOLS[@]}" "${MISSING_AUR[@]}")
		brew install "${ALL_TOOLS[@]}"

	else
		echo -e "${RED}Unknown package manager. Please install these tools manually:${NC}"
		echo "  Official: ${MISSING_TOOLS[*]}"
		echo "  Additional: ${MISSING_AUR[*]}"
		exit 1
	fi

	echo -e "${GREEN}Tool installation complete.${NC}"
}
