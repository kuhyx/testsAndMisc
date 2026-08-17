#!/bin/bash
# Prove a shell split moved every function verbatim.
#
# Extracts each top-level `name() {` block from the pre-split file at a git rev
# and from the post-split files, normalises both through `shfmt -mn`
# (minify: strips comments and indentation, keeps logic), and asserts the set
# of function bodies is identical. Formatting-blind, logic-sensitive.
#
# Usage: verify_shell_split.sh <rev> <old-path> <new-path>...

set -euo pipefail

readonly REV="$1"
readonly OLD_PATH="$2"
shift 2

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Write "<name>\t<shfmt-minified body hash>" for every top-level function.
extract_functions() {
    local src="$1" out="$2"
    awk '
        /^[a-zA-Z_][a-zA-Z0-9_]*\(\)[[:space:]]*\{/ {
            name = $0; sub(/\(\).*/, "", name); gsub(/[[:space:]]/, "", name)
            depth = 0; body = ""
            inside = 1
        }
        inside {
            body = body $0 "\n"
            depth += gsub(/\{/, "{")
            depth -= gsub(/\}/, "}")
            if (depth <= 0) {
                printf "%s\x01%s\x02", name, body
                inside = 0
            }
        }
    ' "$src" > "$TMP_DIR/raw"

    : > "$out"
    while IFS= read -r -d $'\x02' record; do
        [[ -z "$record" ]] && continue
        local fname="${record%%$'\x01'*}"
        local fbody="${record#*$'\x01'}"
        local norm
        norm="$(printf '%s' "$fbody" | shfmt -mn 2>/dev/null | sha256sum | cut -d' ' -f1)"
        printf '%s\t%s\n' "$fname" "$norm" >> "$out"
    done < "$TMP_DIR/raw"
    sort -o "$out" "$out"
}

git show "$REV:$OLD_PATH" > "$TMP_DIR/before.sh"
extract_functions "$TMP_DIR/before.sh" "$TMP_DIR/before.txt"

: > "$TMP_DIR/after_all.sh"
for f in "$@"; do cat "$f" >> "$TMP_DIR/after_all.sh"; printf '\n' >> "$TMP_DIR/after_all.sh"; done
extract_functions "$TMP_DIR/after_all.sh" "$TMP_DIR/after.txt"

before_count="$(wc -l < "$TMP_DIR/before.txt")"
if diff -u "$TMP_DIR/before.txt" "$TMP_DIR/after.txt" > "$TMP_DIR/diff.txt"; then
    echo "IDENTICAL: all ${before_count} top-level functions moved verbatim"
    exit 0
fi
echo "DIFFERENCE FOUND (- before / + after):"
grep -E '^[+-][a-zA-Z_]' "$TMP_DIR/diff.txt" || cat "$TMP_DIR/diff.txt"
exit 1
