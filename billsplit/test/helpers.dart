import 'dart:io';

import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/receipt_screen.dart';
import 'package:file_selector_platform_interface/file_selector_platform_interface.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

const _pathChannel = MethodChannel('plugins.flutter.io/path_provider');

/// Fake [FileSelectorPlatform] driving open/save dialogs in tests.
///
/// file_selector is swapped at the platform-interface level rather than at the
/// method channel: the real implementation talks Pigeon, so a MethodChannel
/// mock would not intercept it.
class _FakeFileSelector extends FileSelectorPlatform {
  _FakeFileSelector({
    this.pickResult,
    this.pickName,
    this.saveResult,
    this.saveThrows = false,
  });

  final Uint8List? pickResult;
  final String? pickName;
  final String? saveResult;
  final bool saveThrows;

  @override
  Future<XFile?> openFile({
    List<XTypeGroup>? acceptedTypeGroups,
    String? initialDirectory,
    String? confirmButtonText,
  }) async {
    if (pickResult == null) return null;
    return XFile.fromData(pickResult!, name: pickName ?? 'picked.json');
  }

  @override
  Future<FileSaveLocation?> getSaveLocation({
    List<XTypeGroup>? acceptedTypeGroups,
    SaveDialogOptions options = const SaveDialogOptions(),
  }) async {
    if (saveThrows) {
      throw PlatformException(code: 'boom', message: 'disk full');
    }
    if (saveResult == null) return null;
    return FileSaveLocation(saveResult!);
  }
}

/// Installs a fake file_selector platform for the current test.
///
/// `pickResult`: bytes returned by openFile (null → user cancelled).
/// `saveResult`: path returned by getSaveLocation (null → user cancelled).
/// `saveThrows`: getSaveLocation raises a PlatformException.
void mockFilePicker({
  Uint8List? pickResult,
  String? pickName,
  String? saveResult,
  bool saveThrows = false,
}) {
  TestWidgetsFlutterBinding.ensureInitialized();
  FileSelectorPlatform.instance = _FakeFileSelector(
    pickResult: pickResult,
    pickName: pickName,
    saveResult: saveResult,
    saveThrows: saveThrows,
  );
  // Record the write instead of touching the disk: a real dart:io future never
  // completes inside testWidgets' fake-async zone, so the export flow would
  // stall before showing its snackbar.
  exportedFiles.clear();
  debugSetExportWriter((path, bytes, mimeType) async {
    exportedFiles[path] = bytes;
  });
}

/// Paths and payloads captured by the stub export writer.
final Map<String, Uint8List> exportedFiles = <String, Uint8List>{};

/// Points path_provider's documents directory at [dir].
void mockPathProvider(Directory dir) {
  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_pathChannel, (call) async => dir.path);
}

/// Clears the path_provider channel mock and the file_selector fake.
void clearChannelMocks() {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_pathChannel, null);
  FileSelectorPlatform.instance = _FakeFileSelector();
  debugSetExportWriter(null);
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
