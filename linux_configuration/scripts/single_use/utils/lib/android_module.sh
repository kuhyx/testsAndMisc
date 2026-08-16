#!/bin/bash
# Building the Magisk hosts module.
#
# Sourced by update_android_hosts.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.

# Build the module zip
build_module() {
	local tmp_dir="$WORK_DIR/guardian_module"
	local module_zip="$WORK_DIR/android_guardian.zip"

	echo "[BUILD] Building Android Guardian module..." >&2

	rm -rf "$tmp_dir"
	mkdir -p "$tmp_dir/system/etc"

	# Copy module files
	cp "$GUARDIAN_MODULE_DIR/module.prop" "$tmp_dir/"
	cp "$GUARDIAN_MODULE_DIR/service.sh" "$tmp_dir/"
	cp "$GUARDIAN_MODULE_DIR/post-fs-data.sh" "$tmp_dir/"
	cp "$GUARDIAN_MODULE_DIR/uninstall.sh" "$tmp_dir/"

	# Build hosts file
	local hosts_file="$tmp_dir/system/etc/hosts"
	if [[ -f /etc/hosts.stevenblack ]]; then
		echo "[BUILD] Using StevenBlack hosts cache..." >&2
		cp /etc/hosts.stevenblack "$hosts_file"
	elif [[ -f /etc/hosts ]]; then
		echo "[BUILD] Using /etc/hosts..." >&2
		cp /etc/hosts "$hosts_file"
	else
		die "No hosts file found"
	fi

	# Append custom blocking entries
	# The blocklist is a data file, not a heredoc: 248 lines of hosts
	# entries that belong under data/ where they can be diffed and edited
	# without touching shell.
	cat "$SCRIPT_DIR/data/android_guardian_blocklist.hosts" >>"$hosts_file"

	local total_entries
	total_entries=$(grep -c "^0\.0\.0\.0 " "$hosts_file" || echo 0)
	echo "[BUILD] Hosts file contains $total_entries blocked domains" >&2

	# Create zip
	(cd "$tmp_dir" && zip -r "$module_zip" . -x "*.DS_Store") >/dev/null

	echo "$module_zip"
}
