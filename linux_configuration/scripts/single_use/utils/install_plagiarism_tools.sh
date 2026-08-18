#!/usr/bin/env bash
# Install Free & Open Source Plagiarism Detection Tools for Text
# Suitable for academic work (theses, papers, etc.)
#
# Tools installed:
# 1. Python NLP-based similarity detection (sklearn, NLTK, spaCy)
# 2. Sherlock text plagiarism detector
# 3. Ferret (Java-based, if Java available)
# 4. Optional: WCopyfind via Wine (Windows tool)

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/plagiarism-tools"
VENV_DIR="${HOME}/.local/share/plagiarism-venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/plagiarism_python.sh
source "$SCRIPT_DIR/lib/plagiarism_python.sh"
# shellcheck source=lib/plagiarism_sherlock.sh
source "$SCRIPT_DIR/lib/plagiarism_sherlock.sh"
# shellcheck source=lib/plagiarism_optional.sh
source "$SCRIPT_DIR/lib/plagiarism_optional.sh"

print_summary() {
	echo ""
	echo "=============================================="
	echo " Installation Complete!"
	echo "=============================================="
	echo ""
	echo "Installed tools:"
	echo ""
	echo "1. Python NLP Plagiarism Checker (TF-IDF, cosine similarity)"
	echo "   Usage: plagcheck file1.txt file2.txt"
	echo "          plagcheck --dir /path/to/documents/ --detailed"
	echo "   Location: $INSTALL_DIR/check_plagiarism.py"
	echo ""
	echo "2. Sherlock (n-gram fingerprinting)"
	echo "   Location: $INSTALL_DIR/sherlock/sherlock.py"
	echo ""
	echo "3. Python virtual environment with NLP libraries:"
	echo "   - scikit-learn (TF-IDF, cosine similarity)"
	echo "   - NLTK (tokenization, stopwords)"
	echo "   - spaCy (NLP processing)"
	echo "   - gensim (document similarity)"
	echo "   - textdistance, fuzzywuzzy (string matching)"
	echo "   Activate with: source $VENV_DIR/bin/activate"
	echo ""
	echo "Quick Start:"
	echo "  plagcheck thesis_v1.pdf thesis_v2.pdf --detailed"
	echo "  plagcheck --dir ./student_papers/ --threshold 0.4"
	echo ""
	echo "Note: Ensure ~/.local/bin is in your PATH:"
	# Printed for the user to paste into their shell rc: $HOME and $PATH must
	# stay literal rather than resolve to this machine's values.
	# shellcheck disable=SC2016
	echo '  export PATH="$HOME/.local/bin:$PATH"'
	echo ""
	echo "=============================================="

	if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
		warn "Add ~/.local/bin to your PATH by adding this to ~/.bashrc or ~/.zshrc:"
		# shellcheck disable=SC2016
		echo '  export PATH="$HOME/.local/bin:$PATH"'
	fi
}

main() {
	echo "=============================================="
	echo " Open Source Plagiarism Detection Installer"
	echo " For Academic Text (Theses, Papers, etc.)"
	echo "=============================================="
	echo ""

	mkdir -p "$INSTALL_DIR"

	install_python_nlp_tools "$SCRIPT_DIR"
	install_sherlock "$SCRIPT_DIR"
	check_ferret
	check_wcopyfind

	print_summary
}

main "$@"
