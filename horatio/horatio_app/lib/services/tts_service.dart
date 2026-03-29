import 'package:flutter_tts/flutter_tts.dart';

/// Service for text-to-speech of cue lines during rehearsal.
class TtsService {
  /// Creates a [TtsService].
  TtsService() : _tts = FlutterTts();

  final FlutterTts _tts;

  bool _isInitialized = false;

  /// Initializes TTS engine with default settings.
  Future<void> initialize() async {
    if (_isInitialized) return;
    await _tts.setLanguage('en-US');
    await _tts.setSpeechRate(0.45);
    await _tts.setVolume(1);
    await _tts.setPitch(1);
    _isInitialized = true;
  }

  /// Speaks the given [text] aloud.
  Future<void> speak(String text) async {
    await initialize();
    await _tts.speak(text);
  }

  /// Stops any currently playing speech.
  Future<void> stop() async {
    await _tts.stop();
  }

  /// Disposes of TTS resources.
  Future<void> dispose() async {
    await _tts.stop();
  }
}
