#!/bin/bash
# MariaDB, PHP and the Nextcloud cron setup.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

configure_mariadb() {
	log_info "Configuring MariaDB..."

	# Generate random password for Nextcloud DB user
	local db_password
	db_password=$(openssl rand -base64 24)

	# Start and enable MariaDB
	systemctl start mariadb
	systemctl enable mariadb

	# Secure MariaDB installation
	mysql -e "DELETE FROM mysql.user WHERE User='';"
	mysql -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
	mysql -e "DROP DATABASE IF EXISTS test;"
	mysql -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
	mysql -e "FLUSH PRIVILEGES;"

	# Create Nextcloud database and user
	mysql -e "CREATE DATABASE IF NOT EXISTS nextcloud CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
	mysql -e "CREATE USER IF NOT EXISTS 'nextcloud'@'localhost' IDENTIFIED BY '$db_password';"
	mysql -e "GRANT ALL PRIVILEGES ON nextcloud.* TO 'nextcloud'@'localhost';"
	mysql -e "FLUSH PRIVILEGES;"

	# Save password for later use
	echo "$db_password" >/root/.nextcloud_db_password
	chmod 600 /root/.nextcloud_db_password

	log_success "MariaDB configured"
	echo "$db_password"
}

download_nextcloud() {
	log_info "Downloading Nextcloud..."

	local nc_version="30.0.2"
	local nc_url="https://download.nextcloud.com/server/releases/nextcloud-${nc_version}.zip"
	local download_dir="/tmp"
	local nc_zip="$download_dir/nextcloud.zip"

	if [[ -f $nc_zip ]]; then
		log_info "Nextcloud archive already downloaded"
	else
		wget -O "$nc_zip" "$nc_url"
	fi

	# Remove existing installation if present
	rm -rf /var/www/nextcloud

	# Extract
	unzip -q "$nc_zip" -d /var/www/

	# Set permissions
	chown -R www-data:www-data /var/www/nextcloud

	log_success "Nextcloud downloaded and extracted"
}

configure_apache() {
	log_info "Configuring Apache..."

	# Enable required modules
	a2enmod rewrite
	a2enmod headers
	a2enmod env
	a2enmod dir
	a2enmod mime
	a2enmod ssl

	# Get server IP for configuration
	local server_ip
	server_ip=$(hostname -I | awk '{print $1}')

	# Create Apache virtual host
	cat >/etc/apache2/sites-available/nextcloud.conf <<EOF
<VirtualHost *:80>
    ServerName $server_ip
    DocumentRoot /var/www/nextcloud

    <Directory /var/www/nextcloud/>
        Require all granted
        AllowOverride All
        Options FollowSymLinks MultiViews

        <IfModule mod_dav.c>
            Dav off
        </IfModule>
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/nextcloud_error.log
    CustomLog \${APACHE_LOG_DIR}/nextcloud_access.log combined
</VirtualHost>
EOF

	# Enable site and disable default
	a2dissite 000-default.conf
	a2ensite nextcloud.conf

	# Restart Apache
	systemctl restart apache2

	log_success "Apache configured"
}
