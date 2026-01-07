#!/bin/bash

# Fix script for media-organizer.service
# The service was failing due to:
# 1. Corrupted ExecStart path (line break in the middle)
# 2. Wrong script path (missing 'utils/' directory)
# 3. User/Group set to root instead of actual user

set -euo pipefail

SERVICE_NAME="media-organizer"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ORGANIZE_SCRIPT="/home/kuhy/linux-configuration/scripts/utils/organize_downloads.sh"
TARGET_USER="kuhy"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
  log "This script needs to be run as root."
  log "Re-executing with sudo..."
  exec sudo "$0" "$@"
fi

log "Fixing media-organizer.service..."

# Verify the organize_downloads.sh script exists
if [[ ! -f $ORGANIZE_SCRIPT ]]; then
  log "ERROR: organize_downloads.sh not found at $ORGANIZE_SCRIPT"
  exit 1
fi

# Stop the service if running (ignore errors)
systemctl stop "$SERVICE_NAME.service" 2> /dev/null || true

# Recreate the service file with correct configuration
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Media File Organizer
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=oneshot
User=$TARGET_USER
Group=$TARGET_USER
ExecStart=$ORGANIZE_SCRIPT
StandardOutput=journal
StandardError=journal
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
EOF

log "Recreated service file: $SERVICE_FILE"

# Reload systemd daemon
systemctl daemon-reload
log "Reloaded systemd daemon"

# Reset the failed state
systemctl reset-failed "$SERVICE_NAME.service" 2> /dev/null || true
log "Reset failed state"

# Re-enable the service
systemctl enable "$SERVICE_NAME.service"
log "Service enabled"

# Optionally start the service to verify it works
log "Starting service to verify fix..."
if systemctl start "$SERVICE_NAME.service"; then
  log "SUCCESS: media-organizer.service started successfully!"
else
  log "WARNING: Service still has issues. Check: journalctl -u $SERVICE_NAME"
fi

# Show current status
log "Current service status:"
systemctl status "$SERVICE_NAME.service" --no-pager || true

log "Fix complete!"
