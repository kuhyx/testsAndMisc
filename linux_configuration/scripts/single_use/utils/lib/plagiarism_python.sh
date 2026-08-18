#!/bin/bash
# Stage 1: Python NLP-based plagiarism detection environment.
#
# Sourced by install_plagiarism_tools.sh; split out to keep it under the
# 250-line cap. Sourced rather than run, so it inherits the caller's strict
# mode and the color/log helpers and INSTALL_DIR/VENV_DIR globals defined
# above the source line.

# Create the venv, pip-install the NLP stack, and install check_plagiarism.py
# (plus the plagiarism_similarity.py module it imports) and its "plagcheck"
# wrapper. $1 is the directory install_plagiarism_tools.sh lives in, so both
# scripts can be copied from beside it.
install_python_nlp_tools() {
	local script_dir="$1"

	echo ""
	echo "=== 1. Installing Python NLP-based Plagiarism Tools ==="

	if ! command -v python3 &>/dev/null; then
		error "Python 3 is required but not installed."
		exit 1
	fi

	if [ ! -d "$VENV_DIR" ]; then
		echo "Creating Python virtual environment..."
		python3 -m venv "$VENV_DIR"
		success "Virtual environment created at $VENV_DIR"
	else
		warn "Virtual environment already exists at $VENV_DIR"
	fi

	# Created at runtime by `python -m venv` above, so there is nothing on disk
	# for the linter to follow at check time.
	# shellcheck disable=SC1091
	source "$VENV_DIR/bin/activate"

	echo "Installing Python packages for text similarity detection..."
	pip install --upgrade pip

	pip install --progress-bar on \
		scikit-learn \
		nltk \
		spacy \
		gensim \
		numpy \
		pandas \
		python-docx \
		PyPDF2 \
		beautifulsoup4 \
		lxml \
		textdistance \
		fuzzywuzzy \
		python-Levenshtein

	success "Python NLP packages installed"

	echo "Downloading NLTK data (stopwords, punkt tokenizer)..."
	python3 "$script_dir/download_nltk_data.py"
	success "NLTK data downloaded"

	echo "Downloading spaCy English model..."
	python3 -m spacy download en_core_web_sm 2>/dev/null || warn "spaCy model download may need manual install: python -m spacy download en_core_web_sm"
	success "spaCy model installed"

	install -m 755 "$script_dir/check_plagiarism.py" "$INSTALL_DIR/check_plagiarism.py"
	install -m 644 "$script_dir/plagiarism_similarity.py" "$INSTALL_DIR/plagiarism_similarity.py"
	success "Created plagiarism checker script at $INSTALL_DIR/check_plagiarism.py"

	mkdir -p "$HOME/.local/bin"
	cat >"$HOME/.local/bin/plagcheck" <<WRAPEOF
#!/usr/bin/env bash
# Wrapper for plagiarism checker
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/check_plagiarism.py" "\$@"
WRAPEOF
	chmod +x "$HOME/.local/bin/plagcheck"
	success "Created 'plagcheck' command in ~/.local/bin/"

	deactivate
}
