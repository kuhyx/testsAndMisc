import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/rehearsal/rehearsal_cubit.dart';
import 'package:horatio_app/bloc/rehearsal/rehearsal_state.dart';
import 'package:horatio_app/services/speech_service.dart';
import 'package:horatio_app/widgets/grade_badge.dart';
import 'package:horatio_app/widgets/line_diff_widget.dart';
import 'package:horatio_core/horatio_core.dart';

/// Interactive rehearsal screen — actor reads cues and types their lines.
class RehearsalScreen extends StatelessWidget {
  /// Creates a [RehearsalScreen].
  const RehearsalScreen({
    required this.script,
    required this.selectedRole,
    this.speechService,
    super.key,
  });

  /// The script being rehearsed.
  final Script script;

  /// The role the actor is playing.
  final Role selectedRole;

  /// Optional [SpeechService] instance for dependency injection in tests.
  final SpeechService? speechService;

  @override
  Widget build(BuildContext context) => BlocProvider(
        create: (_) => RehearsalCubit(
          script: script,
          selectedRole: selectedRole,
        )..start(),
        child: Scaffold(
          appBar: AppBar(
            title: Text('Rehearsing: ${selectedRole.name}'),
          ),
          body: BlocBuilder<RehearsalCubit, RehearsalState>(
            builder: (context, state) => switch (state) {
              RehearsalInitial() => const Center(
                  child: CircularProgressIndicator(),
                ),
              RehearsalAwaitingLine() => _AwaitingLineView(
                  state: state,
                  speechService: speechService,
                ),
              RehearsalFeedback() => _FeedbackView(state: state),
              RehearsalComplete() => _CompleteView(state: state),
            },
          ),
        ),
      );
}

class _AwaitingLineView extends StatefulWidget {
  const _AwaitingLineView({required this.state, this.speechService});

  final RehearsalAwaitingLine state;
  final SpeechService? speechService;

  @override
  State<_AwaitingLineView> createState() => _AwaitingLineViewState();
}

class _AwaitingLineViewState extends State<_AwaitingLineView> {
  final _controller = TextEditingController();
  late final SpeechService _speechService;
  bool _useTyping = false;
  bool _speechAvailable = false;
  bool _isListening = false;
  String _liveTranscript = '';

  @override
  void initState() {
    super.initState();
    _speechService = widget.speechService ?? SpeechService();
    _initSpeech();
  }

  Future<void> _initSpeech() async {
    final available = await _speechService.initialise();
    if (mounted) {
      setState(() => _speechAvailable = available);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _speechService.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_isListening) {
      setState(() => _isListening = false);
      if (_speechService.usesWhisper) {
        // Whisper: batch transcription after recording stops.
        setState(() => _liveTranscript = 'Transcribing...');
        final text = await _speechService.stopListening();
        if (!mounted) return;
        setState(() => _liveTranscript = text);
        if (text.isNotEmpty) {
          context.read<RehearsalCubit>().submitLine(text);
        }
      } else {
        await _speechService.stopListening();
        _submitTranscript();
      }
    } else {
      setState(() {
        _liveTranscript = '';
        _isListening = true;
      });
      await _speechService.startListening(
        onResult: (result) {
          if (!mounted) return;
          setState(() => _liveTranscript = result.recognizedWords);
          if (result.finalResult) {
            setState(() => _isListening = false);
            _submitTranscript();
          }
        },
      );
    }
  }

  void _submitTranscript() {
    final text = _liveTranscript.trim();
    if (text.isNotEmpty) {
      context.read<RehearsalCubit>().submitLine(text);
    }
  }

  void _submitTyped() {
    final text = _controller.text.trim();
    if (text.isNotEmpty) {
      context.read<RehearsalCubit>().submitLine(text);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ProgressBar(
            current: widget.state.lineIndex,
            total: widget.state.totalLines,
          ),
          const SizedBox(height: 24),
          Text(
            widget.state.cueSpeaker,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: colorScheme.secondary,
                ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                widget.state.cueText,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      fontStyle: FontStyle.italic,
                    ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Your line:',
            style: Theme.of(context).textTheme.labelLarge,
          ),
          const SizedBox(height: 12),
          if (_useTyping || !_speechAvailable)
            ..._buildTypingInput()
          else
            ..._buildVoiceInput(colorScheme),
          const Spacer(),
          if (_speechAvailable)
            Center(
              child: TextButton.icon(
                onPressed: () => setState(() {
                  _useTyping = !_useTyping;
                  if (_isListening) {
                    _speechService.stopListening();
                    _isListening = false;
                  }
                }),
                icon: Icon(_useTyping ? Icons.mic : Icons.keyboard),
                label: Text(
                  _useTyping ? 'Use voice instead' : 'Type instead',
                ),
              ),
            ),
        ],
      ),
    );
  }

  List<Widget> _buildVoiceInput(ColorScheme colorScheme) => [
        if (_liveTranscript.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _liveTranscript == 'Transcribing...'
                ? const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: 8),
                      Text('Transcribing...'),
                    ],
                  )
                : Text(
                    _liveTranscript,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: _isListening
                              ? colorScheme.onSurfaceVariant
                              : colorScheme.onSurface,
                          fontStyle: _isListening
                              ? FontStyle.italic
                              : FontStyle.normal,
                        ),
                  ),
          ),
        Center(
          child: GestureDetector(
            onTap: _toggleRecording,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: _isListening ? 100 : 88,
              height: _isListening ? 100 : 88,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _isListening
                    ? colorScheme.error
                    : colorScheme.primary,
                boxShadow: _isListening
                    ? [
                        BoxShadow(
                          color: colorScheme.error.withValues(alpha: 0.4),
                          blurRadius: 24,
                          spreadRadius: 4,
                        ),
                      ]
                    : [],
              ),
              child: Icon(
                _isListening ? Icons.stop : Icons.mic,
                size: 40,
                color: colorScheme.onPrimary,
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: Text(
            _isListening
                ? (_speechService.usesWhisper
                    ? 'Recording — tap to stop & transcribe'
                    : 'Listening — tap to stop')
                : 'Tap to speak your line',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
          ),
        ),
      ];

  List<Widget> _buildTypingInput() => [
        TextField(
          controller: _controller,
          decoration: const InputDecoration(
            hintText: 'Type your line here...',
          ),
          maxLines: 3,
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => _submitTyped(),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton(
            onPressed: _submitTyped,
            child: const Text('Check'),
          ),
        ),
      ];
}

class _FeedbackView extends StatelessWidget {
  const _FeedbackView({required this.state});

  final RehearsalFeedback state;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _ProgressBar(
              current: state.lineIndex,
              total: state.totalLines,
            ),
            const SizedBox(height: 16),
            Center(child: GradeBadge(grade: state.grade)),
            const SizedBox(height: 16),
            Text(
              'Expected:',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 4),
            Text(
              state.expectedLine,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            Text(
              'Your version:',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 4),
            LineDiffWidget(segments: state.diffSegments),
            const Spacer(),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                onPressed: () =>
                    context.read<RehearsalCubit>().nextLine(),
                child: const Text('Next'),
              ),
            ),
          ],
        ),
      );
}

class _CompleteView extends StatelessWidget {
  const _CompleteView({required this.state});

  final RehearsalComplete state;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.celebration, size: 64, color: Colors.amber),
              const SizedBox(height: 16),
              Text(
                'Rehearsal Complete!',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 24),
              _ResultRow(label: 'Perfect', count: state.exactCount, color: Colors.green),
              _ResultRow(label: 'Close', count: state.minorCount, color: Colors.orange),
              _ResultRow(label: 'Needs work', count: state.majorCount, color: Colors.deepOrange),
              _ResultRow(label: 'Missed', count: state.missedCount, color: Colors.red),
              const SizedBox(height: 32),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Done'),
              ),
            ],
          ),
        ),
      );
}

class _ResultRow extends StatelessWidget {
  const _ResultRow({
    required this.label,
    required this.count,
    required this.color,
  });

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.circle, size: 12, color: color),
            const SizedBox(width: 8),
            SizedBox(
              width: 100,
              child: Text(label),
            ),
            Text(
              '$count',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      );
}

class _ProgressBar extends StatelessWidget {
  const _ProgressBar({required this.current, required this.total});

  final int current;
  final int total;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Line ${current + 1} of $total'),
              Text('${((current + 1) / total * 100).toStringAsFixed(0)}%'),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: (current + 1) / total,
          ),
        ],
      );
}
