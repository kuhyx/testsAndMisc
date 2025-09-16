#!/usr/bin/env bash
set -euo pipefail

# LibreTranslate full setup script (Docker-based)
# Features:
#  - Installs Docker if missing (optional --no-docker-install)
#  - Pulls libretranslate image (tag configurable)
#  - Creates persistent data + cache directories
#  - Optionally pre-downloads language models
#  - Generates or accepts an API key; can disable auth
#  - (Removed) systemd service setup – now always ephemeral
#  - Health check + sample translation
#  - Uninstall mode removes container, image, service, and data (optional keep data)
#  - Idempotent: safe to re-run for upgrades (will pull newer image)

SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"

# Defaults
IMAGE="libretranslate/libretranslate"
TAG="latest"
SERVICE_NAME="libretranslate"
DOCKER_INSTALL=1
# Systemd removed – always run ephemeral container
API_KEY=""
GENERATE_API_KEY=1
DISABLE_API_KEY=0
PORT=5000
HOST=0.0.0.0
DATA_DIR="/var/lib/libretranslate"
CACHE_DIR="${DATA_DIR}/cache"
CONFIG_DIR="/etc/libretranslate"
ENV_FILE="${CONFIG_DIR}/libretranslate.env"
PULL_ONLY=0
PRELOAD_LANGS=""
UNINSTALL=0
KEEP_DATA=0
HEALTH_TIMEOUT=15
EXTRA_ENV=()
NO_COLOR=0
KEEP_ALIVE=0
RUN_COMMAND=()
DEBUG=0

# Colors
if [[ -t 1 && ${NO_COLOR} -eq 0 ]]; then
	GREEN="\e[32m"; YELLOW="\e[33m"; RED="\e[31m"; BLUE="\e[34m"; BOLD="\e[1m"; RESET="\e[0m"
else
	GREEN=""; YELLOW=""; RED=""; BLUE=""; BOLD=""; RESET=""
fi

log() { echo -e "${BLUE}[INFO]${RESET} $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $*" >&2; }
err() { echo -e "${RED}[ERR ]${RESET} $*" >&2; }
success() { echo -e "${GREEN}[OK  ]${RESET} $*"; }

usage() {
	cat <<EOF
${SCRIPT_NAME} v${VERSION}
Setup or uninstall a self-hosted LibreTranslate instance via Docker.

Usage: ${SCRIPT_NAME} [options]

Primary actions:
	--uninstall              Remove service, container, image (data kept unless --purge or --no-keep-data)
	--pull-only              Only pull/update image & exit

Install behavior options:
	--image NAME             Docker image (default: ${IMAGE})
	--tag TAG                Docker tag (default: ${TAG})
	--port N                 Host port to expose (default: ${PORT})
	--host IP                Bind host (default: ${HOST})
	--data-dir PATH          Persistent data directory (default: ${DATA_DIR})
	--cache-dir PATH         Models cache dir (default: ${CACHE_DIR})
	--no-docker-install      Do not attempt to install Docker
	(systemd support removed; container is ephemeral)
	--keep-alive             Keep running (tail logs) until Ctrl-C
	--                       Treat remaining arguments as a command to run after service is healthy; service stops when command exits
	--api-key KEY            Use specified API key
	--generate-api-key       Force generate new random key (default if none provided)
	--disable-api-key        Disable key requirement (open instance)
	--preload-langs CSV      Pre-download language models (e.g. en,es,fr,de)
	--env K=V                Extra environment variable (repeatable)
	--health-timeout SEC     Wait time for health check (default: ${HEALTH_TIMEOUT})
	--debug                  Verbose output (do not suppress curl errors; follow logs on failure)
	--no-color               Disable colored output

Uninstall options:
	--purge                  Remove data directory (implies --uninstall)
	--keep-data              Keep data on uninstall (default)

Misc:
	-h, --help               Show this help
	-v, --version            Show version

Examples:
	${SCRIPT_NAME} --preload-langs en,es,fr --env LT_LOAD_ONLY=en,es,fr
	${SCRIPT_NAME} --api-key mysecret123 --port 8080
	${SCRIPT_NAME} --uninstall --purge
EOF
}

gen_api_key() {
	# Avoid SIGPIPE issues under set -o pipefail by capturing output first
	local key
	key=$(head -c 256 /dev/urandom | tr -dc 'A-Za-z0-9' | head -c 40 || true)
	if [[ -z $key || ${#key} -lt 40 ]]; then
		# Fallback using openssl if available
		if command -v openssl >/dev/null 2>&1; then
			key=$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 40 || true)
		fi
	fi
	if [[ -z $key || ${#key} -lt 20 ]]; then
		# Last resort static warning key (should not happen)
		key="LT$(date +%s)$$RANDOM"
	fi
	printf '%s' "$key"
}

need_cmd() {
	command -v "$1" >/dev/null 2>&1 || { err "Required command '$1' not found"; return 1; }
}

parse_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
			--image) IMAGE="$2"; shift 2;;
			--tag) TAG="$2"; shift 2;;
			--port) PORT="$2"; shift 2;;
			--host) HOST="$2"; shift 2;;
			--data-dir) DATA_DIR="$2"; CACHE_DIR="${DATA_DIR}/cache"; shift 2;;
			--cache-dir) CACHE_DIR="$2"; shift 2;;
			--no-docker-install) DOCKER_INSTALL=0; shift;;
			--keep-alive) KEEP_ALIVE=1; shift;;
			--) shift; RUN_COMMAND=("$@"); break;;
			--api-key) API_KEY="$2"; GENERATE_API_KEY=0; shift 2;;
			--generate-api-key) GENERATE_API_KEY=1; shift;;
			--disable-api-key) DISABLE_API_KEY=1; shift;;
			--preload-langs) PRELOAD_LANGS="$2"; shift 2;;
			--env) EXTRA_ENV+=("$2"); shift 2;;
			--pull-only) PULL_ONLY=1; shift;;
			--uninstall) UNINSTALL=1; shift;;
			--purge) UNINSTALL=1; KEEP_DATA=0; shift;;
			--keep-data) KEEP_DATA=1; shift;;
			--health-timeout) HEALTH_TIMEOUT="$2"; shift 2;;
			--no-color) NO_COLOR=1; shift;;
			--debug) DEBUG=1; shift;;
			-h|--help) usage; exit 0;;
			-v|--version) echo "${VERSION}"; exit 0;;
			*) err "Unknown argument: $1"; usage; exit 1;;
		esac
	done
}

ensure_root() {
	if [[ $EUID -ne 0 ]]; then
		err "This script must run as root (or via sudo)."; exit 1
	fi
}

install_docker() {
	if command -v docker >/dev/null 2>&1; then
		log "Docker already installed"
		return 0
	fi
	if [[ ${DOCKER_INSTALL} -eq 0 ]]; then
		err "Docker is not installed and --no-docker-install specified."; exit 1
	fi
	log "Installing Docker..."
	if command -v apt-get >/dev/null 2>&1; then
		apt-get update -y
		apt-get install -y ca-certificates curl gnupg
		install -d -m 0755 /etc/apt/keyrings
		curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
		chmod a+r /etc/apt/keyrings/docker.gpg
		echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(. /etc/os-release; echo "$VERSION_CODENAME") stable" \
			> /etc/apt/sources.list.d/docker.list
		apt-get update -y
		apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
	else
		err "Unsupported package manager. Please install Docker manually."; exit 1
	fi
	# Attempt to start docker daemon if dockerd exists and systemctl available; otherwise rely on user
	if command -v systemctl >/dev/null 2>&1; then
		(systemctl enable --now docker 2>/dev/null && success "Docker installed and started") || warn "Docker installed; ensure dockerd is running"
	else
		warn "Docker installed; please ensure docker daemon is running"
	fi
}

pull_image() {
	log "Pulling image ${IMAGE}:${TAG}"
	docker pull "${IMAGE}:${TAG}"
	success "Image pulled"
}

detect_container_user() {
    # Determine uid/gid of configured user inside image so host dirs can be chowned
    if ! command -v docker >/dev/null 2>&1; then
        return 0
    fi
    local uid gid
    uid=$(docker run --rm --entrypoint /usr/bin/id "${IMAGE}:${TAG}" -u 2>/dev/null || echo "")
    gid=$(docker run --rm --entrypoint /usr/bin/id "${IMAGE}:${TAG}" -g 2>/dev/null || echo "")
    if [[ -n $uid && -n $gid ]]; then
        CONTAINER_UID=$uid
        CONTAINER_GID=$gid
    fi
}

write_env_file() {
	mkdir -p "${CONFIG_DIR}" "${DATA_DIR}" "${CACHE_DIR}"
	detect_container_user
	if [[ -n ${CONTAINER_UID:-} && -n ${CONTAINER_GID:-} ]]; then
		if command -v stat >/dev/null 2>&1; then
			for d in "${DATA_DIR}" "${CACHE_DIR}"; do
				if [[ -d $d ]]; then
					CUR_UID=$(stat -c %u "$d" 2>/dev/null || echo -1)
					if [[ ${CUR_UID} -ne ${CONTAINER_UID} ]]; then
						chown ${CONTAINER_UID}:${CONTAINER_GID} "$d" 2>/dev/null || warn "Unable to chown $d to ${CONTAINER_UID}:${CONTAINER_GID}"
					fi
				fi
			done
		fi
	fi
	if [[ ${DISABLE_API_KEY} -eq 1 ]]; then
		API_KEY_LINE="LT_NO_API_KEY=true"
	else
		if [[ -z ${API_KEY} && ${GENERATE_API_KEY} -eq 1 ]]; then
			API_KEY=$(gen_api_key)
			GENERATED=1
		else
			GENERATED=0
		fi
		API_KEY_LINE="LT_API_KEYS=${API_KEY}"
	fi

	{ echo "# LibreTranslate environment file"; echo "# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "${API_KEY_LINE}"; 
		[[ -n ${PRELOAD_LANGS} ]] && echo "LT_PRELOAD_LANGS=${PRELOAD_LANGS}"; 
		for kv in "${EXTRA_ENV[@]:-}"; do echo "$kv"; done; } > "${ENV_FILE}.tmp"
	mv "${ENV_FILE}.tmp" "${ENV_FILE}"
	chmod 600 "${ENV_FILE}"
	success "Environment file written: ${ENV_FILE}"
}

start_container_ephemeral() {
	log "Starting ephemeral container..."
	docker rm -f "${SERVICE_NAME}" >/dev/null 2>&1 || true
	docker run -d --name "${SERVICE_NAME}" \
		--env-file "${ENV_FILE}" \
		-v "${DATA_DIR}:/home/libretranslate/.local/share/argos-translate" \
		-v "${CACHE_DIR}:/app/cache" \
		-p "${PORT}:${PORT}" \
		"${IMAGE}:${TAG}" \
		--host 0.0.0.0 --port ${PORT}
	success "Container started (ephemeral)"
	echo
	echo "Endpoint (pending readiness): http://$(hostname -I | awk '{print $1}'):${PORT}" 
	echo "Waiting for health..."
}

health_check() {
	local start=$(date +%s)
	local url="http://127.0.0.1:${PORT}/languages"
	local attempt=0
	while true; do
		attempt=$((attempt+1))
		if curl ${DEBUG:+-v} -fsS "$url" >/dev/null 2>&1; then
			success "Service healthy (attempt $attempt)"
			return 0
		else
			[[ $DEBUG -eq 1 ]] && log "Health attempt $attempt failed"
		fi
		if (( $(date +%s) - start > HEALTH_TIMEOUT )); then
			err "Health check failed after ${HEALTH_TIMEOUT}s (attempts: $attempt)"
			docker logs --tail 200 "${SERVICE_NAME}" || true
			return 1
		fi
		sleep 0.5
	done
}

sample_request() {
	if [[ ${DISABLE_API_KEY} -eq 0 ]]; then
		local key="${API_KEY}"
	else
		local key=""
	fi
	log "Performing sample translation (en->es)..."
	local DATA='{"q":"Hello world","source":"en","target":"es","format":"text"}'
	if [[ -n $key ]]; then
		curl -fsS -H "Content-Type: application/json" -H "Authorization: ${key}" -d "$DATA" "http://127.0.0.1:${PORT}/translate" || warn "Sample request failed"
	else
		curl -fsS -H "Content-Type: application/json" -d "$DATA" "http://127.0.0.1:${PORT}/translate" || warn "Sample request failed"
	fi
	echo
}

uninstall_all() {
	log "Uninstalling LibreTranslate (ephemeral mode)..."
	docker rm -f "${SERVICE_NAME}" 2>/dev/null || true
	docker rmi "${IMAGE}:${TAG}" 2>/dev/null || true
	if [[ ${KEEP_DATA} -eq 0 ]]; then
		rm -rf "${DATA_DIR}" "${CONFIG_DIR}" || true
		success "Data directories removed"
	else
		log "Data kept in ${DATA_DIR} and ${CONFIG_DIR}"
	fi
	success "Uninstall complete"
	exit 0
}

main() {
	parse_args "$@"
	ensure_root

	if [[ ${UNINSTALL} -eq 1 ]]; then
		uninstall_all
	fi

	install_docker
	pull_image
	if [[ ${PULL_ONLY} -eq 1 ]]; then
		log "Pull-only requested, exiting."
		exit 0
	fi

	write_env_file

	# Always ephemeral now
	start_container_ephemeral

	health_check
	sample_request || true

	# If a command is provided, run it and then shutdown container
	if [[ ${#RUN_COMMAND[@]} -gt 0 ]]; then
		log "Running user command: ${RUN_COMMAND[*]}"
		set +e
		"${RUN_COMMAND[@]}"
		CMD_STATUS=$?
		set -e
		log "Command exited with status ${CMD_STATUS}; stopping container"
		docker stop "${SERVICE_NAME}" >/dev/null 2>&1 || true
		exit ${CMD_STATUS}
	fi

	if [[ ${KEEP_ALIVE} -eq 1 ]]; then
		log "Tailing logs (Ctrl-C to stop and remove container)"
		trap 'log "Stopping container"; docker stop "${SERVICE_NAME}" >/dev/null 2>&1 || true; exit 0' INT TERM
		docker logs -f "${SERVICE_NAME}"
		log "Logs ended; stopping container"
		docker stop "${SERVICE_NAME}" >/dev/null 2>&1 || true
	else
		log "Ephemeral container left running in background (id: $(docker inspect --format '{{.Id}}' ${SERVICE_NAME} 2>/dev/null || echo unknown))"
		log "Stop manually with: docker stop ${SERVICE_NAME}"
	fi

	echo
	echo "${BOLD}LibreTranslate is ready.${RESET}" 
	echo "Endpoint: http://$(hostname -I | awk '{print $1}'):${PORT}" 
	if [[ ${DISABLE_API_KEY} -eq 0 ]]; then
		if [[ ${GENERATED:-0} -eq 1 ]]; then
			echo "Generated API key: ${API_KEY}" 
		else
			echo "API key: ${API_KEY}" 
		fi
		echo "Use header: Authorization: <API_KEY>"
	else
		echo "API key authentication DISABLED (public instance)."
	fi
	[[ -n ${PRELOAD_LANGS} ]] && echo "Preloaded languages requested: ${PRELOAD_LANGS}" || true
	echo "Environment file: ${ENV_FILE}" 
	echo "Manage: docker logs -f ${SERVICE_NAME} | docker stop ${SERVICE_NAME}" 
	echo "Uninstall: sudo ${SCRIPT_NAME} --uninstall" 
	echo
}

main "$@"

