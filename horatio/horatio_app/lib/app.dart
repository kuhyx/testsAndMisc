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
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_app/theme/app_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Root widget for the Horatio app.
class HoratioApp extends StatelessWidget {
  /// Creates the [HoratioApp].
  const HoratioApp({
    required this.database,
    required this.recordingsDir,
    required this.prefs,
    super.key,
  });

  /// The drift database instance.
  final AppDatabase database;

  /// SharedPreferences for text scale persistence.
  final SharedPreferences prefs;

  /// Directory where line recordings are stored.
  final String recordingsDir;

  @override
  Widget build(BuildContext context) => MultiRepositoryProvider(
    providers: [
      RepositoryProvider<ScriptRepository>(create: (_) => ScriptRepository()),
      RepositoryProvider<AnnotationDao>(create: (_) => database.annotationDao),
      RepositoryProvider<RecordingDao>(create: (_) => database.recordingDao),
      RepositoryProvider<RecordingService>(
        create: (_) => RecordingService(),
        dispose: (service) => service.dispose(),
      ),
      RepositoryProvider<AudioPlaybackService>(
        create: (_) => AudioPlaybackService(),
        dispose: (service) => service.dispose(),
      ),
      RepositoryProvider<String>.value(value: recordingsDir),
    ],
    child: MultiBlocProvider(
      providers: [
        BlocProvider<ScriptImportCubit>(
          create: (context) =>
              ScriptImportCubit(repository: context.read<ScriptRepository>()),
        ),
        BlocProvider<SrsReviewCubit>(create: (_) => SrsReviewCubit()),
        BlocProvider<TextScaleCubit>(
          create: (_) => TextScaleCubit(prefs: prefs)..loadScale(),
        ),
      ],
      child: const _AutoDetectWrapper(),
    ),
  );
}

/// Runs auto-detect once in didChangeDependencies, then wraps child
/// with a [MediaQuery] override for the user's text scale.
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
        data: mq.copyWith(textScaler: TextScaler.linear(state.scaleFactor)),
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
