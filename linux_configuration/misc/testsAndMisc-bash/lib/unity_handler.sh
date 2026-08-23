#!/bin/bash
# Desktop entry, MIME registration and verification for Unity Hub.
#
# Sourced by fix_unity.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

create_handler_desktop() {
	local exec_cmd="$1"
	local dest="$DESKTOP_DIR/unityhub-url-handler.desktop"
	log_info "Writing handler desktop entry: $dest"
	cat >"$dest" <<DESK
[Desktop Entry]
Name=Unity Hub URL Handler
Comment=Handle unityhub:// links for Unity Hub sign-in
Exec=${exec_cmd}
Terminal=false
Type=Application
Icon=unityhub
Categories=Development;
StartupWMClass=Unity Hub
MimeType=x-scheme-handler/unityhub;x-scheme-handler/unity;
NoDisplay=true
DESK
	log_ok "Desktop entry created/updated."
	echo "$dest"
}

register_mime_handler() {
	local desktop_file="$1"
	# Update desktop database if available
	if command -v update-desktop-database >/dev/null 2>&1; then
		update-desktop-database "$DESKTOP_DIR" || true
	else
		log_warn "update-desktop-database not found (install desktop-file-utils)."
	fi

	# Register as default handler for both schemes
	if command -v xdg-mime >/dev/null 2>&1; then
		xdg-mime default "$(basename "$desktop_file")" x-scheme-handler/unityhub || true
		xdg-mime default "$(basename "$desktop_file")" x-scheme-handler/unity || true
	else
		log_error "xdg-mime not found (install xdg-utils)."
		return 1
	fi
	log_ok "MIME handler registered for unityhub:// (and unity://)."
}

verify_registration() {
	local expected cur1 cur2
	expected="$(basename "$1")"
	cur1="$(xdg-mime query default x-scheme-handler/unityhub 2>/dev/null || true)"
	cur2="$(xdg-mime query default x-scheme-handler/unity 2>/dev/null || true)"
	log_info "Current handler (unityhub): ${cur1:-<none>}"
	log_info "Current handler (unity):    ${cur2:-<none>}"
	if [[ $cur1 == "$expected" ]]; then
		log_ok "unityhub scheme correctly set to $expected"
	else
		log_warn "unityhub scheme not set to $expected (currently: ${cur1:-none})."
	fi
}

maybe_test_open() {
	if [[ $RUN_TEST == true ]]; then
		log_info "Opening test link: unityhub://v1/editor-signin"
		if command -v xdg-open >/dev/null 2>&1; then
			xdg-open 'unityhub://v1/editor-signin' >/dev/null 2>&1 || true
			log_ok "Test link invoked. Check if Unity Hub launches or focuses."
		else
			log_warn "xdg-open not found; cannot run test automatically."
		fi
	else
		log_info "You can test manually with: xdg-open 'unityhub://v1/editor-signin'"
	fi
}
