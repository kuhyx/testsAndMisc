#!/usr/bin/env bash

# A one-stop shell linting helper for this repo.
# - Installs shell linters on Arch Linux (shellcheck, shfmt) and optionally via AUR if available
# - Discovers shell scripts in the repository (by extension or shebang)
# - Runs: shellcheck, shfmt (diff mode), optional: checkbashisms, bashate, and shell syntax checks (bash -n, zsh -n, sh/dash -n)
# - Prints a summarized report and returns non-zero if any linter reports issues
#
# Usage:
#   scripts/meta/shell_check.sh [--path DIR] [--skip-install] [--install-only] [--list-only] [--verbose]
#
# Notes:
# - Arch install uses pacman: shellcheck shfmt
# - Optional linters if available (installed already or via AUR helper yay/paru): checkbashisms, bashate
# - On non-Arch systems, install is skipped with a helpful hint

set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DEFAULT_ROOT=$(cd -- "$SCRIPT_DIR/../../" && pwd)

ROOT_DIR="$DEFAULT_ROOT"
SKIP_INSTALL="false"
INSTALL_ONLY="false"
LIST_ONLY="false"
VERBOSE="false"

log_info() {
  printf '\033[1;34m[INFO]\033[0m %s\n' "$*"
}

log_warn() {
  printf '\033[1;33m[WARN]\033[0m %s\n' "$*"
}

log_error() {
  printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2
}

usage() {
  cat << EOF
Usage: $(basename "$0") [options]

Options:
  --path DIR         Root directory to scan (default: repo root at $DEFAULT_ROOT)
  --skip-install     Skip installing linters
  --install-only     Only install linters, do not scan
  --list-only        Only list discovered shell files, do not run linters
  --verbose          Print additional details while running
  -h, --help         Show this helpLinters used:
	Required: shellcheck, shfmt
	Optional (if available): checkbashisms, bashate
	Syntax checks: bash -n, zsh -n (if installed), sh/dash -n
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      ROOT_DIR="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL="true"
      shift
      ;;
    --install-only)
      INSTALL_ONLY="true"
      shift
      ;;
    --list-only)
      LIST_ONLY="true"
      shift
      ;;
    --verbose)
      VERBOSE="true"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ ! -d $ROOT_DIR ]]; then
  log_error "Path not found: $ROOT_DIR"
  exit 2
fi

is_cmd() { command -v "$1" > /dev/null 2>&1; }

is_arch() { is_cmd pacman; }
have_aur_helper() { is_cmd yay || is_cmd paru; }

install_if_missing() {
  local pkg cmd
  pkg="$1"
  cmd="$2"
  if is_cmd "$cmd"; then
    [[ $VERBOSE == "true" ]] && log_info "Found $cmd"
    return 0
  fi

  if [[ $SKIP_INSTALL == "true" ]]; then
    log_warn "Skipping install of $pkg ($cmd not found)"
    return 1
  fi

  if is_arch; then
    log_info "Installing $pkg via pacman..."
    if ! sudo pacman -S --needed --noconfirm "$pkg"; then
      log_warn "Failed to install $pkg via pacman."
      return 1
    fi
    return 0
  else
    log_warn "Non-Arch system detected. Please install '$pkg' manually."
    return 1
  fi
}

install_linters() {
  local ok=0

  # Core linters
  install_if_missing shellcheck shellcheck || ok=1
  install_if_missing shfmt shfmt || ok=1

  # Optional linters (best-effort)
  # checkbashisms may be in repos or AUR; try pacman first, then AUR helper
  if ! is_cmd checkbashisms; then
    if is_arch; then
      if ! sudo pacman -S --needed --noconfirm checkbashisms 2> /dev/null; then
        if have_aur_helper; then
          log_info "Installing checkbashisms from AUR (requires yay/paru)..."
          if is_cmd yay; then yay -S --noconfirm checkbashisms || true; fi
          if is_cmd paru; then paru -S --noconfirm checkbashisms || true; fi
        else
          log_warn "checkbashisms not installed (no AUR helper)."
        fi
      fi
    fi
  fi

  # bashate (python-based), typically available as python-bashate in AUR
  if ! is_cmd bashate; then
    if is_arch && have_aur_helper; then
      log_info "Installing bashate from AUR (requires yay/paru)..."
      if is_cmd yay; then yay -S --noconfirm python-bashate || true; fi
      if is_cmd paru; then paru -S --noconfirm python-bashate || true; fi
    else
      # Try pip if user has it and wants to
      if is_cmd pipx; then
        log_info "Installing bashate via pipx..."
        pipx install bashate || true
      elif is_cmd pip3; then
        log_info "Installing bashate via pip (user)..."
        pip3 install --user bashate || true
      else
        log_warn "bashate not installed (no AUR helper or pip available)."
      fi
    fi
  fi

  return "$ok"
}

TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR:-}"' EXIT

ABS_FILES_Z="$TMPDIR/files_abs.zlist"
REL_FILES_Z="$TMPDIR/files_rel.zlist"

discover_shell_files() {
  local base="$1"
  local -a all
  all=()

  if git -C "$base" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    while IFS= read -r -d '' f; do all+=("$f"); done < <(git -C "$base" ls-files -z)
    while IFS= read -r -d '' f; do all+=("$f"); done < <(git -C "$base" ls-files --others --exclude-standard -z)
  else
    while IFS= read -r -d '' f; do
      # trim leading ./ to keep consistent style with git paths
      f="${f#./}"
      f="${f#"${base}"/}"
      all+=("$f")
    done < <(find "$base" -type f -print0)
  fi

  local -a shells
  shells=()

  for rel in "${all[@]}"; do
    # skip binary-ish or huge files quickly by extension heuristic
    case "$rel" in
      *.png | *.jpg | *.jpeg | *.gif | *.ico | *.pdf | *.svg | *.zip | *.tar | *.gz | *.xz | *.7z | *.so | *.o | *.bin)
        continue
        ;;
    esac

    local abs="$base/$rel"
    [[ -f $abs && -r $abs ]] || continue

    if [[ $rel == *.sh || $rel == *.bash || $rel == *.zsh ]]; then
      shells+=("$rel")
      continue
    fi

    # Check shebang
    local first
    first=$(head -n 1 -- "$abs" 2> /dev/null || true)
    if [[ $first =~ ^#! && $first =~ (ba|z|d|k)?sh ]]; then
      shells+=("$rel")
      continue
    fi

    # Also catch executable files with shell shebang even without extension
    if [[ -x $abs ]]; then
      if [[ $first =~ ^#! && $first =~ (ba|z|d|k)?sh ]]; then
        shells+=("$rel")
      fi
    fi
  done

  # write lists
  : > "$REL_FILES_Z"
  : > "$ABS_FILES_Z"
  for rel in "${shells[@]}"; do
    printf '%s\0' "$rel" >> "$REL_FILES_Z"
    printf '%s\0' "$base/$rel" >> "$ABS_FILES_Z"
  done
}

print_file_list() {
  local count
  count=$(tr -cd '\0' < "$REL_FILES_Z" | wc -c)
  log_info "Discovered $count shell file(s) under $ROOT_DIR"
  if [[ $VERBOSE == "true" ]]; then
    tr '\0' '\n' < "$REL_FILES_Z" | sed 's/^/  - /'
  fi
}

run_linters() {
  local issues=0
  local count
  count=$(tr -cd '\0' < "$ABS_FILES_Z" | wc -c)
  if [[ $count -eq 0 ]]; then
    log_warn "No shell files found to lint."
    return 0
  fi

  mapfile -d '' -t FILES < "$ABS_FILES_Z"

  log_info "Running shellcheck..."
  local sc_out="$TMPDIR/shellcheck.txt"
  if is_cmd shellcheck; then
    if ! shellcheck -x -S style "${FILES[@]}" > "$sc_out" 2>&1; then
      issues=$((issues + 1))
    fi
  else
    log_warn "shellcheck not found; skipping"
  fi

  log_info "Running shfmt (diff mode)..."
  local shfmt_out="$TMPDIR/shfmt.diff"
  if is_cmd shfmt; then
    if ! shfmt -d -i 2 -ci -sr -s "${FILES[@]}" > "$shfmt_out" 2>&1; then
      # shfmt returns non-zero when diff exists
      issues=$((issues + 1))
    fi
  else
    log_warn "shfmt not found; skipping"
  fi

  log_info "Running checkbashisms (optional)..."
  local cbi_out="$TMPDIR/checkbashisms.txt"
  local cbi_status=0
  if is_cmd checkbashisms; then
    # Only run checkbashisms on scripts that are intended for /bin/sh (or unspecified),
    # skip explicit bash/zsh scripts to avoid false positives.
    local -a CBI_FILES
    CBI_FILES=()
    for f in "${FILES[@]}"; do
      local first
      first=$(head -n 1 -- "$f" 2> /dev/null || true)
      if [[ $first =~ bash || $first =~ zsh ]]; then
        continue
      fi
      CBI_FILES+=("$f")
    done
    if [[ ${#CBI_FILES[@]} -gt 0 ]]; then
      # checkbashisms exits 0 if OK, 1 if issues, other codes for tool warnings
      checkbashisms "${CBI_FILES[@]}" > "$cbi_out" 2>&1
    else
      : > "$cbi_out"
    fi
    cbi_status=$?
    if [[ $cbi_status -eq 1 ]]; then
      issues=$((issues + 1))
    elif [[ $cbi_status -ne 0 ]]; then
      log_warn "checkbashisms exited with status $cbi_status (treated as warning)"
    fi
  else
    log_warn "checkbashisms not found; skipping"
  fi

  log_info "Running bash/zsh/sh syntax checks (-n)..."
  local bash_out="$TMPDIR/bash_syntax.txt"
  local zsh_out="$TMPDIR/zsh_syntax.txt"
  local sh_out="$TMPDIR/sh_syntax.txt"

  # Partition files by shebang for better accuracy
  local -a BASH_FILES ZSH_FILES SH_FILES
  BASH_FILES=()
  ZSH_FILES=()
  SH_FILES=()
  for f in "${FILES[@]}"; do
    local first
    first=$(head -n 1 -- "$f" 2> /dev/null || true)
    if [[ $first =~ bash ]]; then
      BASH_FILES+=("$f")
    elif [[ $first =~ zsh ]]; then
      ZSH_FILES+=("$f")
    else
      SH_FILES+=("$f")
    fi
  done

  if [[ ${#BASH_FILES[@]} -gt 0 ]] && is_cmd bash; then
    if ! bash -n "${BASH_FILES[@]}" 2> "$bash_out"; then
      issues=$((issues + 1))
    fi
  fi
  if [[ ${#ZSH_FILES[@]} -gt 0 ]] && is_cmd zsh; then
    if ! zsh -n "${ZSH_FILES[@]}" 2> "$zsh_out"; then
      issues=$((issues + 1))
    fi
  fi
  # prefer dash if present for /bin/sh style
  if [[ ${#SH_FILES[@]} -gt 0 ]]; then
    if is_cmd dash; then
      if ! dash -n "${SH_FILES[@]}" 2> "$sh_out"; then
        issues=$((issues + 1))
      fi
    elif is_cmd sh; then
      if ! sh -n "${SH_FILES[@]}" 2> "$sh_out"; then
        issues=$((issues + 1))
      fi
    fi
  fi

  echo
  log_info "========== Shell Lint Report =========="

  if [[ -s $sc_out ]]; then
    printf '\n\033[1m-- shellcheck --\033[0m\n'
    cat "$sc_out"
  else
    printf '\n\033[1;32m-- shellcheck: PASS (no issues) --\033[0m\n'
  fi

  if [[ -s $shfmt_out ]]; then
    printf '\n\033[1m-- shfmt (diffs found) --\033[0m\n'
    cat "$shfmt_out"
  else
    printf '\n\033[1;32m-- shfmt: PASS (formatted) --\033[0m\n'
  fi

  if [[ -s $cbi_out ]]; then
    printf '\n\033[1m-- checkbashisms --\033[0m\n'
    cat "$cbi_out"
  else
    printf '\n\033[1;32m-- checkbashisms: PASS (or skipped) --\033[0m\n'
  fi

  if [[ -s $bash_out ]]; then
    printf '\n\033[1m-- bash -n (syntax) --\033[0m\n'
    cat "$bash_out"
  else
    printf '\n\033[1;32m-- bash -n: PASS (or none) --\033[0m\n'
  fi

  if [[ -s $zsh_out ]]; then
    printf '\n\033[1m-- zsh -n (syntax) --\033[0m\n'
    cat "$zsh_out"
  else
    printf '\n\033[1;32m-- zsh -n: PASS (or none) --\033[0m\n'
  fi

  if [[ -s $sh_out ]]; then
    printf '\n\033[1m-- sh/dash -n (syntax) --\033[0m\n'
    cat "$sh_out"
  else
    printf '\n\033[1;32m-- sh/dash -n: PASS (or none) --\033[0m\n'
  fi

  echo
  if [[ $issues -gt 0 ]]; then
    log_error "Linting completed with $issues tool(s) reporting issues."
    return 1
  else
    log_info "All checks passed."
    return 0
  fi
}

# Main
if [[ $INSTALL_ONLY == "true" ]]; then
  install_linters
  exit $?
fi

# Only attempt installs if not list-only
if [[ $LIST_ONLY != "true" ]]; then
  install_linters || true
fi

discover_shell_files "$ROOT_DIR"
print_file_list

if [[ $LIST_ONLY == "true" ]]; then
  exit 0
fi

run_linters
exit $?
