#!/usr/bin/env bash
# Tests for aw_autostart.sh — ActivityWatch's autostart wiring and self-checks.
#
# The subject writes an XDG .desktop entry, appends an `exec` line to the i3
# config, and generates an i3blocks status script. All of it lands under
# $USER_HOME, which the suite points at a throwaway dir -- so unlike its
# siblings this one does not need root paths. It still runs under the jail
# with the rest of the directory's suites; see jail_args beside this file.
#
# The generated i3blocks script is asserted by EXECUTING it against stubbed
# pacman/pgrep, not by grepping its text: "AW on" vs "AW off" is the thing
# that reaches the status bar, and a heredoc that emits syntactically broken
# bash would pass a text check and fail in front of the user.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# The globals aw_autostart.sh inherits from setup_activitywatch.sh.
USER_HOME="$TEST_TMPDIR/home"
ACTUAL_USER="$(id -un)"
mkdir -p "$USER_HOME/.config/i3"

# test_setup calls these two; they live in the entry script, above the source
# line. Redefinable per-assertion, so each definition goes in a subshell -- a
# top-level redefinition would shadow the subject's own view for every later
# assertion.
check_activitywatch_installed() { return 1; }
check_activitywatch_running() { return 1; }

# shellcheck source=../aw_autostart.sh
. "$FEATURES_LIB_DIR/aw_autostart.sh"

# --- setup_autostart: no i3 config present ----------------------------------
rm -f "$USER_HOME/.config/i3/config"
no_i3_out="$(setup_autostart)"
desktop="$USER_HOME/.config/autostart/activitywatch.desktop"
_t_file_has "$desktop" 'Exec=aw-qt' "the XDG autostart entry execs aw-qt"
_t_file_has "$desktop" 'X-GNOME-Autostart-enabled=true' "the XDG entry enables GNOME autostart"
_t_has "$no_i3_out" 'i3 config not found' "setup_autostart reports a missing i3 config"

# --- setup_autostart: appends to an existing i3 config ----------------------
printf '# my i3 config\n' >"$USER_HOME/.config/i3/config"
added_out="$(setup_autostart)"
_t_file_has "$USER_HOME/.config/i3/config" 'exec --no-startup-id aw-qt' "setup_autostart appends the i3 exec line"
_t_has "$added_out" 'Added ActivityWatch to i3 config' "setup_autostart reports the i3 entry was added"

# --- setup_autostart: idempotent -- a second run must not duplicate ---------
again_out="$(setup_autostart)"
_t_eq "1" "$(grep -c 'exec --no-startup-id aw-qt' "$USER_HOME/.config/i3/config")" \
	"a second run does not duplicate the i3 exec line"
_t_has "$again_out" 'already exists in i3 config' "setup_autostart reports the entry already exists"

# --- create_i3blocks_status -------------------------------------------------
status_out="$(create_i3blocks_status)"
status_script="$USER_HOME/.config/i3blocks/activitywatch_status.sh"
_t_eq "0" "$([[ -x $status_script ]] && echo 0 || echo 1)" "the i3blocks status script is executable"
_t_has "$status_out" 'interval=10' "the printed i3blocks block sets interval=10"

# --- the GENERATED script actually works ------------------------------------
# Not installed: pacman -Qi fails and aw-qt is absent from PATH.
# PATH is REPLACED, not prepended, for this one case: aw-qt is genuinely
# installed at /usr/bin/aw-qt on the dev host, so a prepended stub dir cannot
# hide it -- `command -v aw-qt` would find the real one and the case would
# silently assert nothing. The generated script needs only coreutils here.
_t_stub pgrep
printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/pacman"
chmod +x "$TEST_TMPDIR/bin/pacman"
uninstalled="$(PATH="$TEST_TMPDIR/bin:/usr/bin/coreutils-only" "$status_script")"
_t_has "$uninstalled" 'AW uninstalled' "the status script reports 'AW uninstalled' with no package and no binary"

# Installed via the aw-qt binary, but no process running: pgrep must FAIL.
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_TMPDIR/bin/aw-qt"
chmod +x "$TEST_TMPDIR/bin/aw-qt"
printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/pgrep"
chmod +x "$TEST_TMPDIR/bin/pgrep"
off_out="$("$status_script")"
_t_has "$off_out" 'AW off' "the status script reports 'AW off' when installed but not running"

# Installed and running.
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_TMPDIR/bin/pgrep"
chmod +x "$TEST_TMPDIR/bin/pgrep"
on_out="$("$status_script")"
_t_has "$on_out" 'AW on' "the status script reports 'AW on' when the process is found"

# Installed via the pacman package rather than the binary.
rm -f "$TEST_TMPDIR/bin/aw-qt"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_TMPDIR/bin/pacman"
chmod +x "$TEST_TMPDIR/bin/pacman"
pkg_out="$("$status_script")"
_t_has "$pkg_out" 'AW on' "the status script accepts the pacman package as proof of install"

# --- test_setup: everything present -----------------------------------------
present_out="$(
	check_activitywatch_installed() { return 0; }
	check_activitywatch_running() { return 0; }
	test_setup
)"
_t_has "$present_out" '✓ ActivityWatch is installed' "test_setup reports an installed ActivityWatch"
_t_has "$present_out" '✓ ActivityWatch is running' "test_setup reports a running ActivityWatch"
_t_has "$present_out" '✓ XDG autostart file exists' "test_setup finds the XDG autostart file"
_t_has "$present_out" '✓ i3 autostart configured' "test_setup finds the i3 autostart line"
_t_has "$present_out" '✓ i3blocks status script created' "test_setup finds the i3blocks script"

# --- test_setup: nothing present --------------------------------------------
rm -f "$desktop" "$status_script" "$USER_HOME/.config/i3/config"
absent_out="$(
	check_activitywatch_installed() { return 1; }
	check_activitywatch_running() { return 1; }
	test_setup
)"
_t_has "$absent_out" '✗ ActivityWatch is not installed' "test_setup reports a missing ActivityWatch"
_t_has "$absent_out" '✗ ActivityWatch is not running' "test_setup reports a stopped ActivityWatch"
_t_has "$absent_out" '✗ XDG autostart file missing' "test_setup reports the missing XDG file"
_t_has "$absent_out" '! i3 autostart may not be configured' "test_setup reports the missing i3 line"
_t_has "$absent_out" '✗ i3blocks status script missing' "test_setup reports the missing i3blocks script"

# --- show_instructions ------------------------------------------------------
instructions="$(show_instructions)"
_t_has "$instructions" 'http://localhost:5600' "show_instructions gives the web interface URL"
_t_has "$instructions" 'Super+Shift+R' "show_instructions gives the i3 reload shortcut"

_t_report "test_aw_autostart.sh"
