import 'dart:io';

import 'package:record/record.dart';

/// Wraps the [AudioRecorder] for microphone recording.
class RecordingService {
  /// Creates a [RecordingService].
  RecordingService({AudioRecorder? recorder})
      : _recorder = recorder;

  AudioRecorder? _recorder;

  AudioRecorder get _activeRecorder => _recorder ??= AudioRecorder();

  /// Whether the app has microphone permission.
  Future<bool> hasPermission() => _activeRecorder.hasPermission();

  /// Starts recording to the given file path.
  ///
  /// Creates the parent directory if it doesn't exist.
  Future<void> startRecording(String filePath) async {
    final parent = File(filePath).parent;
    if (!parent.existsSync()) {
      await parent.create(recursive: true);
    }
    await _activeRecorder.start(const RecordConfig(), path: filePath);
  }

  /// Stops recording and returns the file path.
  Future<String?> stopRecording() => _activeRecorder.stop();

  /// Releases the recorder resources.
  Future<void> dispose() async {
    final recorder = _recorder;
    if (recorder != null) {
      await recorder.dispose();
    }
  }
}
