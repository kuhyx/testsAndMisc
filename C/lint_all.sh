#!/usr/bin/env bash

# Aggressive linting for all C code in this C/ folder and subfolders
# - Installs missing tools when possible
# - Runs: clang-format (check), cppcheck, flawfinder, clang-tidy (aggressive)
#
# Usage:
#   ./lint_all.sh [--fix-format]
#
# If --fix-format is provided, it will format files in-place with clang-format before linting.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$SCRIPT_DIR"

CYAN='\033[0;36m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; GREEN='\033[0;32m'; NC='\033[0m'

have() { command -v "$1" &>/dev/null; }

pm=""
detect_pm() {
  if have apt-get; then pm=apt; return 0; fi
  if have dnf; then pm=dnf; return 0; fi
  if have yum; then pm=yum; return 0; fi
  if have pacman; then pm=pacman; return 0; fi
  if have zypper; then pm=zypper; return 0; fi
  if have brew; then pm=brew; return 0; fi
  return 1
}

sudo_prefix() {
  if [ "$EUID" -ne 0 ] && have sudo; then echo sudo; else echo; fi
}

install_packages() {
  local pkgs=("clang" "clang-tidy" "clang-format" "cppcheck" "flawfinder" "bear")
  detect_pm || { echo -e "${YELLOW}No supported package manager detected. Skipping auto-install.${NC}"; return 0; }

  echo -e "${CYAN}Attempting to install missing tools using $pm...${NC}"
  case "$pm" in
    apt)
      # Prefer non-interactive installs; ignore missing packages gracefully
      $(sudo_prefix) apt-get update -y || true
      # Try common variants for clang tools
      $(sudo_prefix) apt-get install -y --no-install-recommends \
        clang clang-tidy clang-format cppcheck flawfinder bear || true
      ;;
    dnf)
      $(sudo_prefix) dnf install -y clang clang-tools-extra cppcheck flawfinder bear || true
      ;;
    yum)
      $(sudo_prefix) yum install -y clang clang-tools-extra cppcheck flawfinder bear || true
      ;;
    pacman)
      $(sudo_prefix) pacman --noconfirm -Sy || true
      $(sudo_prefix) pacman --noconfirm -S clang clang-tools-extra cppcheck flawfinder bear || true
      ;;
    zypper)
      $(sudo_prefix) zypper --non-interactive refresh || true
      $(sudo_prefix) zypper --non-interactive install clang clang-tools cppcheck flawfinder bear || true
      ;;
    brew)
      brew update || true
      # llvm contains clang-tidy/format; add others separately
      brew install llvm cppcheck flawfinder bear || true
      # Add llvm tools to PATH if not present
      if ! have clang-tidy && [ -d "/home/linuxbrew/.linuxbrew/opt/llvm/bin" ]; then
        export PATH="/home/linuxbrew/.linuxbrew/opt/llvm/bin:$PATH"
      fi
      ;;
  esac
}

ensure_tools() {
  local missing=()
  for t in clang clang-tidy clang-format cppcheck flawfinder; do
    have "$t" || missing+=("$t")
  done
  if [ ${#missing[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing tools: ${missing[*]}${NC}"
    install_packages
  fi
  local still_missing=()
  for t in clang clang-tidy clang-format cppcheck flawfinder; do
    have "$t" || still_missing+=("$t")
  done
  if [ ${#still_missing[@]} -gt 0 ]; then
    echo -e "${YELLOW}Still missing after install attempt: ${still_missing[*]}${NC}"
  fi
}

# Collect files
mapfile -t C_FILES < <(find "$ROOT_DIR" \
  -type f \( -name '*.c' -o -name '*.h' \) \
  -not -path '*/.*/*' \
  -not -path '*/.git/*' \
  -not -path '*/build/*' \
  -not -path '*/bin/*' \
  -not -path '*/obj/*' \
  -print | sort)

if [ ${#C_FILES[@]} -eq 0 ]; then
  echo -e "${RED}No C source/header files found under: $ROOT_DIR${NC}"
  exit 1
fi

# Unique include dirs where headers live
mapfile -t INCLUDE_DIRS < <(printf '%s\n' "${C_FILES[@]}" | awk -F/ '{ $NF=""; print $0 }' | sed 's# $##;s#[^/]*$##' | sed 's#/$##' | sort -u)

INC_FLAGS=("-I$ROOT_DIR")
for d in "${INCLUDE_DIRS[@]}"; do
  [ -n "$d" ] && INC_FLAGS+=("-I$d")
done

CPU_JOBS=1
if have nproc; then CPU_JOBS="$(nproc)"; elif have getconf; then CPU_JOBS="$(getconf _NPROCESSORS_ONLN || echo 1)"; fi

ensure_tools

FORMAT_ONLY=false
if [ "${1:-}" = "--fix-format" ]; then
  FORMAT_ONLY=true
fi

fail=0

if have clang-format; then
  if $FORMAT_ONLY; then
    echo -e "${CYAN}Formatting with clang-format (in-place)...${NC}"
    printf '%s\0' "${C_FILES[@]}" | xargs -0 -n50 -P "$CPU_JOBS" clang-format -style=file -i || fail=1
  else
    echo -e "${CYAN}Checking formatting with clang-format...${NC}"
    # -n: dry-run, --Werror: exit non-zero if reformatting is needed
    if ! printf '%s\0' "${C_FILES[@]}" | xargs -0 -n50 -P "$CPU_JOBS" clang-format -style=file -n --Werror; then
      echo -e "${YELLOW}clang-format suggests changes. Run with --fix-format to apply.${NC}"
      fail=1
    fi
  fi
else
  echo -e "${YELLOW}clang-format not available; skipping formatting check.${NC}"
fi

if have cppcheck; then
  echo -e "${CYAN}Running cppcheck (aggressive)...${NC}"
  # Build include args for cppcheck
  CPPCHECK_INC=()
  for f in "${INC_FLAGS[@]}"; do
    # convert -Ipath into --include=path for cppcheck? cppcheck uses -I as well
    if [[ "$f" == -I* ]]; then CPPCHECK_INC+=("$f"); fi
  done
  # Use --project if compile_commands.json exists; otherwise lint folder
  if [ -f "$ROOT_DIR/compile_commands.json" ]; then
    cppcheck --enable=all --inconclusive --std=c11 --force --platform=unix64 \
      --library=posix --suppress=missingIncludeSystem \
      --project="$ROOT_DIR/compile_commands.json" || fail=1
  else
    cppcheck --enable=all --inconclusive --std=c11 --force --platform=unix64 \
      --library=posix --suppress=missingIncludeSystem \
      "${CPPCHECK_INC[@]}" "$ROOT_DIR" || fail=1
  fi
else
  echo -e "${YELLOW}cppcheck not available; skipping.${NC}"
fi

if have flawfinder; then
  echo -e "${CYAN}Running flawfinder (security scan)...${NC}"
  # error-level 1+ to be noisy; set to 0 for all messages
  flawfinder --error-level=0 --columns --followdotdirs "$ROOT_DIR" || fail=1
else
  echo -e "${YELLOW}flawfinder not available; skipping.${NC}"
fi

if have clang-tidy; then
  echo -e "${CYAN}Running clang-tidy (aggressive)...${NC}"
  # Prefer compile_commands.json if present
  TIDY_ARGS=("-warnings-as-errors=*" "-header-filter=.*")
  if [ -f "$ROOT_DIR/compile_commands.json" ]; then
    TIDY_ARGS+=("-p" "$ROOT_DIR")
  else
    # Provide basic args so analysis can proceed without a build database
    TIDY_ARGS+=("--extra-arg=-std=c11")
    for inc in "${INC_FLAGS[@]}"; do
      TIDY_ARGS+=("--extra-arg=$inc")
    done
  fi
  # clang-tidy supports parallelism via -j
  clang-tidy -j "$CPU_JOBS" "${TIDY_ARGS[@]}" "${C_FILES[@]}" || fail=1
else
  echo -e "${YELLOW}clang-tidy not available; skipping.${NC}"
fi

echo
if [ "$fail" -ne 0 ]; then
  echo -e "${RED}Linting completed with issues. See output above.${NC}"
else
  echo -e "${GREEN}All lint checks passed.${NC}"
fi

exit "$fail"
