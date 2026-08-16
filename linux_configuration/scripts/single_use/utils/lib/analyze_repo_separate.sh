#!/bin/bash
# Language detection, and per-language comment/code separation: fills a map of
# language -> temp file holding that language's comment-stripped source, plus
# one file of all extracted comments.
#
# Sourced by analyze_repo.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and reads
# RESPECT_GITIGNORE, RESULTS_DIR and the colour constants.
#
# detect_languages lives here rather than beside the other file-discovery
# helpers because the HAS_* flags it sets are read only by
# separate_code_and_comments below. Keeping definition and use in one file is
# what lets shellcheck see them as used.

# separate_code_and_comments <code_files_map_name> <comments_file>
# The map is filled by nameref rather than left in a global, so no mutable
# state crosses the file boundary into the reporting pass.
# Populates LANG_FILES and the HAS_* family from the files present in the cwd.
detect_languages() {
	print_subheader "Detecting languages in repository..."

	if [ "$RESPECT_GITIGNORE" = true ]; then
		if is_git_repo; then
			echo -e "${YELLOW}Note: Respecting .gitignore (excludes node_modules, build outputs, etc.)${NC}"
		else
			echo -e "${YELLOW}Note: Excluding common directories (node_modules, .git, vendor, etc.)${NC}"
		fi
		echo "      Use --no-ignore to include everything."
		echo ""
	fi

	# Count files by extension to detect primary languages (using helper).
	# LANG_FILES is read only here; the HAS_* flags below are what the callers
	# downstream consume, so they stay global.
	local lang count
	local -A LANG_FILES
	LANG_FILES[c]=$(count_files "*.c")
	LANG_FILES[cpp]=$(count_files "*.cpp" "*.cc" "*.cxx")
	LANG_FILES[h]=$(count_files "*.h" "*.hpp" "*.hxx")
	LANG_FILES[python]=$(count_files "*.py")
	LANG_FILES[javascript]=$(count_files "*.js")
	LANG_FILES[typescript]=$(count_files "*.ts" "*.tsx")
	LANG_FILES[java]=$(count_files "*.java")
	LANG_FILES[go]=$(count_files "*.go")
	LANG_FILES[rust]=$(count_files "*.rs")
	LANG_FILES[ruby]=$(count_files "*.rb")
	LANG_FILES[shell]=$(count_files "*.sh" "*.bash")

	echo "Files found by language:"
	for lang in c cpp h python javascript typescript java go rust ruby shell; do
		count=${LANG_FILES[$lang]}
		[ "$count" -gt 0 ] && echo "  $lang: $count files"
	done

	# Determine which language families are present
	HAS_C_FAMILY=false
	HAS_PYTHON=false
	HAS_JS_FAMILY=false
	HAS_SHELL=false
	HAS_RUBY=false
	HAS_GO=false
	HAS_RUST=false
	HAS_JAVA=false

	((LANG_FILES[c] + LANG_FILES[cpp] + LANG_FILES[h] > 0)) && HAS_C_FAMILY=true
	((LANG_FILES[python] > 0)) && HAS_PYTHON=true
	((LANG_FILES[javascript] + LANG_FILES[typescript] > 0)) && HAS_JS_FAMILY=true
	((LANG_FILES[shell] > 0)) && HAS_SHELL=true
	((LANG_FILES[ruby] > 0)) && HAS_RUBY=true
	((LANG_FILES[go] > 0)) && HAS_GO=true
	((LANG_FILES[rust] > 0)) && HAS_RUST=true
	((LANG_FILES[java] > 0)) && HAS_JAVA=true
}

separate_code_and_comments() {
	local -n LANG_CODE_FILES="$1"
	local COMMENTS_TEMP="$2"

	# Create per-language output directory
	mkdir -p "$RESULTS_DIR/per_language"

	# Process C/C++ files
	if $HAS_C_FAMILY; then
		echo "Processing C/C++ files..."
		LANG_CODE_FILES["c_cpp"]=$(mktemp /tmp/code_c_cpp.XXXXXX.tmp)
		find_files "*.c" "*.cpp" "*.cc" "*.cxx" "*.h" "*.hpp" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[c_cpp]}"

		# Extract and strip C-style comments
		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[c_cpp]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[c_cpp]}" >"${LANG_CODE_FILES[c_cpp]}.clean"
		mv "${LANG_CODE_FILES[c_cpp]}.clean" "${LANG_CODE_FILES[c_cpp]}"
	fi

	# Process JavaScript files (separate from TypeScript)
	if $HAS_JS_FAMILY; then
		echo "Processing JavaScript files..."
		LANG_CODE_FILES["javascript"]=$(mktemp /tmp/code_js.XXXXXX.tmp)
		find_files "*.js" "*.jsx" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[javascript]}"

		echo "Processing TypeScript files..."
		LANG_CODE_FILES["typescript"]=$(mktemp /tmp/code_ts.XXXXXX.tmp)
		find_files "*.ts" "*.tsx" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[typescript]}"

		# Extract and strip comments from both
		for lang_file in "${LANG_CODE_FILES[javascript]}" "${LANG_CODE_FILES[typescript]}"; do
			[ ! -s "$lang_file" ] && continue
			perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "$lang_file" >>"$COMMENTS_TEMP"
			perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "$lang_file" >"${lang_file}.clean"
			mv "${lang_file}.clean" "$lang_file"
		done
	fi

	# Process Python files
	if $HAS_PYTHON; then
		echo "Processing Python files..."
		LANG_CODE_FILES["python"]=$(mktemp /tmp/code_python.XXXXXX.tmp)
		find_files "*.py" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[python]}"

		perl -ne 'if (/^\s*#(.*)/) { print "$1\n"; } elsif (/#(.*)$/) { print "$1\n"; }' "${LANG_CODE_FILES[python]}" >>"$COMMENTS_TEMP"
		perl -0777 -ne 'while (/"""(.+?)"""/gs) { print "$1\n"; } while (/'"'"''"'"''"'"'(.+?)'"'"''"'"''"'"'/gs) { print "$1\n"; }' "${LANG_CODE_FILES[python]}" >>"$COMMENTS_TEMP"
		perl -pe 's/#.*$//' "${LANG_CODE_FILES[python]}" | perl -0777 -pe 's/""".*?"""//gs; s/'"'"''"'"''"'"'.*?'"'"''"'"''"'"'//gs' >"${LANG_CODE_FILES[python]}.clean"
		mv "${LANG_CODE_FILES[python]}.clean" "${LANG_CODE_FILES[python]}"
	fi

	# Process Go files
	if $HAS_GO; then
		echo "Processing Go files..."
		LANG_CODE_FILES["go"]=$(mktemp /tmp/code_go.XXXXXX.tmp)
		find_files "*.go" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[go]}"

		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[go]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[go]}" >"${LANG_CODE_FILES[go]}.clean"
		mv "${LANG_CODE_FILES[go]}.clean" "${LANG_CODE_FILES[go]}"
	fi

	# Process Rust files
	if $HAS_RUST; then
		echo "Processing Rust files..."
		LANG_CODE_FILES["rust"]=$(mktemp /tmp/code_rust.XXXXXX.tmp)
		find_files "*.rs" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[rust]}"

		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[rust]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[rust]}" >"${LANG_CODE_FILES[rust]}.clean"
		mv "${LANG_CODE_FILES[rust]}.clean" "${LANG_CODE_FILES[rust]}"
	fi

	# Process Ruby files
	if $HAS_RUBY; then
		echo "Processing Ruby files..."
		LANG_CODE_FILES["ruby"]=$(mktemp /tmp/code_ruby.XXXXXX.tmp)
		find_files "*.rb" | head -5000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[ruby]}"

		perl -ne 'if (/#(.*)$/) { print "$1\n"; }' "${LANG_CODE_FILES[ruby]}" >>"$COMMENTS_TEMP"
		perl -0777 -ne 'while (/=begin(.+?)=end/gs) { print "$1\n"; }' "${LANG_CODE_FILES[ruby]}" >>"$COMMENTS_TEMP"
		perl -pe 's/#.*$//' "${LANG_CODE_FILES[ruby]}" | perl -0777 -pe 's/=begin.*?=end//gs' >"${LANG_CODE_FILES[ruby]}.clean"
		mv "${LANG_CODE_FILES[ruby]}.clean" "${LANG_CODE_FILES[ruby]}"
	fi

	# Process Shell files
	if $HAS_SHELL; then
		echo "Processing Shell files..."
		LANG_CODE_FILES["shell"]=$(mktemp /tmp/code_shell.XXXXXX.tmp)
		find_files "*.sh" "*.bash" | head -5000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[shell]}"

		perl -ne 'if (/^\s*#(.*)/ && !/^#!/) { print "$1\n"; } elsif (/#(.*)$/) { print "$1\n"; }' "${LANG_CODE_FILES[shell]}" >>"$COMMENTS_TEMP"
		perl -pe 's/#.*$//' "${LANG_CODE_FILES[shell]}" >"${LANG_CODE_FILES[shell]}.clean"
		mv "${LANG_CODE_FILES[shell]}.clean" "${LANG_CODE_FILES[shell]}"
	fi

	# Process Java files
	if $HAS_JAVA; then
		echo "Processing Java files..."
		LANG_CODE_FILES["java"]=$(mktemp /tmp/code_java.XXXXXX.tmp)
		find_files "*.java" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[java]}"

		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[java]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[java]}" >"${LANG_CODE_FILES[java]}.clean"
		mv "${LANG_CODE_FILES[java]}.clean" "${LANG_CODE_FILES[java]}"
	fi

	local COMMENT_LINES
	COMMENT_LINES=$(wc -l <"$COMMENTS_TEMP")
	echo ""
	echo "Processed languages: ${!LANG_CODE_FILES[*]}"
	echo "Total comment lines: $COMMENT_LINES"
}
