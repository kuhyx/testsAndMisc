#!/bin/bash
# Per-language keyword, function-call and import reporting, plus the combined
# cross-language rollups.
#
# Sourced by analyze_repo.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and reads
# RESULTS_DIR, TOP_N and the colour constants.
#
# The KEYWORDS_* tables live here rather than in their own data file because
# report_languages below is their only consumer; keeping definition and use in
# one file is what lets shellcheck see them as used.
#
# Note: LANG_KEYWORDS also indexes shell and java, for which no table has ever
# been defined. The lookup guards on a non-empty value, so those two languages
# are skipped rather than failing. Pre-existing; preserved by this split.

#------------------------------------------------------------------------------
# C/C++ keywords
KEYWORDS_C="auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|int|long|register|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while|inline|restrict|_Bool|_Complex|_Imaginary"
KEYWORDS_CPP="$KEYWORDS_C|alignas|alignof|and|and_eq|asm|atomic_cancel|atomic_commit|atomic_noexcept|bitand|bitor|bool|catch|char16_t|char32_t|char8_t|class|co_await|co_return|co_yield|compl|concept|const_cast|consteval|constexpr|constinit|decltype|delete|dynamic_cast|explicit|export|false|friend|mutable|namespace|new|noexcept|not|not_eq|nullptr|operator|or|or_eq|override|private|protected|public|reflexpr|reinterpret_cast|requires|static_assert|static_cast|synchronized|template|this|thread_local|throw|true|try|typeid|typename|using|virtual|wchar_t|xor|xor_eq"

# Python keywords
KEYWORDS_PYTHON="False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield"

# JavaScript/TypeScript keywords
KEYWORDS_JS="abstract|arguments|await|boolean|break|byte|case|catch|char|class|const|continue|debugger|default|delete|do|double|else|enum|eval|export|extends|false|final|finally|float|for|function|goto|if|implements|import|in|instanceof|int|interface|let|long|native|new|null|package|private|protected|public|return|short|static|super|switch|synchronized|this|throw|throws|transient|true|try|typeof|undefined|var|void|volatile|while|with|yield"
KEYWORDS_TS="$KEYWORDS_JS|any|as|asserts|bigint|declare|get|infer|intrinsic|is|keyof|module|namespace|never|out|override|readonly|require|set|string|symbol|type|unique|unknown"

# Go keywords
KEYWORDS_GO="break|case|chan|const|continue|default|defer|else|fallthrough|for|func|go|goto|if|import|interface|map|package|range|return|select|struct|switch|type|var"

# Rust keywords
KEYWORDS_RUST="as|async|await|break|const|continue|crate|dyn|else|enum|extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return|self|Self|static|struct|super|trait|true|type|unsafe|use|where|while"

# Ruby keywords
KEYWORDS_RUBY="BEGIN|END|alias|and|begin|break|case|class|def|defined|do|else|elsif|end|ensure|false|for|if|in|module|next|nil|not|or|redo|rescue|retry|return|self|super|then|true|undef|unless|until|when|while|yield"
#------------------------------------------------------------------------------
# Multi-language comment processing - KEEP LANGUAGES SEPARATE

# report_languages <code_files_map_name> <comments_file>
# Takes the map built by separate_code_and_comments explicitly, so no mutable
# state crosses the file boundary between the two passes.
report_languages() {
	local -n _code_files="$1"
	local COMMENTS_TEMP="$2"
	local lang code_file keywords output_file lang_file CODE_TEMP

	print_subheader "Per-Language Keyword Analysis"

	# Map language names to keyword variables
	declare -A LANG_KEYWORDS
	LANG_KEYWORDS[c_cpp]="$KEYWORDS_CPP"
	LANG_KEYWORDS[python]="$KEYWORDS_PYTHON"
	LANG_KEYWORDS[javascript]="$KEYWORDS_JS"
	LANG_KEYWORDS[typescript]="$KEYWORDS_TS"
	LANG_KEYWORDS[go]="$KEYWORDS_GO"
	LANG_KEYWORDS[rust]="$KEYWORDS_RUST"
	LANG_KEYWORDS[ruby]="$KEYWORDS_RUBY"
	LANG_KEYWORDS[shell]="$KEYWORDS_SHELL"
	LANG_KEYWORDS[java]="$KEYWORDS_JAVA"

	# Analyze each language separately
	for lang in "${!_code_files[@]}"; do
		code_file="${_code_files[$lang]}"
		keywords="${LANG_KEYWORDS[$lang]}"
		output_file="$RESULTS_DIR/per_language/keywords_${lang}.txt"

		if [ -f "$code_file" ] && [ -s "$code_file" ] && [ -n "$keywords" ]; then
			echo ""
			echo -e "${YELLOW}=== $lang Keywords ===${NC}"
			ugrep -o "\b($keywords)\b" "$code_file" 2>/dev/null |
				fast_count 50 |
				tee "$output_file"
		fi
	done

	#------------------------------------------------------------------------------
	# Per-Language Function Analysis
	#------------------------------------------------------------------------------
	print_subheader "Per-Language Function Calls"

	for lang in "${!_code_files[@]}"; do
		code_file="${_code_files[$lang]}"
		output_file="$RESULTS_DIR/per_language/functions_${lang}.txt"

		if [ -f "$code_file" ] && [ -s "$code_file" ]; then
			echo ""
			echo -e "${YELLOW}=== $lang Functions ===${NC}"
			ugrep -o '\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(' "$code_file" 2>/dev/null |
				sed 's/\s*(//' |
				grep -vE '^(if|for|while|switch|catch|elif)$' |
				fast_count 30 |
				tee "$output_file"
		fi
	done

	#------------------------------------------------------------------------------
	# Per-Language Import Analysis
	#------------------------------------------------------------------------------
	print_subheader "Per-Language Imports/Includes"

	# C/C++ includes
	if [ -n "${_code_files[c_cpp]}" ] && [ -s "${_code_files[c_cpp]}" ]; then
		echo -e "${YELLOW}=== C/C++ Includes ===${NC}"
		ugrep -o '#include\s*[<"][^>"]+[>"]' "${_code_files[c_cpp]}" 2>/dev/null |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_c_cpp.txt"
	fi

	# Python imports
	if [ -n "${_code_files[python]}" ] && [ -s "${_code_files[python]}" ]; then
		echo ""
		echo -e "${YELLOW}=== Python Imports ===${NC}"
		ugrep -o '^\s*(from\s+\S+\s+import\s+\S+|import\s+\S+)' "${_code_files[python]}" 2>/dev/null |
			sed 's/^\s*//' |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_python.txt"
	fi

	# JavaScript imports
	if [ -n "${_code_files[javascript]}" ] && [ -s "${_code_files[javascript]}" ]; then
		echo ""
		echo -e "${YELLOW}=== JavaScript Imports ===${NC}"
		ugrep -o "(import\s+.*\s+from\s+['\"][^'\"]+['\"]|require\s*\(['\"][^'\"]+['\"]\))" "${_code_files[javascript]}" 2>/dev/null |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_javascript.txt"
	fi

	# TypeScript imports
	if [ -n "${_code_files[typescript]}" ] && [ -s "${_code_files[typescript]}" ]; then
		echo ""
		echo -e "${YELLOW}=== TypeScript Imports ===${NC}"
		ugrep -o "(import\s+.*\s+from\s+['\"][^'\"]+['\"]|require\s*\(['\"][^'\"]+['\"]\))" "${_code_files[typescript]}" 2>/dev/null |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_typescript.txt"
	fi

	# Go imports
	if [ -n "${_code_files[go]}" ] && [ -s "${_code_files[go]}" ]; then
		echo ""
		echo -e "${YELLOW}=== Go Imports ===${NC}"
		ugrep -o '"[^"]+/[^"]+"' "${_code_files[go]}" 2>/dev/null |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_go.txt"
	fi

	# Rust use statements
	if [ -n "${_code_files[rust]}" ] && [ -s "${_code_files[rust]}" ]; then
		echo ""
		echo -e "${YELLOW}=== Rust Use Statements ===${NC}"
		ugrep -o '^\s*use\s+[^;]+' "${_code_files[rust]}" 2>/dev/null |
			sed 's/^\s*//' |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_rust.txt"
	fi

	# Java imports
	if [ -n "${_code_files[java]}" ] && [ -s "${_code_files[java]}" ]; then
		echo ""
		echo -e "${YELLOW}=== Java Imports ===${NC}"
		ugrep -o '^\s*import\s+[^;]+' "${_code_files[java]}" 2>/dev/null |
			sed 's/^\s*//' |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_java.txt"
	fi

	# Ruby requires
	if [ -n "${_code_files[ruby]}" ] && [ -s "${_code_files[ruby]}" ]; then
		echo ""
		echo -e "${YELLOW}=== Ruby Requires ===${NC}"
		ugrep -o "(require\s+['\"][^'\"]+['\"]|require_relative\s+['\"][^'\"]+['\"])" "${_code_files[ruby]}" 2>/dev/null |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_ruby.txt"
	fi

	# Shell sources
	if [ -n "${_code_files[shell]}" ] && [ -s "${_code_files[shell]}" ]; then
		echo ""
		echo -e "${YELLOW}=== Shell Sources ===${NC}"
		ugrep -o '(source\s+[^\s]+|\.\s+[^\s]+)' "${_code_files[shell]}" 2>/dev/null |
			fast_count 30 |
			tee "$RESULTS_DIR/per_language/imports_shell.txt"
	fi

	#------------------------------------------------------------------------------
	# Combined Analysis (for overview/backward compatibility)
	#------------------------------------------------------------------------------
	print_subheader "Combined Code Identifiers (all languages)"

	# Create combined CODE_TEMP
	CODE_TEMP=$(mktemp)
	for lang_file in "${_code_files[@]}"; do
		[ -f "$lang_file" ] && cat "$lang_file" >>"$CODE_TEMP"
	done

	ugrep -o '\b[a-zA-Z_][a-zA-Z0-9_]*\b' "$CODE_TEMP" 2>/dev/null |
		fast_count "$TOP_N" |
		tee "$RESULTS_DIR/code_identifiers.txt"

	print_subheader "Most Used Words in COMMENTS"
	ugrep -o '\b[a-zA-Z_][a-zA-Z0-9_]*\b' "$COMMENTS_TEMP" 2>/dev/null |
		fast_count "$TOP_N" |
		tee "$RESULTS_DIR/comment_words.txt"

	# Create combined files from per-language analysis (for backward compatibility)
	{
		echo "# Combined keywords from all languages"
		echo "# Format: count keyword (from per_language/keywords_*.txt)"
		cat "$RESULTS_DIR/per_language"/keywords_*.txt 2>/dev/null | grep -v '^$' | sort -t' ' -k1 -nr | head -100
	} >"$RESULTS_DIR/grep_keywords.txt"

	{
		echo "# Combined functions from all languages"
		echo "# See per_language/functions_*.txt for language-specific breakdown"
		cat "$RESULTS_DIR/per_language"/functions_*.txt 2>/dev/null | grep -v '^$' | sort -t' ' -k1 -nr | head -100
	} >"$RESULTS_DIR/grep_function_calls.txt"

	{
		echo "# Combined imports from all languages"
		echo "# See per_language/imports_*.txt for language-specific breakdown"
		cat "$RESULTS_DIR/per_language"/imports_*.txt 2>/dev/null | grep -v '^$' | sort -t' ' -k1 -nr | head -100
	} >"$RESULTS_DIR/grep_imports.txt"

	# List what per-language files were created
	echo ""
	echo "Per-language analysis files created:"
	find "$RESULTS_DIR/per_language/" -maxdepth 1 -type f -printf '  %f\n' 2>/dev/null || true
}
