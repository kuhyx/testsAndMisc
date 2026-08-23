#!/bin/bash
# Remote SSL setup and the remote install phase.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep rpi_nc_ssl.sh
# under the 250-line cap. Sourced rather than run, so it inherits the
# caller's strict mode and the variables defined above the source line.

phase_setup_ssl_remote() {
	log_info "=== Setting up Let's Encrypt SSL via SSH ==="

	if [[ -z $PI_PASSWORD ]]; then
		die "PI_PASSWORD not set. Run install-remote first."
	fi

	local pi_ip
	pi_ip=$(discover_raspberry_pi)

	if [[ -z $pi_ip ]]; then
		die "Failed to discover Raspberry Pi"
	fi

	# Get DuckDNS credentials if not set
	if [[ -z $DUCKDNS_DOMAIN ]] || [[ -z $DUCKDNS_TOKEN ]]; then
		echo
		log_info "To get auto-trusted HTTPS, you need a free DuckDNS domain."
		log_info "1. Go to https://www.duckdns.org/ and sign in"
		log_info "2. Create a subdomain (e.g., 'myhomecloud')"
		log_info "3. Copy your token"
		echo

		read -r -p "Enter your DuckDNS subdomain (without .duckdns.org): " DUCKDNS_DOMAIN
		read -r -p "Enter your DuckDNS token: " DUCKDNS_TOKEN
		read -r -p "Enter your email (for Let's Encrypt): " LETSENCRYPT_EMAIL
	fi

	save_config

	log_info "Copying script to Pi..."
	sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no "$0" "${PI_USER}@${pi_ip}:/tmp/raspberry_pi_nextcloud.sh"

	log_info "Running SSL setup on Pi..."
	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI_USER}@${pi_ip}" \
		"echo '$PI_PASSWORD' | sudo -S DUCKDNS_DOMAIN='$DUCKDNS_DOMAIN' DUCKDNS_TOKEN='$DUCKDNS_TOKEN' LETSENCRYPT_EMAIL='$LETSENCRYPT_EMAIL' bash /tmp/raspberry_pi_nextcloud.sh setup-ssl"

	local full_domain="${DUCKDNS_DOMAIN}.duckdns.org"

	log_success "========================================"
	log_success "SSL setup complete!"
	log_success "========================================"
	echo
	log_info "Access your Nextcloud at: https://$full_domain"
	log_info "This works on ALL devices without certificate warnings!"
}

# =============================================================================
# Remote Installation
# =============================================================================

phase_install_remote() {
	log_info "=== Installing Nextcloud via SSH ==="

	if [[ -z $PI_PASSWORD ]]; then
		die "PI_PASSWORD not set. Did you run flash script first?"
	fi

	local pi_ip
	pi_ip=$(discover_raspberry_pi)

	if [[ -z $pi_ip ]]; then
		die "Failed to discover Raspberry Pi"
	fi

	log_info "Using Raspberry Pi at: $pi_ip"

	# Remove old host key if present
	ssh-keygen -R "$pi_ip" 2>/dev/null || true

	log_info "Copying script to Pi..."
	sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no "$0" "${PI_USER}@${pi_ip}:/tmp/raspberry_pi_nextcloud.sh"

	log_info "Running system configuration on Pi..."
	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI_USER}@${pi_ip}" \
		"echo '$PI_PASSWORD' | sudo -S bash /tmp/raspberry_pi_nextcloud.sh configure"

	log_info "Installing Nextcloud on Pi..."
	auto_generate_nextcloud_password
	save_config

	log_success "Nextcloud admin user: $NEXTCLOUD_ADMIN_USER"
	log_success "Nextcloud admin password: $NEXTCLOUD_ADMIN_PASSWORD"

	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI_USER}@${pi_ip}" \
		"echo '$PI_PASSWORD' | sudo -S NEXTCLOUD_ADMIN_PASSWORD='$NEXTCLOUD_ADMIN_PASSWORD' NEXTCLOUD_ADMIN_USER='$NEXTCLOUD_ADMIN_USER' bash /tmp/raspberry_pi_nextcloud.sh install-local"

	log_info "Fixing Nextcloud issues..."
	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI_USER}@${pi_ip}" \
		"echo '$PI_PASSWORD' | sudo -S bash /tmp/raspberry_pi_nextcloud.sh fix"

	log_success "========================================"
	log_success "Remote Nextcloud installation complete!"
	log_success "========================================"
	echo
	log_info "=== Access Information ==="
	log_info "Nextcloud URL: https://$pi_ip"
	log_info "Admin user: $NEXTCLOUD_ADMIN_USER"
	log_info "Admin password: $NEXTCLOUD_ADMIN_PASSWORD"
	log_info "All credentials saved in: $CONFIG_FILE"
	echo
	log_info "=== Trust the certificate ==="
	log_info "Run: $0 install-ca"
}
