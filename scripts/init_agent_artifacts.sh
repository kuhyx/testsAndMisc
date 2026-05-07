#!/bin/bash
# Bootstrap superpowers artifacts (contract + evidence) for current branch/task.

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
TASK_INPUT=""
FORCE=0

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [--task "Task title"] [--force]

Creates starter artifacts:
  - docs/superpowers/contracts/<slug>.json
  - docs/superpowers/evidence/<slug>.json
  - docs/superpowers/sessions/<slug>.jsonl

Defaults:
  - slug is derived from --task if provided; otherwise from current git branch
  - existing files are not overwritten unless --force is set
EOF
}

slugify() {
    local input="$1"
    local normalized

    normalized="$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]')"
    normalized="$(printf '%s' "$normalized" | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"

    if [[ -z "$normalized" ]]; then
        printf 'task'
    else
        printf '%s' "$normalized"
    fi
}

get_branch_name() {
    local branch
    branch="$(git branch --show-current 2>/dev/null || true)"
    if [[ -z "$branch" ]]; then
        printf 'task'
    else
        printf '%s' "$branch"
    fi
}

write_file() {
    local path="$1"
    local content="$2"

    if [[ -f "$path" && "$FORCE" -ne 1 ]]; then
        echo "ℹ️  Skipping existing file: $path"
        return 0
    fi

    printf '%s' "$content" > "$path"
    echo "✅ Wrote: $path"
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --task)
                TASK_INPUT="${2:-}"
                if [[ -z "$TASK_INPUT" ]]; then
                    echo "Error: --task requires a value" >&2
                    exit 1
                fi
                shift 2
                ;;
            --force)
                FORCE=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown argument: $1" >&2
                usage
                exit 1
                ;;
        esac
    done

    local base_input
    if [[ -n "$TASK_INPUT" ]]; then
        base_input="$TASK_INPUT"
    else
        base_input="$(get_branch_name)"
    fi

    local slug
    slug="$(slugify "$base_input")"

    local contracts_dir="docs/superpowers/contracts"
    local evidence_dir="docs/superpowers/evidence"
    local sessions_dir="docs/superpowers/sessions"

    mkdir -p "$contracts_dir" "$evidence_dir" "$sessions_dir"

    local contract_path="$contracts_dir/${slug}.json"
    local evidence_path="$evidence_dir/${slug}.json"
    local session_path="$sessions_dir/${slug}.jsonl"

    local contract_content
    contract_content=$(cat <<EOF
{
  "title": "${base_input}",
  "objective": "Define what success looks like for ${base_input}.",
  "acceptance_criteria": [
    "Criterion 1",
    "Criterion 2"
  ],
  "out_of_scope": [
    "Explicitly excluded work item"
  ],
  "verifier": "pre-commit + task-specific tests"
}
EOF
)

    local evidence_content
    evidence_content=$(cat <<EOF
{
  "intent": "Describe the expected user-visible outcome for ${base_input}.",
  "scope": [
    "Impacted modules/files",
    "Constraints/non-goals"
  ],
  "changes": [
    "Implementation summary item 1",
    "Implementation summary item 2"
  ],
  "verification": [
    {
      "command": "pre-commit run --files <changed-files>",
      "result": "pass",
      "evidence": "Paste command output summary"
    }
  ],
  "risks": [
    "Risk 1",
    "Risk 2"
  ],
  "rollback": [
    "Revert commit(s)",
    "Re-run validation checks"
  ]
}
EOF
)

    local now
    now="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    local session_content
    session_content=$(cat <<EOF
{"timestamp":"${now}","event":"init","task":"${base_input}","note":"session initialized"}
EOF
)

    write_file "$contract_path" "$contract_content"
    write_file "$evidence_path" "$evidence_content"
    write_file "$session_path" "$session_content"

    echo ""
    echo "Artifacts ready for task slug: $slug"
}

main "$@"
