#!/bin/bash
# Raspberry Pi OS download and SD-card flashing.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

download_raspberry_pi_os() {
	local download_dir="/tmp/rpi-image"
	local image_url="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-11-19/2024-11-19-raspios-bookworm-arm64-lite.img.xz"
	local image_file="$download_dir/raspios.img.xz"
	local extracted_image="$download_dir/raspios.img"
	local expected_size=459000608 # Size in bytes from content-length

	mkdir -p "$download_dir"

	if [[ -f $extracted_image ]]; then
		log_info "Using existing image at $extracted_image"
		echo "$extracted_image"
		return
	fi

	# Check if download exists and is complete
	if [[ -f $image_file ]]; then
		local actual_size
		actual_size=$(stat -c%s "$image_file" 2>/dev/null || stat -f%z "$image_file" 2>/dev/null || echo 0)
		if [[ $actual_size -lt $expected_size ]]; then
			log_warning "Incomplete download detected ($actual_size < $expected_size bytes), re-downloading..."
			rm -f "$image_file"
		else
			log_info "Image archive already downloaded"
		fi
	fi

	if [[ ! -f $image_file ]]; then
		log_info "Downloading Raspberry Pi OS Lite (64-bit)..."
		log_info "This may take a while depending on your internet connection..."

		# Try to use aria2c for faster download, fall back to wget/curl
		# Redirect all output to stderr so it doesn't interfere with function return value
		if command -v aria2c &>/dev/null; then
			aria2c -x 4 -c -d "$download_dir" --out="raspios.img.xz" "$image_url" >&2
		elif command -v wget &>/dev/null; then
			wget --continue --show-progress -O "$image_file" "$image_url" >&2
		elif command -v curl &>/dev/null; then
			curl -L -C - -o "$image_file" "$image_url" --progress-bar >&2
		else
			die "No download tool available. Install wget, curl, or aria2c"
		fi

		# Verify download size
		local actual_size
		actual_size=$(stat -c%s "$image_file" 2>/dev/null || stat -f%z "$image_file" 2>/dev/null || echo 0)
		if [[ $actual_size -lt $expected_size ]]; then
			die "Download incomplete: got $actual_size bytes, expected $expected_size"
		fi
		log_success "Download complete: $actual_size bytes"
	fi

	log_info "Extracting image..."
	xz -dk "$image_file"

	if [[ ! -f $extracted_image ]]; then
		die "Failed to extract image"
	fi

	echo "$extracted_image"
}

flash_sd_card() {
	local image_path="$1"

	log_warning "This will ERASE ALL DATA on $SD_CARD_DEVICE"
	read -r -p "Are you sure you want to continue? (yes/no): " confirm

	if [[ $confirm != "yes" ]]; then
		die "Aborted by user"
	fi

	# Unmount any mounted partitions
	log_info "Unmounting partitions on $SD_CARD_DEVICE..."
	for partition in "${SD_CARD_DEVICE}"*; do
		if mountpoint -q "$partition" 2>/dev/null || mount | grep -q "$partition"; then
			umount "$partition" 2>/dev/null || true
		fi
	done

	log_info "Flashing image to SD card..."
	log_info "This will take several minutes..."

	dd if="$image_path" of="$SD_CARD_DEVICE" bs=4M status=progress conv=fsync

	sync
	log_success "Image flashed successfully!"
}

configure_headless_boot() {
	log_info "Configuring headless boot (SSH and WiFi)..."

	# Wait for partitions to be available
	sleep 2
	partprobe "$SD_CARD_DEVICE" 2>/dev/null || true
	sleep 2

	# Mount boot partition
	local boot_partition
	if [[ -b "${SD_CARD_DEVICE}1" ]]; then
		boot_partition="${SD_CARD_DEVICE}1"
	elif [[ -b "${SD_CARD_DEVICE}p1" ]]; then
		boot_partition="${SD_CARD_DEVICE}p1"
	else
		die "Could not find boot partition"
	fi

	local boot_mount="/tmp/rpi-boot"
	mkdir -p "$boot_mount"
	mount "$boot_partition" "$boot_mount"

	# Enable SSH
	touch "$boot_mount/ssh"
	log_success "SSH enabled"

	# Configure WiFi (optional)
	read -r -p "Do you want to configure WiFi? (y/n): " configure_wifi
	if [[ $configure_wifi == "y" ]]; then
		read -r -p "WiFi SSID: " wifi_ssid
		read -r -s -p "WiFi Password: " wifi_password
		echo

		cat >"$boot_mount/wpa_supplicant.conf" <<EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$wifi_ssid"
    psk="$wifi_password"
    key_mgmt=WPA-PSK
}
EOF
		log_success "WiFi configured"
	fi

	# Create userconf.txt for first user (Raspberry Pi OS Bookworm+)
	if [[ -z $PI_PASSWORD ]]; then
		prompt_password "Enter password for Pi user '$PI_USER'" PI_PASSWORD
	fi

	local encrypted_password
	encrypted_password=$(echo "$PI_PASSWORD" | openssl passwd -6 -stdin)
	echo "${PI_USER}:${encrypted_password}" >"$boot_mount/userconf.txt"
	log_success "User '$PI_USER' configured"

	# Set hostname
	local root_partition
	if [[ -b "${SD_CARD_DEVICE}2" ]]; then
		root_partition="${SD_CARD_DEVICE}2"
	elif [[ -b "${SD_CARD_DEVICE}p2" ]]; then
		root_partition="${SD_CARD_DEVICE}p2"
	fi

	if [[ -n $root_partition ]]; then
		local root_mount="/tmp/rpi-root"
		mkdir -p "$root_mount"
		mount "$root_partition" "$root_mount"

		echo "$PI_HOSTNAME" >"$root_mount/etc/hostname"
		sed -i "s/raspberrypi/$PI_HOSTNAME/g" "$root_mount/etc/hosts"

		log_success "Hostname set to '$PI_HOSTNAME'"

		umount "$root_mount"
	fi

	umount "$boot_mount"

	log_success "SD card configured for headless boot!"
	log_info "Insert the SD card into your Raspberry Pi and power it on."
	log_info "Find the Pi's IP address from your router or use: nmap -sn 192.168.1.0/24"
}
