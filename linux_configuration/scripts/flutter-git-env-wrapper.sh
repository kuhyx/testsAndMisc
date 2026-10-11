#!/bin/bash

# Strip the git-hook environment, then hand off to the real SDK binary.
# Linked into ~/.local/bin by linux_configuration/fixes/fix_flutter_git_env.sh
# -- see that script for why this exists. Invoked through a symlink named
# after the tool it fronts (flutter, dart).

set -euo pipefail

tool="$(basename "$0")"
real="/usr/bin/${tool}"

[[ -x $real ]] || {
	echo "flutter-git-env: $real is missing or not executable" >&2
	exit 127
}

# Drop our own directory so a PATH lookup inside the real tool cannot find
# this wrapper again. The Flutter entry point does exactly such a lookup.
clean_path=""
IFS=':' read -r -a path_parts <<<"$PATH"
for part in "${path_parts[@]}"; do
	[[ $part == "$HOME/.local/bin" ]] && continue
	clean_path="${clean_path:+$clean_path:}$part"
done

# GIT_DIR is the one that actually bites; the rest are exported by git in the
# same breath and would mislead the SDK the same way.
exec env \
	-u GIT_DIR \
	-u GIT_WORK_TREE \
	-u GIT_INDEX_FILE \
	-u GIT_COMMON_DIR \
	-u GIT_OBJECT_DIRECTORY \
	-u GIT_ALTERNATE_OBJECT_DIRECTORIES \
	-u GIT_NAMESPACE \
	-u GIT_PREFIX \
	PATH="$clean_path" \
	"$real" "$@"
