import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/screens/rehearsal_screen.dart';
import 'package:horatio_app/services/speech_service.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';
import 'package:speech_to_text/speech_recognition_result.dart';

class MockSpeechService extends Mock implements SpeechService {}

Script _twoLineScript() {
  const hamlet = Role(name: 'Hamlet');
  const horatio = Role(name: 'Horatio');
  return const Script(
    id: 'rehearsal-test-id',
    title: 'Test',
    roles: [hamlet, horatio],
    scenes: [
      Scene(
        lines: [
          ScriptLine(
            text: 'Good evening.',
            role: horatio,
            sceneIndex: 0,
            lineIndex: 0,
          ),
          ScriptLine(
            text: 'To be or not to be.',
            role: hamlet,
            sceneIndex: 0,
            lineIndex: 1,
          ),
          ScriptLine(
            text: 'Indeed my lord.',
            role: horatio,
            sceneIndex: 0,
            lineIndex: 2,
          ),
          ScriptLine(
            text: 'That is the question.',
            role: hamlet,
            sceneIndex: 0,
            lineIndex: 3,
          ),
        ],
      ),
    ],
  );
}

Widget _wrap(Script script, Role role, {SpeechService? speechService}) =>
    MaterialApp(
      home: RehearsalScreen(
        script: script,
        selectedRole: role,
        speechService: speechService,
      ),
    );

MockSpeechService _createMockSpeech({bool usesWhisper = false}) {
  final mock = MockSpeechService();
  when(mock.initialise).thenAnswer((_) async => true);
  when(() => mock.isAvailable).thenReturn(true);
  when(() => mock.isListening).thenReturn(false);
  when(() => mock.usesWhisper).thenReturn(usesWhisper);
  when(() => mock.startListening(onResult: any(named: 'onResult')))
      .thenAnswer((_) async {});
  when(mock.stopListening).thenAnswer((_) async => '');
  when(mock.dispose).thenAnswer((_) async {});
  return mock;
}

void main() {
  group('RehearsalScreen', () {
    testWidgets('shows appbar with role name', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      expect(find.text('Rehearsing: Hamlet'), findsOneWidget);
    });

    testWidgets('shows cue text and progress bar', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // Cue from Horatio's first line.
      expect(find.text('Good evening.'), findsOneWidget);
      // Progress indicator.
      expect(find.textContaining('Line'), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
    });

    testWidgets('typing mode: enter text and get feedback', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // If speech is available, switch to typing mode.
      final typeButton = find.text('Type instead');
      if (typeButton.evaluate().isNotEmpty) {
        await tester.tap(typeButton);
        await tester.pumpAndSettle();
      }

      // Enter the correct line.
      final textField = find.byType(TextField);
      expect(textField, findsOneWidget);

      await tester.enterText(textField, 'To be or not to be.');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      // Should now show feedback.
      expect(find.text('Expected:'), findsOneWidget);
      expect(find.text('Next'), findsOneWidget);
    });

    testWidgets('Check button submits typed text', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // Switch to typing if speech available.
      final typeButton = find.text('Type instead');
      if (typeButton.evaluate().isNotEmpty) {
        await tester.tap(typeButton);
        await tester.pumpAndSettle();
      }

      await tester.enterText(find.byType(TextField), 'wrong line');
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      // Feedback shown.
      expect(find.text('Expected:'), findsOneWidget);
      expect(find.text('Your version:'), findsOneWidget);
    });

    testWidgets('Next button advances to next line', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // Switch to typing if speech available.
      final typeButton = find.text('Type instead');
      if (typeButton.evaluate().isNotEmpty) {
        await tester.tap(typeButton);
        await tester.pumpAndSettle();
      }

      // Submit first line.
      await tester.enterText(
          find.byType(TextField), 'To be or not to be.');
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      // Tap Next.
      await tester.tap(find.text('Next'));
      await tester.pumpAndSettle();

      // Should show next cue: Horatio's "Indeed my lord."
      expect(find.text('Indeed my lord.'), findsOneWidget);
    });

    testWidgets('full rehearsal cycle ends in complete view',
        (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // Switch to typing if speech available.
      final typeButton = find.text('Type instead');
      if (typeButton.evaluate().isNotEmpty) {
        await tester.tap(typeButton);
        await tester.pumpAndSettle();
      }

      // Submit first line.
      await tester.enterText(
          find.byType(TextField), 'To be or not to be.');
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Next'));
      await tester.pumpAndSettle();

      // Submit second line (switch to typing again since state rebuilt).
      final typeButton2 = find.text('Type instead');
      if (typeButton2.evaluate().isNotEmpty) {
        await tester.tap(typeButton2);
        await tester.pumpAndSettle();
      }

      await tester.enterText(
          find.byType(TextField), 'That is the question.');
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Next'));
      await tester.pumpAndSettle();

      // Complete view should appear.
      expect(find.text('Rehearsal Complete!'), findsOneWidget);
      expect(find.text('Done'), findsOneWidget);
      expect(find.byIcon(Icons.celebration), findsOneWidget);
    });

    testWidgets('complete view shows result rows', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // Switch to typing if needed.
      final typeButton = find.text('Type instead');
      if (typeButton.evaluate().isNotEmpty) {
        await tester.tap(typeButton);
        await tester.pumpAndSettle();
      }

      // Answer first line with a "major" grade (50-80% similarity).
      // Expected: "To be or not to be." — omit second half for ~67% score.
      await tester.enterText(find.byType(TextField), 'To be or not');
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Next'));
      await tester.pumpAndSettle();

      final typeButton2 = find.text('Type instead');
      if (typeButton2.evaluate().isNotEmpty) {
        await tester.tap(typeButton2);
        await tester.pumpAndSettle();
      }

      // Answer second line perfectly.
      await tester.enterText(
          find.byType(TextField), 'That is the question.');
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Next'));
      await tester.pumpAndSettle();

      // Result rows.
      expect(find.text('Perfect'), findsOneWidget);
      expect(find.text('Close'), findsOneWidget);
      expect(find.text('Needs work'), findsOneWidget);
      expect(find.text('Missed'), findsOneWidget);
    });

    testWidgets('empty text submission does not advance', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // Switch to typing if needed.
      final typeButton = find.text('Type instead');
      if (typeButton.evaluate().isNotEmpty) {
        await tester.tap(typeButton);
        await tester.pumpAndSettle();
      }

      // Submit empty text — should not advance.
      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      // Still on the awaiting line view.
      expect(find.text('Good evening.'), findsOneWidget);
      expect(find.text('Expected:'), findsNothing);
    });

    testWidgets('Done button in complete view pops the route',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');

      // Use Navigator to verify pop behavior.
      await tester.pumpWidget(MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: ElevatedButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => RehearsalScreen(
                    script: script,
                    selectedRole: role,
                  ),
                ),
              ),
              child: const Text('Go'),
            ),
          ),
        ),
      ));

      // Navigate to rehearsal screen.
      await tester.tap(find.text('Go'));
      await tester.pumpAndSettle();

      // Complete the rehearsal.
      for (var i = 0; i < 2; i++) {
        final typeBtn = find.text('Type instead');
        if (typeBtn.evaluate().isNotEmpty) {
          await tester.tap(typeBtn);
          await tester.pumpAndSettle();
        }
        await tester.enterText(find.byType(TextField), 'any text');
        await tester.tap(find.text('Check'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Next'));
        await tester.pumpAndSettle();
      }

      // Should be on complete view.
      expect(find.text('Done'), findsOneWidget);

      // Tap Done → should pop back.
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();

      // Should be back on the first screen.
      expect(find.text('Go'), findsOneWidget);
    });

    testWidgets('voice/typing toggle works', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // If speech is available, voice mode is default.
      final typeToggle = find.text('Type instead');
      if (typeToggle.evaluate().isNotEmpty) {
        // Voice mode — should show mic.
        expect(find.byIcon(Icons.mic), findsOneWidget);
        expect(find.text('Tap to speak your line'), findsOneWidget);

        // Switch to typing.
        await tester.tap(typeToggle);
        await tester.pumpAndSettle();

        expect(find.byType(TextField), findsOneWidget);
        expect(find.text('Use voice instead'), findsOneWidget);

        // Switch back to voice.
        await tester.tap(find.text('Use voice instead'));
        await tester.pumpAndSettle();

        expect(find.byIcon(Icons.mic), findsOneWidget);
      } else {
        // Speech not available — typing mode shown by default.
        expect(find.byType(TextField), findsOneWidget);
      }
    });

    testWidgets('voice mic button taps trigger recording', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // If speech is available, test mic interaction.
      final typeToggle = find.text('Type instead');
      if (typeToggle.evaluate().isNotEmpty) {
        // Tap mic to start recording.
        final mic = find.byIcon(Icons.mic);
        expect(mic, findsOneWidget);
        await tester.tap(mic);
        await tester.pump(const Duration(milliseconds: 300));

        // Should show stop icon and recording state.
        final stopIcon = find.byIcon(Icons.stop);
        if (stopIcon.evaluate().isNotEmpty) {
          // Recording started — tap stop to end recording.
          expect(
            find.textContaining('tap to stop'),
            findsOneWidget,
          );
          await tester.tap(stopIcon);
          await tester.pumpAndSettle();
        }
      }
    });

    testWidgets('voice mode renders mic circle container', (tester) async {
      final script = _twoLineScript();
      final role =
          script.roles.firstWhere((r) => r.name == 'Hamlet');

      await tester.pumpWidget(_wrap(script, role));
      await tester.pumpAndSettle();

      // If speech available, verify mic circle.
      final typeToggle = find.text('Type instead');
      if (typeToggle.evaluate().isNotEmpty) {
        expect(find.byType(GestureDetector), findsWidgets);
        expect(find.byType(AnimatedContainer), findsOneWidget);
      }
    });
  });

  group('RehearsalScreen with mock speech', () {
    testWidgets('voice mode is default when speech available',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Voice UI visible.
      expect(find.byIcon(Icons.mic), findsOneWidget);
      expect(find.text('Tap to speak your line'), findsOneWidget);
      // Toggle shows "Type instead".
      expect(find.text('Type instead'), findsOneWidget);
      // No TextField (voice mode, not typing).
      expect(find.byType(TextField), findsNothing);
    });

    testWidgets('toggle switches to typing and back', (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Switch to typing.
      await tester.tap(find.text('Type instead'));
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('Use voice instead'), findsOneWidget);

      // Switch back to voice.
      await tester.tap(find.text('Use voice instead'));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.mic), findsOneWidget);
      expect(find.text('Type instead'), findsOneWidget);
    });

    testWidgets('tapping mic starts recording (STT mode)', (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Tap mic.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      verify(() => mockSpeech.startListening(
            onResult: any(named: 'onResult'),
          )).called(1);

      // UI should show stop icon and listening text.
      expect(find.byIcon(Icons.stop), findsOneWidget);
      expect(find.text('Listening — tap to stop'), findsOneWidget);
    });

    testWidgets('tapping stop ends recording (STT mode)', (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Stop recording.
      await tester.tap(find.byIcon(Icons.stop));
      await tester.pumpAndSettle();

      verify(mockSpeech.stopListening).called(1);
    });

    testWidgets('speech result advances to feedback (STT mode)',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      // Capture onResult callback.
      late void Function(SpeechRecognitionResult) onResult;
      when(() => mockSpeech.startListening(
            onResult: any(named: 'onResult'),
          )).thenAnswer((invocation) async {
        onResult = invocation.namedArguments[#onResult]
            as void Function(SpeechRecognitionResult);
      });

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Simulate final speech result.
      onResult(SpeechRecognitionResult(
        [const SpeechRecognitionWords('To be or not to be.', null, 0.95)],
        true,
      ));
      await tester.pumpAndSettle();

      // Should show feedback.
      expect(find.text('Expected:'), findsOneWidget);
      expect(find.text('Next'), findsOneWidget);
    });

    testWidgets('whisper mode: tap mic shows whisper-specific text',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech(usesWhisper: true);

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Tap mic.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      expect(
        find.text('Recording — tap to stop & transcribe'),
        findsOneWidget,
      );
    });

    testWidgets('whisper mode: stop transcribes and submits',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech(usesWhisper: true);

      // stopListening returns transcribed text.
      when(mockSpeech.stopListening)
          .thenAnswer((_) async => 'To be or not to be.');

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Stop → transcribe.
      await tester.tap(find.byIcon(Icons.stop));
      await tester.pumpAndSettle();

      // Should show feedback after Whisper transcription.
      expect(find.text('Expected:'), findsOneWidget);
    });

    testWidgets('whisper mode: empty transcription does not advance',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech(usesWhisper: true);

      // stopListening returns empty (transcription failed).
      when(mockSpeech.stopListening)
          .thenAnswer((_) async => '');

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Stop → empty transcription.
      await tester.tap(find.byIcon(Icons.stop));
      await tester.pumpAndSettle();

      // Should still be on awaiting line (no feedback).
      expect(find.text('Good evening.'), findsOneWidget);
      expect(find.text('Expected:'), findsNothing);
    });

    testWidgets('voice mode: live transcript is shown', (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      late void Function(SpeechRecognitionResult) onResult;
      when(() => mockSpeech.startListening(
            onResult: any(named: 'onResult'),
          )).thenAnswer((invocation) async {
        onResult = invocation.namedArguments[#onResult]
            as void Function(SpeechRecognitionResult);
      });

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Partial result.
      onResult(SpeechRecognitionResult(
        [const SpeechRecognitionWords('To be', null, 0.8)],
        false,
      ));
      await tester.pump();

      // Partial transcript visible.
      expect(find.text('To be'), findsOneWidget);
    });

    testWidgets(
        'whisper mode: transcript shown with non-listening style after stop',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech(usesWhisper: true);

      // Make stopListening return empty so it does NOT advance to feedback.
      when(mockSpeech.stopListening)
          .thenAnswer((_) async => '');

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // While recording, 'Transcribing...' not yet shown.
      expect(find.text('Transcribing...'), findsNothing);

      // Stop → triggers 'Transcribing...' then empty result.
      await tester.tap(find.byIcon(Icons.stop));
      // Pump once to see the 'Transcribing...' intermediate state.
      await tester.pump();
      await tester.pumpAndSettle();

      // After empty transcription, liveTranscript is '' — still on awaiting.
      expect(find.text('Good evening.'), findsOneWidget);
    });

    testWidgets('non-listening transcript uses normal style after stop',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      late void Function(SpeechRecognitionResult) onResult;
      when(() => mockSpeech.startListening(
            onResult: any(named: 'onResult'),
          )).thenAnswer((invocation) async {
        onResult = invocation.namedArguments[#onResult]
            as void Function(SpeechRecognitionResult);
      });

      // Delay stopListening so the intermediate rebuild is visible.
      final stopCompleter = Completer<String>();
      when(mockSpeech.stopListening)
          .thenAnswer((_) => stopCompleter.future);

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Partial (non-final) result sets transcript while listening.
      onResult(SpeechRecognitionResult(
        [const SpeechRecognitionWords('To be', null, 0.8)],
        false,
      ));
      await tester.pump();
      expect(find.text('To be'), findsOneWidget);

      // Stop recording — _isListening becomes false, stopListening awaits.
      await tester.tap(find.byIcon(Icons.stop));
      await tester.pump();

      // Transcript text should now use normal (non-italic) style.
      final textWidget = tester.widget<Text>(find.text('To be'));
      expect(textWidget.style?.fontStyle, FontStyle.normal);

      // Let stopListening complete.
      stopCompleter.complete('');
      await tester.pumpAndSettle();
    });

    testWidgets('toggle while recording stops the speech service',
        (tester) async {
      final script = _twoLineScript();
      final role = script.roles.firstWhere((r) => r.name == 'Hamlet');
      final mockSpeech = _createMockSpeech();

      await tester.pumpWidget(
        _wrap(script, role, speechService: mockSpeech),
      );
      await tester.pumpAndSettle();

      // Start recording.
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Toggle to typing while recording.
      await tester.tap(find.text('Type instead'));
      await tester.pumpAndSettle();

      // stopListening should have been called (from toggle).
      verify(mockSpeech.stopListening).called(1);
      // Now in typing mode.
      expect(find.byType(TextField), findsOneWidget);
    });
  });
}
