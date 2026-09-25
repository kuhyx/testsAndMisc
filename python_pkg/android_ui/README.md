# android_ui — drive Android apps by element, never by coordinates

Shared across every repo with an Android surface (`~/src/screen-locker`'s
workout_app, `~/src/todo`, `~/src/dufs-cloud/app`). Works against a plain release APK
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
export PYTHONPATH=~/src/testsAndMisc
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
  - **But check `hint` first.** Material/Flutter text fields publish their
    label as `hint` and leave text/content-desc empty; those ARE addressable
    (since 2026-08-27) and need no app change. Adding a `Semantics(label:)`
    wrapper to such a field is actively harmful — it emits a SECOND labelled
    node at the same rect, and wrapping in `MergeSemantics` to collapse them
    removes the `hint` from Android's tree entirely, making the whole form
    anonymous. Verified on the manual-workout form; reverted.
  - Verify any a11y change with `adb exec-out uiautomator dump`, never with
    `flutter test`: the widget test asserts on Flutter's internal
    `SemanticsNode`, while this tool reads Android's `AccessibilityNodeInfo`.
    Nine widget tests passed green on the build whose on-device labels had
    just gone empty.
- Scrolling is not yet modelled: a widget outside the viewport is not in the
  tree. Scroll with `adb shell input swipe` first, or add `scroll_to()`.

## One phone, many sessions

Sessions share the phone by working on separate displays. By default every
command drives the real screen (display 0) and takes this session's
`pkg:__screen__` lease (`python_pkg.phone_lease`: owner = the nearest
ancestor `claude` process, 180 s past the last call). A call from another
session waits up to 60 s, then exits 3 naming the holder. Do not retry in a
loop.

`--display self` drives this session's virtual display instead
(`~/.claude/scripts/phone_vd.sh start <package>` creates it) and takes only
that app's lease, so several sessions can act at once:

    android-ui --display self dump
    android-ui --display self tap "Save"

`uiautomator dump` sees display 0 only, so on a virtual display the tree
comes from the `com.kuhy.a11ydump` instrumentation helper (`A11yDump.java`,
`_a11y_helper.py`): built once into `~/.cache/android_ui/` and installed
with `adb install -r -t` on first use. Its package must stay in
phone-focus-mode's whitelist, or the focus-owner sweep hides it. Android
runs one instrumentation per package, so a second `am instrument` kills
the first: dumps of one phone queue behind a host-side `flock`
(`~/.cache/android_ui/a11ydump-<serial>.lock`). Every
`input` call carries `-d` (0 for the real screen), because input without it
goes to whichever display last took focus. A numeric `--display` that is
another session's virtual display is refused.

Raw `adb` from a Claude Bash call is covered too: the
`~/.claude/hooks/phone_guard_pretool.sh` hook (`python_pkg.phone_guard`)
takes the matching lease or blocks the call. See the `phone-deploy` skill,
section 3, for the full rules.
