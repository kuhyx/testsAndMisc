#!/bin/bash
# Enforce evidence artifacts for commits that touch source code.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly EVIDENCE_GLOB='docs/superpowers/evidence/*.json'

has_code_changes() {
  git diff --cached --name-only --diff-filter=ACMR | grep -Eq '\.(py|sh|c|h|cpp|hpp|cc|go|rs|ts|tsx|js|jsx|dart)$'
}

find_staged_evidence_files() {
  git diff --cached --name-only --diff-filter=ACMR | grep -E '^docs/superpowers/evidence/.*\.json$' || true
}

validate_json_schema() {
  local file_path="$1"
  python "${SCRIPT_DIR}/validate_evidence.py" "$file_path"
}

main() {
  if ! has_code_changes; then
    echo "✓ No code changes detected; evidence artifact not required"
    exit 0
  fi

  local evidence_files
  evidence_files="$(find_staged_evidence_files)"

  if [[ -z "$evidence_files" ]]; then
    echo "❌ Code changes detected, but no staged evidence artifact found."
    echo "   Required: ${EVIDENCE_GLOB}"
    echo "   Tip: copy docs/superpowers/evidence/template.json and fill it in."
    exit 1
  fi

  local failed=0
  while IFS= read -r file_path; do
    [[ -z "$file_path" ]] && continue
    if ! validate_json_schema "$file_path"; then
      failed=1
    fi
  done <<< "$evidence_files"

  if [[ $failed -eq 1 ]]; then
    echo "❌ Evidence artifact validation failed"
    exit 1
  fi

  echo "✓ Evidence artifact checks passed"
}

main "$@"
