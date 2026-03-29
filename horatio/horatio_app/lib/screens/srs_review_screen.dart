import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_state.dart';
import 'package:horatio_core/horatio_core.dart';

/// SRS flashcard review screen.
class SrsReviewScreen extends StatelessWidget {
  /// Creates an [SrsReviewScreen].
  const SrsReviewScreen({required this.cards, super.key});

  /// The cards to review in this session.
  final List<SrsCard> cards;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Review Cards'),
        ),
        body: BlocBuilder<SrsReviewCubit, SrsReviewState>(
          builder: (context, state) => switch (state) {
            SrsReviewIdle() => const Center(
                child: Text('No review session active.'),
              ),
            SrsReviewInProgress() => _ReviewCardView(state: state),
            SrsReviewDone() => _ReviewDoneView(state: state),
          },
        ),
      );
}

class _ReviewCardView extends StatelessWidget {
  const _ReviewCardView({required this.state});

  final SrsReviewInProgress state;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Progress indicator.
            LinearProgressIndicator(
              value: (state.cardIndex + 1) / state.totalCards,
            ),
            const SizedBox(height: 8),
            Text(
              'Card ${state.cardIndex + 1} of ${state.totalCards}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const Spacer(),
            // Cue text.
            Card(
              child: SizedBox(
                width: double.infinity,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    children: [
                      Text(
                        'CUE',
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        state.card.cueText,
                        style:
                            Theme.of(context).textTheme.bodyLarge?.copyWith(
                                  fontStyle: FontStyle.italic,
                                ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            // Answer (hidden or revealed).
            if (state.showingAnswer) ...[
              Card(
                color: Theme.of(context)
                    .colorScheme
                    .primaryContainer
                    .withValues(alpha: 0.3),
                child: SizedBox(
                  width: double.infinity,
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        Text(
                          'YOUR LINE',
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          state.card.answerText,
                          style: Theme.of(context).textTheme.bodyLarge,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              _GradeButtons(),
            ] else ...[
              FilledButton(
                onPressed: () =>
                    context.read<SrsReviewCubit>().showAnswer(),
                child: const Text('Show Answer'),
              ),
            ],
            const Spacer(),
          ],
        ),
      );
}

class _GradeButtons extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 8,
        runSpacing: 8,
        alignment: WrapAlignment.center,
        children: [
          _gradeButton(
            context,
            label: 'Again',
            quality: ReviewQuality.blackout,
            color: Colors.red,
          ),
          _gradeButton(
            context,
            label: 'Hard',
            quality: ReviewQuality.correctDifficult,
            color: Colors.orange,
          ),
          _gradeButton(
            context,
            label: 'Good',
            quality: ReviewQuality.correctHesitation,
            color: Colors.blue,
          ),
          _gradeButton(
            context,
            label: 'Easy',
            quality: ReviewQuality.perfect,
            color: Colors.green,
          ),
        ],
      );

  Widget _gradeButton(
    BuildContext context, {
    required String label,
    required ReviewQuality quality,
    required Color color,
  }) =>
      OutlinedButton(
        onPressed: () => context.read<SrsReviewCubit>().gradeCard(quality),
        style: OutlinedButton.styleFrom(
          foregroundColor: color,
          side: BorderSide(color: color),
        ),
        child: Text(label),
      );
}

class _ReviewDoneView extends StatelessWidget {
  const _ReviewDoneView({required this.state});

  final SrsReviewDone state;

  @override
  Widget build(BuildContext context) {
    final accuracy = state.totalReviewed > 0
        ? (state.correctCount / state.totalReviewed * 100).toStringAsFixed(0)
        : '0';

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, size: 64, color: Colors.green),
            const SizedBox(height: 16),
            Text(
              'Review Complete!',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            Text(
              '${state.correctCount}/${state.totalReviewed} correct ($accuracy%)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
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
}
