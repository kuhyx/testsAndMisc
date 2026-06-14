# dwm (i3-like, compiled from source)

Versioned customisation for [suckless dwm](https://dwm.suckless.org/). This
directory is the **source of truth**; the installer
[`../scripts/single_use/features/setup_dwm.sh`](../scripts/single_use/features/setup_dwm.sh)
clones upstream `dwm` master, copies these files on top, applies the two
`dwm.c` patches, and builds. Nothing here is a full fork of dwm — only the
files we actually change live in the repo, so upstream stays bleeding-edge.

## How a build works

`setup_dwm.sh` runs, in order:

1. `git clone` / `git reset --hard origin/master` into `~/.local/src/dwm`
   (always the latest upstream).
2. Copy `config.h` over the clone.
3. `heal_config` — auto-merge any new upstream scalar knob (e.g. `refreshrate`)
   that the current `dwm.c` needs but our `config.h` predates.
4. Apply `patches/focus-on-click.patch` and
   `patches/fullscreen-pointer-confine.patch` to `dwm.c` — done with `perl`
   rewrites (robust against upstream line shifts), not `git apply`. The
   `.patch` files are the human-readable record of exactly those changes.
5. `make && sudo make install`.
6. Compile `pointer-confine.c` and install `bin/*` to `/usr/local/bin`.

Because the clone is reset every run, the patches are **re-applied each build**,
which is what keeps "always latest master" working.

## Files

| Path | What it is |
| --- | --- |
| `config.h` | dwm config: Mod4, Dracula colours, 10 tags, bottom bar, vim-style focus/move, multi-monitor keys, media keys, `movestack`/`togglefullscr` defined inline so `dwm.c` needs no extra patch for them. |
| `pointer-confine.c` | Standalone helper: traps the X pointer on the current monitor with XFixes pointer barriers until killed. Used for fullscreen gaming so the cursor can't slide onto the other screen. |
| `patches/focus-on-click.patch` | No-ops `enternotify`/`motionnotify` so the pointer never changes focus or switches monitors — focus only changes on click or via keys. |
| `patches/fullscreen-pointer-confine.patch` | Hooks `setfullscreen`/`unmanage` to start/stop `pconfine-auto` so the cursor-lock turns on automatically when a window goes fullscreen. |
| `bin/dwm-session` | lightdm session launcher (autostart + `dwmstatus` + `exec dwm`). |
| `bin/dwmstatus` | Status feeder: CPU/GPU/board temps, RAM, load, volume, clock → root window name. `dwmstatus once` prints the line without `xsetroot`. |
| `bin/dwm-rebuild` | Recompile `~/.local/src/dwm` in place (quick local rebuild). |
| `bin/switch-wm` | Flip the lightdm boot session between `i3` and `dwm`. |
| `bin/pconfine-auto` | `on`/`off` single-instance control of the `pointer-confine` daemon (called by the dwm hooks and the panic key). |

## Customising

- **Permanent change:** edit the file here (e.g. `config.h`), then re-run
  `setup_dwm.sh`. Log out / back in to apply (dwm has no live restart).
- **Quick experiment:** edit `~/.local/src/dwm/config.h` directly and run
  `dwm-rebuild` — but note the next `setup_dwm.sh` run overwrites it from here.

## Notable bindings (Mod = Super)

- `Mod+Return` terminal, `Mod+d` dmenu, `Mod+f` fullscreen, `Mod+Shift+q` kill,
  `Mod+Shift+e` exit, `Mod+Shift+r` recompile.
- Multi-monitor: `Mod+,`/`Mod+.` (or `Mod+Ctrl+←/→`) focus the other screen;
  `Mod+Shift+,`/`Mod+Shift+.` (or `Mod+Ctrl+Shift+←/→`) throw the window there.
- `Mod+Shift+p` force-releases the fullscreen cursor-lock if a barrier sticks.

## Dependencies

Build/runtime: `libx11 libxft libxinerama gcc make dmenu terminator`, plus
`xorg-xsetroot` for the status bar and `libxfixes` for `pointer-confine`
(present as a dep of Xorg). Install missing ones interactively — this system's
`pacman` is a wrapper that deadlocks when driven non-interactively.
