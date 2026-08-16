#!/bin/bash
# Nextcloud on Raspberry Pi 5 Setup Script
# This script handles multiple phases:
# 1. Flash Raspberry Pi OS to SD card (locally or on remote laptop)
# 2. Configure Pi for remote access (run on Pi after first boot)
# 3. Install and configure Nextcloud (run on Pi)
#
# Usage:
#   ./setup_nextcloud_raspberry.sh flash            - Flash SD card locally
#   ./setup_nextcloud_raspberry.sh flash-remote     - Flash SD card on remote laptop via SSH
#   ./setup_nextcloud_raspberry.sh configure        - Configure Pi for remote access (run on Pi)
#   ./setup_nextcloud_raspberry.sh nextcloud        - Install Nextcloud (run on Pi)
#   ./setup_nextcloud_raspberry.sh all-remote       - Run configure + nextcloud via SSH

set -euo pipefail

# Script directory for config file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.nextcloud_raspberry.conf"

# Load configuration from gitignored config file if it exists
if [[ -f $CONFIG_FILE ]]; then
	# shellcheck source=/dev/null
	source "$CONFIG_FILE"
fi

# Configuration - Customize these values (or set in config file)
PI_HOSTNAME="${PI_HOSTNAME:-nextcloud-pi}"
PI_USER="${PI_USER:-pi}"
PI_PASSWORD="${PI_PASSWORD:-}" # Leave empty to be prompted
PI_TIMEZONE="${PI_TIMEZONE:-Europe/Warsaw}"
PI_LOCALE="${PI_LOCALE:-en_US.UTF-8}"
NEXTCLOUD_ADMIN_USER="${NEXTCLOUD_ADMIN_USER:-admin}"
NEXTCLOUD_ADMIN_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD:-}" # Leave empty to be prompted
NEXTCLOUD_DATA_DIR="${NEXTCLOUD_DATA_DIR:-/var/www/nextcloud/data}"
SD_CARD_DEVICE="${SD_CARD_DEVICE:-}" # e.g., /dev/sdb - will be detected if empty

# Remote laptop configuration - will be auto-discovered if not set
# Default to kuchy for the remote laptop, can be overridden via config file
REMOTE_LAPTOP_USER="${REMOTE_LAPTOP_USER:-kuchy}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# All log functions output to stderr so they don't interfere with function return values
log_info() {
	echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
	echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
	echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
	echo -e "${RED}[ERROR]${NC} $1" >&2
}

die() {
	log_error "$1"
	exit 1
}

check_root() {
	if [[ $EUID -ne 0 ]]; then
		die "This script must be run as root. Use: sudo $0"
	fi
}

save_config() {
	# Save discovered/used configuration to gitignored config file
	cat >"$CONFIG_FILE" <<EOF
# Nextcloud Raspberry Pi Setup - Auto-generated config
# This file is gitignored and stores discovered settings

# Remote laptop (auto-discovered)
REMOTE_LAPTOP_USER="${REMOTE_LAPTOP_USER}"

# Pi configuration
PI_HOSTNAME="${PI_HOSTNAME}"
PI_USER="${PI_USER}"
PI_TIMEZONE="${PI_TIMEZONE}"
NEXTCLOUD_ADMIN_USER="${NEXTCLOUD_ADMIN_USER}"

# Generated passwords (KEEP THIS FILE SECURE!)
PI_PASSWORD="${PI_PASSWORD}"
NEXTCLOUD_ADMIN_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD}"
EOF
	chmod 600 "$CONFIG_FILE"
	log_info "Configuration saved to $CONFIG_FILE"
}

generate_password() {
	# Generate a secure random password (16 chars, alphanumeric + some symbols)
	local length="${1:-16}"
	# Use /dev/urandom for randomness, base64 encode, take first N chars
	# Using dd to avoid SIGPIPE with pipefail
	local chars
	chars=$(dd if=/dev/urandom bs=256 count=1 2>/dev/null | tr -dc 'A-Za-z0-9!@#$%&*' | cut -c1-"$length")
	echo "$chars"
}

auto_generate_pi_password() {
	if [[ -z $PI_PASSWORD ]]; then
		PI_PASSWORD=$(generate_password 16)
		log_info "Auto-generated Pi password (will be saved to config file)"
	fi
}

auto_generate_nextcloud_password() {
	if [[ -z $NEXTCLOUD_ADMIN_PASSWORD ]]; then
		NEXTCLOUD_ADMIN_PASSWORD=$(generate_password 20)
		log_info "Auto-generated Nextcloud admin password (will be saved to config file)"
	fi
}

prompt_password() {
	local prompt="$1"
	local var_name="$2"
	local password=""
	local password_confirm=""

	while true; do
		read -r -s -p "$prompt: " password
		echo
		read -r -s -p "Confirm password: " password_confirm
		echo

		if [[ $password == "$password_confirm" ]]; then
			if [[ -z $password ]]; then
				log_warning "Password cannot be empty. Please try again."
				continue
			fi
			eval "$var_name='$password'"
			break
		else
			log_warning "Passwords do not match. Please try again."
		fi
	done
}

# =============================================================================
# PHASE 1: Flash Raspberry Pi OS to SD Card
# =============================================================================

detect_sd_card() {
	log_info "Detecting removable storage devices..."

	# List block devices that are removable
	local devices
	devices=$(lsblk -d -o NAME,SIZE,TYPE,RM,TRAN | grep -E "disk.*1.*usb|disk.*1.*mmc" | awk '{print "/dev/"$1" ("$2")"}')

	if [[ -z $devices ]]; then
		log_warning "No removable devices detected automatically."
		log_info "Available block devices:"
		lsblk -d -o NAME,SIZE,TYPE,RM,TRAN
		echo
		read -r -p "Enter the SD card device path (e.g., /dev/sdb): " SD_CARD_DEVICE
	else
		echo "Detected removable devices:"
		echo "$devices"
		echo
		read -r -p "Enter the SD card device path from above (e.g., /dev/sdb): " SD_CARD_DEVICE
	fi

	# Validate device exists
	if [[ ! -b $SD_CARD_DEVICE ]]; then
		die "Device $SD_CARD_DEVICE does not exist or is not a block device"
	fi

	# Safety check - don't flash system drive
	local root_device
	root_device=$(findmnt -n -o SOURCE / | sed 's/[0-9]*$//' | sed 's/p[0-9]*$//')
	if [[ $SD_CARD_DEVICE == "$root_device" ]]; then
		die "Cannot flash to the system drive!"
	fi
}

# shellcheck source=lib/nc_image.sh
source "$SCRIPT_DIR/lib/nc_image.sh"
# shellcheck source=lib/nc_flash.sh
source "$SCRIPT_DIR/lib/nc_flash.sh"
# shellcheck source=lib/nc_remote.sh
source "$SCRIPT_DIR/lib/nc_remote.sh"
# shellcheck source=lib/nc_remote_flash.sh
source "$SCRIPT_DIR/lib/nc_remote_flash.sh"
# shellcheck source=lib/nc_packages.sh
source "$SCRIPT_DIR/lib/nc_packages.sh"
# shellcheck source=lib/nc_services.sh
source "$SCRIPT_DIR/lib/nc_services.sh"
# shellcheck source=lib/nc_php.sh
source "$SCRIPT_DIR/lib/nc_php.sh"
# shellcheck source=lib/nc_discover.sh
source "$SCRIPT_DIR/lib/nc_discover.sh"


main() {
	local command="${1:-help}"

	case "$command" in
	flash)
		phase_flash
		;;
	flash-remote)
		phase_flash_remote
		;;
	flash-remote-execute)
		phase_flash_remote_execute "${2:-}"
		;;
	configure)
		phase_configure
		;;
	nextcloud)
		phase_nextcloud
		;;
	all-remote)
		phase_all_remote
		;;
	help | --help | -h)
		show_help
		;;
	*)
		log_error "Unknown command: $command"
		show_help
		exit 1
		;;
	esac
}

main "$@"
