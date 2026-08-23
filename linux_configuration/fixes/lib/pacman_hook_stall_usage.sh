#!/bin/bash
# Usage/help text for diagnose_pacman_hook_stall.sh.
# Sourced, not executed; inherits the caller's strict mode and globals.

usage() {
	cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Drives repeated pacman transactions and captures diagnostics when one stalls
at its first PreTransaction hook.

Options:
  -n, --runs N          Number of transactions to drive (default: $RUNS)
  -p, --package NAME    Package to reinstall from cache (default: $PACKAGE)
  -t, --timeout S       Seconds of pacman.log silence => stall (default: $STALL_TIMEOUT)
      --hard-timeout S  Seconds before killing a stalled run (default: $HARD_TIMEOUT)
      --with-load       Also apply memory pressure (the hypothesis under test).
                        Run this with nothing else going - it deliberately
                        breaks the one-heavy-job-at-a-time rule.
      --watch           Passive mode: drive nothing, just watch pacman.log and
                        dump diagnostics when someone else's transaction stalls
                        on a hook. Intended to run as a systemd service.
  -o, --out DIR         Where to write stall dumps (default: $OUT_DIR)
  -h, --help            Show this help

Exit status: 0 if the loop completed (with or without stalls), non-zero on a
setup failure. The stall count is reported in the summary.
EOF
	exit 0
}
