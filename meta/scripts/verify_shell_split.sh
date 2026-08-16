#!/usr/bin/env bash
# Verify a shell script split into lib/*.sh: syntax, lint, libs reachable.
#
# Usage: verify_shell_split.sh <script> <function> [function...]
#
# The stubbed run is the part that matters. bash -n and shellcheck both pass on
# a script whose `source` line resolves to nothing, so this mirrors the repo
# tree into a temp dir, replaces the final `main "$@"` with a probe that only
# checks the named functions are defined, and runs that. Nothing else executes,
# which is what makes it safe for installers and enforcement scripts.
#
# Across 18 splits it caught five bugs no static check did: SCRIPT_DIR computed
# from $0, a redeclared readonly SCRIPT_DIR, a source line displaced by a second
# split, and two libs sourcing a sibling. See docs/shell-split-recipes.md.
#
# Only works when the script ends in `main "$@"` or `main`. Scripts that run
# top-level statements need the by-hand checks in that doc instead.

set -euo pipefail

script="$1"
shift
required_funcs=("$@")

dir="$(dirname "$script")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "--- $(basename "$script")"
for lib in "$dir"/lib/*.sh; do
	[[ -e $lib ]] || continue
	# bash -n first: a split landing inside a heredoc produces a file the
	# linter only warns about (SC1094 in the caller) but which bash rejects.
	bash -n "$lib" || {
		echo "  $lib does not parse -- the split probably cut inside a heredoc" >&2
		exit 1
	}
	shellcheck "$lib" || exit 1
done
bash -n "$script" || exit 1
shellcheck -x "$script" || exit 1

dollar='$'
grep -q "source \"${dollar}SCRIPT_DIR/" "$script" || {
	echo "no source line found" >&2
	exit 1
}

# Mirror the repo tree so repo-relative sources (../../lib/common.sh) resolve.
repo="$(git -C "$dir" rev-parse --show-toplevel)"
rel="$(realpath --relative-to="$repo" "$script")"
mkdir -p "$tmp/$(dirname "$rel")"
cp -r "$repo/linux_configuration/scripts/lib" "$tmp/linux_configuration/scripts/" 2>/dev/null || true
cp "$script" "$tmp/$rel"
[[ -d "$dir/lib" ]] && cp -r "$dir/lib" "$tmp/$(dirname "$rel")/"
entry="$tmp/$rel"

probe='for f in'
for f in "${required_funcs[@]}"; do probe+=" $f"; done
probe+="; do declare -F \"${dollar}f\" >/dev/null || { echo \"MISSING: ${dollar}f\"; exit 1; }; done"
probe+='; echo "  libs sourced, functions defined"'

python3 - "$entry" "$probe" <<'PY'
import sys
from pathlib import Path
p, probe = Path(sys.argv[1]), sys.argv[2]
out = [probe + "\n" if l.rstrip() in ('main "$@"', "main") else l
       for l in p.read_text().splitlines(keepends=True)]
p.write_text("".join(out))
PY
bash "$entry"
