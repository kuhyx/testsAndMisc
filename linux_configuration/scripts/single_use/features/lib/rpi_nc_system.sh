#!/bin/bash
# System configuration phase.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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
