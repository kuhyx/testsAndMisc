#!/bin/bash
# update_android_hosts.sh - Update Android hosts file from Linux config
set -euo pipefail

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"
# shellcheck source=../lib/android.sh
source "$SCRIPT_DIR/../lib/android.sh"

# Initialize Android script (handles sudo, sets WORK_DIR)
init_android_script "$@"

log "Updating Android hosts file from Linux configuration..."

# Check device connection
check_adb_device

# Check root access
check_adb_root

# Use the StevenBlack cache or /etc/hosts
HOSTS_FILE="$WORK_DIR/hosts"
if [[ -f /etc/hosts.stevenblack ]]; then
	log "Using StevenBlack hosts cache..."
	cp /etc/hosts.stevenblack "$HOSTS_FILE"
elif [[ -f /etc/hosts ]]; then
	log "Using /etc/hosts..."
	cp /etc/hosts "$HOSTS_FILE"
else
	die "No hosts file found"
fi

# Show stats
TOTAL_ENTRIES=$(grep -c "^0\.0\.0\.0 " "$HOSTS_FILE" || echo 0)
log "Hosts file contains $TOTAL_ENTRIES blocked domains"

# Push to device
log "Pushing hosts file to device..."
adb push "$HOSTS_FILE" /sdcard/hosts || die "Failed to push hosts file"

# Install systemlessly
log "Updating systemless hosts..."
adb shell "su -c 'mkdir -p /data/adb/modules/systemless_hosts/system/etc'" || die "Failed to create module directory"
adb shell "su -c 'cp /sdcard/hosts /data/adb/modules/systemless_hosts/system/etc/hosts'" || die "Failed to install hosts file"
adb shell "su -c 'chmod 644 /data/adb/modules/systemless_hosts/system/etc/hosts'" || die "Failed to set permissions"
adb shell "su -c 'rm /sdcard/hosts'"

echo "[$(date +'%Y-%m-%d %H:%M:%S%z')] ✓ Hosts file updated successfully"

# Append custom blocking entries
echo "[$(date +'%Y-%m-%d %H:%M:%S%z')] Adding custom blocking entries..."
adb shell "su -c 'cat >> /data/adb/modules/systemless_hosts/system/etc/hosts << \"CUSTOM_EOF\"

# Custom blocking entries
# YouTube
0.0.0.0 youtube.com
0.0.0.0 www.youtube.com
0.0.0.0 m.youtube.com
0.0.0.0 youtu.be
0.0.0.0 youtube-nocookie.com
0.0.0.0 www.youtube-nocookie.com
0.0.0.0 youtubei.googleapis.com
0.0.0.0 youtube.googleapis.com
0.0.0.0 yt3.ggpht.com
0.0.0.0 ytimg.com
0.0.0.0 i.ytimg.com
0.0.0.0 s.ytimg.com
0.0.0.0 i9.ytimg.com
0.0.0.0 googlevideo.com
0.0.0.0 r1---sn-4g5e6nls.googlevideo.com
0.0.0.0 r1---sn-4g5lne7s.googlevideo.com

# Steam Store

# Discord (selective blocking - media only, voice chat allowed)
0.0.0.0 cdn.discordapp.com
0.0.0.0 media.discordapp.net
0.0.0.0 images-ext-1.discordapp.net
0.0.0.0 images-ext-2.discordapp.net
0.0.0.0 attachments-1.discordapp.net
0.0.0.0 attachments-2.discordapp.net
0.0.0.0 tenor.com
0.0.0.0 giphy.com

# Food Delivery Services
# Polish services
0.0.0.0 pyszne.pl
0.0.0.0 www.pyszne.pl
0.0.0.0 m.pyszne.pl
0.0.0.0 glovo.com
0.0.0.0 www.glovo.com
0.0.0.0 m.glovo.com
0.0.0.0 bolt.eu
0.0.0.0 food.bolt.eu
0.0.0.0 woltwojta.pl
0.0.0.0 www.woltwojta.pl
0.0.0.0 wolt.com
0.0.0.0 www.wolt.com
0.0.0.0 m.wolt.com

# International services
0.0.0.0 ubereats.com
0.0.0.0 www.ubereats.com
0.0.0.0 m.ubereats.com
0.0.0.0 uber.com
0.0.0.0 www.uber.com
0.0.0.0 m.uber.com
0.0.0.0 deliveroo.com
0.0.0.0 www.deliveroo.com
0.0.0.0 m.deliveroo.com
0.0.0.0 deliveroo.co.uk
0.0.0.0 www.deliveroo.co.uk
0.0.0.0 foodpanda.com
0.0.0.0 www.foodpanda.com
0.0.0.0 m.foodpanda.com
0.0.0.0 grubhub.com
0.0.0.0 www.grubhub.com
0.0.0.0 m.grubhub.com
0.0.0.0 doordash.com
0.0.0.0 www.doordash.com
0.0.0.0 m.doordash.com
0.0.0.0 justeat.com
0.0.0.0 www.justeat.com
0.0.0.0 m.justeat.com
0.0.0.0 justeat.co.uk
0.0.0.0 www.justeat.co.uk
0.0.0.0 postmates.com
0.0.0.0 www.postmates.com
0.0.0.0 seamless.com
0.0.0.0 www.seamless.com
0.0.0.0 menulog.com.au
0.0.0.0 www.menulog.com.au
0.0.0.0 delivery.com
0.0.0.0 www.delivery.com

# Fast food chain apps and websites
0.0.0.0 mcdonalds.com
0.0.0.0 www.mcdonalds.com
0.0.0.0 m.mcdonalds.com
0.0.0.0 mcdonalds.pl
0.0.0.0 www.mcdonalds.pl
0.0.0.0 kfc.com
0.0.0.0 www.kfc.com
0.0.0.0 m.kfc.com
0.0.0.0 kfc.pl
0.0.0.0 www.kfc.pl
0.0.0.0 burgerking.com
0.0.0.0 www.burgerking.com
0.0.0.0 m.burgerking.com
0.0.0.0 burgerking.pl
0.0.0.0 www.burgerking.pl
0.0.0.0 pizzahut.com
0.0.0.0 www.pizzahut.com
0.0.0.0 m.pizzahut.com
0.0.0.0 pizzahut.pl
0.0.0.0 www.pizzahut.pl
0.0.0.0 dominos.com
0.0.0.0 www.dominos.com
0.0.0.0 m.dominos.com
0.0.0.0 dominos.pl
0.0.0.0 www.dominos.pl
0.0.0.0 subway.com
0.0.0.0 www.subway.com
0.0.0.0 m.subway.com
0.0.0.0 subway.pl
0.0.0.0 www.subway.pl
CUSTOM_EOF
'" || {
	echo "[$(date +'%Y-%m-%d %H:%M:%S%z')] ✗ Failed to add custom entries"
	exit 1
}

echo "[$(date +'%Y-%m-%d %H:%M:%S%z')] ✓ Custom entries added successfully"

# Count and display blocked domains
domain_count=$(adb shell "su -c 'cat /system/etc/hosts | grep -c \"^0.0.0.0\"'" 2>/dev/null | tr -d '\r')
if [[ -n $domain_count ]]; then
	echo "[$(date +'%Y-%m-%d %H:%M:%S%z')] ✓ Total blocked domains: $domain_count"
fi

echo "[$(date +'%Y-%m-%d %H:%M:%S%z')] ✓ Changes will take effect immediately for new connections"
echo "[$(date +'%Y-%m-%d %H:%M:%S%z')]   (Optional: Toggle airplane mode or reboot to force all apps to reconnect)"
log "✓ Total blocked domains: $TOTAL_ENTRIES"
log ""
log "Changes will take effect immediately for new connections."
log "To apply to all apps, reboot the device or toggle airplane mode."
