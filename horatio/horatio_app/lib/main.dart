import 'dart:io';

import 'package:device_preview/device_preview.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final dbFolder = await getApplicationDocumentsDirectory();
  final dbFile = File(p.join(dbFolder.path, 'horatio.sqlite'));
  final database = AppDatabase(NativeDatabase(dbFile));

  runApp(
    DevicePreview(
      builder: (_) => HoratioApp(database: database),
    ),
  );
}
