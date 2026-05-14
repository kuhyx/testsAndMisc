#!/bin/bash
# Require a workflow contract artifact for larger code changes.

set -euo pipefail

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
  python - "$file_path" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))

required = [
    "title",
    "objective",
    "acceptance_criteria",
    "out_of_scope",
    "verifier",
]

missing = [field for field in required if field not in data]
if missing:
    raise SystemExit(f"{path}: missing required fields: {', '.join(missing)}")

if not isinstance(data["title"], str) or not data["title"].strip():
    raise SystemExit(f"{path}: title must be non-empty string")

if not isinstance(data["objective"], str) or not data["objective"].strip():
    raise SystemExit(f"{path}: objective must be non-empty string")

if not isinstance(data["verifier"], str) or not data["verifier"].strip():
    raise SystemExit(f"{path}: verifier must be non-empty string")

for field in ("acceptance_criteria", "out_of_scope"):
    value = data[field]
    if not isinstance(value, list) or not value:
        raise SystemExit(f"{path}: {field} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SystemExit(f"{path}: {field} items must be non-empty strings")

print(f"{path}: contract schema OK")
PY
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
