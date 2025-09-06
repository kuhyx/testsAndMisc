#!/bin/bash
# Generic pre-exec wrapper for browsers: ensures /etc/hosts is (re)installed
# before launching the actual browser binary.

set -euo pipefail

HOSTS_INSTALL_SCRIPT="__HOSTS_INSTALL_SCRIPT__"

prog_name="$(basename "$0")"
real_bin="/usr/bin/${prog_name}"

# Best-effort: install hosts file quietly; don't block browser startup
if command -v sudo >/dev/null 2>&1; then
  sudo -n "$HOSTS_INSTALL_SCRIPT" >/dev/null 2>&1 || true
else
  "$HOSTS_INSTALL_SCRIPT" >/dev/null 2>&1 || true
fi

exec "$real_bin" "$@"
