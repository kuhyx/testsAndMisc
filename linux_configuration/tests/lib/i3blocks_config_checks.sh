#!/bin/bash
# i3blocks efficiency: config wiring, status icons, focus/GPU/ethernet guards.
# Sourced by test_i3blocks_efficiency.sh; inherits its strict mode and its
# helpers (fail, assert_equals, assert_le, epoch_utc, count_execs) plus the
# BIN_DIR / TMP_DIR / CONFIG_FILE / I3BLOCKS_DIR paths it sets up.

i3_tests_config_and_guards() {
	printf 'Checking config uses dedicated low-fork scripts...\n'
	grep -q '^command=~/.config/i3blocks/time.sh$' "$CONFIG_FILE" \
	  || fail 'time block should call time.sh'
	grep -q '^interval=persist$' "$CONFIG_FILE" \
	  || fail 'config should use persist interval for time block'
	grep -q '^command=~/.config/i3blocks/memory.sh$' "$CONFIG_FILE" \
	  || fail 'memory block should call memory.sh'
	grep -q '^command=~/.config/i3blocks/ethernet.sh$' "$CONFIG_FILE" \
	  || fail 'ethernet block should call ethernet.sh'
	grep -q '^command=~/.config/i3blocks/disk.sh$' "$CONFIG_FILE" \
	  || fail 'disk block should call disk.sh'
	grep -q '^interval=10$' "$CONFIG_FILE" \
	  || fail 'cpu block should poll at 10s interval'
	grep -A2 '^\[motherboard_temperature\]$' "$CONFIG_FILE" | grep -q '^interval=30$' \
	  || fail 'motherboard block should poll at 30s interval'
	grep -A2 '^\[memory\]$' "$CONFIG_FILE" | grep -q '^interval=30$' \
	  || fail 'memory block should poll at 30s interval'
	grep -A2 '^\[ethernet\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
	  || fail 'ethernet block should use persist mode'
	grep -A2 '^\[claude_usage\]$' "$CONFIG_FILE" | grep -q '^interval=60$' \
	  || fail 'claude_usage block should poll at 60s interval'
	grep -q '^command=~/.config/i3blocks/claude_usage.sh$' "$CONFIG_FILE" \
	  || fail 'claude_usage block should call claude_usage.sh'

	# Blocks for hardware/software absent from this machine were removed; make sure
	# they do not silently return. Each rendered permanently-dead text in the bar.
	for removed_block in bluetooth battery wifi activitywatch warp network_monitor; do
	  if grep -q "^\[${removed_block}\]$" "$CONFIG_FILE"; then
	    fail "removed block [${removed_block}] should not be in the config"
	  fi
	done

	printf 'Checking status icons avoid Font Awesome private-use codepoints...\n'
	# The fonts named in the i3 bar's pango string are not installed, so private-use
	# codepoints (U+E000-U+F8FF) fall through to whatever font claims them - which
	# rendered the ethernet icon as a star and the wifi icon as Cyrillic. Plain
	# Unicode/emoji resolve consistently instead.
	for icon_script in "$I3BLOCKS_DIR"/*.sh; do
	  if grep -qP '[\x{E000}-\x{F8FF}]|\\u[eEfF][0-9a-fA-F]{3}' "$icon_script"; then
	    fail "$(basename "$icon_script") should not use private-use-area icon codepoints"
	  fi
	done

	printf 'Checking focus detection path avoids extra xdotool lookups...\n'
	! grep -Fq "xdotool getwindowname \"\$wid\"" "$REPO_DIR/scripts/lib/common.sh" \
	  || fail 'focus detection should not call xdotool getwindowname in hot path'

	printf 'Checking GPU dedupe guards exist...\n'
	grep -Fq 'emit_if_changed()' "$I3BLOCKS_DIR/gpu_monitor.sh" \
	  || fail 'gpu monitor should dedupe repeated identical samples'
	grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/ethernet.sh" \
	  || fail 'ethernet script should use shared persist helper'
	grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/gpu_monitor.sh" \
	  || fail 'gpu script should use shared persist helper'
	grep -Fq 'i3blocks_update_if_changed_key "ethernet_output"' "$I3BLOCKS_DIR/ethernet.sh" \
	  || fail 'ethernet script should dedupe unchanged output'

	printf 'Checking ethernet picks a physical NIC over virtual bridges...\n'
	# Regression: the old loop returned the first non-loopback interface, which on a
	# machine with docker installed is a `br-*` bridge (always "down", and sorted
	# before enp*/eth*), so the bar reported "down" on a live wired connection.
	grep -Fq 'iface_path}/device' "$I3BLOCKS_DIR/ethernet.sh" \
	  || fail 'ethernet script should require a real device to skip virtual interfaces'

	return 0
}
