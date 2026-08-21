#!/usr/bin/env bash
# Tests for the three generation phases: lib/study_gen_docs.sh,
# lib/study_gen_anki.sh and lib/study_gen_llm.sh.
#
# Each phase reads the grep_*.txt files the analysis step wrote and produces
# one output file. The cases below pin what actually matters about each output
# rather than its exact bytes: that every extracted term appears, that the Anki
# file keeps the tab-separated shape its importer requires, and that the LLM
# prompt keeps the instructions that stop an assistant answering from memory
# instead of from the docs it was told to read.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=study_harness.sh
. "${SCRIPT_DIR}/study_harness.sh"
# shellcheck source=../study_doc_urls.sh
. "${SCRIPT_DIR}/../study_doc_urls.sh"
# shellcheck source=../study_doc_urls_more.sh
. "${SCRIPT_DIR}/../study_doc_urls_more.sh"
# shellcheck source=../study_doc_lookup.sh
. "${SCRIPT_DIR}/../study_doc_lookup.sh"
# shellcheck source=../study_gen_docs.sh
. "${SCRIPT_DIR}/../study_gen_docs.sh"
# shellcheck source=../study_gen_anki.sh
. "${SCRIPT_DIR}/../study_gen_anki.sh"
# shellcheck source=../study_gen_llm.sh
. "${SCRIPT_DIR}/../study_gen_llm.sh"

echo "== generate_doc_links: writes a section per term kind =="
reset_state
stage_results
generate_doc_links >/dev/null
docs="$(cat "${DOCS_FILE}")"
_t_has "$docs" "def" "a keyword appears in the doc index"
_t_has "$docs" "print" "a function call appears"
_t_has "$docs" "os" "an import appears"
_t_has "$docs" "docs.python.org" "terms carry a resolved documentation link"

echo "== generate_doc_links: honours TOP_N =="
reset_state
printf '%s\n' "9 alpha" "8 bravo" "7 charlie" "6 delta" >"${RESULTS_DIR}/grep_keywords.txt"
: >"${RESULTS_DIR}/grep_function_calls.txt"
: >"${RESULTS_DIR}/grep_imports.txt"
TOP_N=2
generate_doc_links >/dev/null
docs="$(cat "${DOCS_FILE}")"
_t_has "$docs" "alpha" "the top term is included"
if [[ "$docs" == *"charlie"* ]]; then
	_t_fail "a term past TOP_N is excluded"
else
	_t_pass "a term past TOP_N is excluded"
fi

echo "== generate_doc_links: missing input files are not fatal =="
reset_state
# A repo with no imports at all is normal, and the analysis simply does not
# write that file. The phase must still produce its other sections.
printf '%s\n' "9 def" >"${RESULTS_DIR}/grep_keywords.txt"
generate_doc_links >/dev/null
_t_has "$(cat "${DOCS_FILE}")" "def" "the surviving section is still written"

echo "== generate_doc_links: uses the offline mirror when installed =="
reset_state
stage_results
enable_offline_docs "${OFFLINE_DOCS_DIR}/python/os.md"
generate_doc_links >/dev/null
_t_has "$(cat "${DOCS_FILE}")" "${OFFLINE_DOCS_DIR}" "cards cite a local path an assistant can read"

echo "== generate_doc_links: per-language mode =="
reset_state
stage_results
# The presence of per_language/ switches the phase onto an entirely separate
# path that resolves each language's terms against that language's docs.
stage_per_language python javascript rust
generate_doc_links >/dev/null
docs="$(cat "${DOCS_FILE}")"
_t_has "$docs" "Language Keywords" "the per-language section header is written"
_t_has "$docs" "Python" "a language gets a display name"
_t_has "$docs" "JavaScript" "the JavaScript display name is mapped"
_t_has "$docs" "Rust" "a third language is included"
_t_has "$docs" "alpha_python" "a per-language keyword is listed"
_t_has "$docs" "fn_javascript" "a per-language function is listed"
_t_has "$docs" "mod_rust" "a per-language import is listed"

echo "== generate_doc_links: per-language name mapping =="
reset_state
stage_results
stage_per_language c_cpp typescript shell
generate_doc_links >/dev/null
docs="$(cat "${DOCS_FILE}")"
_t_has "$docs" "C/C++" "c_cpp maps to the C/C++ display name"
_t_has "$docs" "TypeScript" "typescript maps to its display name"
_t_has "$docs" "Shell/Bash" "shell maps to the Shell/Bash display name"

echo "== generate_doc_links: per-language covers the remaining names =="
reset_state
stage_results
stage_per_language go ruby java klingon
generate_doc_links >/dev/null
docs="$(cat "${DOCS_FILE}")"
_t_has "$docs" "Go" "go maps to its display name"
_t_has "$docs" "Ruby" "ruby maps to its display name"
_t_has "$docs" "Java" "java maps to its display name"
_t_has "$docs" "klingon" "an unmapped language falls back to its raw name"

echo "== generate_doc_links: per-language skips empty and comment lines =="
reset_state
stage_results
stage_per_language python
# An empty file and a comment-only line are both normal analysis output; each
# must be skipped rather than producing a card with no term.
: >"${RESULTS_DIR}/per_language/functions_python.txt"
printf '%s\n' "# a comment" "5 realterm" >"${RESULTS_DIR}/per_language/imports_python.txt"
generate_doc_links >/dev/null
docs="$(cat "${DOCS_FILE}")"
_t_has "$docs" "realterm" "the real term survives"
if [[ "$docs" == *"a comment"* ]]; then
	_t_fail "a comment line is skipped"
else
	_t_pass "a comment line is skipped"
fi

echo "== generate_anki_cards: tab-separated with a header =="
reset_state
stage_results
generate_anki_cards >/dev/null
anki="$(cat "${ANKI_FILE}")"
_t_has "$anki" "Anki Import File" "the importer header is present"
_t_has "$anki" "Fields separated by: Tab" "the header states the separator"
_t_has "$anki" "def" "a keyword card is written"
_t_has "$anki" "print" "a function card is written"
# Every non-comment line must carry at least one tab, or the import silently
# collapses the card into a single field.
bad=0
while IFS= read -r line; do
	[[ -z "$line" || "$line" == \#* ]] && continue
	[[ "$line" == *$'\t'* ]] || bad=$((bad + 1))
done <"${ANKI_FILE}"
_t_eq "0" "$bad" "every card line is tab-separated"

echo "== generate_anki_cards: honours TOP_N =="
reset_state
printf '%s\n' "9 alpha" "8 bravo" "7 charlie" >"${RESULTS_DIR}/grep_keywords.txt"
: >"${RESULTS_DIR}/grep_function_calls.txt"
TOP_N=1
generate_anki_cards >/dev/null
anki="$(cat "${ANKI_FILE}")"
_t_has "$anki" "alpha" "the top term becomes a card"
if [[ "$anki" == *"bravo"* ]]; then
	_t_fail "a term past TOP_N is excluded"
else
	_t_pass "a term past TOP_N is excluded"
fi

echo "== generate_anki_cards: no input files still writes a valid file =="
reset_state
generate_anki_cards >/dev/null
_t_has "$(cat "${ANKI_FILE}")" "Anki Import File" "an empty analysis still produces an importable file"

echo "== generate_anki_cards: one card template per keyword category =="
reset_state
# Each category gets its own answer text, so a card for `if` explains control
# flow rather than repeating a generic definition. Covering every arm is what
# proves no category silently falls through to the default template.
printf '%s\n' "9 if" "8 for" "7 try" "6 class" "5 async" "4 frobnicate" \
	>"${RESULTS_DIR}/grep_keywords.txt"
: >"${RESULTS_DIR}/grep_function_calls.txt"
TOP_N=6
generate_anki_cards >/dev/null
anki="$(cat "${ANKI_FILE}")"
_t_has "$anki" "Conditional control flow" "a conditional keyword gets the control-flow answer"
_t_has "$anki" "Loop construct" "a loop keyword gets the loop answer"
_t_has "$anki" "Exception handling" "an exception keyword gets the exception answer"
_t_has "$anki" "Type definition" "a type keyword gets the type answer"
_t_has "$anki" "Asynchronous programming" "an async keyword gets the async answer"
_t_has "$anki" "frobnicate" "an uncategorised keyword still gets a card"

echo "== generate_llm_prompt: project-internal items are skipped =="
reset_state
# A relative or aliased import points at the repo being studied, not at any
# documentation, so a flashcard for it could only be answered from guesswork.
# These must be marked skippable rather than sent to the assistant as a topic.
printf '%s\n' "9 ./local_module" "8 @/aliased" "7 src/thing" "6 app.config" "5 os" \
	>"${RESULTS_DIR}/grep_imports.txt"
printf '%s\n' "9 def" >"${RESULTS_DIR}/grep_keywords.txt"
printf '%s\n' "8 print" >"${RESULTS_DIR}/grep_function_calls.txt"
TOP_N=5
generate_llm_prompt >/dev/null
_t_has "$(cat "${LLM_PROMPT_FILE}")" "INTERNAL - SKIP" "an internal import is marked skippable"

echo "== generate_llm_prompt: single-letter functions are dropped =="
reset_state
# Minified JS turns every function into one or two characters. A flashcard for
# `a` teaches nothing and cannot be looked up, so those are dropped rather than
# sent to the assistant as topics.
printf '%s\n' "9 def" >"${RESULTS_DIR}/grep_keywords.txt"
printf '%s\n' "9 a" "8 b" "7 realFunction" >"${RESULTS_DIR}/grep_function_calls.txt"
printf '%s\n' "6 os" >"${RESULTS_DIR}/grep_imports.txt"
TOP_N=5
generate_llm_prompt >/dev/null
prompt="$(cat "${LLM_PROMPT_FILE}")"
_t_has "$prompt" "realFunction" "a real function name survives"
if [[ "$prompt" =~ [0-9]+\ a$'\n' ]]; then
	_t_fail "a single-letter function is dropped"
else
	_t_pass "a single-letter function is dropped"
fi

echo "== generate_llm_prompt: keeps the read-the-docs instructions =="
reset_state
stage_results
generate_llm_prompt >/dev/null
prompt="$(cat "${LLM_PROMPT_FILE}")"
# These four instructions are the entire reason the prompt exists: without
# them an assistant writes flashcards from memory, which is exactly the
# failure the offline-docs pipeline was built to prevent.
_t_has "$prompt" "READ DOCS VIA TERMINAL" "the read-the-file instruction survives"
_t_has "$prompt" "DO NOT USE YOUR OWN KNOWLEDGE" "the no-memory instruction survives"
_t_has "$prompt" "IF YOU CANNOT READ A FILE" "the unreadable-file instruction survives"
_t_has "$prompt" "NEVER FALL BACK TO GENERAL KNOWLEDGE" "the no-fallback instruction survives"
_t_has "$prompt" "def" "the extracted keywords are listed"

echo "== generate_llm_prompt: import lines are handled as imports =="
reset_state
stage_results
printf '%s\n' "12 import os" "7 from sys import argv" >"${RESULTS_DIR}/grep_imports.txt"
generate_llm_prompt >/dev/null
_t_has "$(cat "${LLM_PROMPT_FILE}")" "os" "a whole import statement still resolves to its module"

echo "== generate_llm_prompt: offline paths are cited when available =="
reset_state
stage_results
enable_offline_docs "${OFFLINE_DOCS_DIR}/python/os.md"
generate_llm_prompt >/dev/null
_t_has "$(cat "${LLM_PROMPT_FILE}")" "${OFFLINE_DOCS_DIR}" "the prompt cites readable local paths"

echo "== generate_llm_prompt: no inputs still writes the instructions =="
reset_state
generate_llm_prompt >/dev/null
_t_has "$(cat "${LLM_PROMPT_FILE}")" "DO NOT USE YOUR OWN KNOWLEDGE" \
	"an empty analysis still produces a usable prompt"

_t_summary
