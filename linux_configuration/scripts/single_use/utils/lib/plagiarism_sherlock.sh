#!/bin/bash
# Stage 2: Sherlock text plagiarism detector.
#
# Sourced by install_plagiarism_tools.sh; split out to keep it under the
# 250-line cap. Sourced rather than run, so it inherits the caller's strict
# mode and the color/log helpers and INSTALL_DIR global defined above the
# source line.

# Clone the upstream sherlock-py tool, falling back to the bundled
# sherlock.py (n-gram fingerprinting) when git or the clone is unavailable.
# $1 is the directory install_plagiarism_tools.sh lives in, so the fallback
# sherlock.py can be copied from beside it.
install_sherlock() {
	local script_dir="$1"

	echo ""
	echo "=== 2. Installing Sherlock Text Plagiarism Detector ==="

	local sherlock_dir="$INSTALL_DIR/sherlock"
	if [ -d "$sherlock_dir" ]; then
		warn "Sherlock already installed at $sherlock_dir"
		return
	fi

	if ! command -v git &>/dev/null; then
		warn "Git not available, skipping Sherlock installation"
		return
	fi

	# There are several Sherlock implementations; using a popular Python one
	if git clone --depth 1 https://github.com/Zedeldi/sherlock-py.git "$sherlock_dir" 2>/dev/null; then
		success "Sherlock installed at $sherlock_dir"
		return
	fi

	warn "Could not clone sherlock-py, trying alternative..."
	mkdir -p "$sherlock_dir"
	install -m 755 "$script_dir/sherlock.py" "$sherlock_dir/sherlock.py"
	success "Sherlock installed at $sherlock_dir"
}
