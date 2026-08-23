#!/usr/bin/env bash
# Tests for unity_handler.sh — the unityhub:// URL handler registration.
#
# No jail: the only write goes to $DESKTOP_DIR, pointed at a throwaway dir,
# and every external (update-desktop-database, xdg-mime, xdg-open) is
# intercepted by the harness's PATH stub dir.
#
# The generated .desktop file is asserted on its CONTENT: the MimeType and
# Exec lines are what make the handler work, and a file that exists with the
# wrong Exec is exactly the bug a presence check would pass.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./transcribe_harness.sh
. "$SCRIPT_DIR/transcribe_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script defines above its source line.
DESKTOP_DIR="$TEST_TMPDIR/applications"
RUN_TEST=false
mkdir -p "$DESKTOP_DIR"

log_info() { printf '[INFO] %s\n' "$*"; }
log_ok() { printf '[OK] %s\n' "$*"; }
log_warn() { printf '[WARN] %s\n' "$*"; }
log_error() { printf '[ERR] %s\n' "$*"; }

# shellcheck source=../unity_handler.sh
. "$TRANSCRIBE_LIB_DIR/unity_handler.sh"

# --- create_handler_desktop -------------------------------------------------
create_out="$(create_handler_desktop '/opt/unityhub/unityhub %u')"
desktop_file="${create_out##*$'\n'}"
_t_eq "$DESKTOP_DIR/unityhub-url-handler.desktop" "$desktop_file" \
	"create_handler_desktop returns the path it wrote"
desktop_body="$(cat "$desktop_file")"
_t_has "$desktop_body" 'Exec=/opt/unityhub/unityhub %u' \
	"the Exec line carries the command it was given"
_t_has "$desktop_body" 'x-scheme-handler/unityhub;x-scheme-handler/unity;' \
	"both URL schemes are declared in MimeType"
_t_has "$desktop_body" 'NoDisplay=true' "the entry is hidden from menus"

# --- register_mime_handler: both tools present ------------------------------
_t_stub update-desktop-database
_t_stub xdg-mime
_t_reset_calls
register_mime_handler "$desktop_file" >/dev/null
mime_calls="$(_t_calls)"
_t_has "$mime_calls" 'update-desktop-database' "the desktop database is refreshed"
_t_has "$mime_calls" 'default unityhub-url-handler.desktop x-scheme-handler/unityhub' \
	"xdg-mime registers the unityhub scheme by BASENAME, not full path"
_t_has "$mime_calls" 'unityhub-url-handler.desktop x-scheme-handler/unity' \
	"xdg-mime also registers the bare unity scheme"

# --- register_mime_handler: no update-desktop-database is survivable --------
_t_unstub update-desktop-database
no_db_out="$(register_mime_handler "$desktop_file" 2>&1)"
_t_has "$no_db_out" 'update-desktop-database not found' \
	"a missing update-desktop-database is reported"
_t_has "$no_db_out" 'MIME handler registered' "registration still completes without it"

# --- register_mime_handler: no xdg-mime is FATAL ----------------------------
# Without xdg-mime nothing is registered, so this must fail rather than
# report success -- the distinction the else branch exists to make.
_t_unstub xdg-mime
no_mime_rc=0
register_mime_handler "$desktop_file" >/dev/null 2>&1 || no_mime_rc=$?
_t_eq "1" "$no_mime_rc" "a missing xdg-mime returns non-zero rather than claiming success"

# --- verify_registration: the handler matches -------------------------------
cat >"$TEST_TMPDIR/bin/xdg-mime" <<'XDGMIME'
#!/usr/bin/env bash
printf 'unityhub-url-handler.desktop\n'
XDGMIME
chmod +x "$TEST_TMPDIR/bin/xdg-mime"
match_out="$(verify_registration "$desktop_file" 2>&1)"
_t_has "$match_out" 'correctly set to unityhub-url-handler.desktop' \
	"verify_registration confirms a correctly registered handler"

# --- verify_registration: a foreign handler warns ---------------------------
cat >"$TEST_TMPDIR/bin/xdg-mime" <<'XDGMIME'
#!/usr/bin/env bash
printf 'some-other-app.desktop\n'
XDGMIME
chmod +x "$TEST_TMPDIR/bin/xdg-mime"
wrong_out="$(verify_registration "$desktop_file" 2>&1)"
_t_has "$wrong_out" 'not set to' "verify_registration warns when another app owns the scheme"
_t_has "$wrong_out" 'some-other-app.desktop' "the warning names the handler actually registered"

# --- verify_registration: nothing registered at all -------------------------
cat >"$TEST_TMPDIR/bin/xdg-mime" <<'XDGMIME'
#!/usr/bin/env bash
exit 1
XDGMIME
chmod +x "$TEST_TMPDIR/bin/xdg-mime"
none_out="$(verify_registration "$desktop_file" 2>&1)"
_t_has "$none_out" '<none>' "an unset scheme is reported as <none> rather than blank"

# --- maybe_test_open: disabled prints the manual command --------------------
manual_out="$(maybe_test_open 2>&1)"
_t_has "$manual_out" 'test manually with' "RUN_TEST=false explains how to test by hand"

# --- maybe_test_open: enabled invokes xdg-open ------------------------------
_t_stub xdg-open
_t_reset_calls
opened_out="$(
	RUN_TEST=true
	maybe_test_open 2>&1
)"
_t_has "$(_t_calls)" 'unityhub://v1/editor-signin' "RUN_TEST=true opens the test link"
_t_has "$opened_out" 'Test link invoked' "the run reports that the link was invoked"

# --- maybe_test_open: enabled but xdg-open missing --------------------------
_t_unstub xdg-open
no_open_out="$(
	RUN_TEST=true
	maybe_test_open 2>&1
)"
_t_has "$no_open_out" 'xdg-open not found' "a missing xdg-open warns instead of failing"

_t_report "test_unity_handler.sh"
