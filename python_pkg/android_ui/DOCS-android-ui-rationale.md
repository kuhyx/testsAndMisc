# Android UI automation: rationale and Flutter pitfalls

## why this is not a nicety

Observed in one session (2026-08-10, workout_app Firebase verification):

- **Silent mis-taps.** A tap at `(540, 1705)` intended for the password field
  landed with the field unfocused. The typed password went nowhere. Nothing
  errored — the next screenshot just showed an empty box. A no-op and a hit are
  indistinguishable without dumping the tree and diffing.
- **Layout shift invalidates every coordinate.** Opening the soft keyboard moved
  the email field from y=1572 to y=1319. Coordinates captured one step earlier
  were already wrong.
- **Screenshot scaling is a manual multiply.** The harness renders 1080x2400 at
  900x2000, so every read coordinate needs `* 1.20`. One forgotten multiply is
  an off-screen tap.
- **Screenshots are expensive.** A full-page PNG per step burns far more context
  than the equivalent element list, and can't be grepped or asserted on.

`uiautomator dump` already solves this and is on every device — no new
dependency:

```bash
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml
# -> <node text="Connect Firebase" class="android.widget.Button"
#           bounds="[32,1808][1048,1878]" .../>
```

This is how the same session recovered: dumping the tree found both `EditText`
nodes by class and gave exact centers, and the retry worked first time.

- **Observed 2026-08-10, must be handled:** while a Flutter `TextField` holds
  focus, the dump returns ONLY the `EditText` nodes — the rest of the tree
  (including the button you are about to tap) is missing, and it stays missing
  across retries, so a naive retry loop never converges. Worse, `KEYCODE_BACK`
  to dismiss the keyboard is treated by Flutter as a route pop: it navigated
  out of Settings and discarded the typed credentials, twice. The tool must
  unfocus without popping the route (tap dead space, or `dumpsys input_method`
  to check `mInputShown` first) and must distinguish "tree is partial" from
  "element is genuinely absent" rather than reporting a false negative.
