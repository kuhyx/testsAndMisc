#!/bin/bash
# Enforce evidence artifacts for commits that touch source code.

set -euo pipefail

readonly EVIDENCE_GLOB='docs/superpowers/evidence/*.json'

has_code_changes() {
  git diff --cached --name-only --diff-filter=ACMR | grep -Eq '\.(py|sh|c|h|cpp|hpp|cc|go|rs|ts|tsx|js|jsx|dart)$'
}

find_staged_evidence_files() {
  git diff --cached --name-only --diff-filter=ACMR | grep -E '^docs/superpowers/evidence/.*\.json$' || true
}

validate_json_schema() {
  local file_path="$1"

  python - "$file_path" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:  # pragma: no cover - hook error path
    raise SystemExit(f"{path}: invalid JSON ({exc})")

required = [
    "intent",
    "scope",
    "changes",
    "verification",
    "risks",
    "rollback",
]

missing = [key for key in required if key not in data]
if missing:
    raise SystemExit(f"{path}: missing required keys: {', '.join(missing)}")

if not isinstance(data["intent"], str) or not data["intent"].strip():
    raise SystemExit(f"{path}: intent must be a non-empty string")

for key in ("scope", "changes", "risks", "rollback"):
    value = data[key]
    if not isinstance(value, list) or not value:
        raise SystemExit(f"{path}: {key} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SystemExit(f"{path}: {key} entries must be non-empty strings")

verification = data["verification"]
if not isinstance(verification, list) or not verification:
    raise SystemExit(f"{path}: verification must be a non-empty list")

required_verification_fields = {"command", "result", "evidence"}
for index, item in enumerate(verification):
    if not isinstance(item, dict):
        raise SystemExit(f"{path}: verification[{index}] must be an object")
    missing_fields = required_verification_fields - item.keys()
    if missing_fields:
        missing_joined = ", ".join(sorted(missing_fields))
        raise SystemExit(
            f"{path}: verification[{index}] missing fields: {missing_joined}"
        )
    for field in required_verification_fields:
        value = item[field]
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(
                f"{path}: verification[{index}].{field} must be a non-empty string"
            )

content_lower = path.read_text(encoding="utf-8").lower()
for phrase in ("should work", "probably fine", "seems right"):
    if phrase in content_lower:
        raise SystemExit(
            f"{path}: contains rationalization phrase '{phrase}', replace with evidence"
        )

print(f"{path}: schema OK")
PY
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
