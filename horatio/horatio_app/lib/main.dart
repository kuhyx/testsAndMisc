import 'dart:io';

import 'package:device_preview/device_preview.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // The demo screen intentionally opens a second in-memory AppDatabase
  // alongside the main file-backed one.  They use different executors so
  // there is no risk of data corruption.
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;

  final dbFolder = await getApplicationDocumentsDirectory();
  final dbFile = File(p.join(dbFolder.path, 'horatio.sqlite'));
  final database = AppDatabase(NativeDatabase(dbFile));
  final recordingsDir = p.join(dbFolder.path, 'horatio_recordings');
  final prefs = await SharedPreferences.getInstance();

  runApp(
    DevicePreview(
      builder: (_) => HoratioApp(
        database: database,
        recordingsDir: recordingsDir,
        prefs: prefs,
      ),
    ),
  );
}
