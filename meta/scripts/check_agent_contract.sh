#!/bin/bash
# Require a workflow contract artifact for larger code changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly CONTRACT_GLOB='docs/superpowers/contracts/*.json'
readonly MULTI_FILE_THRESHOLD=4

list_staged_code_files() {
  git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(py|sh|c|h|cpp|hpp|cc|go|rs|ts|tsx|js|jsx|dart)$' || true
}

list_staged_contract_files() {
  git diff --cached --name-only --diff-filter=ACMR | grep -E '^docs/superpowers/contracts/.*\.json$' || true
}

validate_contract_file() {
  local file_path="$1"
  python "${SCRIPT_DIR}/validate_contract.py" "$file_path"
}

main() {
  local code_files
  code_files="$(list_staged_code_files)"

  if [[ -z "$code_files" ]]; then
    echo "✓ No code files staged; workflow contract not required"
    exit 0
  fi

  local code_file_count
  code_file_count=$(printf '%s\n' "$code_files" | sed '/^$/d' | wc -l | tr -d ' ')

  if (( code_file_count < MULTI_FILE_THRESHOLD )); then
    echo "✓ ${code_file_count} code file(s) staged; no multi-file contract required"
    exit 0
  fi

  local contract_files
  contract_files="$(list_staged_contract_files)"

  if [[ -z "$contract_files" ]]; then
    echo "❌ ${code_file_count} code files staged but no workflow contract artifact found."
    echo "   Required: ${CONTRACT_GLOB}"
    echo "   Tip: start from docs/superpowers/contracts/template.json."
    exit 1
  fi

  local failed=0
  while IFS= read -r file_path; do
    [[ -z "$file_path" ]] && continue
    if ! validate_contract_file "$file_path"; then
      failed=1
    fi
  done <<< "$contract_files"

  if [[ $failed -eq 1 ]]; then
    echo "❌ Workflow contract validation failed"
    exit 1
  fi

  echo "✓ Multi-file workflow contract checks passed"
}

main "$@"
