# Logitech G29: no force feedback in BeamNG.drive (native Linux)

Files: `fixes/install_new_lg4ff.sh` (optional driver upgrade),
`~/src/steam-backlog-enforcer/steam_backlog_enforcer/_desktop_env.py` (the
host-level env var). Shifter companion: `DOCS-g29-shifter.md`.

## Symptom

BeamNG.drive 0.39.x, **native Linux build** (not Proton): the G29 steers,
pedals and buttons work, but the wheel is limp — no resistance, no
self-centring. Other games with FFB are unaffected.

## Cause (measured 2026-09-14, BeamNG 0.39.4.0, SDL 3.4.12 static)

`~/.local/share/BeamNG/BeamNG.drive/current/beamng.log`:

```
D|logHapticFeatures| Device joystick3 supports the following ffb features:
    Constant Sine Triangle SawToothUp SawToothDown Spring Damper Friction Status Query
I|inputRegistry| Created ffbid 0, ... on device joystick3 with axis id=0
E|updateFrame| Failed to get joystick3 FFB effect status:     (x12,201 per session)
```

That feature list is SDL3's **HIDAPI lg4ff** driver (`SDL_hidapi_lg4ff.c`),
which talks to the wheel over hidraw and bypasses the kernel `hid-logitech`
driver — the kernel driver advertises only constant/gain/autocenter
(`capabilities/ff` = `300040000 0`). The hidapi haptic backend advertises a
status query it cannot answer; BeamNG polls it every frame, gets an error, and
treats the effect as dead. Known regression:
<https://www.beamng.com/threads/ffb-not-working-on-linux.110807/>.

Not involved: the shifter HID-BPF (input direction only), hidraw permissions
(SDL had already opened the device), Proton (not used).

## Fix: make SDL use the kernel driver

Two env vars exist; they are not interchangeable:

| var                           | scope                                 | use                                                                        |
| ----------------------------- | ------------------------------------- | -------------------------------------------------------------------------- |
| `SDL_JOYSTICK_HIDAPI_LG4FF=0` | only the Logitech-wheel HIDAPI driver | **host-level**: set for every game, gamepads keep HIDAPI (BT rumble, LEDs) |
| `SDL_JOYSTICK_HIDAPI=0`       | all of SDL's HIDAPI joystick drivers  | forum-proven fallback, per-game only                                       |

Both names verified against strings in `BinLinux/BeamNG.drive.x64`.

1. **Per game** — Steam → BeamNG.drive → Properties → Launch Options:

   ```
   SDL_JOYSTICK_HIDAPI_LG4FF=0 LSFG_PROCESS=BeamNG.Drive gamemoderun %command%
   ```

   The previous value had no `%command%`, so Steam appended
   `LSFG_PROCESS=... gamemoderun ./BinLinux/BeamNG.drive.x64` as _arguments_
   to the game (visible in `pgrep -a BeamNG.drive.x64`) and neither gamemode
   nor LSFG was ever applied.

2. **Host level** — Steam on this machine is started by
   `steam-backlog-enforcer` through `sudo -u kuhy env <allowlist> steam …`.
   `sudo`'s `env_reset` makes that list the entire environment Steam and every
   game sees, so `/etc/environment`, `~/.profile` or `~/.pam_environment`
   never reach it. The variable lives in `desktop_env_args()` in the
   enforcer's `_desktop_env.py`. Check it landed:

   ```bash
   tr '\0' '\n' < /proc/$(pgrep -x steam)/environ | grep LG4FF
   ```

   A missing line means Steam predates the enforcer change — it takes effect
   on the next Steam launch (`systemctl restart steam-backlog-enforcer` kills
   a running game; check `pgrep -f BeamNG.drive.x64` first).

## Verify

- Game-independent motor check, BeamNG closed:
  `fftest /dev/input/by-id/usb-Logitech_G29_Driving_Force_Racing_Wheel-event-joystick`
  — effects 0 (constant) and 4 (autocenter) must move the wheel.
- In a fresh `beamng.log` the haptic feature line becomes the kernel-style
  list and `grep -c 'FFB effect status' beamng.log` drops to 0. A non-zero
  count with working force is fine; a zero count with no force is not.
- The gate is physical: drive a car, feel resistance and centring.

## Optional: new-lg4ff instead of the in-tree driver

`fixes/install_new_lg4ff.sh` installs `new-lg4ff-dkms-git` (AUR). Its
`dkms.conf` sets `DEST_MODULE_NAME="hid-logitech"`, so DKMS places it in
`updates/dkms/` and it shadows the in-tree module _by name_ — no blacklist,
no `modules-load.d`. Once loaded it registers as `hid_logitech_new`. Adds
spring/damper/friction/periodic effects and the `spring_level` /
`damper_level` / `friction_level` / `gain` / `autocenter` sysfs knobs.

Traps the script handles:

- `mkinitcpio`'s `autodetect` hook bundles `hid-logitech` into the initramfs
  because the wheel is plugged in at build time; a stale in-tree copy there
  would load first at boot. The script regenerates the presets when an image
  carries the module.
- `dkms status <name>` is a prefix filter that prints _everything_ on a miss;
  always grep `dkms status` output.
- USB interface 1 of the G29 (`0003:046D:C24F.0007`) is unbound by design.

```bash
~/src/testsAndMisc/linux_configuration/fixes/install_new_lg4ff.sh           # install (runs yay; needs a TTY)
~/src/testsAndMisc/linux_configuration/fixes/install_new_lg4ff.sh --status  # which module owns the wheel + ff caps
~/src/testsAndMisc/linux_configuration/fixes/install_new_lg4ff.sh --revert  # pacman -Rns + reload, no reboot
```
