#!/bin/bash
# Individual Thorium profile repairs: state, locks, caches.
#
# Sourced by fix_thorium.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# Fix 1: Handle corrupted Local State file (most common crash cause)
fix_local_state() {
	log_info "Checking Local State file..."
	local local_state="$THORIUM_CONFIG_DIR/Local State"

	if [[ -f $local_state ]]; then
		# Check if it's valid JSON
		if ! python3 -c "import json; json.load(open('$local_state'))" 2>/dev/null; then
			log_warn "Local State file appears corrupted"
			backup_if_exists "$local_state"
		else
			# Even if valid JSON, back it up as it can still cause crashes
			log_info "Local State exists - backing up (common crash source)"
			backup_if_exists "$local_state"
		fi
	else
		log_info "No Local State file found (OK for fresh install)"
	fi
}

# Fix 2: Clear singleton lock files
fix_singleton_locks() {
	log_info "Clearing singleton lock files..."
	local locks=(
		"$THORIUM_CONFIG_DIR/SingletonLock"
		"$THORIUM_CONFIG_DIR/SingletonSocket"
		"$THORIUM_CONFIG_DIR/SingletonCookie"
	)

	local cleared=0
	for lock in "${locks[@]}"; do
		if remove_if_exists "$lock"; then
			((cleared++)) || true
		fi
	done

	if [[ $cleared -eq 0 ]]; then
		log_info "No stale lock files found"
	fi
}

# Fix 3: Clear GPU cache
fix_gpu_cache() {
	log_info "Clearing GPU cache..."
	local gpu_paths=(
		"$THORIUM_CONFIG_DIR/GPUCache"
		"$THORIUM_CONFIG_DIR/Default/GPUCache"
		"$THORIUM_CONFIG_DIR/ShaderCache"
		"$THORIUM_CONFIG_DIR/Default/ShaderCache"
	)

	local cleared=0
	for cache in "${gpu_paths[@]}"; do
		if remove_if_exists "$cache"; then
			((cleared++)) || true
		fi
	done

	if [[ $cleared -eq 0 ]]; then
		log_info "No GPU cache to clear"
	fi
}

# Fix 4: Clear crash reports (can accumulate and cause issues)
fix_crash_reports() {
	log_info "Clearing old crash reports..."
	local crash_dir="$THORIUM_CONFIG_DIR/Crash Reports"

	if [[ -d $crash_dir ]]; then
		local crash_count
		crash_count=$(find "$crash_dir" -type f 2>/dev/null | wc -l)
		if [[ $crash_count -gt 0 ]]; then
			if [[ $DRY_RUN == true ]]; then
				echo "  [dry-run] Would clear $crash_count crash report(s)"
			else
				rm -rf "$crash_dir"
				log_ok "Cleared $crash_count crash report(s)"
			fi
		fi
	fi
}

# Fix 5: Aggressive cleaning (optional)
fix_aggressive() {
	if [[ $AGGRESSIVE != true ]]; then
		return
	fi

	log_warn "Applying aggressive fixes (may lose some site data)..."

	local aggressive_paths=(
		"$THORIUM_CONFIG_DIR/Default/Service Worker"
		"$THORIUM_CONFIG_DIR/Default/Cache"
		"$THORIUM_CONFIG_DIR/Default/Code Cache"
		"$THORIUM_CONFIG_DIR/Default/IndexedDB"
		"$THORIUM_CONFIG_DIR/BrowserMetrics"
		"$THORIUM_CONFIG_DIR/component_crx_cache"
	)

	for path in "${aggressive_paths[@]}"; do
		remove_if_exists "$path"
	done

	# Backup potentially corrupted databases
	local db_files=(
		"$THORIUM_CONFIG_DIR/Default/Web Data"
		"$THORIUM_CONFIG_DIR/Default/History"
	)

	for db in "${db_files[@]}"; do
		if [[ -f $db ]]; then
			log_info "Checking database: $(basename "$db")"
			# Simple corruption check - if sqlite3 can't open it, back it up
			if command -v sqlite3 &>/dev/null; then
				if ! sqlite3 "$db" "PRAGMA integrity_check;" &>/dev/null; then
					log_warn "Database may be corrupted: $(basename "$db")"
					backup_if_exists "$db"
				fi
			fi
		fi
	done
}

# Test if Thorium starts successfully
test_thorium() {
	if [[ $TEST_AFTER != true ]]; then
		return
	fi

	log_info "Testing Thorium startup..."

	if [[ $DRY_RUN == true ]]; then
		echo "  [dry-run] Would test thorium-browser startup"
		return
	fi

	# Start Thorium in background
	thorium-browser &>/dev/null &
	local pid=$!

	# Wait a few seconds and check if it's still running
	sleep 4

	if kill -0 "$pid" 2>/dev/null; then
		log_ok "Thorium started successfully! (PID: $pid)"
		echo -e "${GREEN}Fix successful!${NC} Thorium is now running."

		# Offer to keep it running or kill it
		read -r -p "Keep browser running? [Y/n] " response
		case "$response" in
		[nN]*)
			kill "$pid" 2>/dev/null || true
			log_info "Browser closed"
			;;
		*)
			log_info "Browser left running"
			;;
		esac
	else
		log_error "Thorium still crashing after fixes"
		echo -e "${RED}Standard fixes did not resolve the issue.${NC}"
		echo ""
		echo "Try these additional steps:"
		echo "  1. Run with --aggressive flag for deeper cleaning"
		echo "  2. Test with fresh profile: thorium-browser --user-data-dir=/tmp/thorium-test"
		echo "  3. Reinstall: yay -S thorium-browser-bin"
		echo "  4. Check NVIDIA drivers: nvidia-smi"
		exit 1
	fi
}

# Main execution
