#!/bin/bash
# Package installation and the apt lock wait.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# =============================================================================
# PHASE 2: Configure Pi for Remote Access
# =============================================================================

wait_for_apt_lock() {
	# Wait for any existing apt/dpkg processes to finish
	local max_wait=600 # 10 minutes max
	local waited=0

	while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock >/dev/null 2>&1; do
		if [[ $waited -eq 0 ]]; then
			log_info "Waiting for other apt/dpkg processes to finish..."
			log_info "Current apt processes:"
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

phase_configure() {
	check_root

	log_info "=== Phase 2: Configure Raspberry Pi for Remote Access ==="

	# Wait for any existing apt processes
	wait_for_apt_lock

	# Fix any broken packages first
	log_info "Fixing any broken packages..."
	DEBIAN_FRONTEND=noninteractive dpkg --configure -a --force-confdef --force-confold || true

	# Update system - use non-interactive mode and auto-accept config changes
	log_info "Updating system packages..."
	apt-get update
	DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y

	# Set timezone
	log_info "Setting timezone to $PI_TIMEZONE..."
	timedatectl set-timezone "$PI_TIMEZONE"

	# Set locale
	log_info "Configuring locale..."
	sed -i "s/^# *$PI_LOCALE/$PI_LOCALE/" /etc/locale.gen
	locale-gen
	update-locale LANG="$PI_LOCALE"

	# Configure SSH for security
	log_info "Hardening SSH configuration..."

	# Backup original config
	cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

	# Apply security settings
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

	# Restart SSH
	systemctl restart sshd

	# Install useful packages
	log_info "Installing useful packages..."
	apt-get install -y \
		vim \
		htop \
		curl \
		wget \
		git \
		ufw \
		fail2ban \
		unattended-upgrades

	# Configure firewall
	log_info "Configuring firewall..."
	ufw default deny incoming
	ufw default allow outgoing
	ufw allow ssh
	ufw allow 80/tcp  # HTTP
	ufw allow 443/tcp # HTTPS
	ufw --force enable

	# Configure fail2ban
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

	# Enable automatic security updates
	log_info "Enabling automatic security updates..."
	cat >/etc/apt/apt.conf.d/50unattended-upgrades <<'EOF'
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename},label=Debian-Security";
    "origin=Raspbian,codename=${distro_codename},label=Raspbian";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

	systemctl enable unattended-upgrades

	# Display system info
	log_info "System information:"
	echo "Hostname: $(hostname)"
	echo "IP Address: $(hostname -I | awk '{print $1}')"
	echo "Kernel: $(uname -r)"
	echo "Architecture: $(uname -m)"

	log_success "Phase 2 complete!"
	echo
	log_info "Next step: Run 'sudo ./setup_nextcloud_raspberry.sh nextcloud' to install Nextcloud"
}

# =============================================================================
# PHASE 3: Install Nextcloud
# =============================================================================

install_nextcloud_dependencies() {
	log_info "Installing Nextcloud dependencies..."

	apt-get update
	apt-get install -y \
		apache2 \
		mariadb-server \
		libapache2-mod-php \
		php \
		php-gd \
		php-mysql \
		php-curl \
		php-mbstring \
		php-intl \
		php-gmp \
		php-bcmath \
		php-xml \
		php-zip \
		php-imagick \
		php-apcu \
		php-redis \
		redis-server \
		unzip \
		certbot \
		python3-certbot-apache

	log_success "Dependencies installed"
}
