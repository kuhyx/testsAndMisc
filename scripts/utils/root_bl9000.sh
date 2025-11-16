#!/usr/bin/env bash

# Root BL9000 phone from Arch Linux
#
# This script automates the rooting process for BL9000 phones using Magisk.
# It handles:
# - Installing required dependencies (ADB, fastboot, boot image tools)
# - Detecting and connecting to the device
# - Unlocking the bootloader (with user confirmation)
# - Extracting boot image from device
# - Patching boot image with Magisk
# - Flashing patched boot image
#
# Prerequisites:
# - USB debugging must be enabled on the phone
# - OEM unlocking must be enabled in Developer Options
# - Phone should be charged to at least 50%
#
# Conventions: sudo re-exec, idempotent, log with timestamps, follow repo style

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/bl9000-root.log"
WORK_DIR="${HOME}/.cache/bl9000-root"
MAGISK_APK_URL="https://github.com/topjohnwu/Magisk/releases/latest/download/Magisk.apk"
BOOT_IMG=""
PATCHED_BOOT_IMG=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

timestamp() { date '+%Y-%m-%d %H:%M:%S%z'; }

log() {
	local msg="$1"
	echo -e "${GREEN}[$(timestamp)]${NC} $msg"
	if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e $LOG_FILE && -w /var/log ]]; then
		echo "[$(timestamp)] $msg" >>"$LOG_FILE" 2>&1 || true
	fi
}

warn() {
	local msg="$1"
	echo -e "${YELLOW}[WARN]${NC} $msg" >&2
	if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e $LOG_FILE && -w /var/log ]]; then
		echo "[$(timestamp)] [WARN] $msg" >>"$LOG_FILE" 2>&1 || true
	fi
}

error() {
	local msg="$1"
	echo -e "${RED}[ERROR]${NC} $msg" >&2
	if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e $LOG_FILE && -w /var/log ]]; then
		echo "[$(timestamp)] [ERROR] $msg" >>"$LOG_FILE" 2>&1 || true
	fi
}

die() {
	error "$1"
	exit 1
}

print_header() {
	echo
	echo -e "${BLUE}========================================${NC}"
	echo -e "${BLUE}  $1${NC}"
	echo -e "${BLUE}========================================${NC}"
	echo
}

confirm() {
	local prompt="$1"
	local reply
	read -r -p "$(echo -e "${YELLOW}${prompt}${NC} [y/N]: ")" reply
	case "$reply" in
	[Yy][Ee][Ss] | [Yy]) return 0 ;;
	*) return 1 ;;
	esac
}

require_non_root() {
	if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
		die "Do not run this script as root. ADB must run as your regular user to access USB devices properly."
	fi
}

usage() {
	cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] [COMMAND]

Root BL9000 phone from Arch Linux using Magisk.

Commands:
  install-deps      Install required dependencies (adb, fastboot, tools)
  check             Check device connection and prerequisites
  backup            Backup phone data before unlocking bootloader
  unlock            Unlock bootloader (WARNING: wipes all data!)
  root              Extract boot, patch with Magisk, and flash
  full              Run complete rooting process (deps + unlock + root)
  clean             Remove temporary working directory
  help              Show this message

Options:
  -h, --help        Show this message
  --work-dir DIR    Set working directory (default: $WORK_DIR)
  --boot-img FILE   Use existing boot.img instead of extracting from device

Examples:
  $SCRIPT_NAME install-deps        # Install required tools
  $SCRIPT_NAME check               # Verify device connection
  $SCRIPT_NAME backup              # Backup phone data first!
  $SCRIPT_NAME full                # Complete rooting process
  $SCRIPT_NAME root                # Root only (assumes bootloader unlocked)

WARNING: Unlocking the bootloader will ERASE ALL DATA on your phone!
         Make sure to back up important data before proceeding.

EOF
}

install_dependencies() {
	print_header "Installing Dependencies"

	local packages=()
	local missing=()

	# Check for required commands
	if ! command -v adb >/dev/null 2>&1; then
		packages+=("android-tools")
		missing+=("adb")
	fi

	if ! command -v fastboot >/dev/null 2>&1 && ! pacman -Q android-tools >/dev/null 2>&1; then
		packages+=("android-tools")
		missing+=("fastboot")
	fi

	if ! command -v unzip >/dev/null 2>&1; then
		packages+=("unzip")
		missing+=("unzip")
	fi

	if ! command -v curl >/dev/null 2>&1; then
		packages+=("curl")
		missing+=("curl")
	fi

	if ! command -v python3 >/dev/null 2>&1; then
		packages+=("python")
		missing+=("python3")
	fi

	# Check for python-protobuf (needed for boot image tools)
	if ! python3 -c "import google.protobuf" 2>/dev/null; then
		packages+=("python-protobuf")
		missing+=("python-protobuf")
	fi

	if [[ ${#missing[@]} -eq 0 ]]; then
		log "All dependencies are already installed."
		return 0
	fi

	log "Missing dependencies: ${missing[*]}"

	# Remove duplicates
	readarray -t packages < <(printf '%s\n' "${packages[@]}" | sort -u)

	if ! confirm "Install missing packages: ${packages[*]}?"; then
		die "Cannot proceed without required dependencies."
	fi

	log "Installing packages: ${packages[*]}"
	sudo pacman -S --needed --noconfirm "${packages[@]}" || die "Failed to install dependencies"

	# Install payload-dumper-go from AUR if not present (for extracting boot.img from payload.bin)
	if ! command -v payload-dumper-go >/dev/null 2>&1; then
		if confirm "Install payload-dumper-go from AUR for extracting boot images?"; then
			if command -v yay >/dev/null 2>&1; then
				yay -S --needed --noconfirm payload-dumper-go || warn "Failed to install payload-dumper-go (optional)"
			elif command -v paru >/dev/null 2>&1; then
				paru -S --needed --noconfirm payload-dumper-go || warn "Failed to install payload-dumper-go (optional)"
			else
				warn "No AUR helper found. Install payload-dumper-go manually if needed."
			fi
		fi
	fi

	log "Dependencies installed successfully."
}

setup_udev_rules() {
	print_header "Setting Up USB Access"

	local udev_file="/etc/udev/rules.d/51-android.rules"

	if [[ -f $udev_file ]]; then
		log "Android udev rules already exist at $udev_file"
		return 0
	fi

	if ! confirm "Create udev rules for Android device access?"; then
		warn "Skipping udev rules. You may need to run commands with sudo."
		return 0
	fi

	log "Creating Android udev rules..."

	# Create comprehensive udev rules for Android devices
	sudo tee "$udev_file" >/dev/null <<'EOF'
# Android Debug Bridge (ADB) devices
# Add your device's vendor ID if not listed

# Google
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="adbusers"
# MediaTek (common in BL9000)
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="adbusers"
# Generic catch-all for Android devices
SUBSYSTEM=="usb", ATTR{idVendor}=="*", ATTR{idProduct}=="*", MODE="0666", GROUP="adbusers", SYMLINK+="android%n"
EOF

	# Create adbusers group if it doesn't exist
	if ! getent group adbusers >/dev/null; then
		sudo groupadd -r adbusers
		log "Created adbusers group"
	fi

	# Add current user to adbusers group
	if ! groups "$USER" | grep -q '\badbusers\b'; then
		sudo usermod -aG adbusers "$USER"
		log "Added $USER to adbusers group"
		warn "You need to log out and back in for group membership to take effect."
		warn "Alternatively, run: newgrp adbusers"
	fi

	# Reload udev rules
	sudo udevadm control --reload-rules
	sudo udevadm trigger

	log "USB access configured successfully."
}

backup_device_data() {
	print_header "Backing Up Device Data"

	local backup_dir
	backup_dir="${WORK_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
	mkdir -p "$backup_dir"

	log "Backup directory: $backup_dir" # Check device connection first
	if ! adb get-state >/dev/null 2>&1; then
		error "Device not connected. Please connect your device first."
		return 1
	fi

	log "Starting comprehensive backup process..."

	# 1. Backup internal storage (DCIM, Pictures, Documents, Downloads, etc.)
	log "Backing up internal storage (this may take a while)..."
	local storage_dirs=("DCIM" "Pictures" "Documents" "Download" "Music" "Movies" "WhatsApp" "Telegram")

	for dir in "${storage_dirs[@]}"; do
		if adb shell "[ -d /sdcard/$dir ]" 2>/dev/null; then
			log "  → Backing up /sdcard/$dir..."
			if adb pull "/sdcard/$dir" "$backup_dir/$dir" 2>&1 | grep -v "^$"; then
				log "    ✓ $dir backed up successfully"
			else
				warn "    ⚠ Could not backup $dir (may be empty or inaccessible)"
			fi
		fi
	done

	# 2. Backup SMS/MMS (if possible)
	log "Backing up SMS/MMS database..."
	if adb shell "su -c 'cp /data/data/com.android.providers.telephony/databases/mmssms.db /sdcard/mmssms.db'" 2>/dev/null; then
		adb pull /sdcard/mmssms.db "$backup_dir/mmssms.db" 2>/dev/null && log "  ✓ SMS/MMS backed up"
		adb shell "rm /sdcard/mmssms.db" 2>/dev/null || true
	else
		warn "  ⚠ SMS/MMS backup requires root (skipping)"
	fi

	# 3. Backup contacts
	log "Backing up contacts..."
	if adb shell "su -c 'cp /data/data/com.android.providers.contacts/databases/contacts2.db /sdcard/contacts2.db'" 2>/dev/null; then
		adb pull /sdcard/contacts2.db "$backup_dir/contacts2.db" 2>/dev/null && log "  ✓ Contacts backed up"
		adb shell "rm /sdcard/contacts2.db" 2>/dev/null || true
	else
		warn "  ⚠ Contacts backup requires root (skipping)"
	fi

	# 4. Backup call logs
	log "Backing up call logs..."
	if adb shell "su -c 'cp /data/data/com.android.providers.contacts/databases/calllog.db /sdcard/calllog.db'" 2>/dev/null; then
		adb pull /sdcard/calllog.db "$backup_dir/calllog.db" 2>/dev/null && log "  ✓ Call logs backed up"
		adb shell "rm /sdcard/calllog.db" 2>/dev/null || true
	else
		warn "  ⚠ Call logs backup requires root (skipping)"
	fi

	# 5. Backup app list
	log "Backing up installed apps list..."
	adb shell "pm list packages -f" >"$backup_dir/installed_apps.txt"
	log "  ✓ App list saved to installed_apps.txt"

	# 6. Backup APKs for user-installed apps (optional, can be large)
	if confirm "Backup APK files for installed apps? (This can take a long time and use lots of space)"; then
		log "Backing up user-installed APKs..."
		local apk_dir="$backup_dir/apks"
		mkdir -p "$apk_dir"

		# Get user-installed packages
		local user_apps
		user_apps=$(adb shell "pm list packages -3 -f" | sed 's/package://' | cut -d'=' -f2)

		local count=0
		while IFS= read -r pkg; do
			if [[ -n $pkg ]]; then
				log "  → Backing up $pkg..."
				local apk_path
				apk_path=$(adb shell "pm path $pkg" | head -n1 | sed 's/package://')
				if [[ -n $apk_path ]]; then
					adb pull "$apk_path" "$apk_dir/${pkg}.apk" >/dev/null 2>&1 && count=$((count + 1))
				fi
			fi
		done <<<"$user_apps"

		log "  ✓ Backed up $count APK files"
	fi

	# 7. Full ADB backup (app data, if device supports it)
	log "Creating full ADB backup (app data)..."
	if confirm "Create full ADB backup? (You'll need to confirm on your device)"; then
		echo
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
		echo "  On your phone: Tap 'Back up my data' when prompted"
		echo "  You can set a password or leave it blank"
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
		echo

		if adb backup -apk -shared -all -system -f "$backup_dir/full_backup.ab"; then
			log "  ✓ Full ADB backup completed"
			log "    Note: Restore with: adb restore full_backup.ab"
		else
			warn "  ⚠ ADB backup failed or was cancelled"
		fi
	fi

	# 8. Backup device info
	log "Saving device information..."
	{
		echo "Device Backup Information"
		echo "========================="
		echo "Date: $(date)"
		echo
		echo "Device Model: $(adb shell getprop ro.product.model | tr -d '\r\n')"
		echo "Android Version: $(adb shell getprop ro.build.version.release | tr -d '\r\n')"
		echo "Build Number: $(adb shell getprop ro.build.display.id | tr -d '\r\n')"
		echo "Security Patch: $(adb shell getprop ro.build.version.security_patch | tr -d '\r\n')"
		echo "Serial: $(adb shell getprop ro.serialno | tr -d '\r\n')"
		echo
		echo "Installed Apps:"
		adb shell "pm list packages -3" | sed 's/package:/  - /'
	} >"$backup_dir/device_info.txt"

	log "  ✓ Device info saved"

	# Summary
	local backup_size
	backup_size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1 || echo "unknown")

	echo
	echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
	echo -e "${GREEN}║            Backup Completed Successfully!             ║${NC}"
	echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
	echo
	log "Backup location: $backup_dir"
	log "Backup size: $backup_size"
	echo
	echo "What was backed up:"
	echo "  ✓ Photos (DCIM)"
	echo "  ✓ Pictures"
	echo "  ✓ Documents"
	echo "  ✓ Downloads"
	echo "  ✓ Music"
	echo "  ✓ Movies"
	echo "  ✓ WhatsApp data (if present)"
	echo "  ✓ Telegram data (if present)"
	echo "  ✓ Installed apps list"
	echo "  ✓ Device information"
	if [[ -f "$backup_dir/full_backup.ab" ]]; then
		echo "  ✓ Full app data backup"
	fi
	if [[ -d "$backup_dir/apks" ]]; then
		echo "  ✓ APK files"
	fi
	echo
	log "Keep this backup safe! You'll need it to restore your data after rooting."

	return 0
}

check_device() {
	print_header "Checking Device Connection"

	log "Starting ADB server..."
	adb start-server >/dev/null 2>&1 || true

	log "Waiting for device..."
	if ! adb wait-for-device; then
		error "Failed to detect device via ADB."
		echo
		echo "Troubleshooting steps:"
		echo "1. Make sure USB debugging is enabled on your phone"
		echo "   Settings → About Phone → Tap Build Number 7 times"
		echo "   Settings → Developer Options → Enable USB Debugging"
		echo "2. Connect your phone via USB cable"
		echo "3. Accept the 'Allow USB debugging' prompt on your phone"
		echo "4. Run: adb devices"
		echo
		return 1
	fi

	local device_info
	device_info=$(adb devices -l | grep -v "List of devices" | grep -v "^$" | head -n1)

	if [[ -z $device_info ]]; then
		error "No device detected"
		return 1
	fi

	log "Device connected: $device_info"

	# Check device properties
	local model
	model=$(adb shell getprop ro.product.model 2>/dev/null | tr -d '\r\n' || echo "Unknown")
	log "Model: $model"

	local android_version
	android_version=$(adb shell getprop ro.build.version.release 2>/dev/null | tr -d '\r\n' || echo "Unknown")
	log "Android version: $android_version"

	local battery_level
	battery_level=$(adb shell dumpsys battery | grep level | awk '{print $2}' | tr -d '\r\n' || echo "Unknown")
	log "Battery level: ${battery_level}%"

	if [[ $battery_level != "Unknown" && $battery_level -lt 50 ]]; then
		warn "Battery level is below 50%. Charge your phone before proceeding."
		if ! confirm "Continue anyway?"; then
			return 1
		fi
	fi

	# Check if bootloader is unlocked
	local unlock_status
	unlock_status=$(adb shell getprop ro.boot.verifiedbootstate 2>/dev/null | tr -d '\r\n' || echo "unknown")
	if [[ $unlock_status == "orange" || $unlock_status == "red" ]]; then
		log "Bootloader unlock status: ${GREEN}UNLOCKED${NC}"
	else
		warn "Bootloader appears to be LOCKED. You'll need to unlock it to root."
	fi

	# Check if OEM unlocking is enabled
	local oem_unlock
	oem_unlock=$(adb shell getprop sys.oem_unlock_allowed 2>/dev/null | tr -d '\r\n' || echo "unknown")
	if [[ $oem_unlock == "1" ]]; then
		log "OEM unlocking: ${GREEN}ENABLED${NC}"
	else
		warn "OEM unlocking is not enabled in Developer Options."
		echo "Enable it at: Settings → Developer Options → OEM unlocking"
	fi

	return 0
}

unlock_bootloader() {
	print_header "Unlocking Bootloader"

	echo
	echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
	echo -e "${RED}║                         WARNING                               ║${NC}"
	echo -e "${RED}║                                                               ║${NC}"
	echo -e "${RED}║  Unlocking the bootloader will ERASE ALL DATA on your phone! ║${NC}"
	echo -e "${RED}║                                                               ║${NC}"
	echo -e "${RED}║  This includes:                                               ║${NC}"
	echo -e "${RED}║  - All apps and app data                                      ║${NC}"
	echo -e "${RED}║  - Photos, videos, and files                                  ║${NC}"
	echo -e "${RED}║  - System settings                                            ║${NC}"
	echo -e "${RED}║  - Everything else on internal storage                        ║${NC}"
	echo -e "${RED}║                                                               ║${NC}"
	echo -e "${RED}║  Make sure you have backed up important data!                 ║${NC}"
	echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
	echo

	if ! confirm "Have you backed up all important data and want to proceed?"; then
		log "Bootloader unlock cancelled by user."
		return 1
	fi

	if ! confirm "Are you ABSOLUTELY SURE? This cannot be undone!"; then
		log "Bootloader unlock cancelled by user."
		return 1
	fi

	log "Rebooting device to bootloader..."
	adb reboot bootloader || die "Failed to reboot to bootloader"

	log "Waiting for fastboot mode..."
	sleep 5

	if ! fastboot devices | grep -q .; then
		error "Device not detected in fastboot mode."
		echo
		echo "If the device doesn't enter fastboot automatically:"
		echo "1. Power off the phone completely"
		echo "2. Hold Volume Down + Power buttons simultaneously"
		echo "3. Release when you see the bootloader/fastboot screen"
		echo "4. Run: fastboot devices"
		echo
		return 1
	fi

	log "Device in fastboot mode"

	# Check current bootloader status
	local bl_status
	bl_status=$(fastboot getvar unlocked 2>&1 | grep "unlocked:" | awk '{print $2}' || echo "unknown")
	if [[ $bl_status == "yes" ]]; then
		log "Bootloader is already unlocked."
		fastboot reboot
		return 0
	fi

	log "Attempting to unlock bootloader..."

	# Try different unlock commands (varies by device)
	if fastboot flashing unlock 2>&1 | grep -qi "okay\|finished"; then
		log "Bootloader unlock command sent successfully."
	elif fastboot oem unlock 2>&1 | grep -qi "okay\|finished"; then
		log "Bootloader unlock command sent successfully."
	else
		error "Bootloader unlock command may have failed."
		echo
		echo "On your phone:"
		echo "1. Use volume buttons to select 'Unlock the bootloader'"
		echo "2. Press power button to confirm"
		echo

		if ! confirm "Did you complete the unlock on the device?"; then
			fastboot reboot
			return 1
		fi
	fi

	log "Rebooting device..."
	fastboot reboot || true

	log "Bootloader unlocked successfully!"
	log "Device will now boot up and perform factory reset..."
	log "Waiting for device to come back online..."

	sleep 10
	adb wait-for-device || true

	log "Please complete the initial setup on your phone, then re-enable USB debugging."
	echo

	return 0
}

download_magisk() {
	print_header "Downloading Magisk"

	local magisk_apk="$WORK_DIR/magisk.apk"

	if [[ -f $magisk_apk ]]; then
		log "Magisk APK already downloaded at $magisk_apk"
		return 0
	fi

	log "Downloading latest Magisk APK..."
	if ! curl -L -o "$magisk_apk" "$MAGISK_APK_URL"; then
		error "Failed to download Magisk APK"
		return 1
	fi

	log "Magisk downloaded successfully: $magisk_apk"
	return 0
}

extract_boot_image() {
	print_header "Extracting Boot Image"

	local boot_img="$WORK_DIR/boot.img"

	if [[ -n ${BOOT_IMG:-} && -f $BOOT_IMG ]]; then
		log "Using provided boot image: $BOOT_IMG"
		cp "$BOOT_IMG" "$boot_img"
		BOOT_IMG="$boot_img"
		return 0
	fi

	log "Attempting to extract boot image from device..."

	# Method 1: Try to pull boot partition directly
	local boot_partition
	boot_partition=$(adb shell "find /dev/block -name boot | head -n1" 2>/dev/null | tr -d '\r\n' || echo "")

	if [[ -n $boot_partition ]]; then
		log "Found boot partition: $boot_partition"
		if adb pull "$boot_partition" "$boot_img" 2>/dev/null; then
			log "Boot image extracted successfully"
			BOOT_IMG="$boot_img"
			return 0
		fi
	fi

	# Method 2: Try to get boot partition via by-name
	boot_partition=$(adb shell "ls /dev/block/by-name/boot*" 2>/dev/null | head -n1 | tr -d '\r\n' || echo "")

	if [[ -n $boot_partition ]]; then
		log "Found boot partition: $boot_partition"
		if adb shell "su -c 'dd if=$boot_partition of=/sdcard/boot.img'" 2>/dev/null &&
			adb pull /sdcard/boot.img "$boot_img" 2>/dev/null; then
			adb shell rm /sdcard/boot.img 2>/dev/null || true
			log "Boot image extracted successfully"
			BOOT_IMG="$boot_img"
			return 0
		fi
	fi

	error "Failed to extract boot image automatically."
	echo
	echo "Manual extraction options:"
	echo "1. Extract boot.img from your device's firmware package"
	echo "2. Use MTK Droid Tools (for MediaTek devices)"
	echo "3. Get boot.img from device manufacturer's official ROM"
	echo
	echo "Then run: $SCRIPT_NAME root --boot-img /path/to/boot.img"
	echo

	return 1
}

patch_boot_with_magisk() {
	print_header "Patching Boot Image with Magisk"

	if [[ ! -f ${BOOT_IMG:-} ]]; then
		die "Boot image not found: ${BOOT_IMG:-none}"
	fi

	local magisk_apk="$WORK_DIR/magisk.apk"
	if [[ ! -f $magisk_apk ]]; then
		die "Magisk APK not found. Run download step first."
	fi

	log "Installing Magisk APK on device..."
	if ! adb install -r "$magisk_apk" 2>/dev/null; then
		error "Failed to install Magisk APK"
		return 1
	fi

	log "Pushing boot image to device..."
	adb push "$BOOT_IMG" /sdcard/Download/boot.img || die "Failed to push boot image"

	echo
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo "  MANUAL STEP REQUIRED"
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo
	echo "On your phone:"
	echo "1. Open the Magisk app"
	echo "2. Tap 'Install' next to Magisk"
	echo "3. Select 'Select and Patch a File'"
	echo "4. Navigate to Downloads and select boot.img"
	echo "5. Tap 'Let's Go' and wait for patching to complete"
	echo "6. The patched file will be saved as magisk_patched_*.img"
	echo
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo

	if ! confirm "Have you completed patching the boot image in Magisk app?"; then
		error "Patching cancelled by user"
		return 1
	fi

	log "Pulling patched boot image from device..."

	local patched_img
	patched_img=$(adb shell "ls /sdcard/Download/magisk_patched_*.img 2>/dev/null" | tr -d '\r\n' | head -n1 || echo "")

	if [[ -z $patched_img ]]; then
		error "Could not find patched boot image on device."
		echo "Please ensure the patching completed successfully in Magisk app."
		return 1
	fi

	PATCHED_BOOT_IMG="$WORK_DIR/magisk_patched.img"
	if ! adb pull "$patched_img" "$PATCHED_BOOT_IMG"; then
		error "Failed to pull patched boot image"
		return 1
	fi

	log "Patched boot image saved to: $PATCHED_BOOT_IMG"
	return 0
}

flash_patched_boot() {
	print_header "Flashing Patched Boot Image"

	if [[ ! -f ${PATCHED_BOOT_IMG:-} ]]; then
		die "Patched boot image not found: ${PATCHED_BOOT_IMG:-none}"
	fi

	echo
	echo -e "${YELLOW}This will flash the patched boot image to your device.${NC}"
	echo

	if ! confirm "Proceed with flashing?"; then
		log "Flashing cancelled by user"
		return 1
	fi

	log "Rebooting to bootloader..."
	adb reboot bootloader || die "Failed to reboot to bootloader"

	log "Waiting for fastboot mode..."
	sleep 5

	if ! fastboot devices | grep -q .; then
		die "Device not detected in fastboot mode"
	fi

	log "Flashing patched boot image..."
	if ! fastboot flash boot "$PATCHED_BOOT_IMG"; then
		error "Failed to flash boot image"
		return 1
	fi

	log "Flashed successfully!"
	log "Rebooting device..."
	fastboot reboot

	log "Waiting for device to boot..."
	sleep 10
	adb wait-for-device || true

	echo
	echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
	echo -e "${GREEN}║              Root Process Complete!                   ║${NC}"
	echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
	echo
	echo "Your BL9000 phone should now be rooted with Magisk!"
	echo
	echo "Next steps:"
	echo "1. Open the Magisk app on your phone"
	echo "2. Verify that it shows 'Installed' for both Magisk and App"
	echo "3. Grant root access to apps as needed"
	echo "4. Install Magisk modules if desired"
	echo
	echo "Note: Some banking and secure apps may not work with root."
	echo "      Use Magisk's DenyList feature to hide root from specific apps."
	echo

	return 0
}

clean_work_dir() {
	if [[ -d $WORK_DIR ]]; then
		log "Removing working directory: $WORK_DIR"
		rm -rf "$WORK_DIR"
		log "Cleaned successfully"
	else
		log "Work directory doesn't exist: $WORK_DIR"
	fi
}

run_full_process() {
	print_header "BL9000 Full Root Process"

	log "Starting complete rooting process..."

	install_dependencies || die "Failed to install dependencies"
	setup_udev_rules || true

	echo
	if ! confirm "Continue to device check?"; then
		die "Process cancelled by user"
	fi

	check_device || die "Device check failed"

	echo
	if ! confirm "Continue to backup device data?"; then
		die "Process cancelled by user"
	fi

	backup_device_data || warn "Backup failed or incomplete"

	echo
	if ! confirm "Continue to bootloader unlock?"; then
		die "Process cancelled by user"
	fi

	unlock_bootloader || die "Bootloader unlock failed"

	echo
	log "Please complete device setup and re-enable USB debugging, then press Enter..."
	read -r

	check_device || die "Device check failed after unlock"

	download_magisk || die "Failed to download Magisk"
	extract_boot_image || die "Failed to extract boot image"
	patch_boot_with_magisk || die "Failed to patch boot image"
	flash_patched_boot || die "Failed to flash patched boot"

	log "Full root process completed successfully!"
}

run_root_only() {
	print_header "BL9000 Root Process (Skip Unlock)"

	log "Starting root process (assuming bootloader is already unlocked)..."

	check_device || die "Device check failed"
	download_magisk || die "Failed to download Magisk"
	extract_boot_image || die "Failed to extract boot image"
	patch_boot_with_magisk || die "Failed to patch boot image"
	flash_patched_boot || die "Failed to flash patched boot"

	log "Root process completed successfully!"
}

main() {
	require_non_root

	# Create work directory
	mkdir -p "$WORK_DIR"

	local command="${1:-help}"
	shift || true

	# Parse options
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--work-dir)
			WORK_DIR="$2"
			mkdir -p "$WORK_DIR"
			shift 2
			;;
		--boot-img)
			BOOT_IMG="$2"
			if [[ ! -f $BOOT_IMG ]]; then
				die "Boot image file not found: $BOOT_IMG"
			fi
			shift 2
			;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			error "Unknown option: $1"
			usage
			exit 1
			;;
		esac
	done

	case "$command" in
	install-deps)
		install_dependencies
		setup_udev_rules
		;;
	check)
		check_device
		;;
	backup)
		check_device || die "Device check failed"
		backup_device_data
		;;
	unlock)
		check_device || die "Device check failed"
		unlock_bootloader
		;;
	root)
		run_root_only
		;;
	full)
		run_full_process
		;;
	clean)
		clean_work_dir
		;;
	help | --help | -h)
		usage
		;;
	*)
		error "Unknown command: $command"
		usage
		exit 1
		;;
	esac
}

main "$@"
