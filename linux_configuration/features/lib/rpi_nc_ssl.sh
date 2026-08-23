#!/bin/bash
# SSL setup, local and remote.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# =============================================================================
# Setup Let's Encrypt SSL with DuckDNS
# =============================================================================

phase_setup_ssl() {
	check_root

	log_info "=== Setting up Let's Encrypt SSL with DuckDNS ==="

	# Check if DuckDNS is configured
	if [[ -z $DUCKDNS_DOMAIN ]] || [[ -z $DUCKDNS_TOKEN ]]; then
		echo
		log_info "To get auto-trusted HTTPS, you need a free DuckDNS domain."
		log_info "1. Go to https://www.duckdns.org/ and sign in with Google/GitHub/etc."
		log_info "2. Create a subdomain (e.g., 'myhomecloud' for myhomecloud.duckdns.org)"
		log_info "3. Copy your token from the DuckDNS page"
		echo

		read -r -p "Enter your DuckDNS subdomain (without .duckdns.org): " DUCKDNS_DOMAIN
		read -r -p "Enter your DuckDNS token: " DUCKDNS_TOKEN
		read -r -p "Enter your email (for Let's Encrypt notifications): " LETSENCRYPT_EMAIL

		if [[ -z $DUCKDNS_DOMAIN ]] || [[ -z $DUCKDNS_TOKEN ]] || [[ -z $LETSENCRYPT_EMAIL ]]; then
			die "All fields are required"
		fi
	fi

	local full_domain="${DUCKDNS_DOMAIN}.duckdns.org"
	local pi_local_ip
	pi_local_ip=$(hostname -I | awk '{print $1}')

	# Get public IP for DuckDNS (Let's Encrypt needs external access)
	local public_ip
	public_ip=$(curl -s https://api.ipify.org) || public_ip=$(curl -s https://ifconfig.me) || true

	log_info "Domain: $full_domain"
	log_info "Pi local IP: $pi_local_ip"
	log_info "Public IP: $public_ip"

	echo
	log_warning "=== IMPORTANT: Port Forwarding Required ==="
	log_warning "For Let's Encrypt to work, you MUST forward ports on your router:"
	log_warning "  - Forward port 80 (HTTP) to $pi_local_ip"
	log_warning "  - Forward port 443 (HTTPS) to $pi_local_ip"
	log_warning ""
	log_warning "Go to your router admin page (usually http://192.168.1.1)"
	log_warning "and set up port forwarding before continuing."
	echo
	read -r -p "Have you set up port forwarding? (yes/no): " port_forward_done

	if [[ $port_forward_done != "yes" ]]; then
		log_info "Please set up port forwarding and run this command again."
		log_info "Without port forwarding, Let's Encrypt cannot verify your domain."
		exit 0
	fi

	# Update DuckDNS to point to PUBLIC IP (not local IP)
	log_info "Updating DuckDNS to point to public IP $public_ip..."
	local duckdns_response
	# When ip= is empty, DuckDNS auto-detects the public IP
	duckdns_response=$(curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")

	if [[ $duckdns_response != "OK" ]]; then
		die "Failed to update DuckDNS: $duckdns_response"
	fi
	log_success "DuckDNS updated to public IP"

	# Set up automatic DuckDNS updates (cron) - auto-detect public IP
	log_info "Setting up automatic DuckDNS IP updates..."
	mkdir -p /opt/duckdns
	cat >/opt/duckdns/duck.sh <<DUCKEOF
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=" | curl -k -o /opt/duckdns/duck.log -K -
DUCKEOF
	chmod 700 /opt/duckdns/duck.sh

	# Add cron job for DuckDNS update every 5 minutes
	(crontab -l 2>/dev/null || true) | grep -v "duckdns" | {
		cat
		echo "*/5 * * * * /opt/duckdns/duck.sh >/dev/null 2>&1"
	} | crontab -

	log_success "DuckDNS auto-update configured"

	# Wait for DNS propagation
	log_info "Waiting for DNS propagation (this may take a minute)..."
	local dns_ip=""
	local attempts=0
	while [[ $dns_ip != "$public_ip" ]] && [[ $attempts -lt 12 ]]; do
		sleep 5
		dns_ip=$(dig +short "$full_domain" 2>/dev/null | tail -1) || true
		attempts=$((attempts + 1))
		log_info "  DNS lookup: $dns_ip (expecting $public_ip, attempt $attempts/12)"
	done

	if [[ $dns_ip != "$public_ip" ]]; then
		log_warning "DNS may not have propagated yet. Continuing anyway..."
	else
		log_success "DNS verified: $full_domain -> $public_ip"
	fi

	# Install certbot if not present
	if ! command -v certbot &>/dev/null; then
		log_info "Installing certbot..."
		DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-apache
	fi

	# Get Let's Encrypt certificate
	log_info "Obtaining Let's Encrypt certificate..."

	# First update Apache config with the new domain
	cat >/etc/apache2/sites-available/nextcloud-ssl.conf <<EOF
<VirtualHost *:443>
    ServerAdmin ${LETSENCRYPT_EMAIL}
    DocumentRoot /var/www/nextcloud
    ServerName ${full_domain}

    SSLEngine on
    # Certbot will update these paths
    SSLCertificateFile /etc/ssl/nextcloud/server.crt
    SSLCertificateKeyFile /etc/ssl/nextcloud/server.key

    <Directory /var/www/nextcloud/>
        Require all granted
        AllowOverride All
        Options FollowSymLinks MultiViews

        <IfModule mod_dav.c>
            Dav off
        </IfModule>
    </Directory>

    # Security headers
    Header always set Strict-Transport-Security "max-age=15552000; includeSubDomains"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "no-referrer"

    ErrorLog \${APACHE_LOG_DIR}/nextcloud_ssl_error.log
    CustomLog \${APACHE_LOG_DIR}/nextcloud_ssl_access.log combined
</VirtualHost>

<VirtualHost *:80>
    ServerName ${full_domain}
    Redirect permanent / https://${full_domain}/
</VirtualHost>
EOF

	systemctl reload apache2

	# Run certbot
	certbot --apache -d "$full_domain" --non-interactive --agree-tos --email "$LETSENCRYPT_EMAIL" --redirect

	log_success "Let's Encrypt certificate obtained!"

	# Update Nextcloud trusted domains
	log_info "Updating Nextcloud configuration..."
	cd /var/www/nextcloud || { log_error "Nextcloud is not installed at /var/www/nextcloud"; return 1; }
	sudo -u www-data php occ config:system:set trusted_domains 0 --value="$full_domain"
	sudo -u www-data php occ config:system:set overwrite.cli.url --value="https://$full_domain"
	sudo -u www-data php occ config:system:set overwriteprotocol --value="https"
	sudo -u www-data php occ config:system:set overwritehost --value="$full_domain"

	# Keep local access working
	sudo -u www-data php occ config:system:set trusted_domains 1 --value="$pi_local_ip"
	sudo -u www-data php occ config:system:set trusted_domains 2 --value="$PI_HOSTNAME"
	sudo -u www-data php occ config:system:set trusted_domains 3 --value="${PI_HOSTNAME}.local"

	log_success "Nextcloud configured for $full_domain"

	# Set up auto-renewal
	log_info "Setting up automatic certificate renewal..."
	systemctl enable certbot.timer
	systemctl start certbot.timer

	log_success "========================================"
	log_success "Let's Encrypt SSL configured!"
	log_success "========================================"
	echo
	log_info "Your Nextcloud is now accessible at:"
	log_info "  https://$full_domain (from anywhere on the internet)"
	log_info "  https://$pi_local_ip (from your local network)"
	echo
	log_info "This certificate is trusted by ALL browsers and devices automatically!"
	log_info "No manual certificate installation required."
	echo
	log_info "Certificate auto-renewal is enabled."
	log_info "DuckDNS IP auto-update is enabled."
}
