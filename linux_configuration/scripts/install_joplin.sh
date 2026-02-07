#!/usr/bin/env bash
# Install Joplin - free, open-source, self-hostable note-taking app.
# Available on Linux (desktop), Android, iOS, Windows, macOS.
# Supports Markdown, end-to-end encryption, and self-hosted sync.
#
# This script:
#   1. Installs Joplin desktop app (AUR)
#   2. Optionally sets up Joplin Server via Docker for self-hosted sync
#
# Usage: ./install_joplin.sh [--with-server]
#
# Android app: https://play.google.com/store/apps/details?id=net.cozic.joplin
#              or via F-Droid

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

WITH_SERVER=false
JOPLIN_SERVER_PORT=22300
JOPLIN_DATA_DIR="$HOME/.joplin-server"
DUCKDNS_DOMAIN=""
DUCKDNS_TOKEN=""

for arg in "$@"; do
    case "$arg" in
        --with-server) WITH_SERVER=true ;;
        --help|-h)
            echo "Usage: $0 [--with-server]"
            echo ""
            echo "Options:"
            echo "  --with-server  Also set up Joplin Server via Docker"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
        *)
            error "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# ── Check prerequisites ─────────────────────────────────────────────
command -v pacman >/dev/null 2>&1 || { error "pacman not found. This script is for Arch Linux."; exit 1; }

# ── Install Joplin Desktop ──────────────────────────────────────────
install_joplin_desktop() {
    if [[ -f "$HOME/.joplin/Joplin.AppImage" ]]; then
        info "Joplin desktop is already installed at $HOME/.joplin/Joplin.AppImage"
        return
    fi

    info "Installing Joplin desktop app via official installer (AppImage)..."

    # Official Joplin install script downloads the latest AppImage
    wget -O - https://raw.githubusercontent.com/laurent22/joplin/dev/Joplin_install_and_update.sh | bash

    info "Joplin desktop installed at ~/.joplin/Joplin.AppImage"
    info "Launch with: ~/.joplin/Joplin.AppImage  (or 'joplin-desktop' from menu)"
}

# ── Set up DuckDNS for stable URL ───────────────────────────────────
setup_duckdns() {
    info "Setting up DuckDNS for stable server URL..."

    if [[ -z "$DUCKDNS_DOMAIN" ]]; then
        echo ""
        info "Your public IP may change. DuckDNS provides a free stable hostname."
        info "1. Go to https://www.duckdns.org/ and sign in (Google/GitHub/etc.)"
        info "2. Create a subdomain (e.g. 'myjoplin' for myjoplin.duckdns.org)"
        info "3. Copy your token from the DuckDNS dashboard"
        echo ""
        read -r -p "Enter your DuckDNS subdomain (without .duckdns.org): " DUCKDNS_DOMAIN
        read -r -p "Enter your DuckDNS token: " DUCKDNS_TOKEN
    fi

    if [[ -z "$DUCKDNS_DOMAIN" ]] || [[ -z "$DUCKDNS_TOKEN" ]]; then
        warn "DuckDNS not configured. Falling back to raw public IP (may change!)."
        return 1
    fi

    local full_domain="${DUCKDNS_DOMAIN}.duckdns.org"

    # Update DuckDNS now
    info "Updating DuckDNS record for ${full_domain}..."
    local result
    result=$(curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")
    if [[ "$result" == "OK" ]]; then
        info "DuckDNS updated successfully: ${full_domain}"
    else
        warn "DuckDNS update returned: $result"
    fi

    # Set up cron job to keep IP updated every 5 minutes
    local duckdns_script="$JOPLIN_DATA_DIR/duckdns-update.sh"
    cat > "$duckdns_script" <<DUCKEOF
#!/usr/bin/env bash
result=\$(curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")
echo "\$(date): \$result" >> "$JOPLIN_DATA_DIR/duckdns.log"
DUCKEOF
    chmod +x "$duckdns_script"

    # Add cron job (remove old one if exists, add new)
    (crontab -l 2>/dev/null | grep -v "duckdns-update.sh"; echo "*/5 * * * * $duckdns_script") | crontab -
    info "DuckDNS cron job installed (updates every 5 minutes)"

    # Save config for future runs
    local config_file="$JOPLIN_DATA_DIR/.duckdns.conf"
    cat > "$config_file" <<CONFEOF
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN}"
CONFEOF
    chmod 600 "$config_file"

    return 0
}

# ── Set up Joplin Server (Docker) ───────────────────────────────────
setup_joplin_server() {
    info "Setting up Joplin Server via Docker..."

    # Ensure Docker is installed and running
    if ! command -v docker >/dev/null 2>&1; then
        info "Installing Docker..."
        sudo pacman -S --needed --noconfirm docker docker-compose
    fi

    if ! systemctl is-active --quiet docker; then
        info "Starting Docker service..."
        sudo systemctl enable --now docker
    fi

    # Add user to docker group if not already a member
    if ! groups | grep -q '\bdocker\b'; then
        warn "Adding $USER to docker group (re-login required for group to take effect)."
        sudo usermod -aG docker "$USER"
    fi

    # Create data directory
    mkdir -p "$JOPLIN_DATA_DIR"

    local compose_file="$JOPLIN_DATA_DIR/docker-compose.yml"

    # Load saved DuckDNS config if it exists
    if [[ -f "$JOPLIN_DATA_DIR/.duckdns.conf" ]]; then
        # shellcheck source=/dev/null
        source "$JOPLIN_DATA_DIR/.duckdns.conf"
    fi

    # Set up DuckDNS for a stable hostname
    local server_url
    if setup_duckdns; then
        server_url="http://${DUCKDNS_DOMAIN}.duckdns.org:${JOPLIN_SERVER_PORT}"
        info "Using stable DuckDNS URL: $server_url"
    else
        # Fallback to public IP
        local host_ip
        host_ip="$(curl -s --max-time 5 ifconfig.me 2>/dev/null)"
        if [[ -z "$host_ip" ]]; then
            host_ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')"
        fi
        if [[ -z "$host_ip" ]]; then
            host_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
        fi
        if [[ -z "$host_ip" ]]; then
            warn "Could not detect external IP. Falling back to 0.0.0.0"
            host_ip="0.0.0.0"
        fi
        server_url="http://${host_ip}:${JOPLIN_SERVER_PORT}"
        warn "Using raw IP URL (may change!): $server_url"
    fi

    cat > "$compose_file" <<EOF
version: "3"

services:
  joplin-db:
    image: postgres:16
    container_name: joplin-db
    restart: unless-stopped
    volumes:
      - joplin-db-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: joplin
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: changeme
    networks:
      - joplin-net

  joplin-server:
    image: joplin/server:latest
    container_name: joplin-server
    restart: unless-stopped
    depends_on:
      - joplin-db
    ports:
      - "0.0.0.0:${JOPLIN_SERVER_PORT}:22300"
    environment:
      APP_PORT: 22300
      APP_BASE_URL: "${server_url}"
      DB_CLIENT: pg
      POSTGRES_HOST: joplin-db
      POSTGRES_PORT: 5432
      POSTGRES_DATABASE: joplin
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: changeme
    networks:
      - joplin-net

volumes:
  joplin-db-data:

networks:
  joplin-net:
EOF

    info "Starting Joplin Server..."
    docker compose -f "$compose_file" up -d

    echo ""
    info "Joplin Server is running at: ${server_url}"
    echo ""
    echo "  Default admin credentials:"
    echo "    Email:    admin@localhost"
    echo "    Password: admin"
    echo ""
    warn "IMPORTANT: Change the default admin password and the database"
    warn "password (POSTGRES_PASSWORD in $compose_file) immediately!"
    echo ""
    info "Firewall: opening port ${JOPLIN_SERVER_PORT}/tcp for external access..."
    if command -v ufw >/dev/null 2>&1; then
        sudo ufw allow "${JOPLIN_SERVER_PORT}/tcp" || warn "Could not configure ufw"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        if sudo firewall-cmd --permanent --add-port="${JOPLIN_SERVER_PORT}/tcp" \
            && sudo firewall-cmd --reload; then
            :
        else
            warn "Could not configure firewalld"
        fi
    elif command -v iptables >/dev/null 2>&1; then
        sudo iptables -A INPUT -p tcp --dport "${JOPLIN_SERVER_PORT}" -j ACCEPT || warn "Could not configure iptables"
    else
        warn "No firewall tool found. Ensure port ${JOPLIN_SERVER_PORT}/tcp is open manually."
    fi
    echo ""
    echo "  To connect Joplin desktop/Android to this server:"
    echo "    1. Open Joplin → Tools → Options → Synchronisation"
    echo "    2. Set target to 'Joplin Server'"
    echo "    3. Enter URL: ${server_url}"
    echo "    4. Enter your Joplin Server email and password"
    echo ""
    echo "  Server management:"
    echo "    Start:   docker compose -f $compose_file up -d"
    echo "    Stop:    docker compose -f $compose_file down"
    echo "    Logs:    docker compose -f $compose_file logs -f"
    echo "    Update:  docker compose -f $compose_file pull && docker compose -f $compose_file up -d"
}

# ── Main ─────────────────────────────────────────────────────────────
main() {
    echo "╔══════════════════════════════════════════════╗"
    echo "║         Joplin Installation Script           ║"
    echo "║   Free & Open Source Note-Taking App         ║"
    echo "║   https://joplinapp.org                      ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""

    install_joplin_desktop

    if [[ "$WITH_SERVER" == true ]]; then
        setup_joplin_server
    else
        echo ""
        info "Tip: Run with --with-server to also set up Joplin Server"
        info "for self-hosted sync across devices (desktop + Android)."
    fi

    echo ""
    info "Android app available at:"
    info "  Google Play: https://play.google.com/store/apps/details?id=net.cozic.joplin"
    info "  F-Droid:     https://f-droid.org/packages/net.cozic.joplin/"
    echo ""
    info "Done!"
}

main
