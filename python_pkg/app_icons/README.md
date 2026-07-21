# app_icons — shared launcher icons for the Flutter apps

One icon family across every Flutter/Dart app: a charcoal `#211D1B` field with
a single glyph in the shared `unified-design-system` accent (`#B8862E`),
drawn at one stroke weight and optically centred so a row of them lines up.

## Commands

```bash
# what is registered
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.app_icons list

# contact sheet for visual review: full size / circle-masked / 48dp
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.app_icons preview -o /tmp/sheet.png

# write assets into every app repo and rebuild the Android mipmaps
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.app_icons generate --android

# one app, plus the hicolor PNGs for a Linux desktop target
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.app_icons \
    generate --app todo --android --linux-out ~/todo/linux/icons
```

## What gets written

Per app, into `<repo>/assets/icon/`:

| Layer             | Purpose                                                             |
| ----------------- | ------------------------------------------------------------------- |
| `icon`            | Charcoal field + glyph. Legacy square launcher icon and Linux icon. |
| `icon_foreground` | Glyph only, transparent. Adaptive-icon foreground layer.            |
| `icon_monochrome` | Glyph only, white. Android 13+ themed icons.                        |

Both an `.svg` source and a 1024px `.png` are written for each, so a build
never needs `rsvg-convert`. `flutter_launcher_icons` then turns the PNGs into
the density buckets and `mipmap-anydpi-v26/ic_launcher.xml`.

## Design constraints that bite

- **Negative space ≥ half the stroke weight.** Strokes closer than that merge
  into a solid blob at launcher size. A fork whose tines sat exactly one stroke
  width apart rendered as a tulip.
- **Ink must stay inside the 560px safe box.** Android masks adaptive icons to
  roughly the inner 66% of the canvas. `generate` warns when a glyph overflows.
- **Stroked outlines can read wrong.** A stroked three-tine fork reads as a
  trident; a filled fork-and-knife pair reads as cutlery. Prefer a filled
  silhouette when the outline is ambiguous.
- Glyph positioning inside the fragment is irrelevant — `render.centre_offset`
  measures the rendered ink and recentres it. Only the extents matter.

## Adding an app

See the `app-icon` skill (`~/.claude/skills/app-icon/SKILL.md`) for the full
procedure. In short: add a glyph to `glyphs.py`, register the app in
`apps.py`, wire `flutter_launcher_icons` into its `pubspec.yaml`, generate,
review the contact sheet, then verify on the phone.

## Tests

```bash
cd ~/testsAndMisc
python3 -m pytest python_pkg/app_icons --cov=python_pkg.app_icons \
    --cov-report=term-missing
```

External tools (`rsvg-convert`, `magick`, `dart`) are mocked; the suite needs
none of them installed.
