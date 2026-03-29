import 'package:drift/native.dart';
import 'package:horatio_app/database/app_database.dart';

/// Creates an in-memory [AppDatabase] for tests.
AppDatabase createTestDatabase() => AppDatabase(NativeDatabase.memory());
