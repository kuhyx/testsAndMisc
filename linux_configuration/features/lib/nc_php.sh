#!/bin/bash
# PHP, Redis and the Nextcloud install itself.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep nc_services.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

configure_php() {
	log_info "Configuring PHP..."

	# Find PHP version
	local php_version
	php_version=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')
	local php_ini="/etc/php/${php_version}/apache2/php.ini"

	# Backup original
	cp "$php_ini" "${php_ini}.backup"

	# Apply Nextcloud recommended settings
	sed -i 's/memory_limit = .*/memory_limit = 512M/' "$php_ini"
	sed -i 's/upload_max_filesize = .*/upload_max_filesize = 16G/' "$php_ini"
	sed -i 's/post_max_size = .*/post_max_size = 16G/' "$php_ini"
	sed -i 's/max_execution_time = .*/max_execution_time = 360/' "$php_ini"
	sed -i 's/max_input_time = .*/max_input_time = 360/' "$php_ini"
	sed -i 's/;date.timezone.*/date.timezone = Europe\/Warsaw/' "$php_ini"

	# Configure OPcache
	cat >>"$php_ini" <<'EOF'

; Nextcloud OPcache settings
opcache.enable=1
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.memory_consumption=128
opcache.save_comments=1
opcache.revalidate_freq=1
EOF

	# Configure APCu
	echo "apc.enable_cli=1" >>"/etc/php/${php_version}/mods-available/apcu.ini"

	systemctl restart apache2

	log_success "PHP configured"
}

configure_redis() {
	log_info "Configuring Redis..."

	systemctl enable redis-server
	systemctl start redis-server

	log_success "Redis configured"
}

install_nextcloud() {
	log_info "Installing Nextcloud..."

	local db_password
	db_password=$(cat /root/.nextcloud_db_password)

	if [[ -z $NEXTCLOUD_ADMIN_PASSWORD ]]; then
		prompt_password "Enter Nextcloud admin password" NEXTCLOUD_ADMIN_PASSWORD
	fi

	# Create data directory
	mkdir -p "$NEXTCLOUD_DATA_DIR"
	chown -R www-data:www-data "$NEXTCLOUD_DATA_DIR"

	# Get server IP
	local server_ip
	server_ip=$(hostname -I | awk '{print $1}')

	# Run Nextcloud installer
	cd /var/www/nextcloud || { log_error "Nextcloud is not installed at /var/www/nextcloud"; return 1; }
	sudo -u www-data php occ maintenance:install \
		--database "mysql" \
		--database-name "nextcloud" \
		--database-user "nextcloud" \
		--database-pass "$db_password" \
		--admin-user "$NEXTCLOUD_ADMIN_USER" \
		--admin-pass "$NEXTCLOUD_ADMIN_PASSWORD" \
		--data-dir "$NEXTCLOUD_DATA_DIR"

	# Add trusted domain
	sudo -u www-data php occ config:system:set trusted_domains 1 --value="$server_ip"
	sudo -u www-data php occ config:system:set trusted_domains 2 --value="$PI_HOSTNAME"
	sudo -u www-data php occ config:system:set trusted_domains 3 --value="$PI_HOSTNAME.local"

	# Configure Redis caching
	sudo -u www-data php occ config:system:set memcache.local --value='\OC\Memcache\APCu'
	sudo -u www-data php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
	sudo -u www-data php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
	sudo -u www-data php occ config:system:set redis host --value='localhost'
	sudo -u www-data php occ config:system:set redis port --value='6379' --type=integer

	# Set default phone region
	sudo -u www-data php occ config:system:set default_phone_region --value='PL'

	# Enable maintenance window
	sudo -u www-data php occ config:system:set maintenance_window_start --value=1 --type=integer

	log_success "Nextcloud installed"
}

setup_nextcloud_cron() {
	log_info "Setting up Nextcloud background jobs..."

	# Add cron job for background tasks
	crontab -u www-data -l 2>/dev/null || echo "" | crontab -u www-data -
	(
		crontab -u www-data -l 2>/dev/null | grep -v 'nextcloud/cron.php'
		echo "*/5 * * * * php -f /var/www/nextcloud/cron.php"
	) | crontab -u www-data -

	# Switch to cron background job mode
	cd /var/www/nextcloud || { log_error "Nextcloud is not installed at /var/www/nextcloud"; return 1; }
	sudo -u www-data php occ background:cron

	log_success "Cron jobs configured"
}

verify_nextcloud() {
	log_info "Verifying Nextcloud installation..."

	local server_ip
	server_ip=$(hostname -I | awk '{print $1}')

	# Check if Nextcloud is responding
	if curl -s -o /dev/null -w "%{http_code}" "http://${server_ip}/status.php" | grep -q "200"; then
		log_success "Nextcloud is responding!"
	else
		log_warning "Nextcloud may not be fully ready. Check manually."
	fi

	# Run Nextcloud check
	cd /var/www/nextcloud || { log_error "Nextcloud is not installed at /var/www/nextcloud"; return 1; }
	sudo -u www-data php occ status

	echo
	log_success "========================================"
	log_success "Nextcloud installation complete!"
	log_success "========================================"
	echo
	log_info "Access Nextcloud at: http://${server_ip}"
	log_info "Admin user: $NEXTCLOUD_ADMIN_USER"
	log_info "Database password saved at: /root/.nextcloud_db_password"
	echo
	log_info "Recommended next steps:"
	log_info "1. Set up a domain name pointing to your Pi"
	log_info "2. Configure SSL with: sudo certbot --apache"
	log_info "3. Install Nextcloud apps via the web interface"
	log_info "4. Configure external storage if needed"
}

phase_nextcloud() {
	check_root

	log_info "=== Phase 3: Install Nextcloud ==="

	install_nextcloud_dependencies
	local db_password
	db_password=$(configure_mariadb)
	download_nextcloud
	configure_apache
	configure_php
	configure_redis
	install_nextcloud
	setup_nextcloud_cron
	verify_nextcloud

	log_success "Phase 3 complete!"
}
