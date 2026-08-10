# android_ui — drive Android apps by element, never by coordinates

Shared across every repo with an Android surface (`~/screen-locker`'s
workout_app, `~/todo`, `~/dufs-cloud/app`). Works against a plain release APK
on a physical device over `adb` — no root, no emulator, no Flutter debug
connection, no change to app source.

## Why

Driving an app by tapping pixel positions read off a screenshot fails in ways
that look like success. All of these were observed in one session
(2026-08-10), verifying the workout app's Firebase restore:

| Failure                         | What it looks like                                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Tap lands on an unfocused field | Typed text goes nowhere; nothing errors; the next screenshot shows an empty box                                |
| Soft keyboard opens             | A field moves 1572 → 1319; every coordinate captured a step earlier is wrong                                   |
| Widget sits behind the keyboard | The tree reports its _laid-out_ position (1549) not its real one (1939) — a 390px error that taps a letter key |
| Screenshot scaling              | The harness renders 1080×2400 at 900×2000, so every read coordinate needs a manual ×1.2                        |
| Typing into a filled field      | `input text` inserts at the cursor: `old@example.comnew@example.com`                                           |

Two device quirks are handled rather than documented, because both produced
false results before they were understood:

- `uiautomator dump` returns **only the `EditText` nodes** while a Flutter text
  field holds focus. The button you are about to tap is simply missing, and it
  stays missing across retries — a naive retry loop never converges.
- `KEYCODE_BACK` is a **route pop** in Flutter, not a keyboard dismiss. It
  navigates out of the screen and discards typed input.

## Use

```bash
export PYTHONPATH=~/testsAndMisc
python3 -m python_pkg.android_ui dump
python3 -m python_pkg.android_ui find "Connect Firebase"
python3 -m python_pkg.android_ui --exact tap "Back"
python3 -m python_pkg.android_ui wait "Connected." --timeout 30
python3 -m python_pkg.android_ui focus
```

Every subcommand exits non-zero and names the query on failure, so a script can
tell a real failure from a successful no-op.

```python
from python_pkg.android_ui import AndroidUi

ui = AndroidUi()                      # or AndroidUi(serial="23181JEGR08034")
ui.tap("Connect Firebase", exact=True)
ui.type_into_field(0, "kuhy@example.com")   # verifies the field changed
ui.wait_for("Connected.", timeout=30)
```

## Guarantees

- **Ambiguity is an error.** A query matching 0 or >1 elements raises; it never
  silently acts on the first match. (`tap "Back"` correctly refuses when
  "OFFLINE BACKUP" is also on screen — use `--exact`.)
- **Coordinates are never reused.** Every action re-reads the tree immediately
  before acting, and `tap` closes the keyboard first when one is up.
- **Typing is verified.** `type_into` / `type_into_field` re-read the field and
  raise if the contents did not change. They clear before typing, so a filled
  field is replaced, not appended to.
- **Empty fields are findable.** An empty `EditText` has no text, content-desc
  or resource-id; it is kept anyway, addressable by position via
  `editable_fields()` / `type_into_field(index, …)`.
- **Partial trees are retried,** and `keyboard_is_up()` distinguishes "element
  absent" from "element behind the keyboard".

## Known gaps

- A widget with no accessibility label cannot be targeted at all. The workout
  app's Settings gear is one — that is an a11y bug in the app, and this tool
  surfacing it is the point. Add a `Semantics(label: …)` and it becomes
  addressable.
- Scrolling is not yet modelled: a widget outside the viewport is not in the
  tree. Scroll with `adb shell input swipe` first, or add `scroll_to()`.
