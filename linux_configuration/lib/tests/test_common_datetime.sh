#!/usr/bin/env bash
# Covers the pure helpers in common_datetime.sh: validate_resolution,
# generate_output_filename, has_cmd, ask_yes_no, mount_layers_count, the
# zero-fork time readers, and the two predicates built on them.
#
# NO ASSERTION HERE DEPENDS ON THE WALL CLOCK. This suite runs in
# shell-tests.yml and again on every pre-push via ci-mirror, so
# `is_hour_in_range 9 17` would pass during the working day and fail at
# night — a flake that blocks a push for reasons unrelated to the change.
# The predicates are tested by shimming get_hour/get_day_of_week to fixed
# values; the real readers are asserted on SHAPE only.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=mtk_harness.sh
source "$HERE/mtk_harness.sh"

_t_sandbox
# shellcheck source=../common_datetime.sh
source "$HERE/../common_datetime.sh"

# --- validate_resolution ---------------------------------------------------

_t_rc 0 "a WIDTHxHEIGHT resolution is valid" validate_resolution "1920x1080"
_t_rc 0 "a single-digit resolution is valid" validate_resolution "1x1"
_t_rc 1 "a capital X is not the separator" validate_resolution "1920X1080"
_t_rc 1 "a missing dimension is invalid" validate_resolution "1920x"
_t_rc 1 "a bare number is not a resolution" validate_resolution "1920"
_t_rc 1 "trailing text is rejected" validate_resolution "1920x1080p"
_t_rc 1 "an empty string is not a resolution" validate_resolution ""
# Anchoring matters: an unanchored regex would accept this and the caller
# would go on to pass it to a scaler.
_t_rc 1 "an embedded match is rejected, not extracted" validate_resolution "a1920x1080b"

# --- generate_output_filename ----------------------------------------------

_t_is "./photo_resized.jpg" "$(generate_output_filename "photo.jpg" "_resized")" \
	"suffix goes before the extension, not after"
_t_is "/tmp/photo_small.png" "$(generate_output_filename "/tmp/photo.png" "_small")" \
	"the directory is preserved"
# A file with no extension: the caller's fallback is used, defaulting to jpg.
_t_is "./photo_x.jpg" "$(generate_output_filename "photo" "_x")" \
	"an extensionless input defaults to jpg"
_t_is "./photo_x.png" "$(generate_output_filename "photo" "_x" "png")" \
	"an explicit fallback extension is honoured"
# Only the LAST dot separates the extension.
_t_is "./archive.tar_x.gz" "$(generate_output_filename "archive.tar.gz" "_x")" \
	"only the final extension is split off"
_t_is "/a/b/c_out.jpg" "$(generate_output_filename "/a/b/c.jpg" "_out")" \
	"a nested path is preserved"

# --- has_cmd ---------------------------------------------------------------

_t_rc 0 "has_cmd finds a command that exists" has_cmd bash
_t_rc 1 "has_cmd rejects a command that does not" has_cmd definitely-not-a-real-binary-xyz

# --- ask_yes_no ------------------------------------------------------------

# Reads stdin, so it is drivable without a tty.
_t_yn() {
	printf '%s\n' "$1" | ask_yes_no "prompt?" >/dev/null 2>&1
}
_t_rc 0 "'y' is yes" _t_yn "y"
_t_rc 0 "'Y' is yes" _t_yn "Y"
_t_rc 0 "'yes' is yes" _t_yn "yes"
_t_rc 1 "'n' is no" _t_yn "n"
# Default-no is the safety property: an empty answer must never mean yes.
_t_rc 1 "an empty answer defaults to no" _t_yn ""
_t_rc 1 "unrecognised input is no, not a reprompt" _t_yn "maybe"

# --- mount_layers_count ----------------------------------------------------

# A path with no bind mount over it has zero layers. `/` always appears in
# mountinfo, so it is the one value that is stable on any host.
_t_is "0" "$(mount_layers_count "/definitely/not/a/mount/point")" \
	"an unmounted path counts zero layers"
_t_rc 0 "a mounted path counts without failing" mount_layers_count "/"
root_layers="$(mount_layers_count "/")"
_t_rc 0 "the root mount count is numeric" grep -qE '^[0-9]+$' <<<"$root_layers"

# --- time readers: shape, never value --------------------------------------

_t_rc 0 "get_timestamp returns digits" grep -qE '^[0-9]+$' <<<"$(get_timestamp)"
_t_rc 0 "get_date is YYYY-MM-DD" grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' <<<"$(get_date)"
_t_rc 0 "get_time is HH:MM:SS" grep -qE '^[0-9]{2}:[0-9]{2}:[0-9]{2}$' <<<"$(get_time)"
_t_rc 0 "get_datetime joins both" \
	grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' <<<"$(get_datetime)"
_t_rc 0 "get_day_of_week is 1-7" grep -qE '^[1-7]$' <<<"$(get_day_of_week)"
_t_rc 0 "get_day_name is alphabetic" grep -qE '^[A-Za-z]+$' <<<"$(get_day_name)"
_t_rc 0 "get_hour is 00-23" grep -qE '^([01][0-9]|2[0-3])$' <<<"$(get_hour)"
_t_rc 0 "get_minute is 00-59" grep -qE '^[0-5][0-9]$' <<<"$(get_minute)"
_t_rc 0 "get_second is 00-60" grep -qE '^([0-5][0-9]|60)$' <<<"$(get_second)"
_t_rc 0 "get_uptime_seconds is a whole number" grep -qE '^[0-9]+$' <<<"$(get_uptime_seconds)"
_t_rc 0 "get_boot_datetime is a datetime" \
	grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' <<<"$(get_boot_datetime)"
_t_rc 0 "get_boot_date is a date" grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' <<<"$(get_boot_date)"
_t_rc 0 "get_boot_hour is 00-23" grep -qE '^([01][0-9]|2[0-3])$' <<<"$(get_boot_hour)"

# Boot time is in the past, and by the same margin /proc/uptime reports. This
# is a relation between two readings, so it holds at any wall-clock time.
now_ts="$(get_timestamp)"
up_s="$(get_uptime_seconds)"
_t_rc 0 "boot precedes now by the uptime" test "$((now_ts - up_s))" -le "$now_ts"

# --- predicates, with the clock shimmed ------------------------------------

# is_hour_in_range is half-open: start inclusive, end exclusive. Overriding
# get_hour is what makes these assertions true at 3am and at 3pm alike.
get_hour() { printf '%s' "$T_FAKE_HOUR"; }

T_FAKE_HOUR=06
_t_rc 0 "06 is inside 5..8" is_hour_in_range 5 8
T_FAKE_HOUR=05
_t_rc 0 "the start hour is inside the range" is_hour_in_range 5 8
T_FAKE_HOUR=08
_t_rc 1 "the end hour is outside the range" is_hour_in_range 5 8
T_FAKE_HOUR=04
_t_rc 1 "an hour before the range is outside" is_hour_in_range 5 8
T_FAKE_HOUR=23
_t_rc 1 "an hour after the range is outside" is_hour_in_range 5 8
# A leading zero must not be read as octal — 08 and 09 are the classic trap,
# and the implementation uses 10#$ precisely to avoid it.
#
# Assert on STDERR, not only on the status. Dropping the 10# prefix makes
# bash abort with "value too great for base", which is a non-zero exit that
# an exit-status-only check reads as an ordinary "hour is out of range" —
# so the mutation survives. Mutation-tested: removing 10#$ fails this.
_t_hour_err() {
	T_FAKE_HOUR="$1"
	# Capture stderr ONLY: stdout is discarded first, then stderr is pointed at
	# it. Braces make the order explicit rather than relying on a bare
	# `2>&1 >/dev/null`, which reads backwards.
	{ is_hour_in_range "$2" "$3" >/dev/null; } 2>&1 || true
}
for _t_h in 08 09; do
	_t_is "" "$(_t_hour_err "$_t_h" 9 17)" "${_t_h} raises no arithmetic error"
done
T_FAKE_HOUR=09
_t_rc 0 "09 is parsed as decimal nine, not invalid octal" is_hour_in_range 9 17
T_FAKE_HOUR=08
_t_rc 1 "08 is decimal eight, so it is below the 9..17 range" is_hour_in_range 9 17
T_FAKE_HOUR=00
_t_rc 0 "midnight is parsed as zero" is_hour_in_range 0 1
_t_is "" "$(_t_hour_err 00 0 1)" "00 raises no arithmetic error"

# is_day_of_week takes a list and matches any of them.
get_day_of_week() { printf '%s' "$T_FAKE_DOW"; }

T_FAKE_DOW=1
_t_rc 0 "Monday matches a list containing it" is_day_of_week 1 5 6 7
T_FAKE_DOW=3
_t_rc 1 "Wednesday does not match that list" is_day_of_week 1 5 6 7
T_FAKE_DOW=7
_t_rc 0 "Sunday matches at the end of the list" is_day_of_week 1 5 6 7
T_FAKE_DOW=4
_t_rc 0 "a single-element list matches" is_day_of_week 4
T_FAKE_DOW=4
_t_rc 1 "an empty list matches nothing" is_day_of_week

_t_done "test_common_datetime.sh"
