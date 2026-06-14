#!/bin/bash

# ============================================================================
# setup_dwm.sh — download, configure (i3-like), build & install suckless dwm
# ============================================================================
# Installs dwm ALONGSIDE the existing i3 setup. i3 is never touched; dwm shows
# up as a separate session you can boot into (see switch-wm).
#
# SOURCE OF TRUTH: every customisation lives as a real, version-controlled file
# under  linux_configuration/dwm/  and is COPIED onto a fresh upstream clone:
#   dwm/config.h            -> the i3-like config (keys, colours, rules)
#   dwm/pointer-confine.c   -> XFixes cursor-lock helper for fullscreen gaming
#   dwm/bin/*               -> dwm-session, dwmstatus, dwm-rebuild, switch-wm,
#                              pconfine-auto
#   dwm/patches/*.patch     -> human-readable form of the two dwm.c changes that
#                              this script applies with perl (focus-on-click +
#                              fullscreen pointer-confine)
#
# Bleeding edge: upstream master is cloned and `git reset --hard`'d on every run;
# our files are copied/applied on top, so `git pull && rebuild` keeps working.
# Edit the files in dwm/ and re-run this script to apply a permanent change.
# ============================================================================

set -euo pipefail

readonly SRC_DIR="${HOME}/.local/src/dwm"
readonly DWM_REPO="https://git.suckless.org/dwm"
readonly XSESSION="/usr/share/xsessions/dwm.desktop"
readonly BIN_SESSION="/usr/local/bin/dwm-session"
readonly BIN_STATUS="/usr/local/bin/dwmstatus"
readonly BIN_REBUILD="/usr/local/bin/dwm-rebuild"
readonly BIN_SWITCH="/usr/local/bin/switch-wm"
readonly BIN_CONFINE="/usr/local/bin/pointer-confine"
readonly BIN_CONFINE_AUTO="/usr/local/bin/pconfine-auto"

# Repo dir holding our versioned dwm source (resolved from this script's path,
# so it works regardless of the caller's CWD): features/ -> ... -> dwm/.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_DWM_DIR="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)/dwm"
readonly REPO_DWM_DIR

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!! \033[0m %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# 0. Confirm the versioned dwm source files are present in the repo before we
#    touch anything. Fail fast and clearly if the checkout is incomplete.
# ---------------------------------------------------------------------------
validate_repo_files() {
    local f missing=()
    local need=(
        "config.h"
        "pointer-confine.c"
        "bin/dwm-session"
        "bin/dwmstatus"
        "bin/dwm-rebuild"
        "bin/switch-wm"
        "bin/pconfine-auto"
    )
    for f in "${need[@]}"; do
        [[ -f "${REPO_DWM_DIR}/${f}" ]] || missing+=("${REPO_DWM_DIR}/${f}")
    done
    if ((${#missing[@]})); then
        warn "Missing required dwm source files (is the repo checkout complete?):"
        printf '    %s\n' "${missing[@]}" >&2
        exit 1
    fi
    log "dwm source files present in repo: $REPO_DWM_DIR"
}

# ---------------------------------------------------------------------------
# 1. Dependencies — DETECT ONLY, never auto-install.
#    This system's `pacman` is a digital-wellbeing wrapper that deadlocks when
#    driven non-interactively (stdin /dev/null + the /etc/hosts guard hooks
#    re-enter pacman and futex-deadlock on db.lck). So we never run `pacman -S`
#    from here. We only do a single read-only `pacman -Qq` (no db lock, no
#    transaction hooks) to check what's present, and tell the user to install
#    anything missing themselves, interactively, the way the wrapper expects.
# ---------------------------------------------------------------------------
install_deps() {
    log "Checking dependencies (read-only; the pacman wrapper is NOT invoked for installs)…"
    local required=(libx11 libxft libxinerama gcc make dmenu terminator)
    local optional=(xorg-xsetroot)   # status bar only — dwm runs fine without it
    local installed missing_req=() missing_opt=() p
    installed="$(pacman -Qq 2>/dev/null)" || installed=""

    for p in "${required[@]}"; do
        grep -qxF "$p" <<<"$installed" || missing_req+=("$p")
    done
    for p in "${optional[@]}"; do
        grep -qxF "$p" <<<"$installed" || missing_opt+=("$p")
    done

    if ((${#missing_req[@]})); then
        warn "Missing REQUIRED packages: ${missing_req[*]}"
        warn "Install them yourself (interactively), then re-run this script:"
        warn "    sudo pacman -S ${missing_req[*]}"
        exit 1
    fi
    if ((${#missing_opt[@]})); then
        warn "Optional status-bar package missing: ${missing_opt[*]} — dwm will still run."
        warn "For the status bar, install it later in your terminal:"
        warn "    sudo pacman -S ${missing_opt[*]}"
    fi
    log "All required dependencies present."
}

# ---------------------------------------------------------------------------
# 2. Fetch the LATEST dwm source (bleeding edge — always upstream master HEAD)
#    into a persistent, user-owned location so it can be re-edited and
#    recompiled at will. On re-run we hard-reset to origin/master to pull in
#    upstream changes; our config.h is untracked, so the reset never touches it.
# ---------------------------------------------------------------------------
fetch_dwm() {
    if [[ -d "$SRC_DIR/.git" ]]; then
        log "Updating dwm to the latest upstream master (bleeding edge)…"
        git -C "$SRC_DIR" fetch --quiet origin
        # config.h is untracked, so a hard reset of tracked files preserves it.
        git -C "$SRC_DIR" reset --hard --quiet origin/master
    else
        log "Cloning the latest dwm master into $SRC_DIR…"
        mkdir -p "$(dirname "$SRC_DIR")"
        git clone --quiet "$DWM_REPO" "$SRC_DIR"
    fi
    log "dwm source now at commit $(git -C "$SRC_DIR" rev-parse --short HEAD) ($(git -C "$SRC_DIR" log -1 --format=%cd --date=short))"
}

# ---------------------------------------------------------------------------
# 3. Install our versioned config.h onto the fresh upstream clone. dwm.c stays
#    pristine here — movestack()/togglefullscr() are defined inside config.h, so
#    only the two intentional behaviour changes below patch dwm.c.
# ---------------------------------------------------------------------------
install_config() {
    log "Installing config.h from the repo (${REPO_DWM_DIR}/config.h)…"
    cp -- "${REPO_DWM_DIR}/config.h" "$SRC_DIR/config.h"
}

# ---------------------------------------------------------------------------
# 3b. Auto-merge bleeding-edge config churn. When upstream adds a new config
#     knob (e.g. `refreshrate`), dwm.c starts referencing a symbol our
#     hand-written config.h doesn't define, breaking the build. To keep
#     "always latest master" sustainable, copy across any scalar knob that the
#     current dwm.c needs but our config.h lacks, using upstream's default.
#     Only single-line scalars referenced by dwm.c are merged (arrays we own
#     and unused symbols are left alone), so our customisations always win.
# ---------------------------------------------------------------------------
heal_config() {
    local defh="$SRC_DIR/config.def.h" cfgh="$SRC_DIR/config.h" dwmc="$SRC_DIR/dwm.c"
    [[ -f "$defh" && -f "$dwmc" ]] || return 0
    local line name added=0
    while IFS= read -r line; do
        name="$(sed -nE 's/^.*[^A-Za-z0-9_]([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=.*/\1/p' <<<"$line")"
        [[ -n "$name" ]] || continue
        grep -qw "$name" "$cfgh" && continue   # we already define it — keep ours
        grep -qw "$name" "$dwmc" || continue   # dwm.c doesn't need it — skip
        printf '%s\n' "$line" >>"$cfgh"
        warn "config.h: auto-merged new upstream knob '$name' (bleeding-edge churn)"
        added=1
    done < <(grep -E '^[[:space:]]*static[[:space:]]+const[[:space:]]+[^={]*=[^;{]*;' "$defh")
    ((added)) && log "Merged upstream config symbol(s) into config.h for this build."
    return 0
}

# ---------------------------------------------------------------------------
# 3c. Focus-on-click: stop the pointer from changing focus / switching monitors.
#     dwm defaults to focus-follows-mouse — and worse, crossing the screen
#     boundary over EMPTY space (motionnotify) switches the active monitor, which
#     yanks focus away from a fullscreen game on the other screen (no window edge
#     to stop the pointer). We rewrite enternotify + motionnotify to no-ops so
#     focus only changes on a CLICK or via the Mod+,/. (Mod+Ctrl+arrows) keys.
#     Applied as an idempotent source rewrite after each reset so it survives the
#     bleeding-edge `git pull`. perl -0777 slurps the file so the multi-line
#     function bodies match at once (.*? stops at the first column-0 `}`, i.e. the
#     function's own closing brace — nested if-block braces are tab-indented).
#     The dwm/patches/focus-on-click.patch file is the human-readable equivalent.
#     If upstream refactors these handlers the rewrite no-ops and we warn loudly
#     rather than silently dropping the behaviour.
# ---------------------------------------------------------------------------
apply_focusonclick() {
    local src="$SRC_DIR/dwm.c"
    [[ -f "$src" ]] || return 0

    perl -0777 -i -pe '
        s!\nenternotify\(XEvent \*e\)\n\{.*?\n\}\n!\nenternotify(XEvent *e)\n{\n\t/* focusonclick: pointer never changes focus; use a click or Mod+keys. */\n\t(void)e;\n}\n!s;
        s!\nmotionnotify\(XEvent \*e\)\n\{.*?\n\}\n!\nmotionnotify(XEvent *e)\n{\n\t/* focusonclick: keep the active monitor fixed when crossing screens. */\n\t(void)e;\n}\n!s;
    ' "$src"

    # Verify both rewrites landed; warn (never abort) if upstream changed shape.
    local ok=1
    grep -q 'focusonclick: pointer never changes focus' "$src" || ok=0
    grep -q 'focusonclick: keep the active monitor fixed' "$src" || ok=0
    if ((ok)); then
        log "Applied focus-on-click (pointer no longer changes focus or switches monitors)."
    else
        warn "focus-on-click rewrite did NOT match upstream dwm.c — pointer focus unchanged."
        warn "enternotify/motionnotify were likely refactored upstream; update dwm/patches."
    fi
    return 0
}

# ---------------------------------------------------------------------------
# 3d. Auto pointer-confinement on fullscreen. dwm has no pointer barriers, so on
#     a dual-monitor setup the cursor slides off a fullscreen game onto the other
#     screen (there is no window edge to stop it). We hook setfullscreen() to
#     start the `pointer-confine` helper (XFixes barriers) when a window goes
#     fullscreen and stop it when fullscreen ends; unmanage() also stops it so a
#     game that closes WHILE fullscreen can never leave the cursor trapped. The
#     hook is a quick `if (system(...)) {}` — the `if` consumes system()'s result
#     so -Wall stays warning-free; the trailing `&` returns to dwm immediately.
#     Reapplied after each reset (idempotent via git) and self-verifying; the
#     dwm/patches/fullscreen-pointer-confine.patch file mirrors it for reading.
# ---------------------------------------------------------------------------
apply_fullscreen_confine_hook() {
    local src="$SRC_DIR/dwm.c"
    [[ -f "$src" ]] || return 0

    perl -0777 -i -pe '
        s!(\n\t\tc->isfullscreen = 1;\n)!$1\t\tif (system("pconfine-auto on &")) {}\n!;
        s!(\n\t\tc->isfullscreen = 0;\n)!$1\t\tif (system("pconfine-auto off &")) {}\n!;
        s!(\nunmanage\(Client \*c, int destroyed\)\n\{\n\tMonitor \*m = c->mon;\n\tXWindowChanges wc;\n)!$1\tif (c->isfullscreen) { if (system("pconfine-auto off &")) {} }\n!;
    ' "$src"

    # Expect: 1 "on", 2 "off" (setfullscreen-leave + unmanage). Warn if not.
    local on off
    on=$(grep -c 'pconfine-auto on' "$src")
    off=$(grep -c 'pconfine-auto off' "$src")
    if [[ "$on" == 1 && "$off" == 2 ]]; then
        log "Applied auto pointer-confinement hook (locks the cursor to a fullscreen window's screen)."
    else
        warn "pointer-confine hook only partially applied (on=$on off=$off, expected 1/2)."
        warn "setfullscreen/unmanage were likely refactored upstream; update dwm/patches."
    fi
    return 0
}

# ---------------------------------------------------------------------------
# 4. Build & install (PREFIX defaults to /usr/local).
# ---------------------------------------------------------------------------
build_install() {
    log "Compiling dwm…"
    make -C "$SRC_DIR" clean >/dev/null
    make -C "$SRC_DIR" 2>&1 | tail -15
    log "Installing dwm (sudo make install)…"
    sudo make -C "$SRC_DIR" install 2>&1 | tail -8
}

# ---------------------------------------------------------------------------
# 4b. Build & install the pointer-confine helper (XFixes barriers) from the
#     versioned dwm/pointer-confine.c. Standalone C so it stays out of dwm.c;
#     dwm only spawns it via the setfullscreen() hook. If the X dev headers are
#     missing it fails soft: warn and skip, leaving the rest of dwm fully working
#     (fullscreen just won't auto-lock the cursor).
# ---------------------------------------------------------------------------
build_pointer_confine() {
    log "Compiling pointer-confine from the repo (${REPO_DWM_DIR}/pointer-confine.c)…"
    local bin
    bin="$(mktemp)"
    if cc -std=c99 -pedantic -Wall -O2 "${REPO_DWM_DIR}/pointer-confine.c" -o "$bin" \
            -lX11 -lXfixes -lXinerama 2>/tmp/pointer-confine-build.log; then
        sudo install -m 755 "$bin" "$BIN_CONFINE"
        log "Installed $BIN_CONFINE."
    else
        warn "pointer-confine failed to compile — fullscreen cursor-lock disabled (dwm itself is fine):"
        sed 's/^/    /' /tmp/pointer-confine-build.log >&2 || true
    fi
    rm -f "$bin"
}

# ---------------------------------------------------------------------------
# 5. Install the helper scripts (from the repo) and register the lightdm
#    xsession. The scripts are the versioned files in dwm/bin/; we just place
#    them on PATH with the right mode.
# ---------------------------------------------------------------------------
write_session_files() {
    log "Installing helper scripts from the repo and the lightdm xsession entry…"
    sudo install -m 755 "${REPO_DWM_DIR}/bin/dwm-session"   "$BIN_SESSION"
    sudo install -m 755 "${REPO_DWM_DIR}/bin/dwmstatus"     "$BIN_STATUS"
    sudo install -m 755 "${REPO_DWM_DIR}/bin/dwm-rebuild"   "$BIN_REBUILD"
    sudo install -m 755 "${REPO_DWM_DIR}/bin/switch-wm"     "$BIN_SWITCH"
    sudo install -m 755 "${REPO_DWM_DIR}/bin/pconfine-auto" "$BIN_CONFINE_AUTO"

    # --- xsession entry for lightdm (absolute Exec path) --------------------
    sudo tee "$XSESSION" >/dev/null <<'DESKTOP_EOF'
[Desktop Entry]
Name=dwm (i3-like)
Comment=dynamic window manager, compiled from source
Exec=/usr/local/bin/dwm-session
TryExec=/usr/local/bin/dwm
Type=Application
DesktopNames=dwm
DESKTOP_EOF
}

# ---------------------------------------------------------------------------
# 6. Verify the build links and the session is registered.
# ---------------------------------------------------------------------------
verify() {
    log "Verifying install…"
    local ver
    ver="$(dwm -v 2>&1)" || true   # dwm -v prints version then exit(1)
    log "dwm version: ${ver:-<none>}"
    command -v dwm >/dev/null && log "dwm binary: $(command -v dwm)"
    [[ -f "$XSESSION" ]] && log "xsession registered: $XSESSION"
}

print_summary() {
    cat <<SUMMARY

  dwm is installed alongside i3 (i3 untouched).
  This machine autologins (no session picker), so choose the WM you boot into:
    switch-wm dwm   -> boot dwm     switch-wm i3 -> boot i3     switch-wm -> show
  then reboot. Recovery if dwm misbehaves: TTY (Ctrl+Alt+F3) -> 'switch-wm i3' -> reboot.

  Key bindings (Mod = Super):
    Mod+Return        terminator            Mod+d             dmenu
    Mod+j / Mod+k     focus next / prev     Mod+Shift+j/k     move in stack
    Mod+h / Mod+l     shrink / grow master  Mod+i/Shift+i     +/- master count
    Mod+1..0          view tag 1..10        Mod+Shift+1..0    send to tag
    Mod+f             fullscreen            Mod+Shift+space   toggle floating
    Mod+t / Mod+w     tiling / monocle      Mod+Shift+Return  promote to master
    Mod+Shift+q       kill window           Mod+Shift+e       exit dwm
    Mod+m             mic mute              Mod+Shift+r       recompile (dwm-rebuild)

  Two monitors (no i3-style per-output workspaces — see config.h note):
    Mod+, / Mod+.                 focus the other screen   (or Mod+Ctrl+Left/Right)
    Mod+Shift+, / Mod+Shift+.     throw window there       (or Mod+Ctrl+Shift+L/R)
  Focus-on-click is ON: the pointer no longer steals focus or switches monitors
  when it crosses screens. Focus changes on click/keys.
  Fullscreen cursor-lock is ON: when a window goes fullscreen (games), the cursor
  is trapped on that screen (XFixes barriers) and released when fullscreen ends.
  Stuck barrier? Mod+Shift+p force-releases it.

  Status bar (clock, temps, load, RAM, volume) needs xsetroot:
    sudo pacman -S xorg-xsetroot     # then log out / back in
  Preview it now without the bar:  dwmstatus once

  Customise (permanent): edit files in linux_configuration/dwm/ then re-run this
  script. Quick experiment: edit ~/.local/src/dwm/config.h + run 'dwm-rebuild'
  (re-running setup_dwm.sh overwrites it from the repo).
SUMMARY
}

main() {
    validate_repo_files
    install_deps
    fetch_dwm
    install_config
    heal_config
    apply_focusonclick
    apply_fullscreen_confine_hook
    build_install
    build_pointer_confine
    write_session_files
    verify
    print_summary
}

main "$@"
