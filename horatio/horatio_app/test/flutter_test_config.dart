import 'dart:async';

import 'package:drift/drift.dart';

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  // Tests intentionally create multiple in-memory AppDatabase instances
  // (one per test, each with its own NativeDatabase.memory() executor).
  // Drift's race-condition guard is not applicable here.
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
  await testMain();
}
