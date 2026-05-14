#!/usr/bin/env bash
# run_phone.sh — Visible entrypoint for the phone focus mode workflow.
#
# Quick reference:
#   ./scripts/run_all/run_phone.sh                  Everyday: backup + monitor + minor repair.
#                                                   Shows a warning if the phone was wiped.
#   ./scripts/run_all/run_phone.sh fresh-phone      Full recovery after a factory reset.
#   ./scripts/run_all/run_phone.sh doctor           Diagnose and repair security drift.
#   ./scripts/run_all/run_phone.sh backup           Incremental backup only.
#   ./scripts/run_all/run_phone.sh monitor          Health snapshot only.
#   ./scripts/run_all/run_phone.sh --help           Show full usage.
set -euo pipefail

_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_IMPL="${_REPO_ROOT}/phone_focus_mode/run_phone.sh"

if [[ ! -x "${_IMPL}" ]]; then
    printf 'ERROR: implementation script not found or not executable: %s\n' "${_IMPL}" >&2
    exit 1
fi

exec bash "${_IMPL}" "$@"
