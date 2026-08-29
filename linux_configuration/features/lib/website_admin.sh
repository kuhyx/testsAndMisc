#!/bin/bash
# The browser post editor that ships with the personal website.
#
# Sourced by setup_personal_website.sh; split out to keep every file under the
# 250-line cap. Sourced rather than run, so it inherits the caller's strict
# mode plus WEBSITE_SRC / WEBSITE_DATA_DIR from above the source line.
#
# Deliberately NOT fronted by Caddy. The site is public; its editor writes into
# the content directory and triggers a real build, so it binds to loopback and
# is reached over an SSH tunnel:
#
#   ssh -N -L 4321:127.0.0.1:4321 <this host>
#
# A public route would also break the login outright: the session cookie is
# Secure, which a browser honours only over TLS or on localhost.

readonly ADMIN_PORT="4321"
readonly ADMIN_UNIT="personal-website-admin.service"
readonly ADMIN_UNIT_PATH="/etc/systemd/system/${ADMIN_UNIT}"
readonly ADMIN_ENV_FILE="${WEBSITE_DATA_DIR}/admin.env"
# The generated password, written once so setup needs no interactive prompt.
readonly ADMIN_PASSWORD_FILE="${WEBSITE_DATA_DIR}/admin-password"

# The service's own CLI, wrapped so the tests can stand in for it.
admin_cli() {
	node "${WEBSITE_SRC}/dist-admin/admin.js" "$@"
}

# --- Phase A: build the service and its editor page -------------------------
build_website_admin() {
	log_info "Building the admin editor…"
	(
		cd "$WEBSITE_SRC" || die "Cannot enter ${WEBSITE_SRC}."
		pnpm run build:admin
	)
	[[ -f "${WEBSITE_SRC}/dist-admin/admin.js" ]] ||
		die "Build did not produce ${WEBSITE_SRC}/dist-admin/admin.js."
	# Checked separately: without the page the service starts, answers, and
	# serves a blank document -- a failure that looks like a browser problem.
	[[ -f "${WEBSITE_SRC}/dist-admin/client/index.html" ]] ||
		die "Build did not produce the editor page (dist-admin/client/index.html)."
	log_ok "Admin editor built to ${WEBSITE_SRC}/dist-admin."
}

# --- Phase B: secrets -------------------------------------------------------
# A URL-safe password from the kernel's entropy. Printed nowhere: it goes
# straight into a 0600 file whose path the report names.
admin_new_password() {
	head -c 18 /dev/urandom | base64 | tr -d '\n/+='
}

admin_env_text() {
	cat <<EOF
# Managed by setup_personal_website.sh — do not edit by hand.
# The password itself is NOT here; only a scrypt hash of it.
PW_ADMIN_PASSWORD_HASH=$1
PW_ADMIN_SESSION_SECRET=$2
PW_ADMIN_PORT=${ADMIN_PORT}
PW_ADMIN_HOST=127.0.0.1
PW_ADMIN_ROOT=${WEBSITE_SRC}
EOF
}

# Idempotent on purpose: re-running setup must not silently change the
# password out from under a tunnel you already have open.
ensure_admin_secrets() {
	ensure_dir "$WEBSITE_DATA_DIR"
	if [[ -f $ADMIN_ENV_FILE ]] && grep -q '^PW_ADMIN_PASSWORD_HASH=scrypt' "$ADMIN_ENV_FILE"; then
		log_info "Reusing the existing admin credentials in ${ADMIN_ENV_FILE}."
		return 0
	fi

	local password hash secret
	password="$(admin_new_password)"
	hash="$(printf '%s' "$password" | admin_cli hash-password)" ||
		die "Could not hash the admin password."
	secret="$(admin_cli session-secret)" ||
		die "Could not generate a session secret."

	# umask inside a subshell: setting it for the rest of the process would
	# change the mode of every file the caller writes afterwards.
	(
		umask 077
		admin_env_text "$hash" "$secret" >"$ADMIN_ENV_FILE"
		printf '%s\n' "$password" >"$ADMIN_PASSWORD_FILE"
	)
	chmod 600 "$ADMIN_ENV_FILE" "$ADMIN_PASSWORD_FILE"
	log_ok "Generated admin credentials; the password is in ${ADMIN_PASSWORD_FILE}."
}

# --- Phase C: the unit ------------------------------------------------------
# systemd starts the service with a minimal PATH, and node here comes from nvm
# rather than /usr/bin. The build steps shell out to `node` by name, so the
# directory holding it has to be on the unit's PATH or every save fails at the
# prerender step with a "node: not found" the editor reports as a failed build.
admin_unit_text() {
	local node_bin node_dir
	node_bin="$(command -v node)" || die "node is not on PATH."
	node_dir="$(dirname "$node_bin")"
	cat <<EOF
# Managed by setup_personal_website.sh — do not edit by hand.
[Unit]
Description=Personal website admin editor (loopback only)
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${WEBSITE_SRC}
EnvironmentFile=${ADMIN_ENV_FILE}
Environment=PATH=${node_dir}:/usr/local/bin:/usr/bin
ExecStart=${node_bin} ${WEBSITE_SRC}/dist-admin/admin.js
Restart=always
RestartSec=5
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
# The service exists to write posts and rebuild the site, so its own checkout
# is the one place it must be able to change.
ReadWritePaths=${WEBSITE_SRC}
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
EOF
}

write_admin_unit() {
	admin_unit_text | sudo tee "$ADMIN_UNIT_PATH" >/dev/null
	sudo systemctl daemon-reload
	log_ok "Wrote ${ADMIN_UNIT_PATH}."
}

# --- Phase D: start and verify ----------------------------------------------
wait_for_admin() {
	local code _
	for _ in $(seq 1 20); do
		code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
			"http://127.0.0.1:${ADMIN_PORT}/admin" || echo "000")"
		if [[ $code == "200" ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

start_admin_service() {
	log_info "Starting ${ADMIN_UNIT}…"
	sudo systemctl enable --now "$ADMIN_UNIT"
	sudo systemctl restart "$ADMIN_UNIT"
	if wait_for_admin; then
		log_ok "Admin editor answering on 127.0.0.1:${ADMIN_PORT}."
	else
		sudo systemctl status --no-pager "$ADMIN_UNIT" || true
		die "The admin editor did not come up on 127.0.0.1:${ADMIN_PORT}."
	fi
}

admin_report() {
	cat <<EOF

--- Post editor (not on the internet) --------------------------------------
  Reach it by tunnelling to this host, then opening the local URL:

    ssh -N -L ${ADMIN_PORT}:127.0.0.1:${ADMIN_PORT} $(hostname)
    http://localhost:${ADMIN_PORT}/admin

  Password: cat ${ADMIN_PASSWORD_FILE}   (on this host, 0600)

  Posts written there are ordinary files in ${WEBSITE_SRC}/src/content/blog —
  commit them like any other change.
----------------------------------------------------------------------------
EOF
}

# The one entry point setup_cmd calls.
deploy_admin_service() {
	build_website_admin
	ensure_admin_secrets
	write_admin_unit
	start_admin_service
	admin_report
}

# --- status -----------------------------------------------------------------
admin_status_lines() {
	if systemctl is-active --quiet "$ADMIN_UNIT"; then
		status_line 0 "${ADMIN_UNIT} active"
	else
		status_line 1 "${ADMIN_UNIT} not running"
	fi
	status_line "$(check_http "http://127.0.0.1:${ADMIN_PORT}/admin")" \
		"admin editor answers on 127.0.0.1:${ADMIN_PORT}"
}
