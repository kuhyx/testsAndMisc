#!/bin/bash
# Enforce append-only semantics for session log artifacts.

set -euo pipefail

is_session_log() {
  local file_path="$1"
  [[ "$file_path" =~ ^docs/superpowers/sessions/.*\.(jsonl|log|txt)$ ]]
}

has_deleted_lines() {
  local file_path="$1"

  git diff --cached --unified=0 -- "$file_path" \
    | grep -E '^-' \
    | grep -Ev '^--- '
}

main() {
  local staged_files
  staged_files="$(git diff --cached --name-only --diff-filter=ACMR)"

  local checked=0
  local failures=0

  while IFS= read -r file_path; do
    [[ -z "$file_path" ]] && continue
    if ! is_session_log "$file_path"; then
      continue
    fi

    checked=$((checked + 1))

    if has_deleted_lines "$file_path" >/dev/null; then
      echo "❌ ${file_path}: append-only violation (deletions detected)"
      echo "   Use a new appended line instead of modifying historical entries."
      failures=$((failures + 1))
    fi
  done <<< "$staged_files"

  if (( checked == 0 )); then
    echo "✓ No session logs staged"
    exit 0
  fi

  if (( failures > 0 )); then
    echo "❌ Append-only session checks failed"
    exit 1
  fi

  echo "✓ Append-only session checks passed"
}

main "$@"
