#!/bin/bash

# Setup script to configure media organizer to run on startup
# Creates systemd service for automatic media file organization

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORGANIZE_SCRIPT="$SCRIPT_DIR/organize_downloads.sh"
SERVICE_NAME="media-organizer"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
USER_NAME="$(whoami)"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if organize script exists
if [[ ! -f "$ORGANIZE_SCRIPT" ]]; then
    log "ERROR: organize_downloads.sh not found at $ORGANIZE_SCRIPT"
    exit 1
fi

# Check if running as root for systemd service creation
if [[ $EUID -ne 0 ]]; then
    log "This script needs to be run as root to create systemd service."
    log "Please run: sudo $0"
    exit 1
fi

log "Setting up media organizer startup service..."

# Create systemd service file
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Media File Organizer
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=oneshot
User=$USER_NAME
Group=$USER_NAME
ExecStart=$ORGANIZE_SCRIPT
StandardOutput=journal
StandardError=journal
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
EOF

log "Created systemd service file: $SERVICE_FILE"

# Reload systemd and enable the service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"

log "Service enabled successfully!"
log "The media organizer will now run on every system startup."
log ""
log "To manually run the service: sudo systemctl start $SERVICE_NAME"
log "To check service status: sudo systemctl status $SERVICE_NAME"
log "To view service logs: sudo journalctl -u $SERVICE_NAME"
log "To disable the service: sudo systemctl disable $SERVICE_NAME"
