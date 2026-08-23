#!/usr/bin/env bash
# Tests for lib/study_doc_urls_more.sh — the Rust, Go, Ruby, Java and shell
# doc-URL builders.
#
# Same shape as test_study_doc_urls.sh: one assertion per case arm plus the
# fallback, since an unmatched term is the common case for anything the
# analysis extracted that is project-specific rather than language-level.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=study_harness.sh
. "${SCRIPT_DIR}/study_harness.sh"
# shellcheck source=../study_doc_urls_more.sh
. "${SCRIPT_DIR}/../study_doc_urls_more.sh"

echo "== rust_doc_url =="
_t_has "$(rust_doc_url "fn" keyword)" "doc.rust-lang.org" "a Rust keyword links to the Rust docs"
_t_has "$(rust_doc_url "Option" builtin)" "Option" "a std type names itself"
_t_has "$(rust_doc_url "Clone" builtin)" "Clone" "a derivable trait names itself"
_t_has "$(rust_doc_url "println" builtin)" "macro" "a macro links to its macro page"
_t_has "$(rust_doc_url "frobnicate" keyword)" "doc.rust-lang.org" "an unknown Rust term stays on the Rust docs"

echo "== go_doc_url =="
_t_has "$(go_doc_url "func" keyword)" "go.dev" "a Go keyword links to go.dev"
_t_has "$(go_doc_url "append" builtin)" "builtin" "a builtin links to the builtin package"
_t_has "$(go_doc_url "fmt" module)" "fmt" "a stdlib package names itself"
_t_has "$(go_doc_url "frobnicate" keyword)" "go.dev" "an unknown Go term stays on go.dev"

echo "== ruby_doc_url =="
_t_has "$(ruby_doc_url "def" keyword)" "ruby-doc.org" "a Ruby keyword links to ruby-doc.org"
_t_has "$(ruby_doc_url "String" builtin)" "String" "a core class names itself"
_t_has "$(ruby_doc_url "each" builtin)" "Enumerable" "an Enumerable method links to the Enumerable page"
_t_has "$(ruby_doc_url "frobnicate" keyword)" "ruby-doc.org" "an unknown Ruby term stays on ruby-doc.org"

echo "== java_doc_url =="
_t_has "$(java_doc_url "class" keyword)" "oracle.com" "a Java keyword links to the Oracle docs"
_t_has "$(java_doc_url "String" builtin)" "String" "a core class names itself"
_t_has "$(java_doc_url "frobnicate" keyword)" "oracle.com" "an unknown Java term stays on the Oracle docs"

echo "== shell_doc_url =="
_t_has "$(shell_doc_url "if" keyword)" "gnu.org" "a shell keyword links to the bash manual"
_t_has "$(shell_doc_url "declare" builtin)" "gnu.org" "a shell builtin links to the bash manual"
# External commands get a man page rather than the bash manual, because they
# are not part of the shell -- a card saying otherwise would be wrong.
_t_has "$(shell_doc_url "grep" builtin)" "man" "an external command links to its man page"
_t_has "$(shell_doc_url "frobnicate" keyword)" "man" "an unknown command is treated as external"

echo "== every builder answers for every input =="
# These are fed straight from the analysis output, punctuation and all. A
# builder returning nothing would emit a card with no link, which is worse than
# a link to a search page.
for fn in rust_doc_url go_doc_url ruby_doc_url java_doc_url shell_doc_url; do
	for term in "" "x" "a-b" "3" "__weird__"; do
		out="$("$fn" "$term" keyword)"
		if [[ -n "$out" ]]; then
			_t_pass "${fn} answers for '${term}'"
		else
			_t_fail "${fn} answers for '${term}' (returned nothing)"
		fi
	done
done

_t_summary
