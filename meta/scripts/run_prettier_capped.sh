#!/usr/bin/env bash
# Run prettier --check inside its own systemd-run scope so its memory
# budget is independent of the outer pre-push cgroup (which has already
# accumulated page-cache footprint from pytest/mypy/pylint/bandit).
#
# Falls back to a direct invocation when systemd-run is unavailable
# (CI / containers without systemd user instance).
set -euo pipefail

if [ $# -eq 0 ]; then
	exit 0
fi

# Cap Node heap on top of the cgroup limit for belt-and-braces safety.
export NODE_OPTIONS="${NODE_OPTIONS:-} --max-old-space-size=384"

# Measured peak RSS checking the 14 yaml/json/markdown files of a large commit
# is ~0.10 GiB, so 512M is ample. The cap must also stay small enough to be
# satisfiable inside a tighter outer scope: a request larger than the caller's
# budget gets this OOM-killed from the inside rather than merely throttled.
if command -v systemd-run >/dev/null 2>&1 &&
	systemctl --user is-active --quiet default.target 2>/dev/null ||
	command -v systemd-run >/dev/null 2>&1; then
	exec systemd-run --user --scope --quiet --collect \
		-p MemoryMax=512M \
		-p MemorySwapMax=0 \
		-- prettier --check "$@"
fi

exec prettier --check "$@"
