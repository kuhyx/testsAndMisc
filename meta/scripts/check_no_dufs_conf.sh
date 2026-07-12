#!/bin/bash
# ============================================================================
# Pre-commit guard: never allow the dufs cloud secret config to be committed.
#
# .dufs_cloud.conf holds the plaintext dufs web password. It is gitignored, but
# `git add -f` can bypass gitignore — this hook is the backstop. It inspects the
# staged set directly (not just the files pre-commit passes) so it catches a
# force-added file regardless of any `files:` filter.
# ============================================================================
set -euo pipefail

# Added/Copied/Modified staged paths.
staged="$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)"

bad="$(printf '%s\n' "$staged" | grep -E '(^|/)\.dufs_cloud\.conf$' || true)"

if [ -n "$bad" ]; then
    echo "ERROR: refusing to commit the dufs secret config (plaintext password):" >&2
    printf '  %s\n' "$bad" >&2
    echo "" >&2
    echo "This file must stay local only. Unstage it: git rm --cached <file>" >&2
    exit 1
fi

exit 0
