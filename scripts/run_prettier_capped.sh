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
export NODE_OPTIONS="${NODE_OPTIONS:-} --max-old-space-size=768"

if command -v systemd-run >/dev/null 2>&1 \
        && systemctl --user is-active --quiet default.target 2>/dev/null \
        || command -v systemd-run >/dev/null 2>&1; then
    exec systemd-run --user --scope --quiet --collect \
        -p MemoryMax=1G \
        -p MemorySwapMax=0 \
        -- prettier --check "$@"
fi

exec prettier --check "$@"
