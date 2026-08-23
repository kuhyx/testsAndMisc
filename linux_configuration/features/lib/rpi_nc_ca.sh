#!/bin/bash
# CA certificate installation.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# =============================================================================
# Install CA Certificate on Client
# =============================================================================

phase_install_ca() {
	log_info "=== Installing Nextcloud CA Certificate ==="

	if [[ -z $PI_PASSWORD ]]; then
		die "PI_PASSWORD not set. Run this after running install-remote or flash."
	fi

	local pi_ip
	pi_ip=$(discover_raspberry_pi)

	if [[ -z $pi_ip ]]; then
		die "Failed to discover Raspberry Pi"
	fi

	log_info "Downloading CA certificate from Pi..."

	local ca_file="/tmp/nextcloud-ca.crt"

	# Use SSH with sudo to cat the file (since it's in a protected directory)
	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no \
		"${PI_USER}@${pi_ip}" "echo '$PI_PASSWORD' | sudo -S cat /etc/ssl/nextcloud/ca.crt" >"$ca_file" 2>/dev/null

	if [[ ! -f $ca_file ]] || [[ ! -s $ca_file ]]; then
		die "Failed to download CA certificate"
	fi

	log_success "CA certificate downloaded to: $ca_file"

	# Detect OS and install appropriately
	if [[ -f /etc/arch-release ]]; then
		log_info "Detected Arch Linux - installing CA..."
		sudo cp "$ca_file" /etc/ca-certificates/trust-source/anchors/nextcloud-ca.crt
		sudo trust extract-compat
		log_success "CA installed in system trust store"

	elif [[ -f /etc/debian_version ]]; then
		log_info "Detected Debian/Ubuntu - installing CA..."
		sudo cp "$ca_file" /usr/local/share/ca-certificates/nextcloud-ca.crt
		sudo update-ca-certificates
		log_success "CA installed in system trust store"

	elif [[ -f /etc/redhat-release ]]; then
		log_info "Detected RHEL/Fedora - installing CA..."
		sudo cp "$ca_file" /etc/pki/ca-trust/source/anchors/nextcloud-ca.crt
		sudo update-ca-trust
		log_success "CA installed in system trust store"

	elif [[ "$(uname)" == "Darwin" ]]; then
		log_info "Detected macOS - installing CA..."
		sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$ca_file"
		log_success "CA installed in system keychain"

	else
		log_warning "Unknown OS - please install CA manually from: $ca_file"
	fi

	# Install in browser certificate stores
	log_info "Installing CA in browser certificate stores..."

	# Chrome/Chromium (uses NSS)
	if [[ -d ~/.pki/nssdb ]] || command -v certutil &>/dev/null; then
		mkdir -p ~/.pki/nssdb
		if ! certutil -d sql:~/.pki/nssdb -L 2>/dev/null | grep -q "Nextcloud"; then
			# Initialize NSS db if needed
			certutil -d sql:~/.pki/nssdb -N --empty-password 2>/dev/null || true
			if certutil -d sql:~/.pki/nssdb -A -n "Nextcloud Home CA" -t "CT,C,C" -i "$ca_file" 2>/dev/null; then
				log_success "CA installed in Chrome/Chromium"
			else
				log_warning "Could not install in Chrome/Chromium NSS db"
			fi
		else
			log_info "CA already installed in Chrome/Chromium"
		fi
	fi

	# Firefox (has its own profile NSS databases)
	if [[ -d ~/.mozilla/firefox ]]; then
		local installed=0
		for profile_dir in ~/.mozilla/firefox/*.default* ~/.mozilla/firefox/*.esr*; do
			if [[ -d $profile_dir ]]; then
				if ! certutil -d sql:"$profile_dir" -L 2>/dev/null | grep -q "Nextcloud"; then
					certutil -d sql:"$profile_dir" -A -n "Nextcloud Home CA" -t "CT,C,C" -i "$ca_file" 2>/dev/null &&
						installed=1
				else
					installed=1
				fi
			fi
		done
		if [[ $installed -eq 1 ]]; then
			log_success "CA installed in Firefox"
		else
			log_warning "Could not install in Firefox - you may need to import manually"
		fi
	fi

	# Add hostname to /etc/hosts if not present
	if ! grep -q "$PI_HOSTNAME" /etc/hosts 2>/dev/null; then
		log_info "Adding $PI_HOSTNAME to /etc/hosts..."
		echo "$pi_ip $PI_HOSTNAME ${PI_HOSTNAME}.local" | sudo tee -a /etc/hosts >/dev/null
		log_success "Added $PI_HOSTNAME to /etc/hosts"
	else
		log_info "$PI_HOSTNAME already in /etc/hosts"
	fi

	# Verify
	log_info "Verifying HTTPS connection..."
	if curl -s --max-time 5 "https://$PI_HOSTNAME/status.php" 2>/dev/null | grep -q "installed"; then
		log_success "HTTPS connection verified - no certificate warnings!"
	else
		log_warning "Could not verify HTTPS - you may need to restart your browser"
	fi

	log_success "========================================"
	log_success "CA Certificate installed!"
	log_success "========================================"
	echo
	log_info "Access Nextcloud at: https://$PI_HOSTNAME"
	log_info "Your browser should now trust the certificate without warnings."
	echo
	log_info "For other devices (phones, tablets, other computers):"
	log_info "  Download: https://$PI_HOSTNAME/ca/nextcloud-ca.crt"
	log_info "  Then install the certificate in your device's trust store."
}

# =============================================================================
# Main
# =============================================================================

show_help() {
	cat <<'EOF'
Nextcloud Installation Script for Raspberry Pi

Usage: ./raspberry_pi_nextcloud.sh <command>

Commands:
  install-remote     Install Nextcloud via SSH from your laptop (recommended)
  setup-ssl-remote   Setup Let's Encrypt SSL with DuckDNS (auto-trusted on all devices)
  install-ca         Install self-signed CA on this machine (alternative to setup-ssl)
  configure          Configure Pi system (run on Pi)
  install-local      Install Nextcloud (run on Pi)
  fix                Fix common Nextcloud issues (run on Pi)
  setup-ssl          Setup Let's Encrypt SSL (run on Pi)
  help               Show this help message

The script will:
1. Configure the Raspberry Pi system (SSH hardening, firewall, etc.)
2. Install Apache, PHP, MariaDB, Redis
3. Download and install Nextcloud
4. Configure caching, background jobs, and security

For HTTPS trusted on ALL devices automatically:
  ./raspberry_pi_nextcloud.sh install-remote
  ./raspberry_pi_nextcloud.sh setup-ssl-remote

  This uses DuckDNS (free) + Let's Encrypt for real trusted certificates.
  Go to https://www.duckdns.org/ to get your free domain first.

For self-signed certificates (requires manual CA install on each device):
  ./raspberry_pi_nextcloud.sh install-remote
  ./raspberry_pi_nextcloud.sh install-ca

For local installation (on Pi):
  sudo ./raspberry_pi_nextcloud.sh configure
  sudo ./raspberry_pi_nextcloud.sh install-local
  sudo ./raspberry_pi_nextcloud.sh fix
  sudo ./raspberry_pi_nextcloud.sh setup-ssl
EOF
}
