import 'package:device_preview/device_preview.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_app/theme/app_theme.dart';

/// Root widget for the Horatio app.
class HoratioApp extends StatelessWidget {
  /// Creates the [HoratioApp].
  const HoratioApp({required this.database, super.key});

  /// The drift database instance.
  final AppDatabase database;

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
          ],
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
