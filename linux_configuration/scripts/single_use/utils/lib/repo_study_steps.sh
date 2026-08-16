#!/bin/bash
# Dependency checks and the per-repo study-material steps.
#
# Sourced by repo_to_study.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

#==============================================================================
# Check Dependencies
#==============================================================================
check_dependencies() {
	local missing=()

	# Check for required scripts
	if [ ! -x "$ANALYZE_SCRIPT" ]; then
		missing+=("analyze_repo.sh not found at $ANALYZE_SCRIPT")
	fi

	if [ ! -x "$STUDY_SCRIPT" ]; then
		missing+=("generate_study_materials.sh not found at $STUDY_SCRIPT")
	fi

	# Check for basic tools
	for cmd in git curl grep sed awk; do
		if ! command -v "$cmd" &>/dev/null; then
			missing+=("$cmd")
		fi
	done

	if [ ${#missing[@]} -gt 0 ]; then
		print_error "Missing dependencies:"
		for dep in "${missing[@]}"; do
			echo "  - $dep"
		done
		exit 1
	fi
}

#==============================================================================
# Ensure Offline Docs are Available
#==============================================================================
ensure_offline_docs() {
	local docs_dir="$HOME/.local/share/offline-docs"

	if [ ! -d "$docs_dir/python" ]; then
		print_info "Offline docs not found. Setting up Python documentation..."
		if [ -x "$SETUP_DOCS_SCRIPT" ]; then
			"$SETUP_DOCS_SCRIPT" --python
		else
			print_info "Run setup_offline_docs.sh --all to enable offline documentation"
		fi
	fi
}

# Global to store repo name for cloned repos
REPO_NAME=""

#==============================================================================
# Get Repository
#==============================================================================
get_repo() {
	local input="$1"
	local repo_dir=""

	# Check if it's a URL (git clone needed)
	if [[ $input =~ ^https?:// ]] || [[ $input =~ ^git@ ]]; then
		print_step "Cloning repository..."

		# Extract repo name from URL
		REPO_NAME=$(basename "$input" .git)
		repo_dir="$WORK_DIR/$REPO_NAME"
		mkdir -p "$WORK_DIR"

		if git clone --depth 1 "$input" "$repo_dir" >&2 2>&1; then
			print_success "Cloned: $input"
		else
			print_error "Failed to clone repository"
			exit 1
		fi

		echo "$repo_dir"
	# Local path
	elif [ -d "$input" ]; then
		# Convert to absolute path
		repo_dir="$(cd "$input" && pwd)"
		REPO_NAME=$(basename "$repo_dir")
		print_success "Using local repository: $repo_dir"
		echo "$repo_dir"
	else
		print_error "Invalid input: '$input' is not a valid URL or directory"
		exit 1
	fi
}

#==============================================================================
# Analyze Repository
#==============================================================================
analyze_repo() {
	local repo_path="$1"
	local repo_name="$REPO_NAME"
	[ -z "$repo_name" ] && repo_name=$(basename "$repo_path")

	print_step "Analyzing repository..."

	# Run the analyzer (it outputs to stderr/stdout, results go to /tmp/repo_analysis/)
	"$ANALYZE_SCRIPT" "$repo_path" >&2 || true

	# Find the results directory
	local results_dir="/tmp/repo_analysis/results_${repo_name}"
	if [ ! -d "$results_dir" ]; then
		# Try without prefix
		results_dir="/tmp/repo_analysis/results"
	fi

	if [ ! -d "$results_dir" ] || [ ! -d "$results_dir/per_language" ]; then
		print_error "Could not find analysis results at $results_dir"
		exit 1
	fi

	print_success "Analysis complete: $results_dir"
	echo "$results_dir"
}

#==============================================================================
# Generate Study Materials
#==============================================================================
generate_materials() {
	local analysis_dir="$1"
	local output_dir="$2"

	print_step "Generating study materials with offline documentation..."

	# Run study materials generator
	cd "$analysis_dir" || { print_error "Cannot enter $analysis_dir"; return 1; }
	if "$STUDY_SCRIPT" . 2>/dev/null | grep -E "^(Created|✓|Files created)" | head -5; then
		print_success "Study materials generated"
	else
		# Try anyway, might have succeeded
		true
	fi

	# Create output directory and copy results
	mkdir -p "$output_dir"

	# Copy generated files
	[ -f "documentation_links.md" ] && cp "documentation_links.md" "$output_dir/"
	[ -f "anki_cards.txt" ] && cp "anki_cards.txt" "$output_dir/"
	[ -f "llm_anki_prompt.md" ] && cp "llm_anki_prompt.md" "$output_dir/"

	# Copy analysis data
	mkdir -p "$output_dir/analysis"
	[ -d "per_language" ] && cp -r "per_language" "$output_dir/analysis/"
	[ -f "grep_imports.txt" ] && cp "grep_imports.txt" "$output_dir/analysis/"
	[ -f "grep_keywords.txt" ] && cp "grep_keywords.txt" "$output_dir/analysis/"
	[ -f "grep_function_calls.txt" ] && cp "grep_function_calls.txt" "$output_dir/analysis/"

	print_success "Files saved to: $output_dir"
}

#==============================================================================
# Show Summary
#==============================================================================
show_summary() {
	local output_dir="$1"

	print_header "Study Materials Ready!"

	echo -e "${BOLD}Output directory:${NC} $output_dir"
	echo ""
	echo -e "${BOLD}Generated files:${NC}"

	if [ -f "$output_dir/documentation_links.md" ]; then
		local doc_lines
		doc_lines=$(wc -l <"$output_dir/documentation_links.md")
		echo -e "  📚 ${GREEN}documentation_links.md${NC} ($doc_lines lines)"
		echo "     Contains links to OFFLINE documentation"
	fi

	if [ -f "$output_dir/anki_cards.txt" ]; then
		local card_count
		card_count=$(grep -c $'^\w' "$output_dir/anki_cards.txt" 2>/dev/null || echo "0")
		echo -e "  🎴 ${GREEN}anki_cards.txt${NC} (~$card_count cards)"
		echo "     Import to Anki: File → Import → Tab separated"
	fi

	if [ -f "$output_dir/llm_anki_prompt.md" ]; then
		echo -e "  🤖 ${GREEN}llm_anki_prompt.md${NC}"
		echo "     Use with ChatGPT/Claude to generate more cards"
	fi

	if [ -d "$output_dir/analysis" ]; then
		echo -e "  📊 ${GREEN}analysis/${NC}"
		echo "     Raw analysis data (imports, keywords, functions per language)"
	fi

	echo ""
	echo -e "${BOLD}Quick preview of imports with offline docs:${NC}"
	if [ -f "$output_dir/documentation_links.md" ]; then
		grep -A20 "import/from" "$output_dir/documentation_links.md" 2>/dev/null |
			grep "^\| \`" | head -5 |
			sed 's/|/│/g'
	fi

	echo ""
	echo -e "${BOLD}Next steps:${NC}"
	echo "  1. Open documentation_links.md to browse offline docs"
	echo "  2. Import anki_cards.txt into Anki for spaced repetition"
	echo "  3. Use llm_anki_prompt.md to generate more targeted cards"
	echo ""
	echo -e "${CYAN}To view a doc:${NC} xdg-open 'file:///path/from/documentation_links.md'"
}

#==============================================================================
# Main
#==============================================================================
