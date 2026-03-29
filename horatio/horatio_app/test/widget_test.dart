import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/screens/home_screen.dart';
import 'package:horatio_app/services/script_repository.dart';

Widget _wrapWithProviders(Widget child) {
  final repository = ScriptRepository();
  return MultiRepositoryProvider(
    providers: [
      RepositoryProvider<ScriptRepository>(create: (_) => repository),
    ],
    child: MultiBlocProvider(
      providers: [
        BlocProvider<ScriptImportCubit>(
          create: (_) => ScriptImportCubit(repository: repository),
        ),
        BlocProvider<SrsReviewCubit>(create: (_) => SrsReviewCubit()),
      ],
      child: MaterialApp(home: child),
    ),
  );
}

void main() {
  testWidgets('HomeScreen shows empty state with public domain suggestions',
      (WidgetTester tester) async {
    await tester.pumpWidget(_wrapWithProviders(const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Horatio'), findsOneWidget);
    expect(find.text('Drop or click to import file'), findsOneWidget);
    expect(find.text('Public Domain Scripts'), findsOneWidget);
    expect(find.text('William Shakespeare'), findsNWidgets(2));
  });

  testWidgets('Empty state lists five public domain scripts',
      (WidgetTester tester) async {
    await tester.pumpWidget(_wrapWithProviders(const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.auto_stories), findsNWidgets(5));
    expect(find.byIcon(Icons.download), findsNWidgets(5));
  });

  testWidgets('Router does not crash when navigating to route without extra',
      (WidgetTester tester) async {
    final repository = ScriptRepository();
    await tester.pumpWidget(
      MultiRepositoryProvider(
        providers: [
          RepositoryProvider<ScriptRepository>(create: (_) => repository),
        ],
        child: MultiBlocProvider(
          providers: [
            BlocProvider<ScriptImportCubit>(
              create: (_) => ScriptImportCubit(repository: repository),
            ),
            BlocProvider<SrsReviewCubit>(create: (_) => SrsReviewCubit()),
          ],
          child: MaterialApp.router(routerConfig: appRouter),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Test every route that requires extra — none should crash.
    for (final path in [
      RoutePaths.roleSelection,
      RoutePaths.schedule,
      RoutePaths.rehearsal,
      RoutePaths.srsReview,
    ]) {
      appRouter.go(path);
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text('Horatio'), findsOneWidget);

      // Return home before next iteration.
      appRouter.go(RoutePaths.home);
      await tester.pumpAndSettle();
    }
  });
}
