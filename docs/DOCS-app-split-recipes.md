# App split recipes (Dart, Kotlin, TypeScript)

Settled while clearing `focus_owner`, `kcd2_dice_solver` and
`reverse_survivors`. Referenced from `refactor_claude_todo_resume.md`.

## Baselines — measure before editing, re-check after

| Project                | Command             | Expect         |
| ---------------------- | ------------------- | -------------- |
| `focus_owner` (Dart)   | `flutter test`      | 94             |
| `focus_owner` (Kotlin) | see below           | 40, 0 failures |
| `kcd2_dice_solver`     | `npm test -- --run` | 288            |
| `reverse_survivors`    | `npm test -- --run` | 160            |

Gradle prints `UP-TO-DATE` rather than a count, so read the JUnit XML, and
**pin the JDK** — the default JDK 26 breaks the AGP jlink transform:

```bash
cd focus_owner/android
JAVA_HOME=/usr/lib/jvm/java-21-openjdk ./gradlew testDebugUnitTest --offline
grep -ho 'tests="[0-9]*"' ../build/app/test-results/testDebugUnitTest/*.xml \
  | grep -oP '\d+' | paste -sd+ | bc
```

## Dart: privates are library-scoped, so use `part`

A separate file is a separate **library**, so `_Card` and friends are invisible
to it. Splitting `main.dart` with `import` + `export` produced 30 errors of the
form "The name `_Card` isn't a class". `part 'x.dart';` + `part of 'main.dart';`
keeps both files in one library and the analyzer goes straight to zero issues.

The part file carries **no imports of its own** — it inherits the library's.

**A `part` cannot rescue a State class.** `status_page_state.dart` stayed over
the cap: its methods call `setState` and read seven private fields, and a
`mixin on State<...>` cannot see them without declaring the state twice.

**Splitting a widget test off its `testWidgets` group loses the binding.**
Four tests failed with "Binding has not yet been initialized" because the
group that had been initialising it implicitly moved away. Add
`TestWidgetsFlutterBinding.ensureInitialized()` to **both** halves.

## Kotlin: no `part`, so use an internal fixture object

Shared `private val`/`private fun` test fixtures go into an
`internal object XFixtures` in the same package, and each test class delegates
to it. Two compile failures came from missing one (`installed`) — list every
`private` member of the original class before cutting.

`EnforcementRunner.kt` is **not splittable** as it stands: its location block
reads the private constructor property `context` and `prefs()` eleven times,
which no extension function can reach.

## TypeScript: `tsc` does not tell you a split worked

Three separate projects had a seam that compiled clean and failed at runtime:

- an import cycle leaves a constant `undefined` at module-init
  (`HEADSTART_POINTS`, twice, in `kcd2`);
- a moved function is simply not there (`survivorStep`, 63 failures);
- a type name that collides with a DOM global resolves to the DOM one — the
  error talks about `anchorNode` rather than saying the name is missing.

**Always run the suite.** Prune the imports the split leaves behind by
iterating on `tsc`'s own TS6133/TS6192/TS6196 output rather than guessing, but
note it cannot see a helper another file still needs.

## Coverage: new files must land inside the include glob

`kcd2` and `reverse_survivors` both gate at 100%. New source modules are picked
up automatically; **shared test fixtures must go in `src/test/`**, which the
coverage `exclude` names by path. Beside the source they count as production
code and break the gate — the same trap recorded for `poker-stakes`.

## A split that empties a file must delete it

`App.test.tsx` lost its last `describe` and vitest failed the whole run with
"No test suite found in file". Remove the shell.
