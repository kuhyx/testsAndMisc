#!/usr/bin/env bash
# lib/study_gen_llm.sh — write llm_anki_prompt.md.
#
# Its nested get_llm_doc_link and generate_*_with_docs helpers stay nested:
# they were defined inside this phase in the pre-split script too, and they
# close over PRIMARY_LANG and TOP_N from it.

# Write the LLM prompt file: the instructions, and the per-topic doc paths
# an assistant is meant to read before writing any flashcard.
generate_llm_prompt() {
	#==============================================================================
	# Generate LLM Prompt for Anki Card Generation
	#==============================================================================
	echo -e "${YELLOW}Generating LLM prompt...${NC}"

	# Helper function to get doc link for a term
	get_llm_doc_link() {
		local term="$1"
		local lang="$2"
		# "true" if the term is a whole import line rather than a bare name.
		# Defaulted for the same reason as the lookup helpers: every current
		# caller passes it, but a bare "$3" would abort under `set -u`.
		local is_import="${3:-false}"

		# Check if it's an internal/project-specific item
		if [[ $term =~ ^@/ ]] || [[ $term =~ ^\./ ]] || [[ $term =~ ^app\. ]] || [[ $term =~ ^src/ ]] || [[ $term =~ from\ \'@/ ]] || [[ $term =~ from\ \'\./ ]]; then
			echo "[INTERNAL - SKIP]"
			return
		fi

		# Try offline lookup
		local offline_result
		if [ "$is_import" = "true" ]; then
			offline_result=$("$LOOKUP_SCRIPT" --import "$term" "$lang" 2>/dev/null | grep "^/" | head -1)
		else
			offline_result=$("$LOOKUP_SCRIPT" "$term" "$lang" 2>/dev/null | grep "^File:" | head -1 | sed 's/^File: //')
		fi

		if [ -n "$offline_result" ]; then
			echo "$offline_result"
		else
			echo "[NO OFFLINE DOC]"
		fi
	}

	# Generate keywords with doc links
	generate_keywords_with_docs() {
		local keywords_file="$RESULTS_DIR/grep_keywords.txt"
		[ ! -f "$keywords_file" ] && echo "No keywords found" && return

		{ grep -v '^#' "$keywords_file" || true; } | head -n "$TOP_N" | while read -r line; do
			local count
			count=$(echo "$line" | awk '{print $1}')
			local keyword
			keyword=$(echo "$line" | awk '{print $2}')
			[ -z "$keyword" ] && continue
			local doc_link
			doc_link=$(get_llm_doc_link "$keyword" "$PRIMARY_LANG" "false")
			echo "$count $keyword → $doc_link"
		done
	}

	# Generate functions with doc links
	generate_functions_with_docs() {
		local functions_file="$RESULTS_DIR/grep_function_calls.txt"
		[ ! -f "$functions_file" ] && echo "No functions found" && return

		{ grep -v '^#' "$functions_file" || true; } | head -n "$TOP_N" | while read -r line; do
			local count
			count=$(echo "$line" | awk '{print $1}')
			local func
			func=$(echo "$line" | awk '{print $2}')

			# Skip single-letter functions (minified code) or empty
			if [ -z "$func" ] || [ ${#func} -le 1 ]; then
				continue
			fi

			local doc_link
			doc_link=$(get_llm_doc_link "$func" "$PRIMARY_LANG" "false")
			echo "$count $func() → $doc_link"
		done
	}

	# Generate imports with doc links
	generate_imports_with_docs() {
		local imports_file="$RESULTS_DIR/grep_imports.txt"
		[ ! -f "$imports_file" ] && echo "No imports found" && return

		{ grep -v '^#' "$imports_file" || true; } | head -n "$TOP_N" | while read -r line; do
			local count
			count=$(echo "$line" | awk '{print $1}')
			local import_stmt
			import_stmt=$(echo "$line" | cut -d' ' -f2-)
			[ -z "$import_stmt" ] && continue

			# Check if internal import
			if [[ $import_stmt =~ @/ ]] || [[ $import_stmt =~ \./ ]] || [[ $import_stmt =~ from\ app\. ]] || [[ $import_stmt =~ from\ src\. ]]; then
				echo "$count $import_stmt → [INTERNAL - SKIP]"
			else
				local doc_link
				doc_link=$(get_llm_doc_link "$import_stmt" "$PRIMARY_LANG" "true")
				echo "$count $import_stmt → $doc_link"
			fi
		done
	}

	cat >"$LLM_PROMPT_FILE" <<'PROMPT_HEADER'
# LLM Prompt: Generate Anki Flashcards

You are creating Anki flashcards from code analysis.

## CRITICAL INSTRUCTIONS

1. **READ DOCS VIA TERMINAL** - Use the `cat` command to read each .md file:
   ```
   cat /home/kuhy/.local/share/offline-docs/mdn-content/files/en-us/web/javascript/reference/statements/const/index.md
   ```
2. **DO NOT USE YOUR OWN KNOWLEDGE** - Base flashcards ONLY on the content you read from the files
3. **IF YOU CANNOT READ A FILE** - Report: "ERROR: Cannot read [path]" and skip that item
4. **NEVER FALL BACK TO GENERAL KNOWLEDGE** - If you can't read the file, skip it entirely
5. **READ ONE FILE AT A TIME** - Run cat for each topic before creating its flashcards

PROMPT_HEADER

	cat >>"$LLM_PROMPT_FILE" <<EOF
## Context
- Primary Language: **$PRIMARY_LANG**

## Top Keywords (by frequency)
Items marked \`[INTERNAL - SKIP]\` are project-specific - skip them.
Items marked \`[NO OFFLINE DOC]\` have no offline documentation - use online docs or skip.
Other items have offline doc paths you can reference.

\`\`\`
$(generate_keywords_with_docs)
\`\`\`

## Top Functions/Methods (by frequency)
\`\`\`
$(generate_functions_with_docs)
\`\`\`

## Top Imports/Includes
\`\`\`
$(generate_imports_with_docs)
\`\`\`
EOF

	cat >>"$LLM_PROMPT_FILE" <<'PROMPT_FOOTER'

## Guidelines

**CRITICAL - Keep answers EXTREMELY short:**
- Most answers should be **1-2 words** or **1 sentence**
- It's common and expected for an answer to be just: "Returns an array" or "Immutable"
- 2 sentences = longer answer, 3 sentences = absolute maximum (rare)
- Each flashcard tests ONE atomic piece of knowledge

**NO DUPLICATES:**
- Before creating a card, check if you already created a similar question
- Each unique fact should appear in EXACTLY ONE card
- Do NOT create multiple cards asking the same thing with slightly different wording

**What to include:**
- Concept cards: "What is X?" / "What does X do?"
- Syntax cards: "How do you write X?" (brief code snippet)
- Comparison cards: "X vs Y - what's the difference?"

**What to SKIP (do NOT create cards for):**
- MDN frontmatter fields: title, slug, page-type, browser-compat, spec-urls
- YAML metadata between `---` markers at the start of files
- Any line that looks like metadata (key: value at start of doc)
- Empty answers - if you can't find content for the back, skip the card entirely

**FINAL CARD FOR EACH TOPIC (EXCEPTION TO SHORT ANSWER RULE):**
- Add EXACTLY ONE full documentation card per topic (no duplicates!)
- Question: `[Topic] - Full MDN Documentation`
- Answer: Copy the .md file content STARTING AFTER the `---` frontmatter block
- Skip the YAML frontmatter (everything between the first two `---` lines)
- Do NOT create this card twice for the same topic

**Skipped items - please review:**
- Items marked `[INTERNAL - SKIP]` are project-specific utilities - I skipped them
- Items marked `[NO OFFLINE DOC]` are third-party libraries without bundled docs
- If you want flashcards for skipped items, tell me which ones to include

## OUTPUT: CREATE AN ANKI FILE

**CREATE A FILE DIRECTLY** - Do not just output text. Use your file creation tool to create:

**File path:** `~/.local/share/study-materials/anki_generated.txt`

**Format:** Tab-separated values (TSV) with Anki metadata headers:

```
#separator:tab
#deck:CodeStudy::JavaScript
#notetype:CodeCard
#columns:Front	Back	Tags
What does <code>const</code> declare?Block-scoped variables with immutable bindings.javascript declarations
```

**Required headers at top of file:**
- `#separator:tab` - Specifies tab as delimiter
- `#deck:CodeStudy::[Language]` - Creates deck "CodeStudy" with sub-deck for language (e.g., CodeStudy::JavaScript)
- `#notetype:CodeCard` - Uses custom note type "CodeCard" (Anki will create if doesn't exist)
- `#columns:Front	Back	Tags` - Column headers (tab-separated)

**Rules:**
- Use ACTUAL `<code>` tags (not escaped &lt;code&gt;)
- Use `<br>` for line breaks within fields
- Use `<pre>` for code blocks
- Tags are space-separated
- Escape any literal tabs within content as spaces

**Example file content:**
```
#separator:tab
#deck:CodeStudy::JavaScript
#notetype:CodeCard
#columns:Front	Back	Tags
What does <code>const</code> declare?Block-scoped variables with immutable bindings.javascript declarations
Can <code>const</code> be reassigned?No, throws TypeError.javascript declarations
const - Full Documentation<pre>[ENTIRE CONTENT OF const/index.md FILE]</pre>javascript declarations full-doc
```

**After creating the file**, tell the user:
- File created at: ~/.local/share/study-materials/anki_generated.txt
- Import in Anki: File → Import → select the file
- Deck: CodeStudy::[Language], Note type: CodeCard
---

**Important:**
- Process only 5-10 items at a time to maintain quality
- Focus on items with offline documentation paths
- Output ONLY the TSV lines, no extra formatting or markdown
PROMPT_FOOTER

	echo -e "${GREEN}Created: $LLM_PROMPT_FILE${NC}"

}
