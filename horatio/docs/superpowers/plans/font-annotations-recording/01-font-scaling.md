## Chunk 1: Font Scaling

### Task 1.1: Add shared_preferences dependency

**Files:**

- Modify: `horatio_app/pubspec.yaml`

- [ ] **Step 1: Add dependency**

In `horatio_app/pubspec.yaml`, add `shared_preferences: ^2.3.0` under `dependencies:` (after `path:`). Also add `audioplayers: ^6.1.0` (needed in Chunk 3 but add now to avoid re-running pub get).

```yaml
path: ^1.9.0
intl: ^0.20.2
shared_preferences: ^2.3.0
audioplayers: ^6.1.0
horatio_core:
```

- [ ] **Step 2: Run pub get**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter pub get
```

Expected: resolves without errors.

---

### Task 1.2: TextScaleState

**Files:**

- Create: `horatio_app/lib/bloc/text_scale/text_scale_state.dart`

- [ ] **Step 1: Create state file**

```dart
import 'package:equatable/equatable.dart';

/// State for [TextScaleCubit].
final class TextScaleState extends Equatable {
  /// Creates a [TextScaleState].
  const TextScaleState({required this.scaleFactor});

  /// The text scale multiplier (0.5 – 3.0).
  final double scaleFactor;

  @override
  List<Object?> get props => [scaleFactor];
}
```

---

### Task 1.3: TextScaleCubit — failing tests

**Files:**

- Create: `horatio_app/test/bloc/text_scale_cubit_test.dart`
- Create: `horatio_app/lib/bloc/text_scale/text_scale_cubit.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  group('TextScaleCubit', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('initial state has scaleFactor 1.0', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      expect(cubit.state, const TextScaleState(scaleFactor: 1.0));
      await cubit.close();
    });

    test('loadScale reads saved value', () async {
      SharedPreferences.setMockInitialValues({'text_scale_factor': 2.0});
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      expect(cubit.state, const TextScaleState(scaleFactor: 2.0));
      await cubit.close();
    });

    test('loadScale uses 1.0 when no saved value', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      expect(cubit.state, const TextScaleState(scaleFactor: 1.0));
      await cubit.close();
    });

    test('setScale persists and emits', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      await cubit.setScale(1.8);
      expect(cubit.state, const TextScaleState(scaleFactor: 1.8));
      expect(prefs.getDouble('text_scale_factor'), 1.8);
      await cubit.close();
    });

    test('autoDetect sets 1.5 for 4K desktop', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      cubit.autoDetect(const Size(1920, 1080), 2.0, isDesktop: true);
      // 1920 * 2.0 = 3840 >= 3200 → 1.5
      expect(cubit.state, const TextScaleState(scaleFactor: 1.5));
      await cubit.close();
    });

    test('autoDetect sets 1.0 for non-4K', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      cubit.autoDetect(const Size(1920, 1080), 1.0, isDesktop: true);
      // 1920 * 1.0 = 1920 < 3200 → 1.0
      expect(cubit.state, const TextScaleState(scaleFactor: 1.0));
      await cubit.close();
    });

    test('autoDetect sets 1.0 for mobile even at high resolution', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      cubit.autoDetect(const Size(1920, 1080), 2.0, isDesktop: false);
      expect(cubit.state, const TextScaleState(scaleFactor: 1.0));
      await cubit.close();
    });

    test('autoDetect skips when preference already saved', () async {
      SharedPreferences.setMockInitialValues({'text_scale_factor': 2.5});
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      cubit.autoDetect(const Size(1920, 1080), 2.0, isDesktop: true);
      // Should NOT override — preference already exists.
      expect(cubit.state, const TextScaleState(scaleFactor: 2.5));
      await cubit.close();
    });

    test('resetToAuto clears preference and re-detects', () async {
      SharedPreferences.setMockInitialValues({'text_scale_factor': 2.5});
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      await cubit.resetToAuto();
      expect(prefs.containsKey('text_scale_factor'), isFalse);
      // After reset, scale should be 1.0 (default).
      expect(cubit.state, const TextScaleState(scaleFactor: 1.0));
      await cubit.close();
    });

    test('TextScaleState equality', () {
      const a = TextScaleState(scaleFactor: 1.0);
      const b = TextScaleState(scaleFactor: 1.0);
      const c = TextScaleState(scaleFactor: 2.0);
      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/bloc/text_scale_cubit_test.dart
```

Expected: Compilation error — `TextScaleCubit` does not exist.

- [ ] **Step 3: Implement TextScaleCubit**

```dart
import 'dart:ui';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Manages text scale factor with SharedPreferences persistence.
class TextScaleCubit extends Cubit<TextScaleState> {
  /// Creates a [TextScaleCubit].
  TextScaleCubit({required SharedPreferences prefs})
      : _prefs = prefs,
        super(const TextScaleState(scaleFactor: 1.0));

  final SharedPreferences _prefs;

  static const _key = 'text_scale_factor';

  bool get _hasSavedPreference => _prefs.containsKey(_key);

  /// Loads the saved scale factor from SharedPreferences.
  void loadScale() {
    final saved = _prefs.getDouble(_key);
    if (saved != null) {
      emit(TextScaleState(scaleFactor: saved));
    }
  }

  /// Sets the scale factor, persisting to SharedPreferences.
  Future<void> setScale(double value) async {
    await _prefs.setDouble(_key, value);
    emit(TextScaleState(scaleFactor: value));
  }

  /// Auto-detects scale for 4K displays. Only runs when no preference saved.
  void autoDetect(Size logicalSize, double dpr, {required bool isDesktop}) {
    if (_hasSavedPreference) return;
    final physicalWidth = logicalSize.width * dpr;
    final scale = (physicalWidth >= 3200 && isDesktop) ? 1.5 : 1.0;
    emit(TextScaleState(scaleFactor: scale));
  }

  /// Clears the saved preference and resets to default 1.0.
  Future<void> resetToAuto() async {
    await _prefs.remove(_key);
    emit(const TextScaleState(scaleFactor: 1.0));
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/bloc/text_scale_cubit_test.dart -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/bloc/text_scale/ horatio_app/test/bloc/text_scale_cubit_test.dart
git commit -m "feat(text-scale): add TextScaleCubit with SharedPreferences persistence"
```

---

### Task 1.4: TextScaleSettingsSheet widget

**Files:**

- Create: `horatio_app/lib/widgets/text_scale_settings_sheet.dart`
- Create: `horatio_app/test/widgets/text_scale_settings_sheet_test.dart`

- [ ] **Step 1: Write failing widget tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:horatio_app/widgets/text_scale_settings_sheet.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late TextScaleCubit cubit;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    cubit = TextScaleCubit(prefs: prefs);
  });

  tearDown(() => cubit.close());

  Widget buildSheet() => MaterialApp(
        home: BlocProvider<TextScaleCubit>.value(
          value: cubit,
          child: const Scaffold(body: TextScaleSettingsSheet()),
        ),
      );

  group('TextScaleSettingsSheet', () {
    testWidgets('shows slider and preview text', (tester) async {
      await tester.pumpWidget(buildSheet());
      expect(find.byType(Slider), findsOneWidget);
      expect(find.textContaining('1.0x'), findsOneWidget);
    });

    testWidgets('slider changes scale', (tester) async {
      await tester.pumpWidget(buildSheet());
      // Drag slider to the right.
      final slider = find.byType(Slider);
      await tester.drag(slider, const Offset(100, 0));
      await tester.pumpAndSettle();
      // After drag, scale should have changed from 1.0.
      expect(cubit.state.scaleFactor, isNot(1.0));
    });

    testWidgets('reset button resets to default', (tester) async {
      await cubit.setScale(2.0);
      await tester.pumpWidget(buildSheet());
      await tester.tap(find.text('Reset to auto'));
      await tester.pumpAndSettle();
      expect(cubit.state, const TextScaleState(scaleFactor: 1.0));
    });

    testWidgets('shows current scale value', (tester) async {
      await cubit.setScale(1.5);
      await tester.pumpWidget(buildSheet());
      expect(find.textContaining('1.5x'), findsOneWidget);
    });
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/text_scale_settings_sheet_test.dart
```

Expected: Compilation error — `TextScaleSettingsSheet` does not exist.

- [ ] **Step 3: Implement TextScaleSettingsSheet**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';

/// A bottom sheet with a slider for adjusting text scale factor.
class TextScaleSettingsSheet extends StatelessWidget {
  /// Creates a [TextScaleSettingsSheet].
  const TextScaleSettingsSheet({super.key});

  @override
  Widget build(BuildContext context) =>
      BlocBuilder<TextScaleCubit, TextScaleState>(
        builder: (context, state) => Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Text Size',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 16),
              Text(
                'Sample text at ${state.scaleFactor.toStringAsFixed(1)}x',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 8),
              Slider(
                value: state.scaleFactor,
                min: 0.5,
                max: 3.0,
                divisions: 25,
                label: '${state.scaleFactor.toStringAsFixed(1)}x',
                onChanged: (value) =>
                    context.read<TextScaleCubit>().setScale(value),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () =>
                      context.read<TextScaleCubit>().resetToAuto(),
                  child: const Text('Reset to auto'),
                ),
              ),
            ],
          ),
        ),
      );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/text_scale_settings_sheet_test.dart -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/widgets/text_scale_settings_sheet.dart horatio_app/test/widgets/text_scale_settings_sheet_test.dart
git commit -m "feat(text-scale): add TextScaleSettingsSheet widget"
```

---

### Task 1.5: Integrate TextScaleCubit into app.dart + main.dart

**Files:**

- Modify: `horatio_app/lib/main.dart`
- Modify: `horatio_app/lib/app.dart`
- Modify: `horatio_app/test/app_test.dart`

- [ ] **Step 1: Update main.dart to init SharedPreferences**

Replace the current `main()` body. Add `SharedPreferences` init and pass to `HoratioApp`:

```dart
import 'dart:io';

import 'package:device_preview/device_preview.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final dbFolder = await getApplicationDocumentsDirectory();
  final dbFile = File(p.join(dbFolder.path, 'horatio.sqlite'));
  final database = AppDatabase(NativeDatabase(dbFile));
  final prefs = await SharedPreferences.getInstance();

  runApp(
    DevicePreview(
      builder: (_) => HoratioApp(database: database, prefs: prefs),
    ),
  );
}
```

- [ ] **Step 2: Update HoratioApp to accept prefs and provide TextScaleCubit**

Replace `app.dart` fully. Key design choices:

- Use `defaultTargetPlatform` instead of `dart:io` `Platform` to avoid web-incompatibility.
- Use a `_AutoDetectWrapper` `StatefulWidget` to run auto-detect exactly once in `initState`, not on every rebuild.

```dart
import 'package:device_preview/device_preview.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_app/theme/app_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Root widget for the Horatio app.
class HoratioApp extends StatelessWidget {
  /// Creates the [HoratioApp].
  const HoratioApp({
    required this.database,
    required this.prefs,
    super.key,
  });

  /// The drift database instance.
  final AppDatabase database;

  /// SharedPreferences for text scale persistence.
  final SharedPreferences prefs;

  @override
  Widget build(BuildContext context) => MultiRepositoryProvider(
        providers: [
          RepositoryProvider<ScriptRepository>(
            create: (_) => ScriptRepository(),
          ),
          RepositoryProvider<AnnotationDao>(
            create: (_) => database.annotationDao,
          ),
        ],
        child: MultiBlocProvider(
          providers: [
            BlocProvider<ScriptImportCubit>(
              create: (context) => ScriptImportCubit(
                repository: context.read<ScriptRepository>(),
              ),
            ),
            BlocProvider<SrsReviewCubit>(
              create: (_) => SrsReviewCubit(),
            ),
            BlocProvider<TextScaleCubit>(
              create: (_) => TextScaleCubit(prefs: prefs)..loadScale(),
            ),
          ],
          child: const _AutoDetectWrapper(),
        ),
      );
}

/// Runs auto-detect once in initState, then wraps child with MediaQuery.
class _AutoDetectWrapper extends StatefulWidget {
  const _AutoDetectWrapper();

  @override
  State<_AutoDetectWrapper> createState() => _AutoDetectWrapperState();
}

class _AutoDetectWrapperState extends State<_AutoDetectWrapper> {
  bool _hasAutoDetected = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_hasAutoDetected) {
      _hasAutoDetected = true;
      final mq = MediaQuery.of(context);
      final isDesktop =
          defaultTargetPlatform == TargetPlatform.linux ||
          defaultTargetPlatform == TargetPlatform.macOS ||
          defaultTargetPlatform == TargetPlatform.windows;
      context.read<TextScaleCubit>().autoDetect(
            mq.size,
            mq.devicePixelRatio,
            isDesktop: isDesktop,
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    return BlocBuilder<TextScaleCubit, TextScaleState>(
      builder: (context, state) => MediaQuery(
        data: mq.copyWith(
          textScaler: TextScaler.linear(state.scaleFactor),
        ),
        child: MaterialApp.router(
          title: 'Horatio',
          theme: AppTheme.light,
          darkTheme: AppTheme.dark,
          locale: DevicePreview.locale(context),
          builder: DevicePreview.appBuilder,
          routerConfig: appRouter,
        ),
      ),
    );
  }
}
```

- [ ] **Step 3: Update app_test.dart**

The `HoratioApp` now requires `prefs`. Update all test usages:

```dart
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers/test_database.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('HoratioApp builds without crashing', (tester) async {
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      HoratioApp(database: createTestDatabase(), prefs: prefs),
    );
    await tester.pumpAndSettle();
    expect(find.text('Horatio'), findsOneWidget);
  });

  testWidgets('SrsReviewCubit is created when srs-review route is visited',
      (tester) async {
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      HoratioApp(database: createTestDatabase(), prefs: prefs),
    );
    await tester.pumpAndSettle();

    unawaited(appRouter.push(RoutePaths.srsReview, extra: <SrsCard>[
      SrsCard(id: 'c1', cueText: 'Cue', answerText: 'Ans'),
    ]));
    await tester.pumpAndSettle();
    expect(find.text('No review session active.'), findsOneWidget);
  });

  testWidgets('AnnotationDao is provided when annotation route is visited',
      (tester) async {
    final db = createTestDatabase();
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(HoratioApp(database: db, prefs: prefs));
    await tester.pumpAndSettle();

    const role = Role(name: 'Hero');
    const script = Script(
      id: 'app-ann-id',
      title: 'Ann Test',
      roles: [role],
      scenes: [
        Scene(
          lines: [
            ScriptLine(
              text: 'Hello.',
              role: role,
              sceneIndex: 0,
              lineIndex: 0,
            ),
          ],
        ),
      ],
    );
    unawaited(appRouter.push(RoutePaths.annotations, extra: script));
    await tester.pumpAndSettle();
    expect(find.text('Annotate: Ann Test'), findsOneWidget);

    // Close the database before teardown to cancel Drift stream timers.
    await db.close();
  });
}
```

- [ ] **Step 4: Run all tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/main.dart horatio_app/lib/app.dart horatio_app/test/app_test.dart horatio_app/pubspec.yaml
git commit -m "feat(text-scale): integrate TextScaleCubit into app root with auto-detect"
```

---

### Task 1.6: Add settings icon to HomeScreen and AnnotationEditorScreen

**Files:**

- Modify: `horatio_app/lib/screens/home_screen.dart`
- Modify: `horatio_app/lib/screens/annotation_editor_screen.dart`
- Modify: `horatio_app/test/screens/annotation_editor_screen_test.dart`

- [ ] **Step 1: Add settings icon to HomeScreen AppBar**

In `home_screen.dart`, add these imports at the top:

```dart
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/widgets/text_scale_settings_sheet.dart';
```

Change:

```dart
appBar: AppBar(title: const Text('Horatio')),
```

to:

```dart
appBar: AppBar(
  title: const Text('Horatio'),
  actions: [
    IconButton(
      icon: const Icon(Icons.text_fields),
      tooltip: 'Text Size',
      onPressed: () => showModalBottomSheet<void>(
        context: context,
        builder: (_) => BlocProvider.value(
          value: context.read<TextScaleCubit>(),
          child: const TextScaleSettingsSheet(),
        ),
      ),
    ),
  ],
),
```

- [ ] **Step 2: Add settings icon to AnnotationEditorScreen AppBar**

In `annotation_editor_screen.dart`, add these imports:

```dart
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/widgets/text_scale_settings_sheet.dart';
```

In `_AnnotationEditorBody.build`, the existing `actions` list looks like:

```dart
actions: [
  IconButton(
    icon: const Icon(Icons.history),
    tooltip: 'History',
    onPressed: () =>
        context.push(RoutePaths.annotationHistory, extra: script),
  ),
],
```

Add the text size button before the history button:

```dart
actions: [
  IconButton(
    icon: const Icon(Icons.text_fields),
    tooltip: 'Text Size',
    onPressed: () => showModalBottomSheet<void>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: context.read<TextScaleCubit>(),
        child: const TextScaleSettingsSheet(),
      ),
    ),
  ),
  IconButton(
    icon: const Icon(Icons.history),
    tooltip: 'History',
    onPressed: () =>
        context.push(RoutePaths.annotationHistory, extra: script),
  ),
],
```

- [ ] **Step 3: Update annotation_editor_screen_test.dart for TextScaleCubit**

In the test file, add these imports:

```dart
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:shared_preferences/shared_preferences.dart';
```

Add to the `setUp` block:

```dart
SharedPreferences.setMockInitialValues({});
```

Create a `TextScaleCubit` in `setUp`:

```dart
late TextScaleCubit textScaleCubit;

setUp(() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  textScaleCubit = TextScaleCubit(prefs: prefs);
  // ... existing setup ...
});

tearDown(() {
  textScaleCubit.close();
  // ... existing teardown ...
});
```

Wrap the existing test `_buildScreen` helpers with a `BlocProvider<TextScaleCubit>.value(value: textScaleCubit, ...)`.

Add a test for the text size button:

```dart
testWidgets('text size button opens settings sheet', (tester) async {
  final script = _testScript();
  await tester.pumpWidget(_buildScreen(script));
  _marksCtrl.add([]);
  _notesCtrl.add([]);
  _snapshotsCtrl.add([]);
  await tester.pumpAndSettle();

  await tester.tap(find.byIcon(Icons.text_fields));
  await tester.pumpAndSettle();

  expect(find.byType(TextScaleSettingsSheet), findsOneWidget);
});
```

- [ ] **Step 4: Run all tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/screens/home_screen.dart horatio_app/lib/screens/annotation_editor_screen.dart horatio_app/test/
git commit -m "feat(text-scale): add text size settings button to home and annotation screens"
```

---

### Task 1.7: Run full pipeline for Chunk 1

- [ ] **Step 1: Run codegen + analyze + test**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh test
```

Expected: 100% coverage, all pass.

- [ ] **Step 2: Fix any issues**

If coverage gaps exist, add missing tests. If analysis warnings, fix them.

---
