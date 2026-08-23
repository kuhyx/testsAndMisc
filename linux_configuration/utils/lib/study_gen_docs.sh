#!/usr/bin/env bash
# lib/study_gen_docs.sh — write documentation_links.md, the markdown index of
# every top keyword, function call and import the analysis found.

# Write the markdown documentation-link file covering every top keyword,
# function call and import in the analysis.
generate_doc_links() {
	#==============================================================================
	# Generate Documentation Links (Markdown)
	#==============================================================================
	echo -e "${YELLOW}Generating documentation links...${NC}"

	cat >"$DOCS_FILE" <<'EOF'
# Documentation Links for Code Review

This document contains links to official documentation for the most commonly used
functions, keywords, and patterns found in the analyzed codebase.

**Note:** Items are grouped by language for accurate documentation links.

---

EOF

	# Check for per-language files
	PER_LANG_DIR="$RESULTS_DIR/per_language"

	if [ -d "$PER_LANG_DIR" ]; then
		echo -e "${GREEN}Using per-language analysis files${NC}"

		# Map internal lang names to doc function names
		lang_to_doc() {
			case "$1" in
			c_cpp) echo "cpp" ;;
			javascript) echo "js" ;;
			typescript) echo "ts" ;;
			shell) echo "bash" ;;
			*) echo "$1" ;;
			esac
		}

		# Process keywords by language
		{
			echo "## Language Keywords"
			echo ""
		} >>"$DOCS_FILE"

		for keyword_file in "$PER_LANG_DIR"/keywords_*.txt; do
			[ ! -f "$keyword_file" ] && continue
			[ ! -s "$keyword_file" ] && continue

			# Extract language name from filename
			lang=$(basename "$keyword_file" | sed 's/keywords_//; s/\.txt//')
			doc_lang=$(lang_to_doc "$lang")

			# Format language name for display
			case "$lang" in
			c_cpp) display_lang="C/C++" ;;
			javascript) display_lang="JavaScript" ;;
			typescript) display_lang="TypeScript" ;;
			python) display_lang="Python" ;;
			rust) display_lang="Rust" ;;
			go) display_lang="Go" ;;
			ruby) display_lang="Ruby" ;;
			java) display_lang="Java" ;;
			shell) display_lang="Shell/Bash" ;;
			*) display_lang="$lang" ;;
			esac

			{
				echo "### $display_lang Keywords"
				echo ""
				echo "| Keyword | Count | Documentation |"
				echo "|---------|-------|---------------|"
			} >>"$DOCS_FILE"

			{ grep -v '^#' "$keyword_file" || true; } | head -n "$TOP_N" | while read -r count term; do
				[ -z "$term" ] && continue
				url=$(get_doc_url "$term" "$doc_lang")
				echo "| \`$term\` | $count | [docs]($url) |" >>"$DOCS_FILE"
			done
			echo "" >>"$DOCS_FILE"
		done

		# Process functions by language
		{
			echo "## Function/Method Calls"
			echo ""
		} >>"$DOCS_FILE"

		for func_file in "$PER_LANG_DIR"/functions_*.txt; do
			[ ! -f "$func_file" ] && continue
			[ ! -s "$func_file" ] && continue

			lang=$(basename "$func_file" | sed 's/functions_//; s/\.txt//')
			doc_lang=$(lang_to_doc "$lang")

			case "$lang" in
			c_cpp) display_lang="C/C++" ;;
			javascript) display_lang="JavaScript" ;;
			typescript) display_lang="TypeScript" ;;
			python) display_lang="Python" ;;
			rust) display_lang="Rust" ;;
			go) display_lang="Go" ;;
			ruby) display_lang="Ruby" ;;
			java) display_lang="Java" ;;
			shell) display_lang="Shell/Bash" ;;
			*) display_lang="$lang" ;;
			esac

			{
				echo "### $display_lang Functions"
				echo ""
				echo "| Function | Count | Documentation |"
				echo "|----------|-------|---------------|"
			} >>"$DOCS_FILE"

			{ grep -v '^#' "$func_file" || true; } | head -n "$TOP_N" | while read -r count term; do
				[ -z "$term" ] && continue
				[[ $term =~ ^(if|for|while|switch|catch|elif)$ ]] && continue
				url=$(get_doc_url "$term" "$doc_lang")
				echo "| \`$term()\` | $count | [docs]($url) |" >>"$DOCS_FILE"
			done
			echo "" >>"$DOCS_FILE"
		done

		# Process imports by language
		{
			echo "## Imports/Includes"
			echo ""
		} >>"$DOCS_FILE"

		for import_file in "$PER_LANG_DIR"/imports_*.txt; do
			[ ! -f "$import_file" ] && continue
			[ ! -s "$import_file" ] && continue

			lang=$(basename "$import_file" | sed 's/imports_//; s/\.txt//')
			doc_lang=$(lang_to_doc "$lang")

			case "$lang" in
			c_cpp) display_lang="C/C++ (#include)" ;;
			javascript) display_lang="JavaScript (import/require)" ;;
			typescript) display_lang="TypeScript (import)" ;;
			python) display_lang="Python (import/from)" ;;
			rust) display_lang="Rust (use)" ;;
			go) display_lang="Go (import)" ;;
			ruby) display_lang="Ruby (require)" ;;
			java) display_lang="Java (import)" ;;
			shell) display_lang="Shell (source)" ;;
			*) display_lang="$lang" ;;
			esac

			{
				echo "### $display_lang"
				echo ""
				echo "| Import | Count | Documentation |"
				echo "|--------|-------|---------------|"
			} >>"$DOCS_FILE"

			{ grep -v '^#' "$import_file" || true; } | head -n "$TOP_N" | while read -r count import; do
				[ -z "$import" ] && continue
				# For offline lookup, pass the full import line for better context
				url=$(get_doc_url "" "$doc_lang" "$import")
				if [ -z "$url" ] || [[ $url == *"search.html"* ]]; then
					# Fallback: extract module and try again
					module=$(echo "$import" | sed -E 's/.*[<"]([^">]+)[">].*/\1/' | sed 's|.*/||' | sed 's/\..*$//')
					url=$(get_doc_url "$module" "$doc_lang")
				fi
				import_escaped="${import//|/\\|}"
				echo "| \`$import_escaped\` | $count | [docs]($url) |" >>"$DOCS_FILE"
			done
			echo "" >>"$DOCS_FILE"
		done

	else
		# Fallback to combined files (old behavior)
		echo -e "${YELLOW}No per-language files found, using combined analysis${NC}"

		if [ -f "$RESULTS_DIR/grep_keywords.txt" ]; then
			{
				echo "## Language Keywords"
				echo ""
				echo "| Keyword | Count | Documentation |"
				echo "|---------|-------|---------------|"
			} >>"$DOCS_FILE"

			{ grep -v '^#' "$RESULTS_DIR/grep_keywords.txt" || true; } | head -n "$TOP_N" | while read -r count term; do
				[ -z "$term" ] && continue
				url=$(get_doc_url "$term" "$PRIMARY_LANG")
				echo "| \`$term\` | $count | [docs]($url) |" >>"$DOCS_FILE"
			done
			echo "" >>"$DOCS_FILE"
		fi

		if [ -f "$RESULTS_DIR/grep_function_calls.txt" ]; then
			{
				echo "## Function/Method Calls"
				echo ""
				echo "| Function | Count | Documentation |"
				echo "|----------|-------|---------------|"
			} >>"$DOCS_FILE"

			{ grep -v '^#' "$RESULTS_DIR/grep_function_calls.txt" || true; } | head -n "$TOP_N" | while read -r count term; do
				[ -z "$term" ] && continue
				[[ $term =~ ^(if|for|while|switch|catch)$ ]] && continue
				url=$(get_doc_url "$term" "$PRIMARY_LANG")
				echo "| \`$term()\` | $count | [docs]($url) |" >>"$DOCS_FILE"
			done
			echo "" >>"$DOCS_FILE"
		fi

		if [ -f "$RESULTS_DIR/grep_imports.txt" ]; then
			{
				echo "## Imports/Includes"
				echo ""
				echo "| Import | Count | Documentation |"
				echo "|--------|-------|---------------|"
			} >>"$DOCS_FILE"

			{ grep -v '^#' "$RESULTS_DIR/grep_imports.txt" || true; } | head -n "$TOP_N" | while read -r count import; do
				[ -z "$import" ] && continue
				module=$(echo "$import" | sed -E 's/.*[<"]([^">]+)[">].*/\1/' | sed 's|.*/||' | sed 's/\..*$//')
				url=$(get_doc_url "$module" "$PRIMARY_LANG")
				import_escaped="${import//|/\\|}"
				echo "| \`$import_escaped\` | $count | [docs]($url) |" >>"$DOCS_FILE"
			done
			echo "" >>"$DOCS_FILE"
		fi
	fi

	{
		echo ""
		echo "---"
		echo "*Generated by analyze_repo.sh + generate_study_materials.sh*"
	} >>"$DOCS_FILE"

	echo -e "${GREEN}Created: $DOCS_FILE${NC}"
}
