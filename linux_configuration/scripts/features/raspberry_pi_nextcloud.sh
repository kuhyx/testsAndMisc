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

wait_for_apt_lock() {
	local max_wait=600
	local waited=0

	while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock >/dev/null 2>&1; do
		if [[ $waited -eq 0 ]]; then
			log_info "Waiting for other apt/dpkg processes to finish..."
			pgrep -a 'apt|dpkg' | head -5 >&2 || true
		fi
		sleep 5
		waited=$((waited + 5))
		if [[ $waited -ge $max_wait ]]; then
			die "Timeout waiting for apt lock after ${max_wait}s"
		fi
		if [[ $((waited % 30)) -eq 0 ]]; then
			log_info "Still waiting... (${waited}s elapsed)"
		fi
	done

	if [[ $waited -gt 0 ]]; then
		log_success "Apt lock acquired after ${waited}s"
	fi
}

# =============================================================================
# Network Discovery (for remote installation)
# =============================================================================

ensure_dependencies() {
	local missing_packages=()

	if ! command -v nmap &>/dev/null; then
		missing_packages+=("nmap")
	fi

	if ! command -v sshpass &>/dev/null; then
		missing_packages+=("sshpass")
	fi

	if [[ ${#missing_packages[@]} -gt 0 ]]; then
		log_info "Installing missing packages: ${missing_packages[*]}"

		if command -v pacman &>/dev/null; then
			sudo pacman -S --noconfirm "${missing_packages[@]}"
		elif command -v apt-get &>/dev/null; then
			sudo apt-get update && sudo apt-get install -y "${missing_packages[@]}"
		elif command -v dnf &>/dev/null; then
			sudo dnf install -y "${missing_packages[@]}"
		else
			die "Could not detect package manager. Please install manually: ${missing_packages[*]}"
		fi
	fi
}

discover_raspberry_pi() {
	log_info "Auto-discovering Raspberry Pi on local network..."

	ensure_dependencies

	local my_ip
	my_ip=$(ip -4 addr show | grep -oP '(?<=inet\s)(?!127\.)\d+(\.\d+){3}' | head -1)
	local gateway
	gateway=$(ip route | grep default | awk '{print $3}' | head -1)
	local network="${gateway%.*}.0/24"

	log_info "Local IP: $my_ip, Network: $network"
	log_info "Scanning for Raspberry Pi (hostname: $PI_HOSTNAME)..."

	local pi_ip=""

	# Try resolving hostname directly
	pi_ip=$(getent hosts "$PI_HOSTNAME" 2>/dev/null | awk '{print $1}' | head -1) || true
	if [[ -z $pi_ip ]]; then
		pi_ip=$(getent hosts "${PI_HOSTNAME}.local" 2>/dev/null | awk '{print $1}' | head -1) || true
	fi

	if [[ -n $pi_ip ]]; then
		log_success "Found Pi by hostname: $pi_ip"
		echo "$pi_ip"
		return
	fi

	log_info "Hostname resolution failed, scanning network..."
	nmap -sn -T4 "$network" &>/dev/null || true

	local ssh_hosts
	ssh_hosts=$(nmap -p 22 --open -sT -T4 "$network" 2>/dev/null | grep "Nmap scan report" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -vw "$my_ip" | sort -u) || true

	if [[ -z $ssh_hosts ]]; then
		die "No SSH-enabled devices found. Is the Pi connected and booted?"
	fi

	log_info "Found SSH-enabled devices: $(echo "$ssh_hosts" | tr '\n' ' ')"

	for ip in $ssh_hosts; do
		log_info "Trying $ip with user '$PI_USER'..."

		if sshpass -p "$PI_PASSWORD" ssh -o BatchMode=no -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${PI_USER}@${ip}" "hostname" 2>/dev/null | grep -qi "$PI_HOSTNAME"; then
			log_success "Found Raspberry Pi at $ip"
			echo "$ip"
			return
		fi

		if sshpass -p "$PI_PASSWORD" ssh -o BatchMode=no -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${PI_USER}@${ip}" "echo ok" 2>/dev/null | grep -q "ok"; then
			log_success "Found device responding to Pi credentials at $ip"
			echo "$ip"
			return
		fi
	done

	die "Could not find Raspberry Pi on network."
}

# =============================================================================
# System Configuration Phase
# =============================================================================

phase_configure_system() {
	check_root

	log_info "=== Configuring Raspberry Pi System ==="

	wait_for_apt_lock

	log_info "Fixing any broken packages..."
	DEBIAN_FRONTEND=noninteractive dpkg --configure -a --force-confdef --force-confold || true

	log_info "Updating system packages..."
	apt-get update
	DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y

	log_info "Setting timezone to $PI_TIMEZONE..."
	timedatectl set-timezone "$PI_TIMEZONE"

	log_info "Configuring locale..."
	sed -i "s/^# *$PI_LOCALE/$PI_LOCALE/" /etc/locale.gen
	locale-gen
	update-locale LANG="$PI_LOCALE"

	log_info "Hardening SSH configuration..."
	cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

	cat >>/etc/ssh/sshd_config.d/hardening.conf <<'EOF'
# Security hardening
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

	systemctl restart sshd

	log_info "Installing useful packages..."
	DEBIAN_FRONTEND=noninteractive apt-get install -y \
		vim \
		htop \
		curl \
		wget \
		git \
		ufw \
		fail2ban \
		unattended-upgrades

	log_info "Configuring firewall..."
	ufw default deny incoming
	ufw default allow outgoing
	ufw allow ssh
	ufw allow 80/tcp
	ufw allow 443/tcp
	ufw --force enable

	log_info "Configuring fail2ban..."
	cat >/etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

	systemctl enable fail2ban
	systemctl restart fail2ban

	log_info "Enabling automatic security updates..."
	cat >/etc/apt/apt.conf.d/50unattended-upgrades <<'EOF'
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename},label=Debian-Security";
    "origin=Raspbian,codename=${distro_codename},label=Raspbian";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

	cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

	log_success "System configuration complete!"
}

# =============================================================================
# Nextcloud Installation Phase
# =============================================================================

phase_install_nextcloud() {
	check_root

	log_info "=== Installing Nextcloud ==="

	wait_for_apt_lock

	log_info "Installing Apache, PHP, MariaDB, and dependencies..."
	DEBIAN_FRONTEND=noninteractive apt-get install -y \
		apache2 \
		mariadb-server \
		php \
		php-gd \
		php-json \
		php-mysql \
		php-curl \
		php-mbstring \
		php-intl \
		php-imagick \
		php-xml \
		php-zip \
		php-bz2 \
		php-bcmath \
		php-gmp \
		php-apcu \
		php-redis \
		php-ldap \
		libapache2-mod-php \
		redis-server \
		certbot \
		python3-certbot-apache \
		imagemagick \
		libmagickcore-6.q16-6-extra

	log_success "Packages installed"

	# Configure MariaDB
	log_info "Configuring MariaDB..."

	local db_password
	db_password=$(generate_password 32)

	mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS nextcloud CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS 'nextcloud'@'localhost' IDENTIFIED BY '${db_password}';
GRANT ALL PRIVILEGES ON nextcloud.* TO 'nextcloud'@'localhost';
FLUSH PRIVILEGES;
EOF

	echo "$db_password" >/root/.nextcloud_db_password
	chmod 600 /root/.nextcloud_db_password
	log_success "MariaDB configured"

	# Download Nextcloud
	log_info "Downloading Nextcloud..."

	cd /tmp
	if [[ ! -f nextcloud.zip ]]; then
		wget -q --show-progress "https://download.nextcloud.com/server/releases/latest.zip" -O nextcloud.zip >&2
	fi

	rm -rf /var/www/nextcloud
	unzip -q nextcloud.zip -d /var/www/
	chown -R www-data:www-data /var/www/nextcloud

	log_success "Nextcloud downloaded and extracted"

	# Configure Apache
	log_info "Configuring Apache..."

	cat >/etc/apache2/sites-available/nextcloud.conf <<'EOF'
<VirtualHost *:80>
    ServerAdmin admin@localhost
    DocumentRoot /var/www/nextcloud

    <Directory /var/www/nextcloud/>
        Require all granted
        AllowOverride All
        Options FollowSymLinks MultiViews

        <IfModule mod_dav.c>
            Dav off
        </IfModule>
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/nextcloud_error.log
    CustomLog ${APACHE_LOG_DIR}/nextcloud_access.log combined
</VirtualHost>
EOF

	a2enmod rewrite
	a2enmod headers
	a2enmod env
	a2enmod dir
	a2enmod mime
	a2enmod ssl
	a2dissite 000-default
	a2ensite nextcloud

	systemctl restart apache2

	log_success "Apache configured"

	# Configure PHP
	log_info "Configuring PHP..."

	local php_version
	php_version=$(php -v | head -1 | grep -oP '\d+\.\d+')

	local php_ini="/etc/php/${php_version}/apache2/php.ini"

	sed -i 's/memory_limit = .*/memory_limit = 512M/' "$php_ini"
	sed -i 's/upload_max_filesize = .*/upload_max_filesize = 16G/' "$php_ini"
	sed -i 's/post_max_size = .*/post_max_size = 16G/' "$php_ini"
	sed -i 's/max_execution_time = .*/max_execution_time = 3600/' "$php_ini"
	sed -i 's/max_input_time = .*/max_input_time = 3600/' "$php_ini"
	sed -i 's/;date.timezone =.*/date.timezone = Europe\/Warsaw/' "$php_ini"

	if ! grep -q "opcache.interned_strings_buffer" "$php_ini"; then
		cat >>"$php_ini" <<'EOF'

; Nextcloud optimizations
opcache.enable=1
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.memory_consumption=128
opcache.save_comments=1
opcache.revalidate_freq=1

; APCu configuration
apc.enable_cli=1
EOF
	fi

	systemctl restart apache2

	log_success "PHP configured"

	# Configure Redis
	log_info "Configuring Redis..."

	systemctl enable redis-server
	systemctl start redis-server

	log_success "Redis configured"

	# Install Nextcloud
	log_info "Installing Nextcloud..."

	auto_generate_nextcloud_password

	local pi_ip
	pi_ip=$(hostname -I | awk '{print $1}')

	cd /var/www/nextcloud
	sudo -u www-data php occ maintenance:install \
		--database "mysql" \
		--database-name "nextcloud" \
		--database-user "nextcloud" \
		--database-pass "$db_password" \
		--admin-user "$NEXTCLOUD_ADMIN_USER" \
		--admin-pass "$NEXTCLOUD_ADMIN_PASSWORD" \
		--data-dir "$NEXTCLOUD_DATA_DIR"

	# Configure trusted domains
	sudo -u www-data php occ config:system:set trusted_domains 1 --value="$pi_ip"
	sudo -u www-data php occ config:system:set trusted_domains 2 --value="$PI_HOSTNAME"
	sudo -u www-data php occ config:system:set trusted_domains 3 --value="${PI_HOSTNAME}.local"

	# Configure caching
	sudo -u www-data php occ config:system:set memcache.local --value='\OC\Memcache\APCu'
	sudo -u www-data php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
	sudo -u www-data php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
	sudo -u www-data php occ config:system:set redis host --value='localhost'
	sudo -u www-data php occ config:system:set redis port --value=6379 --type=integer

	# Set default phone region
	sudo -u www-data php occ config:system:set default_phone_region --value='PL'

	# Set maintenance window
	sudo -u www-data php occ config:system:set maintenance_window_start --value=1 --type=integer

	log_success "Nextcloud installed"

	# Setup background jobs
	log_info "Setting up Nextcloud background jobs..."

	sudo -u www-data php occ background:cron

	# Add cron job
	(
		crontab -u www-data -l 2>/dev/null || true
		echo "*/5 * * * * php -f /var/www/nextcloud/cron.php"
	) | sort -u | crontab -u www-data -

	log_success "Cron jobs configured"

	# Verify installation
	log_info "Verifying Nextcloud installation..."

	if sudo -u www-data php occ status | grep -q "installed: true"; then
		log_success "Nextcloud is responding!"
		sudo -u www-data php occ status
	else
		log_warning "Nextcloud may not be fully configured"
	fi

	save_config

	log_success "========================================"
	log_success "Nextcloud installation complete!"
	log_success "========================================"
	log_info "Access Nextcloud at: http://$pi_ip"
	log_info "Admin user: $NEXTCLOUD_ADMIN_USER"
	log_info "Admin password: $NEXTCLOUD_ADMIN_PASSWORD"
	log_info "Database password saved at: /root/.nextcloud_db_password"
}

# =============================================================================
# Fix Nextcloud Issues
# =============================================================================

# shellcheck disable=SC2120  # Function does not use positional args
phase_fix_issues() {
	check_root

	log_info "=== Fixing Nextcloud Issues ==="

	cd /var/www/nextcloud

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
	cd /var/www/nextcloud
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
