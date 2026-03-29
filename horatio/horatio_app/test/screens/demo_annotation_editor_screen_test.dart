import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_app/screens/demo_annotation_editor_screen.dart';
import 'package:horatio_app/widgets/note_chip.dart';
import 'package:horatio_app/widgets/recording_action_bar.dart';
import 'package:shared_preferences/shared_preferences.dart';

late TextScaleCubit _textScaleCubit;

Future<void> _initTextScale() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  _textScaleCubit = TextScaleCubit(prefs: prefs);
}

Widget _buildDemo() {
  final router = GoRouter(
    initialLocation: '/demo',
    routes: [
      GoRoute(
        path: '/demo',
        builder: (context, state) => const DemoAnnotationEditorScreen(),
      ),
      GoRoute(
        path: '/annotation-history',
        builder: (context, state) =>
            const Scaffold(body: Text('History Screen')),
      ),
    ],
  );
  return BlocProvider<TextScaleCubit>.value(
    value: _textScaleCubit,
    child: MaterialApp.router(routerConfig: router),
  );
}

/// Runs a demo screen widget test entirely inside [tester.runAsync].
///
/// [DemoAnnotationEditorScreen] creates a real Drift in-memory database.
/// Drift schedules timers for initial stream data delivery and for cleanup on
/// disposal (via [StreamQueryStore.markAsClosed] when cubits close and cancel
/// stream subscriptions).  Running the full lifecycle — pump, seed wait, cubit
/// init, assertions, and explicit teardown — inside [tester.runAsync] ensures
/// every timer fires in real time and is never left pending as a fake-async
/// timer when the test ends.
Future<void> _runDemoTest(
  WidgetTester tester,
  Future<void> Function() assertions,
) async {
  await tester.runAsync(() async {
    await tester.pumpWidget(_buildDemo());
    // Seeding completes in real time.
    await Future<void>.delayed(const Duration(seconds: 2));
    // Rebuild with _ready = true; creates AnnotationCubit + RecordingCubit
    // which subscribe to Drift streams.
    await tester.pump();
    // Allow Drift's initial stream deliveries to fire in real time.
    await Future<void>.delayed(const Duration(milliseconds: 500));
    // Settle cubit-driven rebuilds.
    await tester.pump();

    await assertions();

    // Teardown inside runAsync so Drift's markAsClosed timers fire in real
    // time rather than as pending fake-async timers.
    await tester.pumpWidget(const SizedBox.shrink());
    await Future<void>.delayed(const Duration(milliseconds: 300));
  });
}

void main() {
  setUpAll(() async {
    await _initTextScale();
  });

  tearDownAll(() => _textScaleCubit.close());

  group('DemoAnnotationEditorScreen', () {
    testWidgets('shows loading indicator while seeding', (tester) async {
      await tester.runAsync(() async {
        await tester.pumpWidget(_buildDemo());
        await tester.pump();
        // Immediately after the first frame, seeding is still in progress.
        expect(find.byType(CircularProgressIndicator), findsOneWidget);

        // Let seeding finish before disposing so the in-flight DB inserts
        // don't hit a closed database.
        await Future<void>.delayed(const Duration(seconds: 2));

        await tester.pumpWidget(const SizedBox.shrink());
        await Future<void>.delayed(const Duration(milliseconds: 300));
      });
    });

    testWidgets('renders AnnotationEditorScreen after seeding', (tester) async {
      await _runDemoTest(tester, () async {
        expect(find.byType(AnnotationEditorScreen), findsOneWidget);
      });
    });

    testWidgets('shows Hamlet title in app bar', (tester) async {
      await _runDemoTest(tester, () async {
        expect(find.textContaining('Hamlet'), findsWidgets);
      });
    });

    testWidgets('shows demo script lines', (tester) async {
      await _runDemoTest(tester, () async {
        expect(
          find.text(
            'To be, or not to be, that is the question:',
            findRichText: true,
          ),
          findsOneWidget,
        );
      });
    });

    testWidgets('tapping a line shows RecordingActionBar', (tester) async {
      await _runDemoTest(tester, () async {
        await tester.tap(
          find.text(
            'To be, or not to be, that is the question:',
            findRichText: true,
          ),
        );
        await tester.pump();

        expect(find.byType(RecordingActionBar), findsOneWidget);
      });
    });

    testWidgets('demo data shows note chips on seeded line', (tester) async {
      await _runDemoTest(tester, () async {
        // Line 3 has two seeded notes (blocking + intention).
        await tester.tap(
          find.text(
            'Or to take arms against a sea of troubles',
            findRichText: true,
          ),
        );
        await tester.pump();

        expect(find.byType(NoteChip), findsWidgets);
      });
    });
  });
}
