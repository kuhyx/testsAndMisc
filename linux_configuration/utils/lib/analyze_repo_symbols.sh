#!/bin/bash
# ctags symbol extraction, the cscope database, and the clang AST sample.
#
# Sourced by analyze_repo.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and reads
# RESULTS_DIR, TOP_N, RESPECT_GITIGNORE, EXCLUDE_DIRS and the colour constants.

analyze_symbols() {
	print_subheader "Generating tags (this may take a while)..."

	# Generate tags for different kinds
	ctags -R --languages=C,C++ --c-kinds=+fp --fields=+lK -f "$RESULTS_DIR/tags" . 2>/dev/null || true

	if [ -f "$RESULTS_DIR/tags" ]; then
		TOTAL_TAGS=$(grep -ac '^[^!]' "$RESULTS_DIR/tags" 2>/dev/null || echo "0")
		echo "Total symbols found: $TOTAL_TAGS"

		print_subheader "Most Common Symbol Names"
		# Fast: use cut + counts instead of awk + sort | uniq
		# -a flag treats tags file as text (may contain binary-like patterns)
		grep -a '^[^!]' "$RESULTS_DIR/tags" | cut -f1 | fast_count "$TOP_N" |
			tee "$RESULTS_DIR/ctags_symbols.txt"

		print_subheader "Symbol Types Distribution"
		# Fast: extract single-letter kind code after ;" and count
		grep -aoP ';"\t\K[a-z]' "$RESULTS_DIR/tags" 2>/dev/null | fast_count 20 | while read -r count kind; do
			case $kind in
			f) echo "$count functions" ;;
			v) echo "$count variables" ;;
			s) echo "$count structs" ;;
			t) echo "$count typedefs" ;;
			e) echo "$count enum values" ;;
			g) echo "$count enums" ;;
			m) echo "$count struct/union members" ;;
			d) echo "$count macro definitions" ;;
			p) echo "$count function prototypes" ;;
			u) echo "$count unions" ;;
			c) echo "$count classes" ;;
			n) echo "$count namespaces" ;;
			*) echo "$count kind=$kind" ;;
			esac
		done | tee "$RESULTS_DIR/ctags_kinds.txt"
	fi

}

analyze_cscope() {
	print_subheader "Building cscope database..."

	# Find all C source files (respecting .gitignore if available)
	if [ "$RESPECT_GITIGNORE" = true ] && is_git_repo; then
		{
			git ls-files -- '*.c' '*.h' 2>/dev/null
			git ls-files --others --exclude-standard -- '*.c' '*.h' 2>/dev/null
		} | sort -u >"$RESULTS_DIR/cscope.files"
	elif [ "$RESPECT_GITIGNORE" = true ]; then
		find . \( -name "*.c" -o -name "*.h" \) -type f 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/" >"$RESULTS_DIR/cscope.files"
	else
		find . \( -name "*.c" -o -name "*.h" \) -type f >"$RESULTS_DIR/cscope.files" 2>/dev/null
	fi
	FILE_COUNT=$(wc -l <"$RESULTS_DIR/cscope.files")
	echo "Found $FILE_COUNT source files"

	# Build cscope database (can take a while for large repos)
	echo "Building database (this may take several minutes for Linux kernel)..."
	cscope -b -q -i "$RESULTS_DIR/cscope.files" -f "$RESULTS_DIR/cscope.out" 2>/dev/null || true

	if [ -f "$RESULTS_DIR/cscope.out" ]; then
		echo "Database built successfully"
		echo "Database size: $(du -sh "$RESULTS_DIR/cscope.out" | cut -f1)"

		print_subheader "Example: Finding callers of 'printk' function"
		cscope -d -f "$RESULTS_DIR/cscope.out" -L -3 printk 2>/dev/null | head -20 || echo "No results"

		print_subheader "Example: Finding definition of 'struct file'"
		cscope -d -f "$RESULTS_DIR/cscope.out" -L -1 "struct file" 2>/dev/null | head -10 || echo "No results"
	fi

}

analyze_clang_ast() {
	print_subheader "Analyzing a sample file with clang AST dump"

	# Find a simple C file to analyze (respecting .gitignore)
	if [ "$RESPECT_GITIGNORE" = true ] && is_git_repo; then
		SAMPLE_FILE=$(git ls-files -- '*.c' 2>/dev/null | head -20 | while read -r f; do
			[ -f "$f" ] && [ "$(stat -c%s "$f" 2>/dev/null || echo 999999)" -lt 51200 ] && echo "$f"
		done | head -1)
	elif [ "$RESPECT_GITIGNORE" = true ]; then
		SAMPLE_FILE=$(find . -name "*.c" -size -50k -type f 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/" | head -1)
	else
		SAMPLE_FILE=$(find . -name "*.c" -size -50k 2>/dev/null | head -1)
	fi

	if [ -n "$SAMPLE_FILE" ]; then
		echo "Sample file: $SAMPLE_FILE"
		echo ""
		echo "Function declarations in this file:"
		clang -Xclang -ast-dump -fsyntax-only "$SAMPLE_FILE" 2>/dev/null |
			grep -E "FunctionDecl.*<.*>" |
			head -20 |
			sed 's/.*FunctionDecl.*<[^>]*> /  /' |
			tee "$RESULTS_DIR/clang_sample_functions.txt" || echo "Analysis failed (missing headers)"
	fi

	print_subheader "Note: Full clang analysis requires compile_commands.json"
	echo "For proper AST analysis of the Linux kernel, you need to:"
	echo "  1. Configure the kernel: make defconfig"
	echo "  2. Generate compile_commands.json: make compile_commands.json"
	echo "  3. Use clang-query or clang-check with the database"

}
