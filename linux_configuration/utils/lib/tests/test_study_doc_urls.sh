#!/usr/bin/env bash
# Tests for lib/study_doc_urls.sh — the Python, JS, TS and C/C++ doc-URL
# builders.
#
# Each builder is a case dispatch over term categories with a search-URL
# fallback, so every arm gets one assertion plus one for the fallback. The
# fallback matters more than it looks: it is what every unrecognised term hits,
# so a card for an unknown identifier still links somewhere useful instead of
# to an empty string.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=study_harness.sh
. "${SCRIPT_DIR}/study_harness.sh"
# shellcheck source=../study_doc_urls.sh
. "${SCRIPT_DIR}/../study_doc_urls.sh"

echo "== python_doc_url =="
_t_eq "https://docs.python.org/3/reference/compound_stmts.html" \
	"$(python_doc_url "def" keyword)" "a keyword links to the statements reference"
_t_eq "https://docs.python.org/3/library/functions.html#print" \
	"$(python_doc_url "print" builtin)" "a builtin links to its anchor in functions.html"
_t_eq "https://docs.python.org/3/library/os.html" \
	"$(python_doc_url "os" module)" "a stdlib module links to its own page"
_t_eq "https://docs.python.org/3/library/unittest.mock.html" \
	"$(python_doc_url "MagicMock" module)" "a mock helper links to unittest.mock"
_t_eq "https://docs.python.org/3/search.html?q=frobnicate" \
	"$(python_doc_url "frobnicate" keyword)" "an unknown term falls back to search"

echo "== js_doc_url =="
_t_has "$(js_doc_url "const" keyword)" "developer.mozilla.org" "a JS keyword links to MDN"
_t_has "$(js_doc_url "Array" builtin)" "Array" "a builtin object names itself in the URL"
_t_has "$(js_doc_url "frobnicate" keyword)" "frobnicate" "an unknown JS term still carries the term"

echo "== ts_doc_url =="
_t_has "$(ts_doc_url "interface" keyword)" "typescriptlang.org" "a TS term links to the TS handbook"
_t_has "$(ts_doc_url "Partial" keyword)" "utility-types" "a TS utility type links to the utility-types page"
# A term TypeScript does not define is a runtime feature, so it deliberately
# falls through to the JS builder rather than to a TS search page.
_t_has "$(ts_doc_url "frobnicate" keyword)" "developer.mozilla.org" "an unknown TS term falls through to MDN"

echo "== js_doc_url: every category of builtin =="
_t_has "$(js_doc_url "map" builtin)" "Global_Objects/Array" "an array method links under Array"
_t_has "$(js_doc_url "split" builtin)" "Global_Objects/String" "a string method links under String"
_t_has "$(js_doc_url "then" builtin)" "Global_Objects/Promise" "a promise method links under Promise"
_t_has "$(js_doc_url "fetch" builtin)" "docs/Web/API" "a browser API links under Web/API"

echo "== c_doc_url =="
_t_has "$(c_doc_url "printf" builtin)" "cppreference.com" "a C library function links to cppreference"
_t_has "$(c_doc_url "for" keyword)" "cppreference.com" "a C keyword links to cppreference"
_t_has "$(c_doc_url "frobnicate" keyword)" "cppreference.com" "an unknown C term stays on cppreference"

_t_has "$(c_doc_url "stdio" module)" "c/header/stdio.h" "a C header links to its header page"
_t_has "$(c_doc_url "malloc" builtin)" "c/memory" "an allocator links to the memory page"
_t_has "$(c_doc_url "strlen" builtin)" "c/string/byte" "a string function links to the byte-string page"

echo "== cpp_doc_url =="
_t_has "$(cpp_doc_url "vector" builtin)" "cppreference.com" "a C++ container links to cppreference"
_t_has "$(cpp_doc_url "class" keyword)" "cppreference.com" "a C++ keyword links to cppreference"
_t_has "$(cpp_doc_url "frobnicate" keyword)" "cppreference.com" "an unknown C++ term stays on cppreference"

_t_has "$(cpp_doc_url "sort" builtin)" "cpp/algorithm/sort" "an algorithm links under cpp/algorithm"
_t_has "$(cpp_doc_url "unique_ptr" builtin)" "cpp/memory/unique_ptr" "a smart pointer links under cpp/memory"
_t_has "$(cpp_doc_url "optional" builtin)" "cpp/utility" "a utility type links under cpp/utility"

echo "== every builder answers for every input =="
# The generation phases pipe whatever the analysis found straight into these,
# including punctuation and empty strings from a malformed grep line. A builder
# that returned nothing would silently produce a card with no link at all, so
# the invariant worth pinning is that output is never empty.
for fn in python_doc_url js_doc_url ts_doc_url c_doc_url cpp_doc_url; do
	for term in "" "x" "std::vector" "__init__" "a-b" "3"; do
		out="$("$fn" "$term" keyword)"
		if [[ -n "$out" ]]; then
			_t_pass "${fn} answers for '${term}'"
		else
			_t_fail "${fn} answers for '${term}' (returned nothing)"
		fi
	done
done

_t_summary
