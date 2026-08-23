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

	# `|| true` on each: these were top-level statements before the split, where
	# a false `((...)) &&` merely left $? non-zero. As the tail of a function
	# they become its return value, and under `set -e` the last one (java, false
	# for most repos) aborted the whole script.
	((LANG_FILES[c] + LANG_FILES[cpp] + LANG_FILES[h] > 0)) && HAS_C_FAMILY=true || true
	((LANG_FILES[python] > 0)) && HAS_PYTHON=true || true
	((LANG_FILES[javascript] + LANG_FILES[typescript] > 0)) && HAS_JS_FAMILY=true || true
	((LANG_FILES[shell] > 0)) && HAS_SHELL=true || true
	((LANG_FILES[ruby] > 0)) && HAS_RUBY=true || true
	((LANG_FILES[go] > 0)) && HAS_GO=true || true
	((LANG_FILES[rust] > 0)) && HAS_RUST=true || true
	((LANG_FILES[java] > 0)) && HAS_JAVA=true || true
}

# separate_code_and_comments <code_files_map_name> <comments_file>
# The map is filled by nameref rather than left in a global, so no mutable
# state crosses the file boundary into the reporting pass. The local is named
# _code_files, deliberately NOT the caller's name: a nameref whose local name
# equals the variable it points at makes bash warn "circular name reference" on
# every access, which would land in this script's user-facing output.
separate_code_and_comments() {
	local -n _code_files="$1"
	local COMMENTS_TEMP="$2"

	# Create per-language output directory
	mkdir -p "$RESULTS_DIR/per_language"

	# Process C/C++ files
	if $HAS_C_FAMILY; then
		echo "Processing C/C++ files..."
		_code_files["c_cpp"]=$(mktemp /tmp/code_c_cpp.XXXXXX.tmp)
		find_files "*.c" "*.cpp" "*.cc" "*.cxx" "*.h" "*.hpp" | head -15000 | xargs cat 2>/dev/null >"${_code_files[c_cpp]}"

		# Extract and strip C-style comments
		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${_code_files[c_cpp]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${_code_files[c_cpp]}" >"${_code_files[c_cpp]}.clean"
		mv "${_code_files[c_cpp]}.clean" "${_code_files[c_cpp]}"
	fi

	# Process JavaScript files (separate from TypeScript)
	if $HAS_JS_FAMILY; then
		echo "Processing JavaScript files..."
		_code_files["javascript"]=$(mktemp /tmp/code_js.XXXXXX.tmp)
		find_files "*.js" "*.jsx" | head -15000 | xargs cat 2>/dev/null >"${_code_files[javascript]}"

		echo "Processing TypeScript files..."
		_code_files["typescript"]=$(mktemp /tmp/code_ts.XXXXXX.tmp)
		find_files "*.ts" "*.tsx" | head -15000 | xargs cat 2>/dev/null >"${_code_files[typescript]}"

		# Extract and strip comments from both
		for lang_file in "${_code_files[javascript]}" "${_code_files[typescript]}"; do
			[ ! -s "$lang_file" ] && continue
			perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "$lang_file" >>"$COMMENTS_TEMP"
			perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "$lang_file" >"${lang_file}.clean"
			mv "${lang_file}.clean" "$lang_file"
		done
	fi

	# Process Python files
	if $HAS_PYTHON; then
		echo "Processing Python files..."
		_code_files["python"]=$(mktemp /tmp/code_python.XXXXXX.tmp)
		find_files "*.py" | head -15000 | xargs cat 2>/dev/null >"${_code_files[python]}"

		perl -ne 'if (/^\s*#(.*)/) { print "$1\n"; } elsif (/#(.*)$/) { print "$1\n"; }' "${_code_files[python]}" >>"$COMMENTS_TEMP"
		perl -0777 -ne 'while (/"""(.+?)"""/gs) { print "$1\n"; } while (/'"'"''"'"''"'"'(.+?)'"'"''"'"''"'"'/gs) { print "$1\n"; }' "${_code_files[python]}" >>"$COMMENTS_TEMP"
		perl -pe 's/#.*$//' "${_code_files[python]}" | perl -0777 -pe 's/""".*?"""//gs; s/'"'"''"'"''"'"'.*?'"'"''"'"''"'"'//gs' >"${_code_files[python]}.clean"
		mv "${_code_files[python]}.clean" "${_code_files[python]}"
	fi

	# Process Go files
	if $HAS_GO; then
		echo "Processing Go files..."
		_code_files["go"]=$(mktemp /tmp/code_go.XXXXXX.tmp)
		find_files "*.go" | head -15000 | xargs cat 2>/dev/null >"${_code_files[go]}"

		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${_code_files[go]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${_code_files[go]}" >"${_code_files[go]}.clean"
		mv "${_code_files[go]}.clean" "${_code_files[go]}"
	fi

	# Process Rust files
	if $HAS_RUST; then
		echo "Processing Rust files..."
		_code_files["rust"]=$(mktemp /tmp/code_rust.XXXXXX.tmp)
		find_files "*.rs" | head -15000 | xargs cat 2>/dev/null >"${_code_files[rust]}"

		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${_code_files[rust]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${_code_files[rust]}" >"${_code_files[rust]}.clean"
		mv "${_code_files[rust]}.clean" "${_code_files[rust]}"
	fi

	# Process Ruby files
	if $HAS_RUBY; then
		echo "Processing Ruby files..."
		_code_files["ruby"]=$(mktemp /tmp/code_ruby.XXXXXX.tmp)
		find_files "*.rb" | head -5000 | xargs cat 2>/dev/null >"${_code_files[ruby]}"

		perl -ne 'if (/#(.*)$/) { print "$1\n"; }' "${_code_files[ruby]}" >>"$COMMENTS_TEMP"
		perl -0777 -ne 'while (/=begin(.+?)=end/gs) { print "$1\n"; }' "${_code_files[ruby]}" >>"$COMMENTS_TEMP"
		perl -pe 's/#.*$//' "${_code_files[ruby]}" | perl -0777 -pe 's/=begin.*?=end//gs' >"${_code_files[ruby]}.clean"
		mv "${_code_files[ruby]}.clean" "${_code_files[ruby]}"
	fi

	# Process Shell files
	if $HAS_SHELL; then
		echo "Processing Shell files..."
		_code_files["shell"]=$(mktemp /tmp/code_shell.XXXXXX.tmp)
		find_files "*.sh" "*.bash" | head -5000 | xargs cat 2>/dev/null >"${_code_files[shell]}"

		perl -ne 'if (/^\s*#(.*)/ && !/^#!/) { print "$1\n"; } elsif (/#(.*)$/) { print "$1\n"; }' "${_code_files[shell]}" >>"$COMMENTS_TEMP"
		perl -pe 's/#.*$//' "${_code_files[shell]}" >"${_code_files[shell]}.clean"
		mv "${_code_files[shell]}.clean" "${_code_files[shell]}"
	fi

	# Process Java files
	if $HAS_JAVA; then
		echo "Processing Java files..."
		_code_files["java"]=$(mktemp /tmp/code_java.XXXXXX.tmp)
		find_files "*.java" | head -15000 | xargs cat 2>/dev/null >"${_code_files[java]}"

		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${_code_files[java]}" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${_code_files[java]}" >"${_code_files[java]}.clean"
		mv "${_code_files[java]}.clean" "${_code_files[java]}"
	fi

	local COMMENT_LINES
	COMMENT_LINES=$(wc -l <"$COMMENTS_TEMP")
	echo ""
	echo "Processed languages: ${!_code_files[*]}"
	echo "Total comment lines: $COMMENT_LINES"
}
