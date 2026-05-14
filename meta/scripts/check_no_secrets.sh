#!/bin/bash
# Pre-commit hook: check that no staged file contains a secret pattern.
# Patterns are read from .secret-patterns (one regex per line, # = comment).
set -euo pipefail

PATTERNS_FILE=".secret-patterns"

if [ ! -f "$PATTERNS_FILE" ]; then
    # Try finding it relative to the git root
    GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$GIT_ROOT" ] && [ -f "$GIT_ROOT/$PATTERNS_FILE" ]; then
        PATTERNS_FILE="$GIT_ROOT/$PATTERNS_FILE"
    else
        echo "Warning: $PATTERNS_FILE not found, skipping secret check."
        exit 0
    fi
fi

found=0
# Build a temp file with non-comment, non-empty patterns
TMPPATTERNS="$(mktemp)"
trap 'rm -f "$TMPPATTERNS"' EXIT
grep -v '^\s*#' "$PATTERNS_FILE" | grep -v '^\s*$' > "$TMPPATTERNS"

if [ ! -s "$TMPPATTERNS" ]; then
    echo "No secret patterns defined in $PATTERNS_FILE, skipping."
    exit 0
fi

for file in "$@"; do
    # Skip binary files
    if file --brief --mime-encoding "$file" 2>/dev/null | grep -q binary; then
        continue
    fi
    if grep -En -f "$TMPPATTERNS" "$file" 2>/dev/null; then
        echo "^^^ SECRET PATTERN found in: $file"
        found=1
    fi
done

if [ "$found" -eq 1 ]; then
    echo ""
    echo "ERROR: Committed files contain secret patterns from $PATTERNS_FILE"
    echo "Either remove the sensitive data or update $PATTERNS_FILE if this is a false positive."
    exit 1
fi
