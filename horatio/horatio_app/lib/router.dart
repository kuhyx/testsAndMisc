import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_app/screens/annotation_history_screen.dart';
import 'package:horatio_app/screens/demo_annotation_editor_screen.dart';
import 'package:horatio_app/screens/home_screen.dart';
import 'package:horatio_app/screens/import_screen.dart';
import 'package:horatio_app/screens/rehearsal_screen.dart';
import 'package:horatio_app/screens/role_selection_screen.dart';
import 'package:horatio_app/screens/schedule_screen.dart';
import 'package:horatio_app/screens/srs_review_screen.dart';
import 'package:horatio_core/horatio_core.dart';

/// Route paths.
abstract final class RoutePaths {
  /// Home / script library.
  static const String home = '/';

  /// Import a new script.
  static const String import_ = '/import';

  /// Select a role after importing a script.
  static const String roleSelection = '/role-selection';

  /// View memorization schedule.
  static const String schedule = '/schedule';

  /// Interactive rehearsal mode.
  static const String rehearsal = '/rehearsal';

  /// SRS flashcard review.
  static const String srsReview = '/srs-review';

  /// Annotation editor.
  static const String annotations = '/annotations';

  /// Annotation history.
  static const String annotationHistory = '/annotation-history';

  /// Interactive demo — ephemeral in-memory Hamlet excerpt.
  static const String demo = '/demo';
}

/// Application router configuration.
final GoRouter appRouter = GoRouter(
  routes: [
    GoRoute(
      path: RoutePaths.home,
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: RoutePaths.import_,
      builder: (context, state) => const ImportScreen(),
    ),
    GoRoute(
      path: RoutePaths.roleSelection,
      redirect: (context, state) =>
          state.extra == null ? RoutePaths.home : null,
      builder: (context, state) {
        if (state.extra case final Script script) {
          return RoleSelectionScreen(script: script);
        }
        return const SizedBox.shrink();
      },
    ),
    GoRoute(
      path: RoutePaths.schedule,
      redirect: (context, state) =>
          state.extra == null ? RoutePaths.home : null,
      builder: (context, state) {
        if (state.extra case final Map<String, Object> extra) {
          return ScheduleScreen(
            script: extra['script']! as Script,
            selectedRole: extra['role']! as Role,
          );
        }
        return const SizedBox.shrink();
      },
    ),
    GoRoute(
      path: RoutePaths.rehearsal,
      redirect: (context, state) =>
          state.extra == null ? RoutePaths.home : null,
      builder: (context, state) {
        if (state.extra case final Map<String, Object> extra) {
          return RehearsalScreen(
            script: extra['script']! as Script,
            selectedRole: extra['role']! as Role,
          );
        }
        return const SizedBox.shrink();
      },
    ),
    GoRoute(
      path: RoutePaths.srsReview,
      redirect: (context, state) =>
          state.extra == null ? RoutePaths.home : null,
      builder: (context, state) {
        if (state.extra case final List<SrsCard> cards) {
          return SrsReviewScreen(cards: cards);
        }
        return const SizedBox.shrink();
      },
    ),
    GoRoute(
      path: RoutePaths.annotations,
      redirect: (context, state) =>
          state.extra == null ? RoutePaths.home : null,
      builder: (context, state) {
        if (state.extra case final Script script) {
          return AnnotationEditorScreen(script: script);
        }
        return const SizedBox.shrink();
      },
    ),
    GoRoute(
      path: RoutePaths.annotationHistory,
      redirect: (context, state) =>
          state.extra == null ? RoutePaths.home : null,
      builder: (context, state) {
        if (state.extra case final Script script) {
          return AnnotationHistoryScreen(script: script);
        }
        return const SizedBox.shrink();
      },
    ),
    GoRoute(
      path: RoutePaths.demo,
      builder: (context, state) => const DemoAnnotationEditorScreen(),
    ),
  ],
  errorBuilder: (context, state) => Scaffold(
    appBar: AppBar(title: const Text('Not Found')),
    body: Center(child: Text('Page not found: ${state.uri}')),
  ),
);
