import 'dart:io';

import 'package:billsplit/state/app_state.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

const _pickerChannel = MethodChannel('miguelruivo.flutter.plugins.filepicker');
const _pathChannel = MethodChannel('plugins.flutter.io/path_provider');

/// Mocks the file_picker method channel.
///
/// `pickResult`: bytes returned by pickFiles (null → user cancelled).
/// `saveResult`: path returned by saveFile (null → user cancelled).
/// `saveThrows`: saveFile raises a PlatformException.
void mockFilePicker({
  Uint8List? pickResult,
  String? pickName,
  String? saveResult,
  bool saveThrows = false,
}) {
  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_pickerChannel, (call) async {
    if (call.method == 'save') {
      if (saveThrows) {
        throw PlatformException(code: 'boom', message: 'disk full');
      }
      return saveResult;
    }
    // pickFiles ('custom'/'any'/...)
    if (pickResult == null) return null;
    return <Map<dynamic, dynamic>>[
      {
        'path': '/tmp/${pickName ?? 'picked.json'}',
        'name': pickName ?? 'picked.json',
        'size': pickResult.length,
        'bytes': pickResult,
      },
    ];
  });
}

/// Points path_provider's documents directory at [dir].
void mockPathProvider(Directory dir) {
  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_pathChannel, (call) async => dir.path);
}

/// Clears both channel mocks.
void clearChannelMocks() {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
    ..setMockMethodCallHandler(_pickerChannel, null)
    ..setMockMethodCallHandler(_pathChannel, null);
}

/// Creates an [AppState] persisted under a fresh temp directory.
AppState tempState() {
  final dir = Directory.systemTemp.createTempSync('billsplit_ui');
  addTearDown(() => dir.deleteSync(recursive: true));
  return AppState(overrideDir: dir)..loaded = true;
}

/// Pumps [home] inside the app shell with [state] provided.
Future<void> pumpApp(WidgetTester tester, AppState state, Widget home) {
  return tester.pumpWidget(
    ChangeNotifierProvider.value(
      value: state,
      child: MaterialApp(home: home),
    ),
  );
}

/// Fires the debounced save timer so tests end with no pending timers.
Future<void> flushSaves(WidgetTester tester) =>
    tester.pump(const Duration(milliseconds: 450));
