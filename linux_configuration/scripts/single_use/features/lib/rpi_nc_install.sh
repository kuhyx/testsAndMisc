#!/bin/bash
# The Nextcloud install phase.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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

	cd /tmp || { log_error "Cannot enter /tmp"; return 1; }
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

	cd /var/www/nextcloud || { log_error "Nextcloud is not installed at /var/www/nextcloud"; return 1; }
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
