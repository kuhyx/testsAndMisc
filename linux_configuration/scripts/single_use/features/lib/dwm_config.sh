#!/bin/bash
# dwm config install, healing and the patch applications.
#
# Sourced by setup_dwm.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

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
