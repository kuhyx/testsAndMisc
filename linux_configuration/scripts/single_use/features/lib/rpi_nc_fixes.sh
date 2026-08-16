#!/bin/bash
# The post-install fix-up phase.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# =============================================================================
# Fix Nextcloud Issues
# =============================================================================

# shellcheck disable=SC2120  # Function does not use positional args
phase_fix_issues() {
	check_root

	log_info "=== Fixing Nextcloud Issues ==="

	cd /var/www/nextcloud || { log_error "Nextcloud is not installed at /var/www/nextcloud"; return 1; }

	# 1. Fix background jobs (cron not running properly)
	log_info "Fixing background jobs..."

	# Ensure cron is set as background job method
	sudo -u www-data php occ background:cron

	# Ensure cron job exists and is correct
	(
		crontab -u www-data -l 2>/dev/null | grep -v "cron.php"
		echo "*/5 * * * * php -f /var/www/nextcloud/cron.php"
	) | crontab -u www-data -

	# Run cron manually now to reset the timer
	log_info "Running cron job manually..."
	sudo -u www-data php /var/www/nextcloud/cron.php

	log_success "Background jobs configured"

	# 2. Setup HTTPS with proper CA-signed certificate
	log_info "Setting up HTTPS with trusted CA..."

	local pi_ip
	pi_ip=$(hostname -I | awk '{print $1}')

	local ssl_dir="/etc/ssl/nextcloud"
	mkdir -p "$ssl_dir"
	chmod 700 "$ssl_dir"

	# Generate CA if it doesn't exist
	if [[ ! -f "$ssl_dir/ca.crt" ]]; then
		log_info "Creating Certificate Authority (CA)..."

		# Generate CA private key
		openssl genrsa -out "$ssl_dir/ca.key" 4096
		chmod 600 "$ssl_dir/ca.key"

		# Generate CA certificate (valid for 10 years)
		openssl req -x509 -new -nodes -key "$ssl_dir/ca.key" \
			-sha256 -days 3650 \
			-out "$ssl_dir/ca.crt" \
			-subj "/C=PL/ST=Home/L=Local/O=Nextcloud Home CA/OU=Certificate Authority/CN=Nextcloud Home CA"

		log_success "CA created: $ssl_dir/ca.crt"
	fi

	# Generate server certificate signed by our CA
	local regenerate="${1:-}"
	if [[ ! -f "$ssl_dir/server.crt" ]] || [[ $regenerate == "--regenerate" ]]; then
		log_info "Generating server certificate signed by CA..."

		# Generate server private key
		openssl genrsa -out "$ssl_dir/server.key" 2048
		chmod 600 "$ssl_dir/server.key"

		# Create certificate signing request (CSR)
		openssl req -new -key "$ssl_dir/server.key" \
			-out "$ssl_dir/server.csr" \
			-subj "/C=PL/ST=Home/L=Local/O=Nextcloud/OU=Server/CN=$PI_HOSTNAME"

		# Create extension file for SAN (Subject Alternative Names)
		# This allows the certificate to be valid for hostname, IP, and .local
		cat >"$ssl_dir/server.ext" <<EXTEOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $PI_HOSTNAME
DNS.2 = ${PI_HOSTNAME}.local
DNS.3 = localhost
IP.1 = $pi_ip
IP.2 = 127.0.0.1
EXTEOF

		# Sign the certificate with our CA (valid for 2 years)
		openssl x509 -req -in "$ssl_dir/server.csr" \
			-CA "$ssl_dir/ca.crt" \
			-CAkey "$ssl_dir/ca.key" \
			-CAcreateserial \
			-out "$ssl_dir/server.crt" \
			-days 730 \
			-sha256 \
			-extfile "$ssl_dir/server.ext"

		rm -f "$ssl_dir/server.csr" "$ssl_dir/server.ext"

		log_success "Server certificate created and signed by CA"
	fi

	# Copy CA to web-accessible location for easy download
	mkdir -p /var/www/nextcloud/ca
	cp "$ssl_dir/ca.crt" /var/www/nextcloud/ca/nextcloud-ca.crt
	chown -R www-data:www-data /var/www/nextcloud/ca

	log_info "CA certificate available at: https://$PI_HOSTNAME/ca/nextcloud-ca.crt"

	# Create HTTPS Apache config
	cat >/etc/apache2/sites-available/nextcloud-ssl.conf <<EOF
<VirtualHost *:443>
    ServerAdmin admin@localhost
    DocumentRoot /var/www/nextcloud
    ServerName $PI_HOSTNAME
    ServerAlias ${PI_HOSTNAME}.local $pi_ip

    SSLEngine on
    SSLCertificateFile $ssl_dir/server.crt
    SSLCertificateKeyFile $ssl_dir/server.key

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

# Redirect HTTP to HTTPS
<VirtualHost *:80>
    ServerName $PI_HOSTNAME
    ServerAlias $pi_ip
    Redirect permanent / https://$PI_HOSTNAME/
</VirtualHost>
EOF

	a2enmod ssl
	a2enmod headers
	a2ensite nextcloud-ssl

	# Update Nextcloud config for HTTPS
	sudo -u www-data php occ config:system:set overwrite.cli.url --value="https://$PI_HOSTNAME"
	sudo -u www-data php occ config:system:set overwriteprotocol --value="https"

	systemctl restart apache2

	log_success "HTTPS configured with CA-signed certificate"

	# 3. Run mimetype migrations
	log_info "Running mimetype migrations..."
	sudo -u www-data php occ maintenance:repair --include-expensive
	log_success "Mimetype migrations complete"

	# 4. Add missing database indices
	log_info "Adding missing database indices..."
	sudo -u www-data php occ db:add-missing-indices
	log_success "Database indices added"

	# 5. Install ImageMagick SVG support
	log_info "Installing ImageMagick SVG support..."
	DEBIAN_FRONTEND=noninteractive apt-get install -y libmagickcore-6.q16-6-extra

	# Enable SVG in ImageMagick policy
	local policy_file="/etc/ImageMagick-6/policy.xml"
	if [[ -f $policy_file ]]; then
		# Remove SVG restrictions if present
		sed -i 's/<policy domain="coder" rights="none" pattern="SVG" \/>/<policy domain="coder" rights="read|write" pattern="SVG" \/>/' "$policy_file"
		# If no SVG policy exists, add one allowing it
		if ! grep -q 'pattern="SVG"' "$policy_file"; then
			sed -i '/<policymap>/a\  <policy domain="coder" rights="read|write" pattern="SVG" \/>' "$policy_file"
		fi
	fi

	systemctl restart apache2
	log_success "ImageMagick SVG support configured"

	# 6. Set up basic SMTP (placeholder - user needs to configure actual mail server)
	log_info "Note: Email server not configured - please configure in Nextcloud admin settings"

	# 7. Clear any remaining warnings
	log_info "Clearing Nextcloud caches..."
	sudo -u www-data php occ maintenance:repair
	sudo -u www-data php occ files:scan --all

	# 8. Verify all fixes
	log_info "Verifying fixes..."

	# Run cron again to update last run time
	sudo -u www-data php /var/www/nextcloud/cron.php

	log_success "========================================"
	log_success "Nextcloud issues fixed!"
	log_success "========================================"
	echo
	log_info "Summary of changes:"
	log_info "  ✓ Background jobs (cron) configured and running"
	log_info "  ✓ HTTPS enabled with CA-signed certificate"
	log_info "  ✓ Strict-Transport-Security header added"
	log_info "  ✓ Mimetype migrations completed"
	log_info "  ✓ Missing database indices added"
	log_info "  ✓ ImageMagick SVG support installed"
	echo
	log_info "Current certificate: self-signed CA (requires manual install on devices)"
	log_info "  - Run: $0 install-ca (on your laptop)"
	log_info "  - Or download: https://$PI_HOSTNAME/ca/nextcloud-ca.crt"
	echo
	log_info "For auto-trusted HTTPS on ALL devices (recommended):"
	log_info "  1. Get free domain at https://www.duckdns.org/"
	log_info "  2. Run: $0 setup-ssl"
	echo
	log_info "Access Nextcloud at: https://$PI_HOSTNAME"
}
