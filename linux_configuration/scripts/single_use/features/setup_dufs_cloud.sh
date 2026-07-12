#!/bin/bash
# setup_dufs_cloud.sh — Self-hosted "cloud" storage (dufs) on this Arch PC.
#
# Stands up dufs (a single Rust binary: web UI + built-in WebDAV over a real
# folder), bound to 127.0.0.1 and fronted by the EXISTING Caddy reverse proxy
# (from setup_gitea.sh) for automatic public HTTPS at a new DuckDNS subdomain.
# Also mirrors the KeePassXC vault into the served folder on every change so it
# is always fetchable from the phone (KeePassDX syncs it natively over WebDAV).
#
# Reuses the host's existing exposure stack — it does NOT add a second Caddy,
# a second DuckDNS updater, or hand-edit /etc/nftables.conf. See
# .github/skills/self-hosted-service-exposure/SKILL.md.
#
# Run as your normal user (NOT root). It uses sudo only for pacman, the binary
# install, systemd units and the firewall flag. Idempotent — safe to re-run.
#
# Usage:
#   ./setup_dufs_cloud.sh          Install / update everything
#   ./setup_dufs_cloud.sh -h       Show help

set -euo pipefail

# --- Pinned dufs release (verified by sha256) --------------------------------
readonly DUFS_VERSION="0.46.0"
readonly DUFS_SHA256="817769f726613194bcff9d0e3e481eaccc86ac11208857614f36a8c02f410977"
readonly DUFS_ASSET="dufs-v${DUFS_VERSION}-x86_64-unknown-linux-musl.tar.gz"
readonly DUFS_URL="https://github.com/sigoden/dufs/releases/download/v${DUFS_VERSION}/${DUFS_ASSET}"
readonly DUFS_BIN="/usr/local/bin/dufs"
readonly DUFS_PORT=5000

# --- Existing host infrastructure (from setup_gitea.sh / install_joplin.sh) --
readonly CADDY_CONTAINER="gitea-caddy"
readonly CADDYFILE="${HOME}/gitea/Caddyfile"
readonly CADDYFILE_IN_CONTAINER="/etc/caddy/Caddyfile"
readonly DUCKDNS_UPDATER="${HOME}/.joplin-server/duckdns-update.sh"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly SYSTEMD_SRC="${SCRIPT_DIR}/systemd"
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"
readonly CONFIG_FILE="${SCRIPT_DIR}/.dufs_cloud.conf"

# Git repo root (used by the paranoid secret guards below).
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null || true)"
readonly REPO_ROOT

# shellcheck source=../../lib/common.sh
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../../lib/common.sh"

# OS user that will own and run the service (not the dufs web-login user).
SYS_USER="$(get_actual_user)"
readonly SYS_USER

# Config values (populated from CONFIG_FILE / prompts).
DUFS_USER=""
DUFS_PASSWORD=""
DUFS_SUBDOMAIN=""
CLOUD_ROOT=""

die() {
	log_error "$1"
	exit 1
}

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit 0
}

# --- Step 1: preflight -------------------------------------------------------
preflight() {
	log_info "Preflight checks"
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root (it will sudo where needed)."

	# Runtime deps; install any that are missing from the official repos.
	install_missing_pacman_packages curl rsync inotify-tools openssl

	# The public-exposure stack must already exist (Caddy from setup_gitea.sh).
	has_cmd docker || die "docker not found — run setup_gitea.sh first."
	docker ps --format '{{.Names}}' | grep -qx "${CADDY_CONTAINER}" \
		|| die "Caddy container '${CADDY_CONTAINER}' not running — run setup_gitea.sh first."
	[[ -f ${CADDYFILE} ]] || die "Caddyfile ${CADDYFILE} missing — run setup_gitea.sh first."
	[[ -x ${DUCKDNS_UPDATER} ]] || die "DuckDNS updater ${DUCKDNS_UPDATER} missing — run install_joplin.sh first."
	log_ok "Host exposure stack present (docker + ${CADDY_CONTAINER} + DuckDNS updater)"
}

# --- Step 2: configuration (gitignored .conf, prompt when empty) -------------
load_config() {
	if [[ -f ${CONFIG_FILE} ]]; then
		# shellcheck source=/dev/null
		source "${CONFIG_FILE}"
	fi
	DUFS_USER="${DUFS_USER:-}"
	DUFS_PASSWORD="${DUFS_PASSWORD:-}"
	DUFS_SUBDOMAIN="${DUFS_SUBDOMAIN:-}"
	CLOUD_ROOT="${CLOUD_ROOT:-}"
}

prompt_config() {
	if [[ -z ${DUFS_USER} ]]; then
		read -r -p "dufs web username [${SYS_USER}]: " DUFS_USER
		DUFS_USER="${DUFS_USER:-${SYS_USER}}"
	fi
	if [[ -z ${DUFS_PASSWORD} ]]; then
		read -r -s -p "dufs web password: " DUFS_PASSWORD
		echo
		[[ -n ${DUFS_PASSWORD} ]] || die "A password is required (this server is public)."
	fi
	if [[ -z ${DUFS_SUBDOMAIN} ]]; then
		read -r -p "public subdomain [kuhy-cloud.duckdns.org]: " DUFS_SUBDOMAIN
		DUFS_SUBDOMAIN="${DUFS_SUBDOMAIN:-kuhy-cloud.duckdns.org}"
	fi
	if [[ -z ${CLOUD_ROOT} ]]; then
		read -r -p "cloud storage folder [${HOME}/cloud]: " CLOUD_ROOT
		CLOUD_ROOT="${CLOUD_ROOT:-${HOME}/cloud}"
	fi
}

# Paranoid guard: never persist the plaintext password unless git is certain
# the file is ignored. This is checked against the live .gitignore, so a broken
# or removed ignore rule stops the write instead of leaking the secret.
assert_config_gitignored() {
	[[ -n ${REPO_ROOT} ]] || die "Not inside a git repo — refusing to write the secret config."
	if ! git -C "${REPO_ROOT}" check-ignore -q "${CONFIG_FILE}"; then
		die "Refusing to write ${CONFIG_FILE}: it is NOT gitignored. Restore the .gitignore rule first — will not risk leaking the password."
	fi
}

save_config() {
	assert_config_gitignored
	# 0600, gitignored — holds the plaintext web password so re-runs stay
	# non-interactive. Never committed (see .gitignore + the check-no-dufs-conf
	# pre-commit hook, which blocks it even against `git add -f`).
	umask 077
	{
		printf 'DUFS_USER=%q\n' "${DUFS_USER}"
		printf 'DUFS_PASSWORD=%q\n' "${DUFS_PASSWORD}"
		printf 'DUFS_SUBDOMAIN=%q\n' "${DUFS_SUBDOMAIN}"
		printf 'CLOUD_ROOT=%q\n' "${CLOUD_ROOT}"
	} >"${CONFIG_FILE}"
	chmod 600 "${CONFIG_FILE}"
	log_ok "Saved config to ${CONFIG_FILE} (0600)"
}

# --- Step 3: install the pinned, checksum-verified dufs binary ---------------
install_dufs() {
	if [[ -x ${DUFS_BIN} ]] && "${DUFS_BIN}" --version 2>/dev/null | grep -q "${DUFS_VERSION}"; then
		log_ok "dufs ${DUFS_VERSION} already installed"
		return 0
	fi
	log_info "Installing dufs ${DUFS_VERSION}"
	local tmp
	tmp="$(mktemp -d)"
	# shellcheck disable=SC2064
	trap "rm -rf '${tmp}'" RETURN
	curl -fsSL -o "${tmp}/${DUFS_ASSET}" "${DUFS_URL}"
	echo "${DUFS_SHA256}  ${tmp}/${DUFS_ASSET}" | sha256sum -c - \
		|| die "dufs checksum mismatch — refusing to install."
	tar -xzf "${tmp}/${DUFS_ASSET}" -C "${tmp}"
	sudo install -m 0755 "${tmp}/dufs" "${DUFS_BIN}"
	log_ok "Installed ${DUFS_BIN}"
}

# Paranoid guard: never let dufs serve a directory that would expose secrets
# (home root, ~/.ssh, ~/.config — which holds dufs.yaml — ~/.gnupg, / , or the
# git repo which holds the gitignored .dufs_cloud.conf).
assert_cloud_root_safe() {
	local resolved home_r
	resolved="$(readlink -m "${CLOUD_ROOT}")"
	home_r="$(readlink -m "${HOME}")"
	case "${resolved}" in
	"${home_r}" | / | "${home_r}/.ssh" | "${home_r}/.ssh/"* \
		| "${home_r}/.config" | "${home_r}/.config/"* \
		| "${home_r}/.gnupg" | "${home_r}/.gnupg/"*)
		die "Unsafe cloud folder '${CLOUD_ROOT}' — it would expose sensitive files. Use a dedicated folder like ${HOME}/cloud." ;;
	esac
	if [[ -n ${REPO_ROOT} && (${resolved} == "${REPO_ROOT}" || ${resolved} == "${REPO_ROOT}/"*) ]]; then
		die "Unsafe cloud folder '${CLOUD_ROOT}' — it is inside the git repo (which holds the secret config). Use a dedicated folder."
	fi
}

# --- Step 4: served folder ---------------------------------------------------
create_serve_dir() {
	assert_cloud_root_safe
	ensure_dir "${CLOUD_ROOT}"
	ensure_dir "${CLOUD_ROOT}/Keepass"
	chmod 700 "${CLOUD_ROOT}"
	log_ok "Cloud folder ${CLOUD_ROOT} ready"
}

# --- Step 5: dufs config (SHA-512 hashed password, no anonymous access) -------
write_dufs_config() {
	local cfg_dir="${HOME}/.config/dufs"
	local cfg="${cfg_dir}/dufs.yaml"
	local hash
	# Read the password from stdin so it never appears in the process argv (ps).
	hash="$(printf '%s' "${DUFS_PASSWORD}" | openssl passwd -6 -stdin)"
	# Serve the cloud_gallery SPA (render-spa) ONLY once it is deployed into the
	# cloud root — a fresh dufs with no gallery keeps the default file listing.
	local render=""
	[[ -f "${CLOUD_ROOT}/index.html" ]] && render="render-spa: true"
	ensure_dir "${cfg_dir}"
	umask 077
	cat >"${cfg}" <<EOF
# Generated by setup_dufs_cloud.sh — do not edit by hand.
serve-path: ${CLOUD_ROOT}
bind: 127.0.0.1
port: ${DUFS_PORT}
allow-all: true
${render}
auth:
  - "${DUFS_USER}:${hash}@/:rw"
EOF
	chmod 600 "${cfg}"
	log_ok "Wrote ${cfg} (auth required, password hashed)"
}

# --- Step 6: systemd units (render placeholders → /etc/systemd/system) -------
render_unit() {
	local name="$1"
	sed -e "s|__USER__|${SYS_USER}|g" \
		-e "s|__HOME__|${HOME}|g" \
		-e "s|__CLOUD_ROOT__|${CLOUD_ROOT}|g" \
		"${SYSTEMD_SRC}/${name}" | sudo tee "/etc/systemd/system/${name}" >/dev/null
}

install_units() {
	log_info "Installing systemd units"
	render_unit dufs.service
	render_unit keepass-cloud-sync.service
	render_unit keepass-cloud-sync.path
	sudo systemctl daemon-reload
	sudo systemctl enable --now dufs.service
	log_ok "dufs.service enabled and started"
}

# --- Step 7: Caddy reverse-proxy block (append + reload) ---------------------
configure_caddy() {
	if grep -qE "^${DUFS_SUBDOMAIN} \{" "${CADDYFILE}"; then
		log_ok "Caddyfile already has a block for ${DUFS_SUBDOMAIN}"
	else
		log_info "Adding Caddy block for ${DUFS_SUBDOMAIN}"
		# NOTE: appended to the shared Gitea Caddyfile. Re-running setup_gitea.sh
		# regenerates that file and drops this block — re-run setup_dufs_cloud.sh
		# to restore it. Caddyfile uses tab indentation.
		printf '\n%s {\n\treverse_proxy 127.0.0.1:%s\n}\n' "${DUFS_SUBDOMAIN}" "${DUFS_PORT}" \
			>>"${CADDYFILE}"
	fi
	docker exec "${CADDY_CONTAINER}" caddy reload --config "${CADDYFILE_IN_CONTAINER}" \
		|| die "caddy reload failed — check 'docker logs ${CADDY_CONTAINER}'."
	log_ok "Caddy reloaded (auto-HTTPS will be issued once the subdomain resolves)"
}

# --- Step 8: DuckDNS subdomain (extend existing updater; no new cron) --------
configure_duckdns() {
	local label="${DUFS_SUBDOMAIN%.duckdns.org}"
	if grep -qE "domains=[^&\"']*${label}([,&\"']|$)" "${DUCKDNS_UPDATER}"; then
		log_ok "DuckDNS updater already includes '${label}'"
	else
		log_info "Adding '${label}' to the existing DuckDNS updater"
		sed -i -E "s|(domains=)([^&\"']*)|\1\2,${label}|" "${DUCKDNS_UPDATER}"
	fi
	# Refresh now (harmless if the subdomain isn't registered yet).
	bash "${DUCKDNS_UPDATER}" || log_warn "DuckDNS update returned non-zero (register the subdomain first)."
	if getent hosts "${DUFS_SUBDOMAIN}" >/dev/null 2>&1; then
		log_ok "${DUFS_SUBDOMAIN} resolves"
	else
		log_warn "${DUFS_SUBDOMAIN} does not resolve yet — create the '${label}' subdomain in the DuckDNS dashboard."
	fi
}

# --- Step 9: firewall (open 80/443 via the owning script, idempotent) -------
ensure_firewall() {
	if sudo nft list ruleset 2>/dev/null | grep -qE 'dport \{[^}]*80[^}]*443'; then
		log_ok "Firewall already allows tcp/80 + tcp/443"
	elif [[ -f ${WG_SCRIPT} ]]; then
		log_info "Opening 80/443 via setup_wireguard_ssh.sh allow-web"
		sudo bash "${WG_SCRIPT}" allow-web
	else
		log_warn "setup_wireguard_ssh.sh not found — ensure tcp/80+443 are open."
	fi
}

# --- Step 10: KeePass auto-sync (initial mirror + enable the path watcher) ---
setup_autosync() {
	log_info "Setting up KeePass auto-sync watcher"
	# Mirror only the vault file (not the whole dir with local .backup_* vaults).
	rsync -a "${HOME}/Keepass/Passwords.kdbx" "${CLOUD_ROOT}/Keepass/"
	sudo systemctl enable --now keepass-cloud-sync.path
	log_ok "Vault mirrored and watcher enabled"
}

# --- Step 11: report ---------------------------------------------------------
print_report() {
	local url="https://${DUFS_SUBDOMAIN}"
	cat <<EOF

============================================================================
  dufs cloud is up.
    Web UI / WebDAV : ${url}/
    Login           : ${DUFS_USER} / (your password)
    Served folder   : ${CLOUD_ROOT}
    KeePassDX target: ${url}/Keepass/Passwords.kdbx  (WebDAV)

  If the subdomain is new, create it once in the DuckDNS dashboard
  (label: ${DUFS_SUBDOMAIN%.duckdns.org}) so Caddy can issue TLS.

  Acceptance test: on your phone with Wi-Fi OFF (cellular), open ${url}/,
  log in, and confirm you see Keepass/Passwords.kdbx.
============================================================================
EOF
}

main() {
	[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage
	print_setup_header "Self-hosted dufs cloud storage"
	preflight
	load_config
	prompt_config
	save_config
	install_dufs
	create_serve_dir
	write_dufs_config
	install_units
	configure_caddy
	configure_duckdns
	ensure_firewall
	setup_autosync
	print_report
}

main "$@"
