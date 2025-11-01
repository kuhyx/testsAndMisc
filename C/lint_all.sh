#!/usr/bin/env bash

# Lint all C code in C/ and its subfolders with aggressive rules
# - Installs required tools if missing (clang-tidy, clang-format, cppcheck, flawfinder)
# - Uses compile_commands.json if present for clang-tidy; otherwise uses sane defaults
# - Checks formatting with clang-format --dry-run --Werror
# - Runs cppcheck with exhaustive rules
# - Runs flawfinder for security issues

set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}==>${NC} $*"; }
ok() { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err() { echo -e "${RED}✗${NC} $*"; }

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
C_DIR="${ROOT_DIR}/C"
AUTOFIX=${LINT_AUTOFIX:-1}

if [[ ! -d "${C_DIR}" ]]; then
	err "C directory not found at ${C_DIR}"
	exit 1
fi

ISSUES=0
MISSING=()
C_FILES=()
C_SOURCES=()

need_cmd() {
	command -v "$1" >/dev/null 2>&1 || MISSING+=("$1")
}

detect_pkg_manager() {
	if command -v pacman >/dev/null 2>&1; then echo pacman; return; fi
	if command -v apt-get >/dev/null 2>&1; then echo apt; return; fi
	if command -v apt >/dev/null 2>&1; then echo apt; return; fi
	if command -v dnf >/dev/null 2>&1; then echo dnf; return; fi
	if command -v zypper >/dev/null 2>&1; then echo zypper; return; fi
	if command -v apk >/dev/null 2>&1; then echo apk; return; fi
	echo none
}

install_tools() {
	info "Checking required tools..."
	need_cmd clang-tidy
	need_cmd clang-format
	need_cmd cppcheck
	need_cmd flawfinder

	if [[ ${#MISSING[@]} -eq 0 ]]; then
		ok "All tools present: clang-tidy, clang-format, cppcheck, flawfinder"
		return 0
	fi

	warn "Missing tools: ${MISSING[*]} — attempting to install with sudo"
	local pm
	pm=$(detect_pkg_manager)
	case "$pm" in
		pacman)
			sudo pacman -S --needed --noconfirm clang clang-tools-extra clang-format cppcheck flawfinder || true
			;;
		apt|apt-get)
			sudo "$pm" update -y || true
			# clang-tidy and clang-format may be versioned; prefer unversioned meta pkgs
			sudo "$pm" install -y clang-tidy clang-format cppcheck flawfinder || true
			;;
		dnf)
			sudo dnf install -y clang-tools-extra clang cppcheck flawfinder || true
			;;
		zypper)
			sudo zypper --non-interactive install clang-tools clang-tools-extra cppcheck flawfinder || true
			;;
		apk)
			sudo apk add clang-extra-tools clang cppcheck flawfinder || true
			;;
		*)
			warn "Unsupported package manager. Please install: clang-tidy clang-format cppcheck flawfinder"
			;;
	esac

	# Re-check after attempted install
	MISSING=()
	need_cmd clang-tidy
	need_cmd clang-format
	need_cmd cppcheck
	need_cmd flawfinder
	if [[ ${#MISSING[@]} -ne 0 ]]; then
		warn "Still missing: ${MISSING[*]} — continuing, but related steps may be skipped"
	else
		ok "Tools installed"
	fi
}

ensure_configs() {
	# Provide default aggressive configs if missing
	if [[ ! -f "${C_DIR}/.clang-tidy" ]]; then
		warn ".clang-tidy not found in C/. Creating a default aggressive config."
		cat >"${C_DIR}/.clang-tidy" <<'YAML'
Checks: >
	clang-analyzer-*,bugprone-*,cert-*,concurrency-*,hicpp-*,misc-*,performance-*,
	portability-*,readability-*,clang-diagnostic-*,cppcoreguidelines-*
WarningsAsErrors: '*'
HeaderFilterRegex: '.*'
AnalyzeTemporaryDtors: true
FormatStyle: none
YAML
	fi

	if [[ ! -f "${C_DIR}/.clang-format" ]]; then
		warn ".clang-format not found in C/. Creating a default style."
		cat >"${C_DIR}/.clang-format" <<'YAML'
BasedOnStyle: LLVM
IndentWidth: 4
TabWidth: 4
UseTab: Never
ColumnLimit: 100
SortIncludes: true
AlignConsecutiveAssignments: true
AlignConsecutiveDeclarations: true
AllowShortIfStatementsOnASingleLine: false
BreakBeforeBraces: Allman
Standard: C23
YAML
	fi
}

collect_files() {
	# shellcheck disable=SC2207
	C_FILES=($(find "${C_DIR}" -type f \( -name '*.c' -o -name '*.h' -o -name '*.inc' \) \
		-not -path '*/.*' -not -path '*/build/*' -not -path '*/dist/*' -not -path '*/out/*' \
		-not -path '*/bin/*' -not -path '*/obj/*'))
	if [[ ${#C_FILES[@]} -eq 0 ]]; then
		warn "No C files found under ${C_DIR}"
	else
		ok "Found ${#C_FILES[@]} C-related files to check"
	fi
	mapfile -t C_SOURCES < <(find "${C_DIR}" -type f -name '*.c' \
		-not -path '*/.*' -not -path '*/build/*' -not -path '*/dist/*' -not -path '*/out/*' \
		-not -path '*/bin/*' -not -path '*/obj/*')
}

apply_clang_format_fix() {
	if ! command -v clang-format >/dev/null 2>&1; then
		warn "clang-format unavailable; skipping auto-format"
		return
	fi
	if [[ ${#C_FILES[@]} -eq 0 ]]; then
		return
	fi
	info "Applying clang-format -i to source files"
	local formatted=0
	for f in "${C_FILES[@]}"; do
		if clang-format -i "$f" 2>/dev/null; then
			formatted=$((formatted+1))
		fi
	done
	ok "clang-format applied to ${formatted} file(s)"
}

apply_clang_tidy_fix() {
	if ! command -v clang-tidy >/dev/null 2>&1; then
		warn "clang-tidy unavailable; skipping auto-fix"
		return
	fi
	if [[ ${#C_SOURCES[@]} -eq 0 ]]; then
		return
	fi
	local db="${C_DIR}/compile_commands.json"
	local used_db="no"
	if [[ -f "$db" ]] && head -n 1 "$db" | grep -q '\['; then
		used_db="yes"
	fi
	info "Applying clang-tidy --fix to C sources"
	local failures=0
	for f in "${C_SOURCES[@]}"; do
		local rel
		rel=$(realpath --relative-to="${ROOT_DIR}" "$f" 2>/dev/null || echo "$f")
		printf '  • %s\n' "$rel"
		if [[ "$used_db" == "yes" ]]; then
			if ! clang-tidy "$f" -p "${C_DIR}" --fix --format-style=file --quiet >/dev/null 2>&1; then
				failures=$((failures+1))
			fi
		else
			if ! clang-tidy "$f" --fix --format-style=file --quiet -- -std=c2x -I"$(dirname "$f")" -I"${C_DIR}" >/dev/null 2>&1; then
				failures=$((failures+1))
			fi
		fi
	done
	if [[ $failures -gt 0 ]]; then
		warn "clang-tidy auto-fix encountered $failures issue(s); manual review may be required"
	else
		ok "clang-tidy auto-fix pass completed"
	fi
}

apply_autofix() {
	if [[ "$AUTOFIX" == "0" ]]; then
		info "Automatic fixes disabled (LINT_AUTOFIX=0)"
		return
	fi
	info "Automatic fixes enabled (LINT_AUTOFIX=${AUTOFIX})"
	apply_clang_format_fix
	apply_clang_tidy_fix
	# Refresh file lists in case new files were introduced by fixes
	collect_files
}

run_clang_format() {
	if ! command -v clang-format >/dev/null 2>&1; then
		warn "clang-format unavailable; skipping format check"
		return
	fi
	info "Checking formatting with clang-format (--dry-run --Werror)"
	local bad=0
	for f in "${C_FILES[@]}"; do
		if ! clang-format --dry-run --Werror "$f" >/dev/null 2>&1; then
			echo "format issue: $f"
			bad=$((bad+1))
		fi
	done
	if [[ $bad -gt 0 ]]; then
		warn "clang-format found $bad files needing formatting"
		ISSUES=$((ISSUES+bad))
	else
		ok "Formatting OK"
	fi
}

run_cppcheck() {
	if ! command -v cppcheck >/dev/null 2>&1; then
		warn "cppcheck unavailable; skipping"
		return
	fi
	info "Running cppcheck (aggressive, recursive)"
	# Use a temp report file to avoid noisy exit codes stopping script
	local report
	report=$(mktemp)
	local opts=(--enable=all --inconclusive --std=c23 --check-level=exhaustive --force \
		--quiet --error-exitcode=2 --inline-suppr --suppress=missingIncludeSystem \
		--library=posix)
	# Exclude common non-source dirs
	opts+=(--exclude=build --exclude=dist --exclude=out --exclude=.git --exclude=bin --exclude=obj)
	if ! cppcheck "${opts[@]}" "${C_DIR}" 2>"$report"; then
		warn "cppcheck reported issues (see summary below)"
		ISSUES=$((ISSUES+1))
	else
		ok "cppcheck passed"
	fi
	if [[ -s "$report" ]]; then
		echo
		echo "cppcheck output:" && sed -e 's/^/  /' "$report"
	fi
	rm -f "$report"
}

run_clang_tidy() {
	if ! command -v clang-tidy >/dev/null 2>&1; then
		warn "clang-tidy unavailable; skipping"
		return
	fi
	info "Running clang-tidy on .c files"
		local db="${C_DIR}/compile_commands.json"
	local used_db="no"
	if [[ ${#C_SOURCES[@]} -eq 0 ]]; then
		warn "No .c files for clang-tidy"
		return
	fi
		if [[ -f "$db" ]]; then
			# Basic validation: ensure JSON array starts with [ and includes "directory"
			if head -n 1 "$db" | grep -q '\['; then
				used_db="yes"
			else
				warn "compile_commands.json seems malformed; ignoring"
			fi
		fi
	local failures=0
	for f in "${C_SOURCES[@]}"; do
		if [[ "$used_db" == "yes" ]]; then
			clang-tidy "$f" -p "${C_DIR}" --quiet || failures=$((failures+1))
		else
			# Fallback args: try C23 and include local dir
			clang-tidy "$f" --quiet -- -std=c2x -I"$(dirname "$f")" -I"${C_DIR}" || failures=$((failures+1))
		fi
	done
	if [[ $failures -gt 0 ]]; then
		warn "clang-tidy found issues in $failures file(s)"
		ISSUES=$((ISSUES+failures))
	else
		ok "clang-tidy passed"
	fi
}

run_flawfinder() {
	if ! command -v flawfinder >/dev/null 2>&1; then
		warn "flawfinder unavailable; skipping"
		return
	fi
	info "Running flawfinder (security-focused scan)"
	local report
	report=$(mktemp)
		if ! flawfinder --quiet --columns --minlevel=1 --falsepositive "${C_DIR}" >"$report" 2>/dev/null; then
		warn "flawfinder reported issues"
		ISSUES=$((ISSUES+1))
	else
		ok "flawfinder completed"
	fi
	if [[ -s "$report" ]]; then
		echo
		echo "flawfinder notable findings:" && head -n 200 "$report" | sed -e 's/^/  /'
	fi
	rm -f "$report"
}

summary_exit() {
	echo
	if [[ $ISSUES -gt 0 ]]; then
		err "Lint completed with $ISSUES issue(s) detected"
		echo "Tip: run 'clang-format -i' to fix formatting; many clang-tidy checks support '--fix'"
		exit 1
	else
		ok "All checks passed with no issues"
	fi
}

main() {
	echo -e "${BLUE}C folder – aggressive lint suite${NC}"
	echo
	install_tools
	ensure_configs
	collect_files
	apply_autofix
	run_clang_format
	run_cppcheck
	run_clang_tidy
	run_flawfinder
	summary_exit
}

main "$@"
