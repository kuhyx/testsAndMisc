#!/bin/bash
# Stages 3-4: optional plagiarism tools that need a manual download.
#
# Sourced by install_plagiarism_tools.sh; split out to keep it under the
# 250-line cap. Sourced rather than run, so it inherits the caller's strict
# mode and the color/log helpers and INSTALL_DIR global defined above the
# source line.

# Ferret (Java-based) - Optional
check_ferret() {
	echo ""
	echo "=== 3. Checking for Ferret (Java-based plagiarism tool) ==="

	if ! command -v java &>/dev/null; then
		warn "Java not installed, skipping Ferret"
		return
	fi

	local ferret_dir="$INSTALL_DIR/ferret"
	if [ -d "$ferret_dir" ]; then
		return
	fi

	mkdir -p "$ferret_dir"
	echo "Ferret is a Java-based tool from University of Hertfordshire."
	echo "Download manually from: https://homepages.herts.ac.uk/~comqcln/Ferret/"
	echo "Place JAR file in: $ferret_dir"
	warn "Ferret requires manual download (academic license)"
}

# WCopyfind via Wine (Optional)
check_wcopyfind() {
	echo ""
	echo "=== 4. WCopyfind Information (Windows tool, needs Wine) ==="

	if command -v wine &>/dev/null; then
		echo "Wine is available. WCopyfind can be run via Wine."
		echo "Download from: https://plagiarism.bloomfieldmedia.com/software/wcopyfind/"
		echo "Run with: wine /path/to/WCopyfind.exe"
		warn "WCopyfind requires manual download"
		return
	fi

	echo "Wine not installed. To use WCopyfind:"
	echo "  1. Install wine: sudo apt install wine  (or equivalent)"
	echo "  2. Download WCopyfind from: https://plagiarism.bloomfieldmedia.com/software/wcopyfind/"
	warn "WCopyfind skipped (Wine not available)"
}
