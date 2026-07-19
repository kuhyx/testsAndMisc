#!/usr/bin/env bats
# Unit tests for the pure helpers in scripts/diagnostics/.
#
# Requires: bats (extra/bats). Run with:
#   bats linux_configuration/tests/test_network_diagnostics.bats
#
# Only the arithmetic and classification logic is covered. The sampling loops
# are deliberately untested: they read live NIC counters and sleep in real
# time, so testing them would assert against mocks rather than behaviour. The
# helpers below are where every off-by-one actually lives.

setup() {
    REPO_DIR="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/.." && pwd)"
    DIAG_DIR="$REPO_DIR/scripts/diagnostics"
    # Both scripts guard main() behind a BASH_SOURCE check, so sourcing them
    # loads the helpers without starting a measurement run.
    # shellcheck source=/dev/null
    source "$DIAG_DIR/steam-download-duty.sh"
    # shellcheck source=/dev/null
    source "$DIAG_DIR/line-speed-probe.sh"
}

# --- bytes_to_mbps ---------------------------------------------------------

@test "bytes_to_mbps: 125MB in 1s is exactly 1000 Mbps" {
    [ "$(bytes_to_mbps 125000000 1)" -eq 1000 ]
}

@test "bytes_to_mbps: averages over a multi-second window" {
    [ "$(bytes_to_mbps 125000000 10)" -eq 100 ]
}

@test "bytes_to_mbps: no traffic yields zero" {
    [ "$(bytes_to_mbps 0 5)" -eq 0 ]
}

@test "bytes_to_mbps: a zero-second window returns 0 instead of dividing by zero" {
    [ "$(bytes_to_mbps 125000000 0)" -eq 0 ]
}

# --- duty_pct --------------------------------------------------------------

@test "duty_pct: reproduces the measured Steam run (22s of 60)" {
    [ "$(duty_pct 22 60)" -eq 36 ]
}

@test "duty_pct: fully active is 100" {
    [ "$(duty_pct 60 60)" -eq 100 ]
}

@test "duty_pct: fully stalled is 0" {
    [ "$(duty_pct 0 60)" -eq 0 ]
}

@test "duty_pct: zero total returns 0 instead of dividing by zero" {
    [ "$(duty_pct 5 0)" -eq 0 ]
}

# --- mean_of ---------------------------------------------------------------

@test "mean_of: averages several samples" {
    [ "$(mean_of 100 200 300)" -eq 200 ]
}

@test "mean_of: no samples yields zero" {
    [ "$(mean_of)" -eq 0 ]
}

@test "mean_of: a single sample is itself" {
    [ "$(mean_of 7)" -eq 7 ]
}

@test "mean_of: integer division truncates rather than rounding" {
    [ "$(mean_of 2 3)" -eq 2 ]
}

# --- classify --------------------------------------------------------------

@test "classify: high duty means the link is the ceiling (depotdownloader run)" {
    [ "$(classify 97 712)" = "LINK_LIMITED" ]
}

@test "classify: duty boundary at 80 counts as link-limited" {
    [ "$(classify 80 50)" = "LINK_LIMITED" ]
}

@test "classify: low duty with fast bursts is the Steam-client signature" {
    [ "$(classify 36 474)" = "CLIENT_IDLE" ]
}

@test "classify: burst boundary at 400 counts as client-idle" {
    [ "$(classify 79 400)" = "CLIENT_IDLE" ]
}

@test "classify: slow bursts and low duty is neither diagnosis" {
    [ "$(classify 30 399)" = "MIXED" ]
}

# --- sustained_of ----------------------------------------------------------

@test "sustained_of: discards the first half (slow start and burst allowance)" {
    [ "$(sustained_of 500 500 100 100)" -eq 100 ]
}

@test "sustained_of: odd counts keep 2 of 3, dropping only the first" {
    [ "$(sustained_of 10 20 30)" -eq 25 ]
}

@test "sustained_of: a single sample is itself" {
    [ "$(sustained_of 5)" -eq 5 ]
}

@test "sustained_of: no samples yields zero" {
    [ "$(sustained_of)" -eq 0 ]
}

# --- max_of ----------------------------------------------------------------

@test "max_of: finds the peak" {
    [ "$(max_of 100 986 400)" -eq 986 ]
}

@test "max_of: no samples yields zero" {
    [ "$(max_of)" -eq 0 ]
}

@test "max_of: a single sample is itself" {
    [ "$(max_of 42)" -eq 42 ]
}

# --- verdict_for -----------------------------------------------------------

@test "verdict_for: the depotdownloader result reads as a healthy line" {
    [ "$(verdict_for 696)" = "LINE_OK" ]
}

@test "verdict_for: 600 is the healthy boundary" {
    [ "$(verdict_for 600)" = "LINE_OK" ]
}

@test "verdict_for: just below the healthy boundary is partial" {
    [ "$(verdict_for 599)" = "PARTIAL" ]
}

@test "verdict_for: 350 is the partial boundary" {
    [ "$(verdict_for 350)" = "PARTIAL" ]
}

@test "verdict_for: just below the partial boundary is slow" {
    [ "$(verdict_for 349)" = "SLOW" ]
}

@test "verdict_for: the measured Steam effective rate reads as slow" {
    [ "$(verdict_for 170)" = "SLOW" ]
}
