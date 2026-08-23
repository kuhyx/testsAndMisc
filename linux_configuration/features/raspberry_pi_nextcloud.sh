#!/bin/bash
# Nextcloud Installation Script for Raspberry Pi
# This script installs and configures Nextcloud on a Raspberry Pi
#
# Usage:
#   ./raspberry_pi_nextcloud.sh install         - Install Nextcloud (run on Pi or via SSH)
#   ./raspberry_pi_nextcloud.sh fix             - Fix common Nextcloud issues
#   ./raspberry_pi_nextcloud.sh install-remote  - Install Nextcloud via SSH from laptop

set -euo pipefail

# Script directory for config file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.raspberry_pi.conf"

# Load configuration from gitignored config file if it exists
if [[ -f $CONFIG_FILE ]]; then
	# shellcheck source=/dev/null
	source "$CONFIG_FILE"
fi

# Configuration
PI_HOSTNAME="${PI_HOSTNAME:-nextcloud-pi}"
PI_USER="${PI_USER:-pi}"
PI_PASSWORD="${PI_PASSWORD:-}"
PI_TIMEZONE="${PI_TIMEZONE:-Europe/Warsaw}"
PI_LOCALE="${PI_LOCALE:-en_US.UTF-8}"
NEXTCLOUD_ADMIN_USER="${NEXTCLOUD_ADMIN_USER:-admin}"
NEXTCLOUD_ADMIN_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD:-}"
NEXTCLOUD_DATA_DIR="${NEXTCLOUD_DATA_DIR:-/var/www/nextcloud/data}"
NEXTCLOUD_VERSION="${NEXTCLOUD_VERSION:-latest}"

# DuckDNS for free domain and Let's Encrypt SSL
# Get your free subdomain at https://www.duckdns.org/
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN:-}"       # e.g., "mycloud" for mycloud.duckdns.org
DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"         # Your DuckDNS token
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}" # Email for Let's Encrypt notifications

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
	cat >"$CONFIG_FILE" <<EOF
# Raspberry Pi Nextcloud Setup - Auto-generated config
# This file is gitignored and stores discovered settings

# Pi configuration
PI_HOSTNAME="${PI_HOSTNAME}"
PI_USER="${PI_USER}"
PI_TIMEZONE="${PI_TIMEZONE}"
NEXTCLOUD_ADMIN_USER="${NEXTCLOUD_ADMIN_USER}"

# Generated passwords (KEEP THIS FILE SECURE!)
PI_PASSWORD="${PI_PASSWORD}"
NEXTCLOUD_ADMIN_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD}"

# DuckDNS for Let's Encrypt SSL (optional)
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN:-}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"
EOF
	chmod 600 "$CONFIG_FILE"
	log_info "Configuration saved to $CONFIG_FILE"
}

generate_password() {
	local length="${1:-16}"
	local chars
	chars=$(dd if=/dev/urandom bs=256 count=1 2>/dev/null | tr -dc 'A-Za-z0-9!@#$%&*' | cut -c1-"$length")
	echo "$chars"
}

auto_generate_nextcloud_password() {
	if [[ -z $NEXTCLOUD_ADMIN_PASSWORD ]]; then
		NEXTCLOUD_ADMIN_PASSWORD=$(generate_password 20)
		log_info "Auto-generated Nextcloud admin password (will be saved to config file)"
	fi
}

# shellcheck source=lib/rpi_nc_deps.sh
source "$SCRIPT_DIR/lib/rpi_nc_deps.sh"
# shellcheck source=lib/rpi_nc_system.sh
source "$SCRIPT_DIR/lib/rpi_nc_system.sh"
# shellcheck source=lib/rpi_nc_install.sh
source "$SCRIPT_DIR/lib/rpi_nc_install.sh"
# shellcheck source=lib/rpi_nc_fixes.sh
source "$SCRIPT_DIR/lib/rpi_nc_fixes.sh"
# shellcheck source=lib/rpi_nc_ssl.sh
source "$SCRIPT_DIR/lib/rpi_nc_ssl.sh"
# shellcheck source=lib/rpi_nc_ssl_remote.sh
source "$SCRIPT_DIR/lib/rpi_nc_ssl_remote.sh"
# shellcheck source=lib/rpi_nc_ca.sh
source "$SCRIPT_DIR/lib/rpi_nc_ca.sh"


main() {
	local command="${1:-help}"

	case "$command" in
	install-remote)
		phase_install_remote
		;;
	setup-ssl-remote)
		phase_setup_ssl_remote
		;;
	setup-ssl)
		phase_setup_ssl
		;;
	install-ca)
		phase_install_ca
		;;
	configure)
		phase_configure_system
		;;
	install-local | install)
		phase_install_nextcloud
		;;
	fix)
		phase_fix_issues
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
