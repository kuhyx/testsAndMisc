#!/bin/bash
# i3blocks efficiency: the claude_usage block's output and fork count.
# Sourced by test_i3blocks_efficiency.sh; inherits its strict mode and its
# helpers (fail, assert_equals, assert_le, epoch_utc, count_execs) plus the
# BIN_DIR / TMP_DIR / CONFIG_FILE / I3BLOCKS_DIR paths it sets up.

i3_tests_claude_usage() {
	printf 'Checking Claude usage block behavior and fork count...\n'
	# claude_usage.sh parses its cache with jq and degrades to "no data" when jq is
	# missing. That is the right runtime behaviour, but it would make every
	# assertion below fail with a misleading message about percentages, so name the
	# real cause instead of letting a missing tool look like a logic bug.
	# Probe by running jq, not with `command -v`: a jq that exists but cannot
	# execute produces exactly the same "no data" output as one that is absent.
	printf '{}' | jq -e . >/dev/null 2>&1 \
	  || fail 'a working jq is required for the claude_usage tests (pacman -S jq)'
	CLAUDE_STATE_DIR="$TMP_DIR/limit-state"
	mkdir -p "$CLAUDE_STATE_DIR"
	claude_now=1786366861

	write_claude_state() {
	  printf '{"five_hour_pct":%s,"five_hour_resets_at":%s,"seven_day_pct":%s,"seven_day_resets_at":%s,"updated_at":%s}\n' \
	    "$1" "$2" "$3" "$4" "$5" >"$CLAUDE_STATE_DIR/state.json"
	}

	run_claude_usage() {
	  LIMIT_STATE_DIR="$CLAUDE_STATE_DIR" NOW_EPOCH="$claude_now" \
	    bash "$I3BLOCKS_DIR/claude_usage.sh"
	}

	# Percentages arrive as floats (e.g. 55.00000000000001) and must be truncated.
	write_claude_state 34 "$((claude_now + 3600))" 55.00000000000001 "$((claude_now + 99999))" "$claude_now"
	claude_output=$(run_claude_usage)
	assert_equals '🤖 5h 34% · 7d 55%' "$(printf '%s\n' "$claude_output" | sed -n '1p')" \
	  'claude usage should show both windows as whole percentages'
	assert_equals '#50FA7B' "$(printf '%s\n' "$claude_output" | sed -n '3p')" \
	  'claude usage should be green well below the limit'

	write_claude_state 70 "$((claude_now + 3600))" 12 "$((claude_now + 99999))" "$claude_now"
	assert_equals '#F1FA8C' "$(run_claude_usage | sed -n '3p')" \
	  'claude usage should warn when a window passes 60%'

	write_claude_state 91 "$((claude_now + 3600))" 12 "$((claude_now + 99999))" "$claude_now"
	assert_equals '#FF5555' "$(run_claude_usage | sed -n '3p')" \
	  'claude usage should go critical when a window passes 85%'

	# The writer only runs while a Claude session is open, so old data must be
	# labelled rather than presented as the current figure.
	write_claude_state 34 "$((claude_now + 3600))" 55 "$((claude_now + 99999))" "$((claude_now - 5000))"
	assert_equals '🤖 5h 34% · 7d 55% (stale)' "$(run_claude_usage | sed -n '1p')" \
	  'claude usage should mark stale cache data'

	# A window whose reset time has passed has rolled over: its cached percentage is
	# meaningless, so it must read as unknown rather than a misleading value.
	write_claude_state 99 "$((claude_now - 10))" 55 "$((claude_now + 99999))" "$claude_now"
	assert_equals '🤖 5h ?% · 7d 55%' "$(run_claude_usage | sed -n '1p')" \
	  'claude usage should not report a rolled-over window as current'

	write_claude_state 34 "$((claude_now + 3600))" 55 null "$claude_now"
	assert_equals '🤖 5h 34% · 7d 55%' "$(run_claude_usage | sed -n '1p')" \
	  'claude usage should tolerate a null seven_day reset time'

	printf 'not json\n' >"$CLAUDE_STATE_DIR/state.json"
	assert_equals '🤖 no data' "$(run_claude_usage | sed -n '1p')" \
	  'claude usage should degrade gracefully on unparsable cache data'

	claude_missing_output=$(LIMIT_STATE_DIR="$TMP_DIR/no-such-dir" NOW_EPOCH="$claude_now" \
	  bash "$I3BLOCKS_DIR/claude_usage.sh")
	assert_equals '🤖 no data' "$(printf '%s\n' "$claude_missing_output" | sed -n '1p')" \
	  'claude usage should degrade gracefully when the cache directory is absent'

	write_claude_state 34 "$((claude_now + 3600))" 55 "$((claude_now + 99999))" "$claude_now"
	assert_le "$(LIMIT_STATE_DIR="$CLAUDE_STATE_DIR" NOW_EPOCH="$claude_now" \
	  count_execs "$I3BLOCKS_DIR/claude_usage.sh")" 3 \
	  'claude usage should stay within bash plus jq'

	# The real cache holds one file per project (~170 on this machine), so the
	# fork budget has to be measured against a populated directory. Measuring it
	# against a single-file dir hid a `stat` call sitting inside the scan loop.
	for filler in $(seq 1 200); do
	  cp "$CLAUDE_STATE_DIR/state.json" "$CLAUDE_STATE_DIR/filler-$filler.json"
	done
	assert_le "$(LIMIT_STATE_DIR="$CLAUDE_STATE_DIR" NOW_EPOCH="$claude_now" \
	  count_execs "$I3BLOCKS_DIR/claude_usage.sh")" 3 \
	  'claude usage fork count must not scale with the number of cached projects'
	rm -f "$CLAUDE_STATE_DIR"/filler-*.json

	return 0
}
