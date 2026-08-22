#!/usr/bin/env bash
# Tests for dwm_config.sh — dwm's config install, healing and source patches.
#
# The subject is driven for real: it rewrites dwm.c with perl, appends to
# config.h, compiles with cc and installs to /usr/local/bin. The generated
# CONTENT is what is worth asserting -- a focus-on-click rewrite that silently
# stops matching upstream is precisely the bug a presence check would miss.
#
# Safe only under meta/scripts/shell_coverage_jail.sh: write_session_files and
# build_pointer_confine install into /usr/local/bin, which the jail
# bind-mounts to a throwaway dir. See jail_args beside this file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

# --- Refuse to run outside the jail -----------------------------------------
# /usr/local/bin is bind-mounted to an empty dir inside the jail. Finding the
# host's own binaries there means we are NOT contained, and the installs below
# would overwrite the real ones.
if [[ -e /usr/local/bin/switch-wm ]] && [[ ! -w /usr/local/bin ]]; then
	printf 'REFUSING: this suite must run under shell_coverage_jail.sh\n' >&2
	exit 1
fi

_t_setup_env
trap _t_teardown EXIT

warn() { printf '[test-warn] %s\n' "$1" >&2; }

# The globals dwm_config.sh inherits from setup_dwm.sh above its source line.
SRC_DIR="$TEST_TMPDIR/src"
REPO_DWM_DIR="$TEST_TMPDIR/repo"
BIN_SESSION="/usr/local/bin/dwm-session"
BIN_STATUS="/usr/local/bin/dwmstatus"
BIN_REBUILD="/usr/local/bin/dwm-rebuild"
BIN_SWITCH="/usr/local/bin/switch-wm"
BIN_CONFINE="/usr/local/bin/pointer-confine"
BIN_CONFINE_AUTO="/usr/local/bin/pconfine-auto"
XSESSION="$TEST_TMPDIR/dwm.desktop"
mkdir -p "$SRC_DIR" "$REPO_DWM_DIR/bin"

# shellcheck source=../dwm_config.sh
. "$FEATURES_LIB_DIR/dwm_config.sh"

# --- install_config ---------------------------------------------------------
printf 'static const int ours = 1;\n' >"$REPO_DWM_DIR/config.h"
install_config
_t_file_has "$SRC_DIR/config.h" 'ours' "install_config copies the repo's config.h onto the clone"

# --- heal_config: no config.def.h is a clean no-op ---------------------------
heal_config
_t_eq "0" "$?" "heal_config returns 0 when config.def.h is absent"

# --- heal_config: merges a knob dwm.c needs and config.h lacks --------------
cat >"$SRC_DIR/config.def.h" <<'DEFH'
static const int refreshrate = 60;
static const int ours = 9;
static const int unused = 3;
DEFH
printf 'int main(void){return refreshrate + ours;}\n' >"$SRC_DIR/dwm.c"
heal_config
_t_file_has "$SRC_DIR/config.h" 'refreshrate' "heal_config merges an upstream knob dwm.c references"
_t_eq "1" "$(grep -c 'ours' "$SRC_DIR/config.h")" "heal_config keeps OUR value and does not duplicate it"
_t_eq "0" "$(grep -c 'unused' "$SRC_DIR/config.h")" "heal_config skips a knob dwm.c never references"

# --- apply_focusonclick: missing dwm.c is a clean no-op ---------------------
rm -f "$SRC_DIR/dwm.c"
apply_focusonclick
_t_eq "0" "$?" "apply_focusonclick returns 0 when dwm.c is absent"

# --- apply_focusonclick: rewrites both handlers ------------------------------
# Shaped like upstream: a column-0 closing brace ends each function body.
cat >"$SRC_DIR/dwm.c" <<'DWMC'
void
enternotify(XEvent *e)
{
	Client *c;
	if (c)
		focus(c);
}

void
motionnotify(XEvent *e)
{
	Monitor *m;
	if (m)
		selmon = m;
}
DWMC
apply_focusonclick
_t_file_has "$SRC_DIR/dwm.c" 'pointer never changes focus' "apply_focusonclick rewrites enternotify"
_t_file_has "$SRC_DIR/dwm.c" 'keep the active monitor fixed' "apply_focusonclick rewrites motionnotify"
_t_eq "0" "$(grep -c 'focus(c);' "$SRC_DIR/dwm.c")" "the original enternotify body is gone"

# --- apply_focusonclick: warns instead of aborting on refactored upstream ---
printf 'void\nsomething_else(void)\n{\n\treturn;\n}\n' >"$SRC_DIR/dwm.c"
focus_out="$(apply_focusonclick 2>&1)"
_t_has "$focus_out" 'did NOT match upstream' "apply_focusonclick warns when the rewrite does not match"

# --- apply_fullscreen_confine_hook: missing dwm.c is a clean no-op -----------
rm -f "$SRC_DIR/dwm.c"
apply_fullscreen_confine_hook
_t_eq "0" "$?" "apply_fullscreen_confine_hook returns 0 when dwm.c is absent"

# --- apply_fullscreen_confine_hook: 1 "on", 2 "off" --------------------------
cat >"$SRC_DIR/dwm.c" <<'DWMC'
void
setfullscreen(Client *c, int fullscreen)
{
	if (fullscreen && !c->isfullscreen) {
		c->isfullscreen = 1;
	} else if (!fullscreen && c->isfullscreen) {
		c->isfullscreen = 0;
	}
}

void
unmanage(Client *c, int destroyed)
{
	Monitor *m = c->mon;
	XWindowChanges wc;
	detach(c);
}
DWMC
hook_out="$(apply_fullscreen_confine_hook 2>&1)"
_t_eq "1" "$(grep -c 'pconfine-auto on' "$SRC_DIR/dwm.c")" "the hook adds exactly one 'on' call"
_t_eq "2" "$(grep -c 'pconfine-auto off' "$SRC_DIR/dwm.c")" "the hook adds two 'off' calls (leave + unmanage)"
_t_has "$hook_out" 'Applied auto pointer-confinement' "the hook reports success at 1/2"

# --- apply_fullscreen_confine_hook: warns on a partial match ----------------
printf 'void\nsetfullscreen(void)\n{\n\treturn;\n}\n' >"$SRC_DIR/dwm.c"
partial_out="$(apply_fullscreen_confine_hook 2>&1)"
_t_has "$partial_out" 'only partially applied' "the hook warns when setfullscreen was refactored"

# --- build_install ----------------------------------------------------------
_t_stub make
build_install
_t_called 'make' "build_install invokes make"

# --- build_pointer_confine: the compile succeeds ----------------------------
printf 'int main(void){return 0;}\n' >"$REPO_DWM_DIR/pointer-confine.c"
_t_stub cc
confine_out="$(build_pointer_confine 2>&1)"
_t_has "$confine_out" "Installed $BIN_CONFINE" "build_pointer_confine installs the helper on a clean compile"
_t_eq "0" "$([[ -f $BIN_CONFINE ]] && echo 0 || echo 1)" "the pointer-confine binary lands in /usr/local/bin"

# --- build_pointer_confine: a failed compile fails SOFT ---------------------
# The real cc fails on a C file that is not C; dwm itself must still install.
cat >"$TEST_TMPDIR/bin/cc" <<'FAILCC'
#!/usr/bin/env bash
# Mimic a real cc failure: dwm_config redirects our stderr to the build log,
# so writing there is enough -- no need to know which argv slot -o landed in.
printf 'error: broken\n' >&2
exit 1
FAILCC
chmod +x "$TEST_TMPDIR/bin/cc"
soft_out="$(build_pointer_confine 2>&1)"
_t_has "$soft_out" 'fullscreen cursor-lock disabled' "a failed compile warns instead of aborting"

# --- write_session_files ----------------------------------------------------
for helper in dwm-session dwmstatus dwm-rebuild switch-wm pconfine-auto; do
	printf '#!/bin/sh\nexit 0\n' >"$REPO_DWM_DIR/bin/$helper"
done
write_session_files
_t_eq "0" "$([[ -x $BIN_SWITCH ]] && echo 0 || echo 1)" "write_session_files installs switch-wm executable"
_t_eq "0" "$([[ -x $BIN_CONFINE_AUTO ]] && echo 0 || echo 1)" "write_session_files installs pconfine-auto executable"
_t_file_has "$XSESSION" 'Exec=/usr/local/bin/dwm-session' "the xsession entry uses an absolute Exec path"
_t_file_has "$XSESSION" 'DesktopNames=dwm' "the xsession entry declares DesktopNames=dwm"

# --- verify -----------------------------------------------------------------
_t_stub dwm
verify_out="$(verify 2>&1)"
_t_has "$verify_out" 'dwm version:' "verify reports the dwm version"
_t_has "$verify_out" 'xsession registered' "verify confirms the xsession is registered"

# --- verify: tolerates a missing dwm binary ---------------------------------
rm -f "$TEST_TMPDIR/bin/dwm"
missing_out="$(verify 2>&1)" || true
_t_has "$missing_out" 'dwm version:' "verify still reports when dwm is absent (dwm -v exits 1)"

# --- print_summary ----------------------------------------------------------
summary_out="$(print_summary)"
_t_has "$summary_out" 'switch-wm dwm' "print_summary documents the switch-wm command"
_t_has "$summary_out" 'Ctrl+Alt+F3' "print_summary documents the TTY recovery path"

_t_report "test_dwm_config.sh"
