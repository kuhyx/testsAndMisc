#!/usr/bin/env bash
# run_phone.sh — Visible entrypoint for the phone focus mode workflow.
#
# The implementation lives in the extracted phone-focus-mode repo
# (~/src/phone-focus-mode); this wrapper only resolves and execs it.
#
# Quick reference:
#   ./meta/scripts/run_all/run_phone.sh              Everyday: backup + monitor + minor repair.
#                                                    Shows a warning if the phone was wiped.
#   ./meta/scripts/run_all/run_phone.sh fresh-phone  Full recovery after a factory reset.
#   ./meta/scripts/run_all/run_phone.sh doctor       Diagnose and repair security drift.
#   ./meta/scripts/run_all/run_phone.sh backup       Incremental backup only.
#   ./meta/scripts/run_all/run_phone.sh monitor      Health snapshot only.
#   ./meta/scripts/run_all/run_phone.sh --help       Show full usage.
set -euo pipefail

_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=../../../linux_configuration/lib/extracted_repos.sh
source "${_REPO_ROOT}/linux_configuration/lib/extracted_repos.sh"

_PFM_DIR="$(require_extracted_repo phone-focus-mode "run_phone.sh")"
_IMPL="${_PFM_DIR}/run_phone.sh"

if [[ ! -f "${_IMPL}" ]]; then
	printf 'ERROR: implementation script not found: %s\n' "${_IMPL}" >&2
	exit 1
fi

exec bash "${_IMPL}" "$@"
