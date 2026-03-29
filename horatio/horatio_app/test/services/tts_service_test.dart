import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/tts_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('TtsService', () {
    late TtsService tts;

    setUp(() {
      tts = TtsService();
      // Stub the flutter_tts platform channel to avoid MissingPluginException.
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('flutter_tts'),
        (call) async {
          switch (call.method) {
            case 'setLanguage':
            case 'setSpeechRate':
            case 'setVolume':
            case 'setPitch':
            case 'stop':
              return 1;
            case 'speak':
              return 1;
            default:
              return null;
          }
        },
      );
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('flutter_tts'),
        null,
      );
    });

    test('initialize sets up TTS engine', () async {
      await tts.initialize();
      // Calling again should be a no-op.
      await tts.initialize();
    });

    test('speak calls initialize first then speaks', () async {
      await tts.speak('Hello');
    });

    test('stop stops speech', () async {
      await tts.stop();
    });

    test('dispose stops speech', () async {
      await tts.dispose();
    });
  });
}
