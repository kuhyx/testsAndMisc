#!/usr/bin/env bash
# lib/study_gen_anki.sh — write anki_cards.txt, the tab-separated import file:
# one card per top keyword and one per top function call.

# Write the tab-separated Anki import file: one card per top keyword and
# one per top function call.
generate_anki_cards() {
	#==============================================================================
	# Generate Anki Cards (Tab-separated for import)
	#==============================================================================
	echo -e "${YELLOW}Generating Anki cards...${NC}"

	cat >"$ANKI_FILE" <<'EOF'
# Anki Import File
# Format: Front<TAB>Back<TAB>Tags
# Import with: File -> Import, select "Fields separated by: Tab"
#
# Card Types:
# 1. "What does X do?" - For functions/methods
# 2. "When to use X?" - For keywords/patterns
# 3. "What is the syntax for X?" - For language constructs
#
EOF

	# Generate cards for top keywords
	if [ -f "$RESULTS_DIR/grep_keywords.txt" ]; then
		echo "# Keywords" >>"$ANKI_FILE"
		{ grep -v '^#' "$RESULTS_DIR/grep_keywords.txt" || true; } | head -n "$TOP_N" | while read -r count term; do
			[ -z "$term" ] && continue
			url=$(get_doc_url "$term" "$PRIMARY_LANG")

			# Create different card types based on term type
			case "$term" in
			if | else | elif | elseif | switch | case | match)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tConditional control flow - executes code based on boolean conditions. See: $url\t${PRIMARY_LANG}::keywords::control-flow" >>"$ANKI_FILE"
				;;
			for | while | loop | do | until)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tLoop construct - repeats code execution. See: $url\t${PRIMARY_LANG}::keywords::loops" >>"$ANKI_FILE"
				;;
			try | except | catch | finally | raise | throw)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tException handling - manages errors and exceptional conditions. See: $url\t${PRIMARY_LANG}::keywords::exceptions" >>"$ANKI_FILE"
				;;
			class | struct | interface | trait | impl)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tType definition - defines custom data structures. See: $url\t${PRIMARY_LANG}::keywords::types" >>"$ANKI_FILE"
				;;
			def | fn | func | function)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tFunction definition - declares a reusable block of code. See: $url\t${PRIMARY_LANG}::keywords::functions" >>"$ANKI_FILE"
				;;
			import | from | use | require | include)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tModule import - brings external code into current scope. See: $url\t${PRIMARY_LANG}::keywords::modules" >>"$ANKI_FILE"
				;;
			async | await | yield)
				echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tAsynchronous programming - handles concurrent operations. See: $url\t${PRIMARY_LANG}::keywords::async" >>"$ANKI_FILE"
				;;
			*)
				echo -e "What does the keyword \`$term\` do in $PRIMARY_LANG?\t[FILL: Look up at $url]\t${PRIMARY_LANG}::keywords" >>"$ANKI_FILE"
				;;
			esac
		done
	fi

	# Generate cards for top functions
	if [ -f "$RESULTS_DIR/grep_function_calls.txt" ]; then
		{
			echo ""
			echo "# Functions"
		} >>"$ANKI_FILE"
		{ grep -v '^#' "$RESULTS_DIR/grep_function_calls.txt" || true; } | head -n "$TOP_N" | while read -r count term; do
			[ -z "$term" ] && continue
			[[ $term =~ ^(if|for|while|switch|catch)$ ]] && continue
			url=$(get_doc_url "$term" "$PRIMARY_LANG")

			echo -e "What does \`$term()\` do in $PRIMARY_LANG? (Used $count times)\t[FILL: Look up at $url]\t${PRIMARY_LANG}::functions" >>"$ANKI_FILE"
		done
	fi

	echo -e "${GREEN}Created: $ANKI_FILE${NC}"

}
