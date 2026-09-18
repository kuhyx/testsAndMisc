# Logitech G29 Driving Force Shifter: 1st/3rd not engaging (HID-BPF fix)

Files: `fixes/g29_shifter.bpf.c` (the fix), `fixes/fix_g29_shifter.sh`
(build/attach/install), `fixes/g29_wheel_mode.sh` (PS3/PS4 mode detection), `fixes/g29_shifter_capture.py` (grades a raw capture).
Force feedback (a separate problem, SDL-side): `DOCS-g29-ffb.md`.

## Symptom

The stick physically locks into every gate, but 1st and 3rd often do not
register in any game unless the stick is shoved hard forward. 2/4/6/R are fine.

## Cause (measured 2026-09-11)

The wheel firmware decodes the shifter's hall sensor into gear buttons itself.
The G29 input report (12 bytes, no report id) carries the raw values too:

| byte | content                                                                     |
| ---- | --------------------------------------------------------------------------- |
| 0–3  | hat (4 bits) + 25 buttons; gears 1–6, R = byte 2 bits 0–6                   |
| 4–5  | wheel, 6–8 pedals                                                           |
| 9    | shifter X: left ≈47–90 (1/2), centre ≈104–139 (3/4), right ≈166–191 (5/6/R) |
| 10   | shifter Y: bottom row ≈30–60, neutral ≈105, top row ≈180–233                |
| 11   | flags; 0x40 = stick pushed down (reverse)                                   |

Firmware thresholds, read off the on/off edges of a raw capture:

| row              | engages  | releases | where this stick actually rests      |
| ---------------- | -------- | -------- | ------------------------------------ |
| top (1/3/5)      | Y ≥ ~195 | Y ≤ ~179 | 180–233, often **180–193 → no gear** |
| bottom (2/4/6/R) | Y ≤ ~56  | Y ≥ ~72  | 30–60                                |

The thresholds are symmetric around Y=125 but this unit's neutral is ≈105
(sensor/magnet offset ~20 rearward), so the top row has no margin. The bottom
row keeps ~15–25 and occasionally drops for a second when the stick relaxes to
Y 58–71 (seen once on 4th, once on 2nd in the baseline captures).

## Fix

`g29_shifter.bpf.c` is a HID-BPF `hid_device_event` program attached by
`udev-hid-bpf`. It re-decodes 1st/3rd from bytes 9/10 with **engage Y ≥ 160,
release Y ≤ 140** (hysteresis kept in a BPF global) and ORs the bit into byte
2 before `hid-logitech` parses the report. It never clears a bit, so the
firmware's own decode is untouched — the working gates cannot regress. It is
transparent to every game, Proton and Steam Input, and FFB is unaffected.
5th is left to the firmware: no capture data for the top-right gate.

The Arch `udev-hid-bpf` package ships no headers; the script shallow-clones the
matching upstream tag into `~/.cache/g29_shifter/` and compiles with the same
clang flags as upstream's `meson.build`.

## The PS3/PS4 selector (found 2026-09-18)

The wheel has a physical PS3/PS4 switch and the USB identity follows it:

| selector | enumerates as             | bound by                 | shifter fix |
| -------- | ------------------------- | ------------------------ | ----------- |
| PS3      | `046D:C294` → `046D:C24F` | hid-logitech (new-lg4ff) | attaches    |
| PS4      | `046D:C260`               | hid-generic              | **cannot**  |

`C260` has a different report layout, no kernel driver knows it (new-lg4ff
0.5.0's table stops at `c24f`), and there is no software way out — only the
switch. On the 2026-09-15 and 2026-09-17 boots the wheel came up as `C260`;
every layer below looked for `C24F` only, so the unit failed once with
"no G29 found", nothing was said, and 1st/3rd were dead until the selector was
flipped ~1 day later (the journal shows `C260` → disconnect → `C294` → `C24F`).

## Surviving reboots

Three layers, because a missed attach is silent — the wheel still works, just
with the bad decode, which is indistinguishable from "the fix stopped working":

1. `udev-hid-bpf install` → `/etc/udev-hid-bpf/g29_shifter.bpf.o` plus
   `/etc/udev/rules.d/99-hid-bpf-g29_shifter.rules`, which attaches on `add`.
2. `g29-shifter-bpf.service` (`systemd/`), enabled at `multi-user.target`, runs
   `fix_g29_shifter.sh --ensure`: a no-op when attached, re-attaches when not.
   No wheel → exit 0 (layer 3 re-runs it on plug-in). Wheel present in PS4 or
   compatibility mode → exit 1 with the mode named, so `systemctl --failed`
   and the journal say _why_ instead of "not found". No notification and no
   retry loop: kuhy ruled that out (2026-09-18, "I want it to just work") —
   flipping the selector re-enumerates the wheel, and layer 3 re-runs the unit.
3. `/etc/udev/rules.d/99-g29-shifter-ensure.rules` pulls that unit in on every
   re-enumeration of `C24F` **or `C260`**, so a wheel powered on in the wrong
   mode is reported at once, and hotplug is covered as well as boot.

`--status` reports all of it, mode first. Verified 2026-09-12 by detaching and
starting the unit: it re-attached and exited cleanly. That test also caught the
unit failing with `HOME: unbound variable` — systemd has no `$HOME`, so the
cache path now falls back. The mode/notification logic is covered by
`tests/test_fix_g29_shifter.bats` against a fake sysfs tree.

## If the symptom returns after a boot

Check `--status` first. `wheel mode: ps4` → flip the selector. If it says
native + attached and gears still misbehave, the sensor's zero has drifted and
the thresholds need recalibrating — the fixed
`Y_TOP_RELEASE` (140) assumes the stick rests near Y≈105. A drift upward of
~+40 would park the rest position _above_ the release line, so a gear would
engage and never let go (the car stays in gear). Measure the rest value:

```bash
sudo ~/src/testsAndMisc/linux_configuration/fixes/g29_shifter_capture.py \
    --record 20 ~/data/g29-captures/neutral.txt --runs
```

with hands off the stick, and compare the reported Y against 105.

## Usage

```bash
~/src/testsAndMisc/linux_configuration/fixes/fix_g29_shifter.sh --test   # attach until unplug
~/src/testsAndMisc/linux_configuration/fixes/fix_g29_shifter.sh          # persistent (udev rule)
~/src/testsAndMisc/linux_configuration/fixes/fix_g29_shifter.sh --status
~/src/testsAndMisc/linux_configuration/fixes/fix_g29_shifter.sh --remove
```

## Verifying / recalibrating

hidraw sees the report _after_ the BPF program, so a raw capture shows the fix:

```bash
sudo timeout 60 xxd -c 12 /dev/hidraw$(basename "$(readlink -f /dev/input/by-id/usb-Logitech_G29_Driving_Force_Racing_Wheel-hidraw)" | tr -dc 0-9) > /tmp/g29.txt
~/src/testsAndMisc/linux_configuration/fixes/g29_shifter_capture.py /tmp/g29.txt --edges
```

Exit code 1 means some gate had a dwell ≥0.25 s with the bit clear. `--edges`
prints X/Y at every on/off transition — that is where the thresholds come
from. If the sensor drifts further, edit the `#define`s at the top of the
`.bpf.c` and re-run the script.
