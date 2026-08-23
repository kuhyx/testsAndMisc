#!/usr/bin/env bash
# lib/tests/study_harness.sh — shared fixture for the generate_study_materials
# split.
#
# Sourced, not executed. These libs are almost pure string logic: the doc-URL
# builders map a term to a URL, and the only external process any of them runs
# is $LOOKUP_SCRIPT, which the tests point at a stub. Nothing here reaches the
# network or reads the real offline-docs mirror.
set -euo pipefail

PASS=0
FAIL=0

_t_pass() {
	PASS=$((PASS + 1))
	printf '  OK: %s\n' "$1"
}

_t_fail() {
	FAIL=$((FAIL + 1))
	printf '  FAIL: %s\n' "$1"
}

_t_eq() {
	local want="$1"
	local got="$2"
	local what="$3"
	if [[ "$got" == "$want" ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want '${want}', got '${got}')"
	fi
}

# Assert a URL builder's output contains a substring. Most builders assemble a
# base URL plus the term, so matching the distinctive fragment is more robust
# than pinning the whole string, which would break on an upstream doc-site move
# without anything actually being wrong.
_t_has() {
	local haystack="$1"
	local needle="$2"
	local what="$3"
	if [[ "$haystack" == *"$needle"* ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want a substring '${needle}', got '${haystack}')"
	fi
}

_t_summary() {
	printf '\n%s: %d passed, %d failed\n' "$(basename "$0")" "$PASS" "$FAIL"
	[[ $FAIL -eq 0 ]]
}

TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TEST_TMPDIR}"' EXIT

# --- globals the libs read --------------------------------------------------

# Read by the generation phases, which the individual test files source
# rather than this harness -- so standalone shellcheck (as the hook runs it,
# with no -x) sees only the write here and reports SC2034. Exported because
# they genuinely cross into the sourced libs.
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export BLUE='\033[0;34m'
export YELLOW='\033[1;33m'
export NC='\033[0m'

export RESULTS_DIR="${TEST_TMPDIR}/results"
export TOP_N=5
export PRIMARY_LANG="python"
mkdir -p "${RESULTS_DIR}"

export DOCS_FILE="${RESULTS_DIR}/documentation_links.md"
export ANKI_FILE="${RESULTS_DIR}/anki_cards.txt"
export LLM_PROMPT_FILE="${RESULTS_DIR}/llm_anki_prompt.md"

export OFFLINE_DOCS_DIR="${TEST_TMPDIR}/offline-docs"
export LOOKUP_SCRIPT="${TEST_TMPDIR}/lookup_docs.sh"
export USE_OFFLINE_DOCS=false

# Install a stub lookup_docs.sh and switch the libs onto the offline path.
#
# The real script prints "File: <path>" for a term lookup and a bare path for
# an --import lookup, and lookup_offline parses each shape differently, so the
# stub reproduces both rather than one.
enable_offline_docs() { # [answer-path]
	local answer="${1:-${OFFLINE_DOCS_DIR}/python/stdlib/os.md}"
	mkdir -p "${OFFLINE_DOCS_DIR}"
	cat >"${LOOKUP_SCRIPT}" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "--import" ]]; then
	printf '%s\\n' "${answer}"
else
	printf 'File: %s\\n' "${answer}"
fi
STUB
	chmod +x "${LOOKUP_SCRIPT}"
	USE_OFFLINE_DOCS=true
}

# Make the offline lookup find nothing, so callers fall back to online URLs.
enable_offline_docs_empty() {
	mkdir -p "${OFFLINE_DOCS_DIR}"
	printf '#!/usr/bin/env bash\nexit 0\n' >"${LOOKUP_SCRIPT}"
	chmod +x "${LOOKUP_SCRIPT}"
	USE_OFFLINE_DOCS=true
}

# A mirror that answers ONLY for the given language and stays silent for every
# other. This is what exercises the TypeScript retry path: a TS lookup misses
# under "typescript", then succeeds when get_doc_url retries under "js".
enable_offline_docs_for_lang() { # <language> [answer-path]
	local only_lang="$1"
	local answer="${2:-${OFFLINE_DOCS_DIR}/js/const.md}"
	mkdir -p "${OFFLINE_DOCS_DIR}"
	cat >"${LOOKUP_SCRIPT}" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "--import" ]]; then
	[[ "\${3:-}" == "${only_lang}" ]] || exit 0
	printf '%s\\n' "${answer}"
else
	[[ "\${2:-}" == "${only_lang}" ]] || exit 0
	printf 'File: %s\\n' "${answer}"
fi
STUB
	chmod +x "${LOOKUP_SCRIPT}"
	USE_OFFLINE_DOCS=true
}

disable_offline_docs() {
	USE_OFFLINE_DOCS=false
	rm -f "${LOOKUP_SCRIPT}"
}

# Write the three grep_*.txt files the generation phases read. Each line is
# "<count> <term>", which is what analyze_repo.sh emits.
stage_results() {
	printf '%s\n' "42 def" "31 class" "20 import" >"${RESULTS_DIR}/grep_keywords.txt"
	printf '%s\n' "18 print" "9 len" "4 range" >"${RESULTS_DIR}/grep_function_calls.txt"
	printf '%s\n' "12 os" "7 sys" "3 json" >"${RESULTS_DIR}/grep_imports.txt"
}

# Write the per-language analysis tree. generate_doc_links takes a completely
# different path when $RESULTS_DIR/per_language exists: instead of three global
# grep_*.txt files it walks keywords_<lang>.txt / functions_<lang>.txt /
# imports_<lang>.txt and resolves each language's terms against that language's
# docs, which is what makes a polyglot repo's index correct.
stage_per_language() { # <lang>...
	local dir="${RESULTS_DIR}/per_language"
	mkdir -p "$dir"
	local lang
	for lang in "$@"; do
		printf '%s\n' "9 alpha_${lang}" "8 beta_${lang}" >"${dir}/keywords_${lang}.txt"
		printf '%s\n' "7 fn_${lang}" >"${dir}/functions_${lang}.txt"
		printf '%s\n' "6 mod_${lang}" >"${dir}/imports_${lang}.txt"
	done
}

# tokei output in the shape detect_language parses.
stage_tokei() { # <language> [second-language]
	{
		printf '===============================================================================\n'
		printf ' Language            Files        Lines         Code     Comments       Blanks\n'
		printf '===============================================================================\n'
		printf ' %-18s    42         5120         4001          610          509\n' "$1"
		[[ -n "${2:-}" ]] && printf ' %-18s    12         1400         1100          150          150\n' "$2"
		printf '===============================================================================\n'
	} >"${RESULTS_DIR}/tokei_stats.txt"
}

reset_state() {
	rm -rf "${RESULTS_DIR:?}"
	mkdir -p "${RESULTS_DIR}"
	TOP_N=5
	PRIMARY_LANG="python"
	disable_offline_docs
}
reset_state
