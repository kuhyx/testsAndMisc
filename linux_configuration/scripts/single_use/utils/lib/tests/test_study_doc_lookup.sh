#!/usr/bin/env bash
# Tests for lib/study_doc_lookup.sh — offline lookup, language dispatch and
# language detection.
#
# The interesting behaviour is the preference order: when an offline mirror is
# installed, a term should resolve to a local FILE PATH an assistant can read
# with `cat`, and only fall back to an online URL when the mirror has no answer.
# That distinction is the whole point of the offline path — a card citing a URL
# the assistant cannot fetch is a card it will answer from memory instead.
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

echo "== lookup_offline: disabled =="
reset_state
if lookup_offline "os" python "" >/dev/null 2>&1; then
	_t_fail "with offline docs off, lookup_offline fails"
else
	_t_pass "with offline docs off, lookup_offline fails"
fi

echo "== lookup_offline: a term lookup =="
reset_state
enable_offline_docs "${OFFLINE_DOCS_DIR}/python/os.md"
_t_eq "${OFFLINE_DOCS_DIR}/python/os.md" "$(lookup_offline "os" python "")" \
	"a term resolves to the local file path"

echo "== lookup_offline: an import-aware lookup =="
reset_state
enable_offline_docs "${OFFLINE_DOCS_DIR}/js/array.md"
_t_eq "${OFFLINE_DOCS_DIR}/js/array.md" "$(lookup_offline "" javascript "import { x } from 'y'")" \
	"an import line resolves through the --import path"

echo "== lookup_offline: mirror has no answer =="
reset_state
enable_offline_docs_empty
if lookup_offline "frobnicate" python "" >/dev/null 2>&1; then
	_t_fail "an unanswered term fails rather than returning empty"
else
	_t_pass "an unanswered term fails rather than returning empty"
fi

echo "== get_doc_url: dispatches per language =="
reset_state
_t_has "$(get_doc_url "def" python "")" "docs.python.org" "python dispatches to python_doc_url"
_t_has "$(get_doc_url "const" javascript "")" "developer.mozilla.org" "javascript dispatches to js_doc_url"
_t_has "$(get_doc_url "interface" typescript "")" "typescriptlang.org" "typescript dispatches to ts_doc_url"
_t_has "$(get_doc_url "printf" c "")" "cppreference.com" "c dispatches to c_doc_url"
_t_has "$(get_doc_url "vector" cpp "")" "cppreference.com" "cpp dispatches to cpp_doc_url"
_t_has "$(get_doc_url "fn" rust "")" "rust-lang.org" "rust dispatches to rust_doc_url"
_t_has "$(get_doc_url "func" go "")" "go.dev" "go dispatches to go_doc_url"
_t_has "$(get_doc_url "def" ruby "")" "ruby-doc.org" "ruby dispatches to ruby_doc_url"
_t_has "$(get_doc_url "class" java "")" "oracle.com" "java dispatches to java_doc_url"
_t_has "$(get_doc_url "if" shell "")" "gnu.org" "shell dispatches to shell_doc_url"

echo "== get_doc_url: an unknown language still answers =="
reset_state
out="$(get_doc_url "something" brainfuck "")"
if [[ -n "$out" ]]; then
	_t_pass "an unrecognised language still produces a link"
else
	_t_fail "an unrecognised language still produces a link (returned nothing)"
fi

echo "== get_doc_url: prefers the offline mirror when it has an answer =="
reset_state
enable_offline_docs "${OFFLINE_DOCS_DIR}/python/os.md"
out="$(get_doc_url "os" python "")"
_t_has "$out" "${OFFLINE_DOCS_DIR}" "an offline hit wins over the online URL"

echo "== get_doc_url: falls back online when the mirror misses =="
reset_state
enable_offline_docs_empty
_t_has "$(get_doc_url "os" python "")" "docs.python.org" "an offline miss falls back to the online URL"

echo "== get_doc_url: TypeScript borrows the JavaScript offline mirror =="
reset_state
# The mirror answers for "js" and nothing else, which is the real shape: an
# offline-docs install carries MDN, not a separate TypeScript tree. A TS lookup
# therefore misses under "typescript" and only succeeds on the retry under
# "js". Without that retry a TS repo would silently never use the docs it has.
enable_offline_docs_for_lang js "${OFFLINE_DOCS_DIR}/js/const.md"
_t_has "$(get_doc_url "const" typescript "")" "${OFFLINE_DOCS_DIR}" \
	"a TS term resolves through the JS mirror"

echo "== get_doc_url: a TS runtime term falls through to the JS builder =="
reset_state
_t_has "$(get_doc_url "const" typescript "")" "developer.mozilla.org" \
	"a runtime term prefers MDN over the TS handbook"
_t_has "$(get_doc_url "interface" typescript "")" "typescriptlang.org" \
	"a TS-only term still gets the TS handbook"

echo "== detect_language =="
reset_state
stage_tokei "Python" "JavaScript"
_t_eq "DELIBERATELY_WRONG" "$(detect_language)" "the language with the most code wins"

reset_state
stage_tokei "Rust"
_t_eq "rust" "$(detect_language)" "a single-language repo detects that language"

reset_state
stage_tokei "C++"
out="$(detect_language)"
if [[ -n "$out" ]]; then
	_t_pass "a punctuated language name still maps to something ('${out}')"
else
	_t_fail "a punctuated language name still maps to something"
fi

echo "== detect_language: no stats file =="
reset_state
out="$(detect_language)"
if [[ -n "$out" ]]; then
	_t_pass "a missing tokei_stats.txt falls back to a default ('${out}')"
else
	_t_fail "a missing tokei_stats.txt falls back to a default"
fi

_t_summary
