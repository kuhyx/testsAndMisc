import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

/// Signature matching [Process.run] for dependency injection.
typedef ProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

/// Wraps speech recognition for all platforms.
///
/// On platforms with native speech_to_text support (Android, iOS, macOS, web),
/// uses the [SpeechToText] plugin directly for live transcription.
///
/// On Linux desktop, records audio via [AudioRecorder] and transcribes with
/// the Whisper CLI (`whisper`) which must be installed separately.
class SpeechService {
  /// Creates a [SpeechService].
  ///
  /// All parameters are optional and intended for testing only.
  SpeechService({
    @visibleForTesting SpeechToText? speech,
    @visibleForTesting AudioRecorder? recorder,
    @visibleForTesting ProcessRunner? processRunner,
    @visibleForTesting bool? overrideIsLinux,
    @visibleForTesting Future<Directory> Function()? tempDirProvider,
  })  : _speech = speech ?? SpeechToText(),
        _recorder = recorder,
        _processRunner = processRunner ?? Process.run,
        _overrideIsLinux = overrideIsLinux,
        _tempDirProvider = tempDirProvider ?? getTemporaryDirectory;

  final SpeechToText _speech;
  AudioRecorder? _recorder;
  final ProcessRunner _processRunner;
  final bool? _overrideIsLinux;
  final Future<Directory> Function() _tempDirProvider;
  bool _initialised = false;
  bool _usesWhisper = false;

  /// Whether speech recognition is available on this device.
  bool get isAvailable => _initialised;

  /// Whether the engine is currently listening.
  bool get isListening => _isRecording || _speech.isListening;


  bool _isRecording = false;
  String? _recordingPath;

  /// Initialises the speech engine. Returns `true` if available.
  ///
  /// On Linux, checks for the `whisper` CLI tool and microphone permission.
  /// On other platforms, tries the native speech_to_text plugin.
  Future<bool> initialise() async {
    if (_overrideIsLinux ?? Platform.isLinux) {
      return _initialised = await _initLinux();
    }
    try {
      _initialised = await _speech.initialize();
    } on MissingPluginException {
      _initialised = false;
    }
    return _initialised;
  }

  Future<bool> _initLinux() async {
    // Check that whisper CLI is available.
    try {
      final result = await _processRunner('which', ['whisper']);
      if (result.exitCode != 0) return false;
    } on ProcessException {
      return false;
    }

    _usesWhisper = true;
    return true;
  }

  /// Starts listening. Calls [onResult] with partial/final transcriptions.
  Future<void> startListening({
    required void Function(SpeechRecognitionResult result) onResult,
  }) async {
    if (!_initialised) return;

    if (_usesWhisper) {
      await _startRecording();
    } else {
      await _speech.listen(onResult: onResult);
    }
  }

  /// Stops listening and returns transcribed text (Whisper) or empty string.
  ///
  /// For native speech_to_text, the result is already delivered via
  /// the [onResult] callback. For Whisper, call this then pass the result.
  Future<String> stopListening() async {
    if (_usesWhisper && _isRecording) {
      return _stopAndTranscribe();
    }
    await _speech.stop();
    return '';
  }

  Future<void> _startRecording() async {
    _recorder ??= AudioRecorder();
    if (!await _recorder!.hasPermission()) return;
    final dir = await _tempDirProvider();
    _recordingPath = p.join(dir.path, 'horatio_recording.wav');
    await _recorder!.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: _recordingPath!,
    );
    _isRecording = true;
  }

  Future<String> _stopAndTranscribe() async {
    await _recorder!.stop();
    _isRecording = false;
    final path = _recordingPath;
    if (path == null || !File(path).existsSync()) return '';

    try {
      final result = await _processRunner(
        'whisper',
        [path, '--model', 'base', '--output_format', 'txt', '--language', 'en'],
      );
      if (result.exitCode != 0) return '';

      // Whisper writes a .txt file next to the audio file.
      final txtPath = '${p.withoutExtension(path)}.txt';
      final txtFile = File(txtPath);
      if (txtFile.existsSync()) {
        final text = txtFile.readAsStringSync().trim();
        // Clean up temp files.
        File(path).deleteSync();
        txtFile.deleteSync();
        return text;
      }
    } on ProcessException {
      // Whisper not available — fall through.
    }
    return '';
  }

  /// Whether this service uses Whisper CLI (batch mode) rather than
  /// live streaming transcription.
  bool get usesWhisper => _usesWhisper;

  /// Human-readable setup instructions for the current platform.
  static String get setupInstructions => Platform.isLinux
      ? 'Install Whisper: pipx install openai-whisper\n'
          'Then restart the app.'
      : 'Speech recognition is not available on this platform.';

  /// Releases resources.
  Future<void> dispose() async {
    await _speech.stop();
    await _recorder?.dispose();
  }
}
